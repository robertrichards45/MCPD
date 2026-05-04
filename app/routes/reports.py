import os
import json
from datetime import datetime, timezone
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, abort, current_app, flash, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy import func
from werkzeug.utils import secure_filename
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from ..extensions import db
from ..models import (
    AccidentReconstruction,
    CleoReport,
    IncidentDraft,
    ReconstructionMeasurement,
    ReconstructionMedia,
    ReconstructionObject,
    ReconstructionTimelineItem,
    ReconstructionVehicle,
    Report,
    ReportAttachment,
    ReportPerson,
    ReportCoAuthor,
    ReportGrade,
    User,
    AuditLog,
)
from ..permissions import can_manage_site, can_manage_team, can_view_user, can_grade_cleoc_reports

bp = Blueprint('reports', __name__)
REVIEWABLE_CLEO_STATUSES = ('SUBMITTED', 'RETURNED', 'GRADED')


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_or_404(model, object_id):
    obj = db.session.get(model, object_id)
    if obj is None:
        abort(404)
    return obj


def _is_test_report_title(title: str) -> bool:
    return str(title or '').strip().lower().startswith(('stress report', 'test report ', 'mock stress report'))


def _report_query():
    return Report.query.filter(
        ~Report.title.ilike('Stress Report%'),
        ~Report.title.ilike('Test Report %'),
        ~Report.title.ilike('Mock Stress Report%'),
    )


def require_admin():
    if not can_manage_site(current_user):
        abort(403)


def _visible_user_ids():
    if can_manage_site(current_user):
        return [u.id for u in User.query.filter_by(active=True).all()]
    if can_manage_team(current_user):
        return [u.id for u in User.query.filter_by(active=True).all() if can_view_user(current_user, u)]
    return [current_user.id]


def _can_view_reconstruction(row):
    if can_manage_site(current_user) or can_manage_team(current_user):
        return True
    return row.officer_id == current_user.id


def _can_edit_reconstruction(row):
    if can_manage_site(current_user) or can_manage_team(current_user):
        return True
    return row.officer_id == current_user.id


def _get_reconstruction_or_404(reconstruction_id):
    row = db.session.get(AccidentReconstruction, reconstruction_id)
    if row is None:
        abort(404)
    if not _can_view_reconstruction(row):
        abort(403)
    return row


def _parse_datetime_local(value):
    raw = str(value or '').strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _float_or_none(value):
    try:
        if value is None or str(value).strip() == '':
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _reconstruction_payload(row):
    vehicles = ReconstructionVehicle.query.filter_by(reconstruction_id=row.id).order_by(ReconstructionVehicle.id.asc()).all()
    objects = ReconstructionObject.query.filter_by(reconstruction_id=row.id).order_by(ReconstructionObject.id.asc()).all()
    measurements = ReconstructionMeasurement.query.filter_by(reconstruction_id=row.id).order_by(ReconstructionMeasurement.id.asc()).all()
    media = ReconstructionMedia.query.filter_by(reconstruction_id=row.id).order_by(ReconstructionMedia.timestamp.desc()).all()
    timeline = ReconstructionTimelineItem.query.filter_by(reconstruction_id=row.id).order_by(ReconstructionTimelineItem.id.asc()).all()
    diagram = {}
    if row.diagram_data_json:
        try:
            diagram = json.loads(row.diagram_data_json)
        except (TypeError, ValueError):
            diagram = {}
    return {
        'vehicles': vehicles,
        'objects': objects,
        'measurements': measurements,
        'media': media,
        'timeline': timeline,
        'diagram': diagram,
    }


