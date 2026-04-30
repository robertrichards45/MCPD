import os
from datetime import datetime, timezone

from flask import Blueprint, render_template, request, redirect, url_for, abort, current_app, send_file
from flask_login import login_required, current_user

from ..extensions import db
from ..models import (
    ReconstructionCase,
    ReconstructionVehicle,
    ReconstructionMeasurement,
    ReconstructionAttachment,
    AuditLog,
)
from ..services.reconstruction_packet import build_reconstruction_packet_pdf


bp = Blueprint("reconstruction", __name__)


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _diagram_json_path(case_id):
    return os.path.join(_case_dir(case_id), "diagram.json")

def _diagram_png_name(case_id):
    return f"case-{case_id}-diagram.png"


def _case_dir(case_id):
    # Keep all reconstruction artifacts in a stable on-disk folder for easy backups.
    root = os.path.join(current_app.config["UPLOAD_ROOT"], "reconstruction", str(case_id))
    os.makedirs(root, exist_ok=True)
    return root


def _get_case_or_404(case_id):
    return ReconstructionCase.query.get_or_404(case_id)


@bp.route("/reconstruction", methods=["GET", "POST"])
@login_required
def case_list():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip() or "Untitled Reconstruction"
        incident_date = (request.form.get("incident_date") or "").strip() or None
        location = (request.form.get("location") or "").strip() or None
        row = ReconstructionCase(
            title=title,
            incident_date=incident_date,
            location=location,
            created_by=current_user.id,
            updated_at=_utcnow_naive(),
        )
        db.session.add(row)
        db.session.add(AuditLog(actor_id=current_user.id, action="recon_case_create", details=title))
        db.session.commit()
        return redirect(url_for("reconstruction.case_detail", case_id=row.id))

    q = (request.args.get("q") or "").strip()
    cases = ReconstructionCase.query.order_by(ReconstructionCase.updated_at.desc()).all()
    if q:
        ql = q.lower()
        cases = [c for c in cases if ql in (c.title or "").lower() or ql in (c.location or "").lower() or ql in str(c.id)]
    return render_template("reconstruction_list.html", user=current_user, cases=cases, q=q)


@bp.route("/reconstruction/<int:case_id>")
@login_required
def case_detail(case_id):
    row = _get_case_or_404(case_id)
    vehicles = ReconstructionVehicle.query.filter_by(case_id=row.id).order_by(ReconstructionVehicle.id.asc()).all()
    measurements = ReconstructionMeasurement.query.filter_by(case_id=row.id).order_by(ReconstructionMeasurement.id.desc()).all()
    attachments = ReconstructionAttachment.query.filter_by(case_id=row.id).order_by(ReconstructionAttachment.uploaded_at.desc()).all()
    return render_template(
        "reconstruction_case.html",
        user=current_user,
        case=row,
        vehicles=vehicles,
        measurements=measurements,
        attachments=attachments,
    )


@bp.route("/reconstruction/<int:case_id>/update", methods=["POST"])
@login_required
def case_update(case_id):
    row = _get_case_or_404(case_id)
    row.title = (request.form.get("title") or "").strip() or row.title
    row.incident_date = (request.form.get("incident_date") or "").strip() or None
    row.location = (request.form.get("location") or "").strip() or None
    row.updated_at = _utcnow_naive()
    db.session.add(row)
    db.session.add(AuditLog(actor_id=current_user.id, action="recon_case_update", details=str(row.id)))
    db.session.commit()
    return redirect(url_for("reconstruction.case_detail", case_id=row.id))


@bp.route("/reconstruction/<int:case_id>/add-vehicle", methods=["POST"])
@login_required
def add_vehicle(case_id):
    row = _get_case_or_404(case_id)
    v = ReconstructionVehicle(
        case_id=row.id,
        unit=(request.form.get("unit") or "").strip() or None,
        make_model=(request.form.get("make_model") or "").strip() or None,
        direction=(request.form.get("direction") or "").strip() or None,
        notes=(request.form.get("notes") or "").strip() or None,
    )
    row.updated_at = _utcnow_naive()
    db.session.add(v)
    db.session.add(row)
    db.session.commit()
    return redirect(url_for("reconstruction.case_detail", case_id=row.id))


