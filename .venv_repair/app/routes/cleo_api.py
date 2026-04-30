import os
import json
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, abort, current_app, send_file, render_template, redirect, url_for
from flask_login import login_required, current_user
from ..extensions import db
from ..models import CleoFormData, CleoFormLayout, CleoFormFile, CleoReport, CleoReportPage, CleoReportGrade, CleoReportAnnotation, User
from ..permissions import can_manage_site, can_manage_team, can_view_user, can_grade_cleoc_reports

bp = Blueprint('cleo_api', __name__)


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

MONTH_ABBR = {
    1: 'JAN', 2: 'FEB', 3: 'MAR', 4: 'APR', 5: 'MAY', 6: 'JUN',
    7: 'JUL', 8: 'AUG', 9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DEC'
}

EDITABLE_REPORT_STATUSES = {'DRAFT', 'RETURNED'}
REVIEWABLE_REPORT_STATUSES = {'SUBMITTED', 'RETURNED', 'GRADED'}
PAGE_LABELS = {
    'incident-admin': 'Incident Admin',
    'ta-main': 'Traffic Accident Main',
    'ta-person': 'Traffic Accident Person',
    'persons': 'Persons',
    'property': 'Property',
    'organization': 'Organization',
    'vehicle': 'Vehicle',
    'offenses': 'Offenses',
    'narrative': 'Narrative',
    'narcotics': 'Narcotics',
    'violation-1408': '1408 Violation',
    'dd-1408': 'DD Form 1408',
}


def _safe_value(data, idx):
    try:
        val = data[idx].get('value', '')
        return (val or '').strip()
    except Exception:
        return ''


def _format_case_date(yyyymmdd):
    if len(yyyymmdd) != 8 or not yyyymmdd.isdigit():
        now = _utcnow_naive()
        return f"{now.day:02d}{MONTH_ABBR[now.month]}{now.year % 100:02d}"
    year = int(yyyymmdd[0:4])
    month = int(yyyymmdd[4:6])
    day = int(yyyymmdd[6:8])
    mon = MONTH_ABBR.get(month, 'JAN')
    return f"{day:02d}{mon}{year % 100:02d}"


def _generate_case_control_number(report, incident_data):
    date_received = _safe_value(incident_data, 1)
    case_category = _safe_value(incident_data, 4)
    project_code = _safe_value(incident_data, 5)
    org_code_full = _safe_value(incident_data, 6)
    org_code = (org_code_full.split(' - ')[0] if org_code_full else 'XXXX').strip() or 'XXXX'
    cat_code = (case_category.split(' - ')[0] if case_category else 'UNK').strip().replace(' ', '')
    suffix = f"{cat_code}{project_code}".replace(' ', '')
    return f"{_format_case_date(date_received)}-{org_code}-{report.id:05d}-{suffix}"


def _page_label(page_key):
    return PAGE_LABELS.get(page_key, page_key.replace('-', ' ').title())


def _report_owner(report):
    return report.owner or User.query.get(report.user_id)


def _can_view_report(report):
    owner = _report_owner(report)
    if not owner:
        return False
    if owner.id == current_user.id:
        return True
    if can_grade_cleoc_reports(current_user):
        return True
    if can_manage_team(current_user):
        return can_view_user(current_user, owner)
    return False


def _can_edit_report(report):
    return report.user_id == current_user.id and (report.status or 'DRAFT') in EDITABLE_REPORT_STATUSES


def _field_label(item, idx):
    label = ''
    if isinstance(item, dict):
        label = (item.get('label') or item.get('name') or item.get('field') or '').strip()
    return label or f'Field {idx + 1}'


def _field_value(item):
    if not isinstance(item, dict):
        return ''
    if 'checked' in item:
        return 'Checked' if item.get('checked') else 'Not Checked'
    return str(item.get('value') or '').strip()


def _page_fields(page):
    try:
        raw_data = json.loads(page.data_json or '[]')
    except Exception:
        raw_data = []
    fields = []
    for idx, item in enumerate(raw_data):
        if not isinstance(item, dict):
            continue
        fields.append(
            {
                'idx': int(item.get('idx', idx)),
                'label': _field_label(item, idx),
                'value': _field_value(item),
            }
        )
    return fields


def _annotation_map(report_id):
    annotations = (
        CleoReportAnnotation.query.filter_by(report_id=report_id)
        .order_by(CleoReportAnnotation.created_at.asc())
        .all()
    )
    annotation_map = {}
    for annotation in annotations:
        key = (annotation.page_key, annotation.field_idx)
        annotation_map.setdefault(key, []).append(annotation)
    return annotation_map