def _build_reconstruction_pdf(row):
    payload = _reconstruction_payload(row)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 0.72 * inch

    def line(text, size=10, bold=False, gap=0.18):
        nonlocal y
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', size)
        c.drawString(0.72 * inch, y, str(text or ''))
        y -= gap * inch

    c.setFillColor(colors.HexColor('#0b1b2d'))
    c.rect(0, height - 0.5 * inch, width, 0.5 * inch, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 13)
    c.drawString(0.72 * inch, height - 0.32 * inch, 'MCPD ACCIDENT RECONSTRUCTION REPORT')
    c.setFillColor(colors.black)
    line(f'Reconstruction #{row.incident_number or row.id}: {row.title}', 15, True, 0.28)
    line(f'Location: {row.location or "Not recorded"}')
    line(f'Date / Time: {row.date_time.strftime("%Y-%m-%d %H:%M") if row.date_time else "Not recorded"}')
    line(f'Investigating Officer: {row.officer.display_name if row.officer else "Not recorded"}')
    line(f'Weather: {row.weather or "Not recorded"}    Road Surface: {row.road_surface or "Not recorded"}')
    y -= 0.08 * inch
    line('Vehicles Involved', 12, True, 0.24)
    if payload['vehicles']:
        for vehicle in payload['vehicles']:
            line(f'{vehicle.label or vehicle.unit or "Vehicle"} | {vehicle.type or vehicle.make_model or "type not set"} | Direction: {vehicle.direction or "n/a"} | Impact Speed: {vehicle.impact_speed or "n/a"}')
            if vehicle.damage_notes or vehicle.notes:
                line(f'  Notes: {vehicle.damage_notes or vehicle.notes}', 9)
    else:
        line('No vehicles recorded.')
    y -= 0.08 * inch
    line('Measurements', 12, True, 0.24)
    if payload['measurements']:
        for measurement in payload['measurements']:
            line(f'{measurement.label}: {measurement.value or "n/a"} {measurement.units or ""} ({measurement.measurement_type or "measurement"})')
    else:
        line('No measurements recorded.')
    y -= 0.08 * inch
    line('Timeline', 12, True, 0.24)
    if payload['timeline']:
        for item in payload['timeline']:
            line(f'{item.event_time or "--"} | {item.event_type or "Event"} | {item.description}')
            if y < 1.2 * inch:
                c.showPage()
                y = height - 0.72 * inch
    else:
        line('No timeline events recorded.')
    y -= 0.08 * inch
    line('Evidence / Media', 12, True, 0.24)
    if payload['media']:
        for item in payload['media']:
            line(f'{item.file_name} | {item.media_type or "media"} | {item.description or ""}')
    else:
        line('No media items recorded.')
    y -= 0.08 * inch
    line('Reconstruction Notes / Conclusion', 12, True, 0.24)
    notes = row.notes or 'No reconstruction conclusion entered.'
    for chunk in [notes[i:i + 95] for i in range(0, len(notes), 95)]:
        line(chunk, 10)
    y -= 0.08 * inch
    c.setFillColor(colors.HexColor('#6b7280'))
    line('Calculations are estimates and must be verified by trained personnel.', 9)
    c.save()
    buffer.seek(0)
    return buffer


@bp.route('/reports')
@login_required
def list_reports():
    visible_ids = _visible_user_ids()
    reports = (
        _report_query()
        .filter(Report.owner_id.in_(visible_ids))
        .order_by(Report.updated_at.desc())
        .all()
    )
    cleo_reports = (
        CleoReport.query
        .filter(CleoReport.user_id.in_(visible_ids))
        .order_by(CleoReport.updated_at.desc())
        .all()
    )
    cleo_review_reports = []
    if can_manage_site(current_user) or can_manage_team(current_user) or can_grade_cleoc_reports(current_user):
        cleo_review_reports = (
            CleoReport.query
            .filter(
                CleoReport.user_id.in_(visible_ids),
                CleoReport.status.in_(REVIEWABLE_CLEO_STATUSES),
            )
            .order_by(CleoReport.updated_at.desc())
            .all()
        )
    active_incident_draft = (
        IncidentDraft.query
        .filter_by(officer_user_id=current_user.id, status='ACTIVE')
        .order_by(IncidentDraft.updated_at.desc())
        .first()
    )
    return render_template(
        'reports_list.html',
        reports=reports,
        cleo_reports=cleo_reports,
        cleo_review_reports=cleo_review_reports,
        active_incident_draft=active_incident_draft,
        report_count=len(reports),
        cleo_count=len(cleo_reports),
        cleo_review_count=len(cleo_review_reports),
        user=current_user,
    )