@bp.route("/reconstruction/<int:case_id>/add-measurement", methods=["POST"])
@login_required
def add_measurement(case_id):
    row = _get_case_or_404(case_id)
    label = (request.form.get("label") or "").strip()
    if not label:
        return redirect(url_for("reconstruction.case_detail", case_id=row.id))
    m = ReconstructionMeasurement(
        case_id=row.id,
        label=label,
        value=(request.form.get("value") or "").strip() or None,
        units=(request.form.get("units") or "").strip() or None,
        notes=(request.form.get("notes") or "").strip() or None,
    )
    row.updated_at = _utcnow_naive()
    db.session.add(m)
    db.session.add(row)
    db.session.commit()
    return redirect(url_for("reconstruction.case_detail", case_id=row.id))


@bp.route("/reconstruction/<int:case_id>/upload", methods=["POST"])
@login_required
def upload(case_id):
    row = _get_case_or_404(case_id)
    f = request.files.get("file")
    kind = (request.form.get("kind") or "").strip() or None
    if not f:
        return redirect(url_for("reconstruction.case_detail", case_id=row.id))

    base = _case_dir(row.id)
    ts = int(_utcnow_naive().timestamp())
    safe_name = (f.filename or "upload").replace("\\", "_").replace("/", "_")
    out_name = f"case-{row.id}-{ts}-{safe_name}"
    out_path = os.path.join(base, out_name)
    f.save(out_path)

    att = ReconstructionAttachment(case_id=row.id, file_path=out_path, kind=kind, uploaded_by=current_user.id)
    row.updated_at = _utcnow_naive()
    db.session.add(att)
    db.session.add(row)
    db.session.add(AuditLog(actor_id=current_user.id, action="recon_upload", details=f"{row.id}:{kind or ''}:{safe_name}"))
    db.session.commit()
    return redirect(url_for("reconstruction.case_detail", case_id=row.id))


@bp.route("/reconstruction/<int:case_id>/file/<int:att_id>")
@login_required
def download_attachment(case_id, att_id):
    row = _get_case_or_404(case_id)
    att = ReconstructionAttachment.query.get_or_404(att_id)
    if att.case_id != row.id:
        abort(404)
    return send_file(att.file_path, as_attachment=True, download_name=os.path.basename(att.file_path))


@bp.route("/reconstruction/<int:case_id>/packet.pdf")
@login_required
def packet_pdf(case_id):
    row = _get_case_or_404(case_id)
    vehicles = ReconstructionVehicle.query.filter_by(case_id=row.id).order_by(ReconstructionVehicle.id.asc()).all()
    measurements = ReconstructionMeasurement.query.filter_by(case_id=row.id).order_by(ReconstructionMeasurement.id.desc()).all()
    attachments = ReconstructionAttachment.query.filter_by(case_id=row.id).order_by(ReconstructionAttachment.uploaded_at.desc()).all()

    # Prefer a user-uploaded diagram attachment (kind=diagram) with a common image extension.
    diagram_path = None
    for a in attachments:
        if (a.kind or "").lower() == "diagram":
            ext = os.path.splitext(a.file_path)[1].lower()
            if ext in [".png", ".jpg", ".jpeg"]:
                diagram_path = a.file_path
                break

    out_dir = os.path.join(_case_dir(row.id), "exports")
    out_path = os.path.join(out_dir, f"reconstruction-case-{row.id}-packet.pdf")
    build_reconstruction_packet_pdf(out_path, row, vehicles, measurements, attachments, diagram_path=diagram_path)
    return send_file(out_path, as_attachment=True, download_name=os.path.basename(out_path))


@bp.route("/reconstruction/<int:case_id>/diagram.json", methods=["GET"])
@login_required
def diagram_get(case_id):
    _get_case_or_404(case_id)
    path = _diagram_json_path(case_id)
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="application/json", as_attachment=False, download_name="diagram.json")


@bp.route("/reconstruction/<int:case_id>/diagram.json", methods=["POST"])
@login_required
def diagram_save(case_id):
    row = _get_case_or_404(case_id)
    payload = request.get_json(silent=True)
    if payload is None:
        abort(400)
    path = _diagram_json_path(row.id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        import json
        json.dump(payload, f, indent=2)
    row.updated_at = _utcnow_naive()
    db.session.add(row)
    db.session.add(AuditLog(actor_id=current_user.id, action="recon_diagram_save", details=str(row.id)))
    db.session.commit()
    return {"ok": True}
