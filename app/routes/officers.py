import csv
import io

from flask import Blueprint, current_app, render_template, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import AuditLog, OfficerProfile, User
from ..permissions import can_manage_site, can_view_user

bp = Blueprint('officers', __name__)


def _load_profile(user_id):
    profile = OfficerProfile.query.filter_by(user_id=user_id).first()
    if profile:
        return profile
    profile = OfficerProfile(user_id=user_id)
    db.session.add(profile)
    db.session.flush()
    return profile


def _normalize_edipi(value):
    return ''.join(character for character in (value or '').strip() if character.isdigit())


@bp.route('/officers', methods=['GET', 'POST'])
@login_required
def officer_directory():
    profile = _load_profile(current_user.id)
    search_term = (request.args.get('q') or '').strip()

    if request.method == 'POST':
        user = db.session.get(User, current_user.id)
        first_name = request.form.get('first_name', '').strip() or None
        last_name = request.form.get('last_name', '').strip() or None
        edipi = _normalize_edipi(request.form.get('edipi', '')) or None
        if edipi and len(edipi) != 10:
            return render_template(
                'officers.html',
                user=current_user,
                profile=profile,
                profiles=_profiles_for_view(search_term=search_term),
                search_term=search_term,
                error='EDIPI must be a 10-digit number.',
            )
        if edipi:
            existing = User.query.filter(User.edipi == edipi, User.id != current_user.id).first()
            if existing:
                return render_template(
                    'officers.html',
                    user=current_user,
                    profile=profile,
                    profiles=_profiles_for_view(search_term=search_term),
                    search_term=search_term,
                    error='That EDIPI is already assigned to another user.',
                )
        email = request.form.get('email', '').strip().lower() or None
        if email:
            existing_email = User.query.filter(User.email == email, User.id != current_user.id).first()
            if existing_email:
                return render_template(
                    'officers.html',
                    user=current_user,
                    profile=profile,
                    profiles=_profiles_for_view(search_term=search_term),
                    search_term=search_term,
                    error='That email is already assigned to another user.',
                )

        user.first_name = first_name
        user.last_name = last_name
        user.display_name_override = request.form.get('display_name', '').strip() or None
        user.name = ' '.join(part for part in [first_name, last_name] if part) or user.name
        user.email = email
        user.phone_number = request.form.get('phone_number', '').strip() or None
        user.address = request.form.get('address', '').strip() or None
        user.badge_employee_id = request.form.get('badge_employee_id', '').strip() or None
        user.section_unit = request.form.get('section_unit', '').strip() or None
        if can_manage_site(current_user):
            user.edipi = edipi
        profile.rank = request.form.get('rank', '').strip() or None
        profile.unit = request.form.get('unit', '').strip() or user.section_unit
        profile.duty_phone = request.form.get('duty_phone', '').strip() or None
        profile.personal_phone = request.form.get('personal_phone', '').strip() or None
        profile.personal_email = request.form.get('personal_email', '').strip() or None
        profile.emergency_contact_name = request.form.get('emergency_contact_name', '').strip() or None
        profile.emergency_contact_relationship = request.form.get('emergency_contact_relationship', '').strip() or None
        profile.emergency_contact_phone = request.form.get('emergency_contact_phone', '').strip() or None
        profile.emergency_contact_address = request.form.get('emergency_contact_address', '').strip() or None

        db.session.add(AuditLog(actor_id=current_user.id, action='officer_profile_update', details=user.username))
        db.session.commit()

        return render_template(
            'officers.html',
            user=current_user,
            profile=profile,
            profiles=_profiles_for_view(search_term=search_term),
            search_term=search_term,
            success='Officer information saved.',
        )

    return render_template(
        'officers.html',
        user=current_user,
        profile=profile,
        profiles=_profiles_for_view(search_term=search_term),
        search_term=search_term,
    )


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    return officer_directory()