@bp.route('/reports/accident-reconstruction')
@login_required
def accident_reconstruction_list():
    visible_ids = _visible_user_ids()
    rows = (
        AccidentReconstruction.query
        .filter(AccidentReconstruction.officer_id.in_(visible_ids))
        .order_by(AccidentReconstruction.updated_at.desc())
        .all()
    )
    return render_template('accident_reconstruction_list.html', rows=rows, user=current_user)


@bp.route('/reports/accident-reconstruction/new', methods=['GET', 'POST'])
@login_required
def accident_reconstruction_new():
    if request.method == 'POST':
        title = (request.form.get('title') or '').strip() or 'Untitled Accident Reconstruction'
        row = AccidentReconstruction(
            incident_number=(request.form.get('incident_number') or '').strip() or None,
            title=title,
            location=(request.form.get('location') or '').strip() or None,
            date_time=_parse_datetime_local(request.form.get('date_time')),
            report_id=request.form.get('report_id', type=int),
            weather=(request.form.get('weather') or '').strip() or None,
            road_surface=(request.form.get('road_surface') or '').strip() or None,
            notes=(request.form.get('notes') or '').strip() or None,
            officer_id=current_user.id,
        )
        db.session.add(row)
        db.session.add(AuditLog(actor_id=current_user.id, action='accident_reconstruction_create', details=title[:120]))
        db.session.commit()
        return redirect(url_for('reports.accident_reconstruction_detail', reconstruction_id=row.id))
    return render_template('accident_reconstruction_new.html', user=current_user)


@bp.route('/reports/<int:report_id>/scene-diagram')
@login_required
def report_scene_diagram(report_id):
    report = _get_or_404(Report, report_id)
    owner = _get_or_404(User, report.owner_id)
    if not can_view_user(current_user, owner):
        abort(403)
    row = (
        AccidentReconstruction.query
        .filter_by(report_id=report.id)
        .order_by(AccidentReconstruction.updated_at.desc())
        .first()
    )
    if row is None:
        row = AccidentReconstruction(
            report_id=report.id,
            incident_number=f'RPT-{report.id}',
            title=report.title or f'Report #{report.id} accident reconstruction',
            officer_id=current_user.id,
            status='DRAFT',
        )
        db.session.add(row)
        db.session.add(AuditLog(actor_id=current_user.id, action='accident_reconstruction_from_report', details=str(report.id)))
        db.session.commit()
    return redirect(url_for('reports.accident_reconstruction_diagram', reconstruction_id=row.id))


@bp.route('/reports/accident-reconstruction/<int:reconstruction_id>', methods=['GET', 'POST'])
@login_required
def accident_reconstruction_detail(reconstruction_id):
    row = _get_reconstruction_or_404(reconstruction_id)
    if request.method == 'POST':
        if not _can_edit_reconstruction(row):
            abort(403)
        row.incident_number = (request.form.get('incident_number') or '').strip() or None
        row.title = (request.form.get('title') or '').strip() or row.title
        row.location = (request.form.get('location') or '').strip() or None
        row.date_time = _parse_datetime_local(request.form.get('date_time'))
        row.weather = (request.form.get('weather') or '').strip() or None
        row.road_surface = (request.form.get('road_surface') or '').strip() or None
        row.notes = (request.form.get('notes') or '').strip() or None
        row.updated_at = _utcnow_naive()
        db.session.add(row)
        db.session.add(AuditLog(actor_id=current_user.id, action='accident_reconstruction_update', details=str(row.id)))
        db.session.commit()
        flash('Accident reconstruction saved.', 'success')
        return redirect(url_for('reports.accident_reconstruction_detail', reconstruction_id=row.id))
    return render_template(
        'accident_reconstruction_detail.html',
        reconstruction=row,
        can_edit=_can_edit_reconstruction(row),
        **_reconstruction_payload(row),
        user=current_user,
    )


