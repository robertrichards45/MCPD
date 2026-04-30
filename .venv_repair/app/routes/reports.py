import json
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from io import BytesIO
from urllib.parse import quote

from flask import Blueprint, render_template, request, redirect, url_for, abort, current_app, flash, make_response, send_file
from flask_login import login_required, current_user
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import func
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models import CleoReport, Report, ReportAttachment, ReportPerson, ReportCoAuthor, ReportGrade, User, AuditLog, ROLE_DESK_SGT, ROLE_WATCH_COMMANDER
from ..permissions import can_manage_site, can_manage_team, can_view_user, can_grade_cleoc_reports
from ..services.call_type_rules import load_call_type_rules
from ..services.forms_pdf_renderer import _pdf_classes

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


def _clean_email(value):
    return (value or '').strip()


def _report_selected_paperwork(report):
    try:
        values = json.loads(report.paperwork_json or '[]')
        return [str(item).strip() for item in values if str(item or '').strip()] if isinstance(values, list) else []
    except json.JSONDecodeError:
        return []


def _report_packet_filename(report):
    base = secure_filename(report.title or f'report-{report.id}') or f'report-{report.id}'
    return f'{base}-packet.pdf'


def _wrap_report_line(text, max_chars=88):
    words = str(text or '').replace('\r', '\n').split()
    lines, current = [], ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or ['']


def _draw_report_wrapped(c, text, x, y, max_chars=88, line_height=11, min_y=52):
    width, height = letter
    for line in _wrap_report_line(text, max_chars=max_chars):
        if y < min_y:
            c.showPage()
            y = height - 54
            c.setFont('Helvetica', 9)
        c.drawString(x, y, line[:140])
        y -= line_height
    return y


def _report_packet_summary_pdf(report, owner, persons, selected_paperwork):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 48
    c.setTitle(f'{report.title or "Report"} Packet')
    c.setAuthor('MCPD Portal')
    c.setSubject('Report packet summary')
    c.setFont('Helvetica-Bold', 15)
    c.drawString(42, y, 'MCPD Report Packet')
    c.setFont('Helvetica', 9)
    c.drawRightString(width - 42, y, f'Report #{report.id}')
    y -= 20
    c.setStrokeColorRGB(0.70, 0.76, 0.82)
    c.line(42, y, width - 42, y)
    y -= 20

    c.setFont('Helvetica-Bold', 10)
    c.drawString(42, y, 'Report Summary')
    y -= 14
    c.setFont('Helvetica', 9)
    summary_rows = [
        f'Title: {report.title or "Untitled"}',
        f'Status: {report.status or "DRAFT"}',
        f'Owner: {owner.display_name}',
        f'Report Type: {report.call_type_slug or "Manual / Other"}',
        f'Updated: {report.updated_at.strftime("%Y-%m-%d %H:%M") if report.updated_at else "Not saved"}',
    ]
    for row in summary_rows:
        c.drawString(54, y, row[:120])
        y -= 12

    y -= 8
    c.setFont('Helvetica-Bold', 10)
    c.drawString(42, y, 'Parties')
    y -= 14
    c.setFont('Helvetica', 9)
    if persons:
        for person in persons:
            c.drawString(54, y, f'{person.role or "Involved person"}: {person.name}'[:120])
            y -= 12
    else:
        c.drawString(54, y, 'No parties added.')
        y -= 12

    y -= 8
    c.setFont('Helvetica-Bold', 10)
    c.drawString(42, y, 'Selected Paperwork')
    y -= 14
    c.setFont('Helvetica', 9)
    if selected_paperwork:
        for item in selected_paperwork:
            c.drawString(54, y, f'- {item}'[:120])
            y -= 12
    else:
        c.drawString(54, y, 'No paperwork selected.')
        y -= 12

    for heading, value in (
        ('Facts', report.facts_text),
        ('Narrative', report.narrative_text),
        ('Blotter', report.blotter_text),
        ('Officer Notes', report.officer_notes),
    ):
        if y < 92:
            c.showPage()
            y = height - 54
        c.setFont('Helvetica-Bold', 10)
        c.drawString(42, y, heading)
        y -= 14
        c.setFont('Helvetica', 9)
        y = _draw_report_wrapped(c, value or 'Not entered.', 54, y, max_chars=92)
        y -= 8

    c.save()
    return buffer.getvalue()


