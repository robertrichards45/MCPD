import json
import os
from datetime import datetime
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, current_app, send_from_directory, flash
from flask_login import login_required, current_user

from ..models import ROLE_WATCH_COMMANDER
from ..services.smart_filing import allowed_file, classify_document, build_storage_path

bp = Blueprint('wc_admin', __name__)

BASE_STORAGE = 'instance/officer_files'
LEARNING_FILE = 'instance/narrative_learning.json'


def is_watch_commander():
    return getattr(current_user, 'role', '') in {ROLE_WATCH_COMMANDER, 'DESK_SERGEANT', 'WEBSITE_CONTROLLER'}


@bp.route('/admin/watch-commander')
@login_required
def dashboard():
    if not is_watch_commander():
        return 'Forbidden', 403
    return render_template('wc_admin/dashboard.html')


@bp.route('/admin/officer-files/<int:user_id>')
@login_required
def officer_files(user_id):
    base = os.path.join(current_app.root_path, BASE_STORAGE, str(user_id))
    tree = {}
    if os.path.exists(base):
        for root, dirs, files in os.walk(base):
            rel = os.path.relpath(root, base)
            tree[rel] = files
    return render_template('wc_admin/officer_files.html', tree=tree, user_id=user_id)


@bp.route('/admin/upload/<int:user_id>', methods=['POST'])
@login_required
def upload(user_id):
    file = request.files.get('file')
    description = request.form.get('description', '')
    if not file or not allowed_file(file.filename):
        flash('Invalid file')
        return redirect(request.referrer or url_for('wc_admin.dashboard'))
    category = classify_document(file.filename, description)
    full_path, stored_name = build_storage_path(os.path.join(current_app.root_path, BASE_STORAGE), user_id, category, file.filename)
    file.save(full_path)
    return redirect(request.referrer or url_for('wc_admin.officer_files', user_id=user_id))


@bp.route('/admin/download/<int:user_id>/<path:filename>')
@login_required
def download(user_id, filename):
    base = os.path.join(current_app.root_path, BASE_STORAGE, str(user_id))
    return send_from_directory(base, filename, as_attachment=True)


@bp.route('/admin/narrative-learning', methods=['POST'])
@login_required
def narrative_learning():
    if not is_watch_commander():
        return jsonify({'ok': False}), 403
    data = request.get_json()
    os.makedirs(os.path.dirname(LEARNING_FILE), exist_ok=True)
    existing = []
    if os.path.exists(LEARNING_FILE):
        with open(LEARNING_FILE, 'r') as f:
            existing = json.load(f)
    existing.insert(0, {
        'incidentType': data.get('incidentType'),
        'original': data.get('original'),
        'edited': data.get('edited'),
        'approvedBy': getattr(current_user, 'username', 'unknown'),
        'timestamp': datetime.utcnow().isoformat()
    })
    existing = existing[:200]
    with open(LEARNING_FILE, 'w') as f:
        json.dump(existing, f)
    return jsonify({'ok': True})


@bp.route('/admin/forms/upload', methods=['POST'])
@login_required
def upload_form_template():
    if not is_watch_commander():
        return 'Forbidden', 403
    file = request.files.get('file')
    if not file:
        return redirect(url_for('wc_admin.dashboard'))
    path = os.path.join(current_app.root_path, 'instance', 'wc_forms')
    os.makedirs(path, exist_ok=True)
    file.save(os.path.join(path, file.filename))
    return redirect(url_for('wc_admin.dashboard'))