@bp.route('/reports/accident-reconstruction/<int:reconstruction_id>/diagram', methods=['GET', 'POST'])
@login_required
def accident_reconstruction_diagram(reconstruction_id):
    row = _get_reconstruction_or_404(reconstruction_id)
    if request.method == 'POST':
        if not _can_edit_reconstruction(row):
            abort(403)
        payload = request.get_json(silent=True) or {}
        row.diagram_data_json = json.dumps(payload)
        row.updated_at = _utcnow_naive()

        for item in payload.get('vehicles', []):
            vehicle_id = item.get('id')
            vehicle = db.session.get(ReconstructionVehicle, vehicle_id) if vehicle_id else None
            if vehicle and vehicle.reconstruction_id == row.id:
                vehicle.x_position = _float_or_none(item.get('x')) or vehicle.x_position
                vehicle.y_position = _float_or_none(item.get('y')) or vehicle.y_position
                vehicle.rotation = _float_or_none(item.get('rotation')) or 0
                vehicle.label = str(item.get('label') or vehicle.label or '').strip() or vehicle.label

        for item in payload.get('objects', []):
            object_id = item.get('id')
            obj = db.session.get(ReconstructionObject, object_id) if object_id else None
            if obj and obj.reconstruction_id == row.id:
                obj.x_position = _float_or_none(item.get('x')) or obj.x_position
                obj.y_position = _float_or_none(item.get('y')) or obj.y_position
                obj.rotation = _float_or_none(item.get('rotation')) or 0
                obj.label = str(item.get('label') or obj.label or '').strip() or obj.label

        db.session.add(row)
        db.session.add(AuditLog(actor_id=current_user.id, action='accident_reconstruction_diagram_save', details=str(row.id)))
        db.session.commit()
        return jsonify({'ok': True})
    return render_template(
        'accident_reconstruction_diagram.html',
        reconstruction=row,
        can_edit=_can_edit_reconstruction(row),
        **_reconstruction_payload(row),
        user=current_user,
    )


@bp.route('/reports/accident-reconstruction/<int:reconstruction_id>/vehicle', methods=['POST'])
@login_required
def accident_reconstruction_add_vehicle(reconstruction_id):
    row = _get_reconstruction_or_404(reconstruction_id)
    if not _can_edit_reconstruction(row):
        abort(403)
    count = ReconstructionVehicle.query.filter_by(reconstruction_id=row.id).count() + 1
    vehicle = ReconstructionVehicle(
        reconstruction_id=row.id,
        label=(request.form.get('label') or '').strip() or f'V{count}',
        type=(request.form.get('type') or '').strip() or 'Sedan',
        direction=(request.form.get('direction') or '').strip() or None,
        pre_crash_speed=_float_or_none(request.form.get('pre_crash_speed')),
        impact_speed=_float_or_none(request.form.get('impact_speed')),
        post_crash_speed=_float_or_none(request.form.get('post_crash_speed')),
        x_position=_float_or_none(request.form.get('x_position')) or (180 + count * 40),
        y_position=_float_or_none(request.form.get('y_position')) or (180 + count * 24),
        rotation=_float_or_none(request.form.get('rotation')) or 0,
        driver=(request.form.get('driver') or '').strip() or None,
        damage_notes=(request.form.get('damage_notes') or '').strip() or None,
        notes=(request.form.get('notes') or '').strip() or None,
    )
    row.updated_at = _utcnow_naive()
    db.session.add(vehicle)
    db.session.add(row)
    db.session.commit()
    return redirect(url_for('reports.accident_reconstruction_detail', reconstruction_id=row.id))


