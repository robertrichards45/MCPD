import os

from flask import Blueprint, abort, after_this_request, flash, redirect, send_file, session, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ..simulator.official_form_pdf import render_actual_training_pdf
from ..simulator.run_store import load_run, load_run_state


bp = Blueprint('scenario_official_forms', __name__, url_prefix='/scenario-paperwork')
SESSION_KEY = 'sentinel_scenario_lab_v2'
_SERVER_STATE_MARKER = '_sentinel_server_state'


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _active_training_state():
    handle = session.get(SESSION_KEY)
    if not isinstance(handle, dict):
        return None
    if handle.get(_SERVER_STATE_MARKER):
        run_id = _text(handle.get('run_id'))
        run = load_run(run_id) if run_id else None
        if run is None or run.trainee_id != getattr(current_user, 'id', None):
            return None
        return load_run_state(run)
    return handle


def _latest_submission(state):
    package = (state or {}).get('training_package') or {}
    rows = package.get('submissions') or []
    return rows[-1] if rows else None


def _send_training_pdf(document_name, values):
    output_path, meta = render_actual_training_pdf(document_name, values)
    if not output_path:
        flash(
            'The actual source PDF for this form could not be rendered. Sentinel will not substitute a made-up form.',
            'warning',
        )
        return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))

    source_pdf = os.path.abspath(str((meta or {}).get('source_pdf') or ''))
    output_abs = os.path.abspath(output_path)

    @after_this_request
    def _cleanup(response):
        try:
            if output_abs and output_abs != source_pdf and os.path.exists(output_abs):
                os.remove(output_abs)
        except OSError:
            pass
        return response

    filename = secure_filename(f'TRAINING-SYNTHETIC-{document_name}.pdf') or 'TRAINING-SYNTHETIC-form.pdf'
    return send_file(output_path, mimetype='application/pdf', as_attachment=False, download_name=filename)


@bp.get('/statement/<statement_id>/actual-pdf')
@login_required
def statement_actual_pdf(statement_id):
    state = _active_training_state()
    if state is None:
        abort(404)
    for statement in ((state.get('world') or {}).get('statements') or []):
        if _text(statement.get('id')) != _text(statement_id) or statement.get('status') != 'received':
            continue
        document_name = _text(statement.get('form_document_name'))
        values = dict(statement.get('form_values') or {})
        if not document_name:
            abort(404)
        return _send_training_pdf(document_name, values)
    abort(404)


@bp.get('/training-form/<document_id>/actual-pdf')
@login_required
def training_form_actual_pdf(document_id):
    state = _active_training_state()
    if state is None:
        abort(404)
    submission = _latest_submission(state)
    if not submission:
        abort(404)
    for document in submission.get('training_forms') or []:
        if _text(document.get('document_id')) != _text(document_id):
            continue
        document_name = _text(document.get('document_name'))
        values = dict(document.get('values') or {})
        if not document_name:
            abort(404)
        return _send_training_pdf(document_name, values)
    abort(404)