@bp.route('/api/me', methods=['GET'])
@login_required
def me():
    return jsonify({'role': current_user.normalized_role, 'username': current_user.username, 'display_name': current_user.display_name})

@bp.route('/api/cleo/<page_key>', methods=['GET'])
@login_required
def cleo_load(page_key):
    row = CleoFormData.query.filter_by(user_id=current_user.id, page_key=page_key).first()
    if not row:
        return jsonify({'data': []})
    return jsonify({'data': json.loads(row.data_json)})

@bp.route('/api/cleo/<page_key>', methods=['POST'])
@login_required
def cleo_save(page_key):
    payload = request.get_json(silent=True) or {}
    data = payload.get('data', [])
    row = CleoFormData.query.filter_by(user_id=current_user.id, page_key=page_key).first()
    if not row:
        row = CleoFormData(user_id=current_user.id, page_key=page_key, data_json=json.dumps(data), updated_at=_utcnow_naive())
        db.session.add(row)
    else:
        row.data_json = json.dumps(data)
        row.updated_at = _utcnow_naive()
    db.session.commit()
    return jsonify({'ok': True})

@bp.route('/api/cleo/<page_key>', methods=['DELETE'])
@login_required
def cleo_clear(page_key):
    row = CleoFormData.query.filter_by(user_id=current_user.id, page_key=page_key).first()
    if row:
        db.session.delete(row)
        db.session.commit()
    return jsonify({'ok': True})

@bp.route('/api/cleo-layout/<page_key>', methods=['GET'])
@login_required
def cleo_layout_load(page_key):
    row = CleoFormLayout.query.filter_by(page_key=page_key).first()
    if not row:
        return jsonify({'layout': []})
    return jsonify({'layout': json.loads(row.layout_json)})

@bp.route('/api/cleo-layout/<page_key>', methods=['POST'])
@login_required
def cleo_layout_save(page_key):
    if not can_manage_site(current_user):
        abort(403)
    payload = request.get_json(silent=True) or {}
    layout = payload.get('layout', [])
    row = CleoFormLayout.query.filter_by(page_key=page_key).first()
    if not row:
        row = CleoFormLayout(page_key=page_key, layout_json=json.dumps(layout), updated_at=_utcnow_naive())
        db.session.add(row)
    else:
        row.layout_json = json.dumps(layout)
        row.updated_at = _utcnow_naive()
    db.session.commit()
    return jsonify({'ok': True})

@bp.route('/api/cleo-layout/<page_key>', methods=['DELETE'])
@login_required
def cleo_layout_clear(page_key):
    if not can_manage_site(current_user):
        abort(403)
    row = CleoFormLayout.query.filter_by(page_key=page_key).first()
    if row:
        db.session.delete(row)
        db.session.commit()
    return jsonify({'ok': True})

@bp.route('/api/cleo-file/<page_key>', methods=['POST'])
@login_required
def cleo_file_upload(page_key):
    files = request.files.getlist('file')
    if not files:
        return jsonify({'ok': False, 'error': 'No file'}), 400
    enclosure_no = request.form.get('enclosure_no', '').strip()
    description = request.form.get('description', '').strip()
    save_dir = os.path.join(current_app.config['UPLOAD_ROOT'], 'cleo')
    os.makedirs(save_dir, exist_ok=True)
    for file in files:
        ext = os.path.splitext(file.filename)[1] or '.pdf'
        filename = f"{current_user.username}-{page_key}-{int(_utcnow_naive().timestamp())}{ext}"
        path = os.path.join(save_dir, filename)
        file.save(path)
        row = CleoFormFile(
            user_id=current_user.id,
            page_key=page_key,
            file_path=path,
            enclosure_no=enclosure_no,
            description=description,
            uploaded_at=_utcnow_naive()
        )
        db.session.add(row)
    db.session.commit()
    return jsonify({'ok': True})

@bp.route('/api/cleo-file/<page_key>/latest', methods=['GET'])
@login_required
def cleo_file_latest(page_key):
    row = CleoFormFile.query.filter_by(user_id=current_user.id, page_key=page_key).order_by(CleoFormFile.uploaded_at.desc()).first()
    if not row:
        return jsonify({'ok': False, 'error': 'No file'}), 404
    return send_file(row.file_path, as_attachment=True)

@bp.route('/api/cleo-file/<page_key>/list', methods=['GET'])
@login_required
def cleo_file_list(page_key):
    rows = CleoFormFile.query.filter_by(user_id=current_user.id, page_key=page_key).order_by(CleoFormFile.uploaded_at.desc()).all()
    files = []
    for r in rows:
        files.append({
            'id': r.id,
            'name': os.path.basename(r.file_path),
            'enclosure': r.enclosure_no or '',
            'description': r.description or '',
            'uploaded_at': r.uploaded_at.isoformat()
        })
    return jsonify({'files': files})