@bp.route('/reports/accident-reconstruction/<int:reconstruction_id>/object', methods=['POST'])
@login_required
def accident_reconstruction_add_object(reconstruction_id):
    row = _get_reconstruction_or_404(reconstruction_id)
    if not _can_edit_reconstruction(row):
        abort(403)
    count = ReconstructionObject.query.filter_by(reconstruction_id=row.id).count() + 1
    obj = ReconstructionObject(
        reconstruction_id=row.id,
        object_type=(request.form.get('object_type') or '').strip() or 'object',
        label=(request.form.get('label') or '').strip() or f'O{count}',
        x_position=_float_or_none(request.form.get('x_position')) or 260,
        y_position=_float_or_none(request.form.get('y_position')) or 220,
        rotation=_float_or_none(request.form.get('rotation')) or 0,
        notes=(request.form.get('notes') or '').strip() or None,
    )
    row.updated_at = _utcnow_naive()
    db.session.add(obj)
    db.session.add(row)
    db.session.commit()
    return redirect(url_for('reports.accident_reconstruction_detail', reconstruction_id=row.id))


@bp.route('/reports/accident-reconstruction/<int:reconstruction_id>/measurement', methods=['POST'])
@login_required
def accident_reconstruction_add_measurement(reconstruction_id):
    row = _get_reconstruction_or_404(reconstruction_id)
    if not _can_edit_reconstruction(row):
        abort(403)
    measurement = ReconstructionMeasurement(
        reconstruction_id=row.id,
        measurement_type=(request.form.get('measurement_type') or '').strip() or 'distance',
        label=(request.form.get('label') or '').strip() or 'Measurement',
        value=(request.form.get('value') or '').strip() or None,
        units=(request.form.get('units') or '').strip() or 'ft',
        start_x=_float_or_none(request.form.get('start_x')),
        start_y=_float_or_none(request.form.get('start_y')),
        end_x=_float_or_none(request.form.get('end_x')),
        end_y=_float_or_none(request.form.get('end_y')),
        notes=(request.form.get('notes') or '').strip() or None,
    )
    row.updated_at = _utcnow_naive()
    db.session.add(measurement)
    db.session.add(row)
    db.session.commit()
    return redirect(url_for('reports.accident_reconstruction_detail', reconstruction_id=row.id))


@bp.route('/reports/accident-reconstruction/<int:reconstruction_id>/media', methods=['POST'])
@login_required
def accident_reconstruction_add_media(reconstruction_id):
    row = _get_reconstruction_or_404(reconstruction_id)
    if not _can_edit_reconstruction(row):
        abort(403)
    upload = request.files.get('file')
    if not upload or not upload.filename:
        flash('Select a media file first.', 'error')
        return redirect(url_for('reports.accident_reconstruction_detail', reconstruction_id=row.id))
    save_root = os.path.join(current_app.config['UPLOAD_ROOT'], 'accident_reconstruction', str(row.id))
    os.makedirs(save_root, exist_ok=True)
    safe_name = secure_filename(upload.filename) or 'media-upload'
    file_name = f"{int(_utcnow_naive().timestamp())}-{safe_name}"
    file_path = os.path.join(save_root, file_name)
    upload.save(file_path)
    item = ReconstructionMedia(
        reconstruction_id=row.id,
        file_path=file_path,
        file_name=safe_name,
        media_type=(request.form.get('media_type') or '').strip() or 'photo',
        description=(request.form.get('description') or '').strip() or None,
        uploaded_by=current_user.id,
        linked_x=_float_or_none(request.form.get('linked_x')),
        linked_y=_float_or_none(request.form.get('linked_y')),
    )
    row.updated_at = _utcnow_naive()
    db.session.add(item)
    db.session.add(row)
    db.session.commit()
    return redirect(url_for('reports.accident_reconstruction_detail', reconstruction_id=row.id))