def _report_packet_bytes(report, owner, persons, attachments):
    selected_paperwork = _report_selected_paperwork(report)
    PdfReader, PdfWriter = _pdf_classes()
    writer = PdfWriter()
    summary = _report_packet_summary_pdf(report, owner, persons, selected_paperwork)
    summary_reader = PdfReader(BytesIO(summary))
    for page in summary_reader.pages:
        writer.add_page(page)

    skipped = []
    included = 0
    for attachment in attachments:
        path = attachment.file_path
        if not path or not os.path.exists(path):
            skipped.append(f'{attachment.page_key}:missing')
            continue
        if not path.lower().endswith('.pdf'):
            skipped.append(f'{attachment.page_key}:not-pdf')
            continue
        try:
            reader = PdfReader(path)
            for page in reader.pages:
                writer.add_page(page)
            included += 1
        except Exception:
            skipped.append(f'{attachment.page_key}:unreadable')

    output = BytesIO()
    writer.write(output)
    return output.getvalue(), {
        'selected_paperwork': selected_paperwork,
        'included_attachments': included,
        'skipped_attachments': skipped,
        'page_count': len(writer.pages),
    }


def _report_packet_context(report_id):
    report = _get_or_404(Report, report_id)
    owner = _get_or_404(User, report.owner_id)
    if not can_view_user(current_user, owner):
        abort(403)
    attachments = ReportAttachment.query.filter_by(report_id=report.id).all()
    persons = ReportPerson.query.filter_by(report_id=report.id).all()
    return report, owner, persons, attachments


def _report_packet_recipients():
    primary = _clean_email(current_user.email)
    if not primary:
        return '', []
    recipients = []
    for user in User.query.filter(User.active.is_(True)).all():
        email = _clean_email(user.email)
        if email and user.has_any_role(ROLE_WATCH_COMMANDER, ROLE_DESK_SGT) and email.lower() != primary.lower():
            recipients.append(email)
    ordered, seen = [], set()
    for item in recipients:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return primary, ordered


