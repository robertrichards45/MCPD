import io
import os
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, abort, current_app, flash, send_file
from flask_login import login_required, current_user
from sqlalchemy import func
from ..extensions import db
from ..models import CleoReport, Report, ReportAttachment, ReportPerson, ReportCoAuthor, ReportGrade, User, AuditLog
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


def require_admin():
    if not can_manage_site(current_user):
        abort(403)


def _visible_user_ids():
    if can_manage_site(current_user):
        return [u.id for u in User.query.filter_by(active=True).all()]
    if can_manage_team(current_user):
        return [u.id for u in User.query.filter_by(active=True).all() if can_view_user(current_user, u)]
    return [current_user.id]


@bp.route('/reports')
@login_required
def list_reports():
    visible_ids = _visible_user_ids()
    reports = (
        Report.query
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
    return render_template(
        'reports_list.html',
        reports=reports,
        cleo_reports=cleo_reports,
        cleo_review_reports=cleo_review_reports,
        report_count=len(reports),
        cleo_count=len(cleo_reports),
        cleo_review_count=len(cleo_review_reports),
        user=current_user,
    )


@bp.route('/reports/new', methods=['GET', 'POST'])
@login_required
def new_report():
    if request.method == 'POST':
        title = request.form.get('title') or 'Untitled Report'
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
    users = {u.id: u for u in User.query.all()}
    return render_template('reports_detail.html', report=r, report_owner=owner, attachments=attachments, persons=persons, coauthors=coauthors, grades=grades, users=users, user=current_user)


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


@bp.route('/reports/<int:report_id>/packet.pdf')
@login_required
def report_packet(report_id):
    """Merge all uploaded PDF attachments for this report into a single download.

    Uses pypdf (already a project dependency) to concatenate pages in the order
    the files were uploaded. If no attachments exist, returns 404.

    TODO (Phase 2): prepend a cover page with incident metadata, title, officer
    name, and date before the merged attachment pages.
    """
    r = _get_or_404(Report, report_id)
    owner = _get_or_404(User, r.owner_id)
    if not can_view_user(current_user, owner):
        abort(403)

    attachments = (
        ReportAttachment.query
        .filter_by(report_id=r.id)
        .order_by(ReportAttachment.uploaded_at.asc())
        .all()
    )
    valid_paths = [a.file_path for a in attachments if a.file_path and os.path.exists(a.file_path)]
    if not valid_paths:
        flash('No uploaded PDFs found for this report. Upload at least one PDF to generate a packet.', 'info')
        return redirect(url_for('reports.report_detail', report_id=r.id))

    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        flash('PDF merge library not available.', 'error')
        return redirect(url_for('reports.report_detail', report_id=r.id))

    writer = PdfWriter()
    for path in valid_paths:
        try:
            reader = PdfReader(path)
            for page in reader.pages:
                writer.add_page(page)
        except Exception:
            continue  # Skip corrupted individual files; never block the whole packet

    if len(writer.pages) == 0:
        flash('Could not read any pages from the uploaded PDFs.', 'error')
        return redirect(url_for('reports.report_detail', report_id=r.id))

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)

    safe_title = ''.join(c if c.isalnum() or c in '-_' else '_' for c in (r.title or 'Report'))[:40]
    filename = f"report-{r.id}-{safe_title}-packet.pdf"
    db.session.add(AuditLog(actor_id=current_user.id, action='report_packet_download', details=str(r.id)))
    db.session.commit()
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=filename)