@bp.route('/reports/accident-reconstruction/<int:reconstruction_id>/timeline', methods=['POST'])
@login_required
def accident_reconstruction_add_timeline(reconstruction_id):
    row = _get_reconstruction_or_404(reconstruction_id)
    if not _can_edit_reconstruction(row):
        abort(403)
    description = (request.form.get('description') or '').strip()
    if not description:
        flash('Timeline description is required.', 'error')
        return redirect(url_for('reports.accident_reconstruction_detail', reconstruction_id=row.id))
    item = ReconstructionTimelineItem(
        reconstruction_id=row.id,
        event_time=(request.form.get('event_time') or '').strip() or None,
        event_type=(request.form.get('event_type') or '').strip() or 'Event',
        description=description,
        linked_vehicle_id=request.form.get('linked_vehicle_id', type=int),
        linked_media_id=request.form.get('linked_media_id', type=int),
    )
    row.updated_at = _utcnow_naive()
    db.session.add(item)
    db.session.add(row)
    db.session.commit()
    return redirect(url_for('reports.accident_reconstruction_detail', reconstruction_id=row.id))


@bp.route('/reports/accident-reconstruction/<int:reconstruction_id>/export')
@login_required
def accident_reconstruction_export(reconstruction_id):
    row = _get_reconstruction_or_404(reconstruction_id)
    pdf = _build_reconstruction_pdf(row)
    file_name = f'accident-reconstruction-{row.incident_number or row.id}.pdf'.replace(' ', '-')
    return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name=file_name)


@bp.route('/reports/new', methods=['GET', 'POST'])
@login_required
def new_report():
    if request.method == 'POST':
        title = request.form.get('title') or 'Untitled Report'
        if _is_test_report_title(title) and not current_app.config.get('TESTING'):
            flash('Automated stress/test reports are disabled outside the test runner.', 'error')
            db.session.add(AuditLog(actor_id=current_user.id, action='report_test_create_blocked', details=title[:120]))
            db.session.commit()
            return redirect(url_for('reports.list_reports'))
        r = Report(title=title, owner_id=current_user.id, status='DRAFT')
        db.session.add(r)
        db.session.commit()
        return redirect(url_for('reports.report_detail', report_id=r.id))
    return render_template('reports_new.html', user=current_user)


@bp.route('/reports/<int:report_id>')
@login_required
def report_detail(report_id):
    r = _get_or_404(Report, report_id)
    owner = _get_or_404(User, r.owner_id)
    if not can_view_user(current_user, owner):
        abort(403)
    attachments = ReportAttachment.query.filter_by(report_id=r.id).all()
    persons = ReportPerson.query.filter_by(report_id=r.id).all()
    coauthors = ReportCoAuthor.query.filter_by(report_id=r.id).all()
    grades = ReportGrade.query.filter_by(report_id=r.id).order_by(ReportGrade.graded_at.desc()).all()
    accident_reconstructions = AccidentReconstruction.query.filter_by(report_id=r.id).order_by(AccidentReconstruction.updated_at.desc()).all()
    users = {u.id: u for u in User.query.all()}
    return render_template(
        'reports_detail.html',
        report=r,
        report_owner=owner,
        attachments=attachments,
        persons=persons,
        coauthors=coauthors,
        grades=grades,
        accident_reconstructions=accident_reconstructions,
        users=users,
        user=current_user,
    )