@bp.route('/api/cleo-file/<int:file_id>', methods=['DELETE'])
@login_required
def cleo_file_delete(file_id):
    row = CleoFormFile.query.get_or_404(file_id)
    if row.user_id != current_user.id and not can_manage_site(current_user):
        abort(403)
    try:
        if os.path.exists(row.file_path):
            os.remove(row.file_path)
    except Exception:
        pass
    db.session.delete(row)
    db.session.commit()
    return jsonify({'ok': True})

@bp.route('/api/cleo-reports', methods=['GET'])
@login_required
def cleo_reports_list():
    rows = CleoReport.query.filter_by(user_id=current_user.id).order_by(CleoReport.created_at.desc()).all()
    return jsonify({'reports': [{'id': r.id, 'title': r.title or '', 'created_at': r.created_at.isoformat(), 'status': r.status or 'DRAFT'} for r in rows]})

@bp.route('/api/cleo-reports', methods=['POST'])
@login_required
def cleo_reports_create():
    payload = request.get_json(silent=True) or {}
    title = (payload.get('title') or '').strip() or None
    row = CleoReport(user_id=current_user.id, title=title, status='DRAFT')
    db.session.add(row)
    db.session.commit()
    return jsonify({'id': row.id})

@bp.route('/api/cleo-reports/<int:report_id>/page/<page_key>', methods=['GET'])
@login_required
def cleo_report_page_load(report_id, page_key):
    report = CleoReport.query.get_or_404(report_id)
    if not _can_view_report(report):
        abort(403)
    row = CleoReportPage.query.filter_by(report_id=report_id, page_key=page_key).first()
    if not row:
        return jsonify({'data': [], 'editable': _can_edit_report(report), 'status': report.status or 'DRAFT'})
    return jsonify({'data': json.loads(row.data_json), 'editable': _can_edit_report(report), 'status': report.status or 'DRAFT'})

@bp.route('/api/cleo-reports/<int:report_id>/page/<page_key>', methods=['POST'])
@login_required
def cleo_report_page_save(report_id, page_key):
    report = CleoReport.query.get_or_404(report_id)
    if not _can_edit_report(report):
        return jsonify({'ok': False, 'error': 'This mock report is locked. Submitted reports are read-only until returned for corrections.'}), 403
    payload = request.get_json(silent=True) or {}
    data = payload.get('data', [])
    row = CleoReportPage.query.filter_by(report_id=report_id, page_key=page_key).first()
    if not row:
        row = CleoReportPage(report_id=report_id, page_key=page_key, data_json=json.dumps(data), updated_at=_utcnow_naive())
        db.session.add(row)
    else:
        row.data_json = json.dumps(data)
        row.updated_at = _utcnow_naive()
    if page_key == 'incident-admin':
        if not (report.title or '').strip():
            report.title = _generate_case_control_number(report, data)
    report.updated_at = _utcnow_naive()
    db.session.commit()
    return jsonify({'ok': True, 'case_control_number': report.title or ''})

@bp.route('/api/cleo-reports/<int:report_id>/summary', methods=['GET'])
@login_required
def cleo_report_summary(report_id):
    report = CleoReport.query.get_or_404(report_id)
    if not _can_view_report(report):
        abort(403)
    pages = CleoReportPage.query.filter_by(report_id=report_id).order_by(CleoReportPage.updated_at.desc()).all()
    incident_type = ''
    incident_page = CleoReportPage.query.filter_by(report_id=report_id, page_key='incident-admin').first()
    if incident_page:
        try:
            incident_data = json.loads(incident_page.data_json or '[]')
            incident_type = _safe_value(incident_data, 0)
        except Exception:
            incident_type = ''
    return jsonify({
        'report': {
            'id': report.id,
            'title': report.title or '',
            'case_control_number': report.title or '',
            'incident_type': incident_type,
            'updated_at': report.updated_at.isoformat(),
            'status': report.status or 'DRAFT',
            'editable': _can_edit_report(report),
        },
        'pages': [{'page_key': p.page_key, 'updated_at': p.updated_at.isoformat()} for p in pages]
    })

@bp.route('/api/cleo-reports/<int:report_id>', methods=['DELETE'])
@login_required
def cleo_report_delete(report_id):
    report = CleoReport.query.filter_by(id=report_id).first()
    if not report:
        abort(404)
    if not (can_manage_site(current_user) or (report.user_id == current_user.id and (report.status or 'DRAFT') in EDITABLE_REPORT_STATUSES)):
        abort(403)
    CleoReportPage.query.filter_by(report_id=report_id).delete()
    CleoReportAnnotation.query.filter_by(report_id=report_id).delete()
    CleoReportGrade.query.filter_by(report_id=report_id).delete()
    db.session.delete(report)
    db.session.commit()
    return jsonify({'ok': True})