def _profiles_for_view(search_term=''):
    if current_user.can_manage_team():
        query = db.session.query(OfficerProfile, User).join(User, User.id == OfficerProfile.user_id)
        term = (search_term or '').strip()
        if term:
            like = f'%{term}%'
            query = query.filter(
                db.or_(
                    User.first_name.ilike(like),
                    User.last_name.ilike(like),
                    User.username.ilike(like),
                    User.officer_number.ilike(like),
                    User.edipi.ilike(like),
                    OfficerProfile.unit.ilike(like),
                    OfficerProfile.emergency_contact_name.ilike(like),
                )
            )
        rows = query.order_by(User.first_name, User.last_name, User.username).all()
        return [(profile, user) for profile, user in rows if can_view_user(current_user, user)]
    return []


@bp.route('/officers/export.csv', methods=['GET'])
@login_required
def officer_directory_export_csv():
    if not current_user.can_manage_team():
        return current_app.response_class('Forbidden', status=403)

    search_term = (request.args.get('q') or '').strip()
    rows = _profiles_for_view(search_term=search_term)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            'name',
            'officer_number',
            'edipi',
            'email',
            'phone_number',
            'address',
            'badge_employee_id',
            'section_unit',
            'rank',
            'unit',
            'duty_phone',
            'personal_phone',
            'personal_email',
            'emergency_contact_name',
            'emergency_contact_relationship',
            'emergency_contact_phone',
            'emergency_contact_address',
        ]
    )
    for profile, user in rows:
        writer.writerow(
            [
                user.display_name,
                user.officer_number or '',
                user.edipi or '',
                user.email or '',
                user.phone_number or '',
                user.address or '',
                user.badge_employee_id or '',
                user.section_unit or '',
                profile.rank or '',
                profile.unit or '',
                profile.duty_phone or '',
                profile.personal_phone or '',
                profile.personal_email or '',
                profile.emergency_contact_name or '',
                profile.emergency_contact_relationship or '',
                profile.emergency_contact_phone or '',
                profile.emergency_contact_address or '',
            ]
        )

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='officer_directory_export_csv',
            details=f'rows={len(rows)}|q={search_term}',
        )
    )
    db.session.commit()
    return current_app.response_class(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=officer-directory.csv'},
    )


@bp.route('/officers/<int:user_id>/export.csv', methods=['GET'])
@login_required
def officer_profile_export_csv(user_id):
    if not current_user.can_manage_team():
        return current_app.response_class('Forbidden', status=403)

    user = db.session.get(User, user_id)
    if not user or not can_view_user(current_user, user):
        return current_app.response_class('Forbidden', status=403)

    profile = OfficerProfile.query.filter_by(user_id=user.id).first() or OfficerProfile(user_id=user.id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            'name',
            'officer_number',
            'edipi',
            'email',
            'phone_number',
            'address',
            'badge_employee_id',
            'section_unit',
            'rank',
            'unit',
            'duty_phone',
            'personal_phone',
            'personal_email',
            'emergency_contact_name',
            'emergency_contact_relationship',
            'emergency_contact_phone',
            'emergency_contact_address',
        ]
    )
    writer.writerow(
        [
            user.display_name,
            user.officer_number or '',
            user.edipi or '',
            user.email or '',
            user.phone_number or '',
            user.address or '',
            user.badge_employee_id or '',
            user.section_unit or '',
            profile.rank or '',
            profile.unit or '',
            profile.duty_phone or '',
            profile.personal_phone or '',
            profile.personal_email or '',
            profile.emergency_contact_name or '',
            profile.emergency_contact_relationship or '',
            profile.emergency_contact_phone or '',
            profile.emergency_contact_address or '',
        ]
    )

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='officer_profile_export_csv',
            details=f'user_id={user.id}',
        )
    )
    db.session.commit()
    return current_app.response_class(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=officer-{user.id}.csv'},
    )