@bp.route('/reports/<int:report_id>/upload', methods=['POST'])
@login_required
def report_upload(report_id):
    r = _get_or_404(Report, report_id)
    if r.owner_id != current_user.id:
        abort(403)
    file = request.files.get('file')
    page_key = request.form.get('page_key') or 'unknown'
    if not file:
        return redirect(url_for('reports.report_detail', report_id=r.id))
    save_dir = os.path.join(current_app.config['UPLOAD_ROOT'], 'reports')
    os.makedirs(save_dir, exist_ok=True)
    filename = f"report-{r.id}-{page_key}-{int(_utcnow_naive().timestamp())}.pdf"
    path = os.path.join(save_dir, filename)
    file.save(path)
    att = ReportAttachment(report_id=r.id, file_path=path, page_key=page_key, uploaded_by=current_user.id)
    db.session.add(att)
    r.updated_at = _utcnow_naive()
    db.session.add(AuditLog(actor_id=current_user.id, action='report_upload', details=f'{r.id}:{page_key}'))
    db.session.commit()
    return redirect(url_for('reports.report_detail', report_id=r.id))


@bp.route('/reports/<int:report_id>/add-person', methods=['POST'])
@login_required
def report_add_person(report_id):
    r = _get_or_404(Report, report_id)
    if r.owner_id != current_user.id:
        abort(403)
    name = request.form.get('name')
    role = request.form.get('role')
    if name:
        db.session.add(ReportPerson(report_id=r.id, name=name, role=role))
        r.updated_at = _utcnow_naive()
        db.session.commit()
    return redirect(url_for('reports.report_detail', report_id=r.id))


@bp.route('/reports/<int:report_id>/add-coauthor', methods=['POST'])
@login_required
def report_add_coauthor(report_id):
    r = _get_or_404(Report, report_id)
    if r.owner_id != current_user.id:
        abort(403)
    username = request.form.get('username')
    normalized_username = str(username or '').strip().lower()
    u = User.query.filter(func.lower(User.username) == normalized_username).first() if normalized_username else None
    if u:
        existing = ReportCoAuthor.query.filter_by(report_id=r.id, user_id=u.id).first()
        if not existing:
            db.session.add(ReportCoAuthor(report_id=r.id, user_id=u.id))
            r.updated_at = _utcnow_naive()
            db.session.commit()
    return redirect(url_for('reports.report_detail', report_id=r.id))


@bp.route('/reports/<int:report_id>/submit', methods=['POST'])
@login_required
def report_submit(report_id):
    r = _get_or_404(Report, report_id)
    if r.owner_id != current_user.id:
        abort(403)
    r.status = 'SUBMITTED'
    r.updated_at = _utcnow_naive()
    db.session.add(AuditLog(actor_id=current_user.id, action='report_submit', details=str(r.id)))
    db.session.commit()
    return redirect(url_for('reports.report_detail', report_id=r.id))


@bp.route('/reports/<int:report_id>/return', methods=['POST'])
@login_required
def report_return(report_id):
    require_admin()
    r = _get_or_404(Report, report_id)
    r.status = 'RETURNED'
    r.updated_at = _utcnow_naive()
    db.session.add(AuditLog(actor_id=current_user.id, action='report_return', details=str(r.id)))
    db.session.commit()
    return redirect(url_for('reports.report_detail', report_id=r.id))


@bp.route('/reports/<int:report_id>/grade', methods=['POST'])
@login_required
def report_grade(report_id):
    require_admin()
    r = _get_or_404(Report, report_id)
    raw_score = (request.form.get('score') or '').strip()
    try:
        score = int(raw_score or 0)
    except ValueError:
        flash('Score must be a whole number between 0 and 100.', 'error')
        return redirect(url_for('reports.report_detail', report_id=r.id))
    score = max(0, min(100, score))
    comments = request.form.get('comments')
    fixes = request.form.get('required_fixes')
    grade = ReportGrade(report_id=r.id, grader_id=current_user.id, score=score, comments=comments, required_fixes=fixes)
    r.status = 'GRADED'
    r.updated_at = _utcnow_naive()
    db.session.add(grade)
    db.session.add(AuditLog(actor_id=current_user.id, action='report_grade', details=str(r.id)))
    db.session.commit()
    return redirect(url_for('reports.report_detail', report_id=r.id))