@bp.route('/cleo/report/<int:report_id>', methods=['GET'])
@login_required
def cleo_report_view(report_id):
    report = CleoReport.query.get_or_404(report_id)
    if not _can_view_report(report):
        abort(403)
    pages = CleoReportPage.query.filter_by(report_id=report.id).order_by(CleoReportPage.page_key.asc()).all()
    annotation_map = _annotation_map(report.id)
    page_summaries = []
    for page in pages:
        fields = _page_fields(page)
        for field in fields:
            field['annotations'] = annotation_map.get((page.page_key, field['idx']), [])
        page_summaries.append(
            {
                'page_key': page.page_key,
                'page_label': _page_label(page.page_key),
                'updated_at': page.updated_at,
                'fields': fields,
                'has_annotations': any(field['annotations'] for field in fields),
            }
        )
    grades = CleoReportGrade.query.filter_by(report_id=report.id).order_by(CleoReportGrade.created_at.desc()).all()
    return render_template(
        'cleo_report.html',
        report=report,
        report_owner=_report_owner(report),
        page_summaries=page_summaries,
        grades=grades,
        can_edit_report=_can_edit_report(report),
        can_grade_report=can_grade_cleoc_reports(current_user),
        user=current_user,
    )

@bp.route('/api/cleo-reports/<int:report_id>/submit', methods=['POST'])
@login_required
def cleo_report_submit(report_id):
    report = CleoReport.query.get_or_404(report_id)
    if not _can_edit_report(report):
        return jsonify({'ok': False, 'error': 'Only the report owner can submit an editable report.'}), 403
    report.status = 'SUBMITTED'
    report.updated_at = _utcnow_naive()
    report.submitted_at = _utcnow_naive()
    report.submitted_by = current_user.id
    db.session.commit()
    return jsonify({'ok': True, 'status': report.status})


@bp.route('/cleo/report/<int:report_id>/grade', methods=['POST'])
@login_required
def cleo_report_grade(report_id):
    if not can_grade_cleoc_reports(current_user):
        abort(403)
    report = CleoReport.query.get_or_404(report_id)
    if not _can_view_report(report):
        abort(403)
    if (report.status or 'DRAFT') not in REVIEWABLE_REPORT_STATUSES:
        abort(400)

    disposition = (request.form.get('disposition') or 'RETURNED').strip().upper()
    if disposition not in {'RETURNED', 'GRADED'}:
        disposition = 'RETURNED'

    raw_score = (request.form.get('score') or '').strip()
    score = int(raw_score) if raw_score.isdigit() else None
    summary = (request.form.get('summary') or '').strip()
    officer_notes = (request.form.get('officer_notes') or '').strip()
    annotations_json = request.form.get('annotations_json') or '[]'

    try:
        annotations_payload = json.loads(annotations_json)
    except Exception:
        annotations_payload = []

    grade = CleoReportGrade(
        report_id=report.id,
        grader_id=current_user.id,
        score=score,
        disposition=disposition,
        summary=summary or None,
        officer_notes=officer_notes or None,
    )
    db.session.add(grade)
    db.session.flush()

    for item in annotations_payload:
        if not isinstance(item, dict):
            continue
        note = (item.get('note') or '').strip()
        page_key = (item.get('page_key') or '').strip()
        if not note or not page_key:
            continue
        db.session.add(
            CleoReportAnnotation(
                report_id=report.id,
                grade_id=grade.id,
                page_key=page_key,
                field_idx=int(item.get('field_idx') or 0),
                field_label=(item.get('field_label') or '').strip() or None,
                field_value_snapshot=(item.get('field_value_snapshot') or '').strip() or None,
                severity=(item.get('severity') or 'REQUIRED_FIX').strip().upper(),
                note=note,
                created_by=current_user.id,
            )
        )

    report.status = disposition
    report.updated_at = _utcnow_naive()
    if disposition == 'RETURNED':
        report.returned_at = _utcnow_naive()
        report.returned_by = current_user.id
    else:
        report.graded_at = _utcnow_naive()
        report.graded_by = current_user.id

    db.session.commit()
    return render_template('cleo_grade_saved.html', report=report, disposition=disposition)

@bp.route('/cleo/reports', methods=['GET'])
@login_required
def cleo_reports_page():
    return redirect(url_for('reports.list_reports'))