def _smtp_send_report_packet(recipient, cc_list, subject, body, attachment_name, attachment_bytes):
    host = os.environ.get('SMTP_HOST', '').strip()
    sender = os.environ.get('SMTP_FROM', '').strip()
    if not host or not sender:
        return False, 'SMTP not configured.'
    port = int(os.environ.get('SMTP_PORT', '587') or '587')
    username = os.environ.get('SMTP_USERNAME', '').strip()
    password = os.environ.get('SMTP_PASSWORD', '').strip()
    use_tls = os.environ.get('SMTP_USE_TLS', '1').strip().lower() in {'1', 'true', 'yes', 'on'}
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient
    if cc_list:
        msg['Cc'] = ', '.join(cc_list)
    msg.set_content(body)
    msg.add_attachment(attachment_bytes, maintype='application', subtype='pdf', filename=attachment_name)
    with smtplib.SMTP(host, port, timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(msg, to_addrs=[recipient] + list(cc_list or []))
    return True, 'sent'


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
    call_types = load_call_type_rules()
    if request.method == 'POST':
        call_type_slug = (request.form.get('call_type') or '').strip()
        call_type = call_types.get(call_type_slug, {})
        typed_title = (request.form.get('title') or '').strip()
        title = typed_title or call_type.get('title') or 'Untitled Report'
        r = Report(title=title, owner_id=current_user.id, status='DRAFT', call_type_slug=call_type_slug or None)
        db.session.add(r)
        db.session.add(AuditLog(actor_id=current_user.id, action='report_create', details=f'{title}:{call_type_slug or "manual"}'))
        db.session.commit()
        return redirect(url_for('reports.report_detail', report_id=r.id))
    return render_template('reports_new.html', user=current_user, call_types=call_types)


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
    call_types = load_call_type_rules()
    selected_call_type = call_types.get(r.call_type_slug or '', {})
    try:
        selected_paperwork = json.loads(r.paperwork_json or '[]')
    except json.JSONDecodeError:
        selected_paperwork = []
    return render_template(
        'reports_detail.html',
        report=r,
        report_owner=owner,
        attachments=attachments,
        persons=persons,
        coauthors=coauthors,
        grades=grades,
        users=users,
        user=current_user,
        call_types=call_types,
        selected_call_type=selected_call_type,
        selected_paperwork=selected_paperwork,
    )


@bp.route('/reports/<int:report_id>/packet/preview')
@login_required
def report_packet_preview(report_id):
    report, owner, persons, attachments = _report_packet_context(report_id)
    pdf_bytes, meta = _report_packet_bytes(report, owner, persons, attachments)
    db.session.add(AuditLog(actor_id=current_user.id, action='report_packet_preview', details=f'{report.id}|pages={meta["page_count"]}|attachments={meta["included_attachments"]}'))
    db.session.commit()
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename="{_report_packet_filename(report)}"'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@bp.route('/reports/<int:report_id>/packet/download')
@login_required
def report_packet_download(report_id):
    report, owner, persons, attachments = _report_packet_context(report_id)
    pdf_bytes, meta = _report_packet_bytes(report, owner, persons, attachments)
    db.session.add(AuditLog(actor_id=current_user.id, action='report_packet_download', details=f'{report.id}|pages={meta["page_count"]}|attachments={meta["included_attachments"]}'))
    db.session.commit()
    response = send_file(
        BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=_report_packet_filename(report),
        mimetype='application/pdf',
    )
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response


@bp.route('/reports/<int:report_id>/packet/email', methods=['POST'])
@login_required
def report_packet_email(report_id):
    report, owner, persons, attachments = _report_packet_context(report_id)
    recipient, cc_list = _report_packet_recipients()
    if not recipient:
        flash('Your profile email is required before emailing report packets. Update Profile and try again.', 'error')
        return redirect(url_for('reports.report_detail', report_id=report.id))
    pdf_bytes, meta = _report_packet_bytes(report, owner, persons, attachments)
    subject = f'{report.title or "MCPD Report"} - Report Packet'
    body = (
        f'Report: {report.title or "Untitled"}\n'
        f'Report #: {report.id}\n'
        f'Status: {report.status or "DRAFT"}\n'
        f'Owner: {owner.display_name}\n'
        f'Paperwork: {", ".join(meta["selected_paperwork"]) if meta["selected_paperwork"] else "None selected"}\n'
        f'Preview: {url_for("reports.report_packet_preview", report_id=report.id, _external=True)}\n'
    )
    try:
        sent, info = _smtp_send_report_packet(
            recipient,
            cc_list,
            subject,
            body,
            _report_packet_filename(report),
            pdf_bytes,
        )
    except Exception as exc:
        sent, info = False, str(exc)
    if sent:
        flash('Report packet emailed to your profile address. CC sent to Watch Commander and Desk Sgt.', 'success')
        db.session.add(AuditLog(actor_id=current_user.id, action='report_packet_email', details=f'{report.id}|recipient={recipient}|cc={len(cc_list)}'))
    else:
        mailto = f'mailto:{quote(recipient)}?subject={quote(subject)}&body={quote(body[:1400])}'
        flash(f'SMTP not configured or failed. Use this fallback link: {mailto}', 'error')
        db.session.add(AuditLog(actor_id=current_user.id, action='report_packet_email_fallback', details=f'{report.id}|reason={info}'))
    db.session.commit()
    return redirect(url_for('reports.report_detail', report_id=report.id))


@bp.route('/reports/<int:report_id>/workflow', methods=['POST'])
@login_required
def report_update_workflow(report_id):
    r = _get_or_404(Report, report_id)
    if r.owner_id != current_user.id:
        abort(403)
    r.call_type_slug = (request.form.get('call_type_slug') or r.call_type_slug or '').strip() or None
    r.facts_text = (request.form.get('facts_text') or '').strip() or None
    r.narrative_text = (request.form.get('narrative_text') or '').strip() or None
    r.blotter_text = (request.form.get('blotter_text') or '').strip() or None
    r.officer_notes = (request.form.get('officer_notes') or '').strip() or None
    r.paperwork_json = json.dumps(request.form.getlist('paperwork'), ensure_ascii=True)
    r.updated_at = _utcnow_naive()
    db.session.add(AuditLog(actor_id=current_user.id, action='report_workflow_save', details=str(r.id)))
    db.session.commit()
    flash('Report workflow saved.', 'success')
    return redirect(url_for('reports.report_detail', report_id=r.id))


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
    missing = []
    if not (r.facts_text or '').strip():
        missing.append('facts')
    if not (r.narrative_text or '').strip():
        missing.append('narrative')
    if missing:
        flash('Report is missing required workflow items: {}.'.format(', '.join(missing)), 'error')
        return redirect(url_for('reports.report_detail', report_id=r.id))
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
