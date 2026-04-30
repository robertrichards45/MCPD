import csv
import io
import json
import os
import re
import uuid
import zipfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from urllib.parse import quote_plus

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    ArmoryAsset,
    ArmoryOfficerCard,
    ArmoryTransaction,
    AuditLog,
    RfiAppointmentUpload,
    RfiWeaponProfile,
    TruckGateCompany,
    TruckGateDriver,
    TruckGateImportRun,
    TruckGateLog,
    TruckGateVehicle,
    User,
    VehicleInspection,
)
from ..permissions import can_access_armory, can_access_rfi, can_access_truck_gate, can_manage_armory, can_manage_rfi, can_manage_truck_gate
from ..services.rfi_defaults import COMMAND_LEVEL_KEYS, default_rfi_identifiers, is_command_level_role
from ..services.armory_import import parse_armory_asset_upload
from ..services.truck_gate_daily_file import build_daily_workbook, daily_workbook_abspath, daily_workbook_filename, daily_workbook_relpath
from ..services.truck_gate_import import (
    DEFAULT_TRUCK_GATE_SOURCE,
    commit_truck_gate_import,
    prepare_truck_gate_row,
    preview_truck_gate_import,
    upsert_truck_gate_row,
)
from ..services.vehicle_inspection_files import (
    build_single_export_bundle,
    build_day_export_zip,
    inspection_template_directory,
    list_template_images,
    template_image_abspath,
    write_inspection_export,
)
from ..services.vehicle_inspection_calibration import (
    clone_first_page_settings_to_all,
    clone_template_settings_to_all,
    calibration_by_filename,
    import_calibration_csv_text,
    import_calibration_config,
    load_calibration,
    nudge_template_settings,
    reset_all_calibration,
    reset_template_position,
    reset_template_scale,
    reset_template_settings,
    update_template_settings,
)
from ..services.vehicle_inspection_overlay import (
    calibrated_field_layout,
    calibrated_overlay_fields,
    calibrated_signature_boxes,
    calibrated_signature_layout,
)

bp = Blueprint('ops_modules', __name__)

try:
    EASTERN_TZ = ZoneInfo('America/New_York')
except ZoneInfoNotFoundError:
    EASTERN_TZ = None


def _get_or_404(model, object_id):
    obj = db.session.get(model, object_id)
    if obj is None:
        abort(404)
    return obj


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_sensitive_cac_path():
    path = (request.path or '').lower()
    return (
        path.startswith('/armory')
        or path.startswith('/truck-gate')
        or path.startswith('/rfi')
    )


def _has_verified_cac_session():
    verify_header = current_app.config.get('CAC_VERIFY_HEADER', 'X-CAC-VERIFY')
    identifier_header = current_app.config.get('CAC_IDENTIFIER_HEADER', 'X-CAC-IDENTIFIER')
    verify_value = (request.headers.get(verify_header, '') or '').strip().upper()
    identifier_value = (request.headers.get(identifier_header, '') or '').strip()
    if verify_value != 'SUCCESS' or not identifier_value:
        return False
    if not getattr(current_user, 'is_authenticated', False):
        return False
    if getattr(current_user, 'cac_identifier', None):
        return current_user.cac_identifier == identifier_value
    return False


@bp.before_request
def enforce_sensitive_module_cac():
    if not current_app.config.get('CAC_AUTH_ENABLED'):
        return None
    if not _is_sensitive_cac_path():
        return None
    if not _has_verified_cac_session():
        abort(403, description='CAC required to access this section.')
    return None


def _display_now():
    if EASTERN_TZ is not None:
        return datetime.now(EASTERN_TZ).strftime('%Y-%m-%d %H:%M:%S ET')
    return datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')


def _current_et_date():
    if EASTERN_TZ is not None:
        return datetime.now(EASTERN_TZ).strftime('%Y-%m-%d')
    return datetime.now().astimezone().strftime('%Y-%m-%d')


def _is_valid_log_date(value):
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return True
    except (TypeError, ValueError):
        return False


def _resolve_log_date(value=None):
    candidate = (value or '').strip()
    if candidate and _is_valid_log_date(candidate):
        return candidate
    return _current_et_date()


def _daily_file_name(log_date):
    return daily_workbook_filename(log_date)


def _daily_export_relpath(log_date):
    return daily_workbook_relpath(log_date)


def _recent_truck_gate_entries(limit=8, log_date=None):
    query = TruckGateLog.query
    if log_date:
        query = query.filter_by(log_date=log_date)
    logs = query.order_by(TruckGateLog.created_at.desc(), TruckGateLog.id.desc()).limit(limit).all()
    items = []
    for log in logs:
        driver = log.driver
        company_name = log.company.name if log.company else (driver.company.name if driver and driver.company else 'Unassigned Company')
        plate = ''
        vehicle = log.vehicle
        if vehicle:
            plate = ' '.join(part for part in [vehicle.plate_number, vehicle.plate_state] if part)
        pieces = [
            driver.full_name if driver else 'Unknown Driver',
            company_name,
        ]
        if plate:
            pieces.append(plate)
        if log.inspection_type:
            pieces.append(log.inspection_type)
        if driver and driver.destination:
            pieces.append(driver.destination)
        items.append(' | '.join(pieces))
    return items


def _daily_truck_gate_logs(log_date, search_term='', inspection_filter=''):
    query = TruckGateLog.query.filter_by(log_date=log_date)
    term = (search_term or '').strip().lower()
    filter_value = (inspection_filter or '').strip()
    if filter_value:
        query = query.filter(TruckGateLog.inspection_type == filter_value)

    logs = query.order_by(TruckGateLog.created_at.asc(), TruckGateLog.id.asc()).all()
    if not term:
        return logs

    filtered = []
    for log in logs:
        driver = log.driver
        vehicle = log.vehicle
        company = log.company or (driver.company if driver else None)
        haystack = ' '.join(
            [
                driver.full_name if driver else '',
                company.name if company else '',
                driver.license_number if driver else '',
                driver.license_state if driver else '',
                vehicle.plate_number if vehicle else '',
                vehicle.plate_state if vehicle else '',
                vehicle.make_model_color if vehicle else '',
                log.inspection_type or '',
                driver.destination if driver else '',
                driver.visit_type if driver else '',
                log.scan_token or '',
                log.notes or '',
            ]
        ).lower()
        if term in haystack:
            filtered.append(log)
    return filtered


def _render_truck_gate(preview=None, import_result=None):
    log_date = _current_et_date()
    import_runs = TruckGateImportRun.query.order_by(TruckGateImportRun.created_at.desc()).limit(5).all()
    recent_logs = _daily_truck_gate_logs(log_date)
    return render_template(
        'truck_gate.html',
        user=current_user,
        can_manage_module=can_manage_truck_gate(current_user),
        module_title='Truck Gate',
        module_key='TRUCK_GATE',
        last_updated=_display_now(),
        default_source_path=DEFAULT_TRUCK_GATE_SOURCE,
        import_preview=preview,
        import_result=import_result,
        import_runs=import_runs,
        driver_total=TruckGateDriver.query.count(),
        company_total=TruckGateCompany.query.count(),
        vehicle_total=TruckGateVehicle.query.count(),
        today_log_total=len(recent_logs),
        import_run_total=len(import_runs),
        current_log_date=log_date,
        daily_file_name=_daily_file_name(log_date),
        daily_export_relpath=_daily_export_relpath(log_date),
        recent_logs=recent_logs,
        driver_options=TruckGateDriver.query.order_by(TruckGateDriver.full_name.asc()).limit(500).all(),
    )


def _truck_gate_database_rows(limit=500, search_term=''):
    query = TruckGateDriver.query
    term = (search_term or '').strip()
    if term:
        like = f'%{term}%'
        query = query.outerjoin(TruckGateCompany, TruckGateDriver.company_id == TruckGateCompany.id).filter(
            db.or_(
                TruckGateDriver.full_name.ilike(like),
                TruckGateDriver.license_number.ilike(like),
                TruckGateDriver.license_state.ilike(like),
                TruckGateDriver.phone_number.ilike(like),
                TruckGateDriver.destination.ilike(like),
                TruckGateDriver.visit_type.ilike(like),
                TruckGateCompany.name.ilike(like),
                TruckGateCompany.phone_number.ilike(like),
            )
        )

    drivers = (
        query.order_by(TruckGateDriver.full_name.asc(), TruckGateDriver.id.asc())
        .limit(limit)
        .all()
    )
    rows = []
    for driver in drivers:
        vehicle = None
        if driver.vehicles:
            vehicle = sorted(driver.vehicles, key=lambda item: item.updated_at or item.created_at, reverse=True)[0]
        if term and vehicle:
            haystack = ' '.join(
                [
                    vehicle.plate_number or '',
                    vehicle.plate_state or '',
                    vehicle.make_model_color or '',
                ]
            ).lower()
            if term.lower() not in haystack:
                driver_haystack = ' '.join(
                    [
                        driver.full_name or '',
                        driver.license_number or '',
                        driver.license_state or '',
                        driver.phone_number or '',
                        driver.destination or '',
                        driver.visit_type or '',
                        driver.company.name if driver.company else '',
                        driver.company.phone_number if driver.company and driver.company.phone_number else '',
                    ]
                ).lower()
                if term.lower() not in driver_haystack:
                    continue
        elif term and not vehicle:
            driver_haystack = ' '.join(
                [
                    driver.full_name or '',
                    driver.license_number or '',
                    driver.license_state or '',
                    driver.phone_number or '',
                    driver.destination or '',
                    driver.visit_type or '',
                    driver.company.name if driver.company else '',
                    driver.company.phone_number if driver.company and driver.company.phone_number else '',
                ]
            ).lower()
            if term.lower() not in driver_haystack:
                continue
        rows.append(
            {
                'driver': driver,
                'company': driver.company,
                'vehicle': vehicle,
                'license_display': ' '.join(part for part in [driver.license_number or '', driver.license_state or ''] if part).strip(),
                'plate_display': ' '.join(part for part in [vehicle.plate_number, vehicle.plate_state] if vehicle and part).strip() if vehicle else '',
            }
        )
    return rows


def _render_truck_gate_daily_log(log_date):
    build_daily_workbook(log_date)
    search_term = (request.args.get('q') or '').strip()
    inspection_filter = (request.args.get('inspection_type') or '').strip()
    logs = _daily_truck_gate_logs(log_date, search_term=search_term, inspection_filter=inspection_filter)
    summary = {
        'total': len(logs),
        'unique_drivers': len({item.driver_id for item in logs if item.driver_id}),
        'full_inspections': sum(1 for item in logs if (item.inspection_type or '') == '100% Inspection'),
        'normal_ops': sum(1 for item in logs if (item.inspection_type or '') == 'Normal Ops'),
    }
    return render_template(
        'truck_gate_daily_log.html',
        user=current_user,
        can_manage_module=can_manage_truck_gate(current_user),
        module_title='Truck Gate Daily Log',
        module_key='TRUCK_GATE',
        last_updated=_display_now(),
        current_log_date=log_date,
        daily_file_name=_daily_file_name(log_date),
        daily_export_relpath=_daily_export_relpath(log_date),
        logs=logs,
        truck_gate_day_summary=summary,
        truck_gate_search_term=search_term,
        truck_gate_inspection_filter=inspection_filter,
        driver_options=TruckGateDriver.query.order_by(TruckGateDriver.full_name.asc()).limit(500).all(),
    )


def _rfi_profiles(limit=500, search_term=''):
    query = RfiWeaponProfile.query
    term = (search_term or '').strip()
    if term:
        like = f'%{term}%'
        query = query.filter(
            db.or_(
                RfiWeaponProfile.first_name.ilike(like),
                RfiWeaponProfile.last_name.ilike(like),
                RfiWeaponProfile.officer_number.ilike(like),
                RfiWeaponProfile.rack_number.ilike(like),
                RfiWeaponProfile.weapon_serial_number.ilike(like),
                RfiWeaponProfile.radio_identifier.ilike(like),
                RfiWeaponProfile.oc_identifier.ilike(like),
            )
        )
    return (
        query.order_by(RfiWeaponProfile.last_name.asc(), RfiWeaponProfile.first_name.asc(), RfiWeaponProfile.id.asc())
        .limit(limit)
        .all()
    )


def _rfi_pending_uploads(limit=20, search_term=''):
    query = RfiAppointmentUpload.query
    term = (search_term or '').strip()
    if term:
        like = f'%{term}%'
        query = query.filter(
            db.or_(
                RfiAppointmentUpload.original_filename.ilike(like),
                RfiAppointmentUpload.extracted_first_name.ilike(like),
                RfiAppointmentUpload.extracted_last_name.ilike(like),
                RfiAppointmentUpload.extracted_officer_number.ilike(like),
                RfiAppointmentUpload.extracted_rack_number.ilike(like),
                RfiAppointmentUpload.extracted_weapon_serial_number.ilike(like),
                RfiAppointmentUpload.status.ilike(like),
            )
        )
    return (
        query.order_by(RfiAppointmentUpload.created_at.desc(), RfiAppointmentUpload.id.desc())
        .limit(limit)
        .all()
    )


def _recent_rfi_activity(limit=10):
    items = []
    pending_count = RfiAppointmentUpload.query.filter(RfiAppointmentUpload.status != 'COMMITTED').count()
    if pending_count:
        items.append(f'Pending review queue: {pending_count}')

    logs = (
        AuditLog.query.filter(AuditLog.action.like('rfi_%'))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .all()
    )
    for log in logs:
        when = log.created_at.strftime('%H:%M:%S') if log.created_at else ''
        action = (log.action or '').replace('_', ' ').title()
        details = (log.details or '').strip()
        if details:
            items.append(f'{when} | {action} | {details}')
        else:
            items.append(f'{when} | {action}')
    return items[:limit]


def _rfi_profile_form_state():
    profile_id = (request.args.get('edit_profile_id') or '').strip()
    if not profile_id.isdigit():
        return None
    return db.session.get(RfiWeaponProfile, int(profile_id))


def _guess_name_parts_from_filename(filename):
    name = os.path.splitext(os.path.basename(filename or ''))[0]
    cleaned = []
    for piece in name.replace('-', ' ').replace('_', ' ').split():
        if piece and piece.isalpha():
            cleaned.append(piece.title())
    if len(cleaned) >= 2:
        return cleaned[0], cleaned[-1]
    if cleaned:
        return cleaned[0], ''
    return '', ''


def _extract_rfi_hints_from_filename(filename):
    name = os.path.splitext(os.path.basename(filename or ''))[0]
    officer_match = re.search(r'(?:officer|badge|id|no)[^\d]*([0-9]{3,10})', name, re.IGNORECASE)
    rack_match = re.search(r'(?:rack|rk)[^A-Za-z0-9]*([A-Za-z0-9-]{1,20})', name, re.IGNORECASE)
    serial_match = re.search(r'(?:serial|sn)[^A-Za-z0-9]*([A-Za-z0-9-]{3,40})', name, re.IGNORECASE)
    return {
        'officer_number': officer_match.group(1) if officer_match else '',
        'rack_number': rack_match.group(1).upper() if rack_match else '',
        'weapon_serial_number': serial_match.group(1).upper() if serial_match else '',
    }


def _armory_users():
    return (
        User.query.filter(User.active.is_(True))
        .order_by(User.last_name.asc(), User.first_name.asc(), User.username.asc())
        .all()
    )


def _armory_assets():
    search_term = (request.args.get('asset_q') or '').strip()
    status_filter = (request.args.get('asset_status') or '').strip().upper()
    query = ArmoryAsset.query
    if search_term:
        like = f'%{search_term}%'
        query = query.filter(
            db.or_(
                ArmoryAsset.asset_type.ilike(like),
                ArmoryAsset.label.ilike(like),
                ArmoryAsset.rack_number.ilike(like),
                ArmoryAsset.serial_number.ilike(like),
                ArmoryAsset.radio_identifier.ilike(like),
                ArmoryAsset.oc_identifier.ilike(like),
            )
        )
    if status_filter:
        query = query.filter_by(status=status_filter)
    return (
        query.order_by(
            ArmoryAsset.asset_type.asc(),
            ArmoryAsset.rack_number.asc(),
            ArmoryAsset.serial_number.asc(),
            ArmoryAsset.id.asc(),
        )
        .all()
    )


def _armory_cards():
    return ArmoryOfficerCard.query.order_by(ArmoryOfficerCard.created_at.desc(), ArmoryOfficerCard.id.desc()).limit(40).all()


def _armory_transactions():
    date_from = (request.args.get('date_from') or '').strip()
    date_to = (request.args.get('date_to') or '').strip()
    officer_id = (request.args.get('officer_id') or '').strip()
    query = ArmoryTransaction.query
    if officer_id.isdigit():
        query = query.filter(ArmoryTransaction.user_id == int(officer_id))
    if date_from:
        try:
            query = query.filter(ArmoryTransaction.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(ArmoryTransaction.created_at < datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        except ValueError:
            pass
    return (
        query.order_by(ArmoryTransaction.created_at.desc(), ArmoryTransaction.id.desc())
        .limit(200)
        .all()
    )


def _render_armory():
    assets = _armory_assets()
    transactions = _armory_transactions()
    rfi_search_term = (request.args.get('q') or '').strip()
    rfi_pending_search_term = (request.args.get('pending_q') or '').strip()
    pending_uploads = _rfi_pending_uploads(search_term=rfi_pending_search_term)
    visible_profiles = _rfi_profiles(search_term=rfi_search_term)
    total_profiles = RfiWeaponProfile.query.count()
    command_profiles = RfiWeaponProfile.query.filter(RfiWeaponProfile.is_command_level.is_(True)).count()
    summary = {
        'total': len(transactions),
        'issue_count': sum(1 for item in transactions if item.action == 'ISSUE'),
        'return_count': sum(1 for item in transactions if item.action == 'RETURN'),
        'void_count': sum(1 for item in transactions if item.status == 'VOID'),
        'open_count': sum(1 for item in transactions if item.status == 'OPEN'),
    }
    return render_template(
        'armory.html',
        user=current_user,
        title='RFI',
        module_title='RFI',
        module_key='RFI',
        last_updated=_display_now(),
        can_access_armory_module=can_access_armory(current_user),
        can_manage_armory_module=can_manage_armory(current_user),
        can_access_rfi_module=can_access_rfi(current_user),
        can_manage_rfi_module=can_manage_rfi(current_user),
        assets=assets,
        armory_asset_total=len(assets),
        armory_users=_armory_users(),
        cards=_armory_cards(),
        transactions=transactions,
        armory_summary=summary,
        armory_asset_q=(request.args.get('asset_q') or '').strip(),
        armory_asset_status=(request.args.get('asset_status') or '').strip().upper(),
        armory_date_from=(request.args.get('date_from') or '').strip(),
        armory_date_to=(request.args.get('date_to') or '').strip(),
        armory_officer_id=(request.args.get('officer_id') or '').strip(),
        command_role_options=sorted(COMMAND_LEVEL_KEYS),
        editing_profile=_rfi_profile_form_state(),
        profiles=visible_profiles,
        pending_uploads=pending_uploads,
        search_term=rfi_search_term,
        pending_search_term=rfi_pending_search_term,
        rfi_total_profiles=total_profiles,
        rfi_command_profiles=command_profiles,
        rfi_pending_count=sum(1 for item in pending_uploads if item.status != 'COMMITTED'),
    )


def _vehicle_inspections(log_date=None, search_term='', status_filter=''):
    query = VehicleInspection.query
    if log_date:
        query = query.filter_by(inspection_date=log_date)
    term = (search_term or '').strip()
    if term:
        query = query.filter(VehicleInspection.vehicle_number.ilike(f'%{term}%'))
    status_value = (status_filter or '').strip().upper()
    if status_value:
        query = query.filter_by(status=status_value)
    return query.order_by(VehicleInspection.created_at.desc(), VehicleInspection.id.desc()).limit(100).all()


def _vehicle_inspection_form_state():
    inspection_id = (request.args.get('inspection_id') or '').strip()
    if not inspection_id.isdigit():
        return None
    return db.session.get(VehicleInspection, int(inspection_id))


def _vehicle_condition_map(inspection):
    values = {
        'lights': '',
        'tires': '',
        'equipment': '',
        'cleanliness': '',
    }
    raw = (inspection.condition_json or '').strip()
    if not raw:
        return values
    for piece in raw.split(';'):
        if '=' not in piece:
            continue
        key, value = piece.split('=', 1)
        key = key.strip()
        if key in values:
            values[key] = value.strip()
    return values


def _selected_armory_cards():
    selected_ids = []
    for raw_value in request.args.getlist('card_id'):
        value = (raw_value or '').strip()
        if value.isdigit():
            selected_ids.append(int(value))

    query = ArmoryOfficerCard.query
    if request.args.get('all') == '1':
        query = query.filter_by(status='ACTIVE')
    elif selected_ids:
        query = query.filter(ArmoryOfficerCard.id.in_(selected_ids))
    else:
        single_id = (request.args.get('card_id') or '').strip()
        if single_id.isdigit():
            query = query.filter_by(id=int(single_id))
        else:
            return []

    return query.order_by(ArmoryOfficerCard.created_at.desc(), ArmoryOfficerCard.id.desc()).all()


@bp.route('/truck-gate', methods=['GET'])
@login_required
def truck_gate():
    if not can_access_truck_gate(current_user):
        abort(403)
    return _render_truck_gate()


@bp.route('/armory', methods=['GET'])
@login_required
def armory():
    if not (can_access_armory(current_user) or can_access_rfi(current_user)):
        abort(403)
    query_args = request.args.to_dict(flat=True)
    return redirect(url_for('ops_modules.rfi', **query_args))


@bp.route('/armory/pin', methods=['POST'])
@login_required
def armory_set_pin():
    if not (can_manage_armory(current_user) or can_manage_rfi(current_user)):
        abort(403)

    user_id = (request.form.get('user_id') or '').strip()
    pin_value = (request.form.get('pin_value') or '').strip()
    if not user_id.isdigit():
        flash('Select an officer before setting a PIN.', 'error')
        return redirect(url_for('ops_modules.rfi'))
    if not pin_value.isdigit() or len(pin_value) < 4 or len(pin_value) > 6:
        flash('PIN must be 4 to 6 digits.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    target_user = db.session.get(User, int(user_id))
    if not target_user:
        flash('That officer was not found.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    target_user.set_pin(pin_value)
    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='armory_pin_set',
            details=f'user_id={target_user.id}',
        )
    )
    db.session.commit()
    flash(f'RFI PIN updated for {target_user.display_name}.', 'success')
    return redirect(url_for('ops_modules.rfi'))


@bp.route('/rfi/pin', methods=['POST'])
@login_required
def rfi_set_pin():
    return armory_set_pin()


@bp.route('/armory/assets', methods=['POST'])
@login_required
def armory_asset_save():
    if not (can_manage_armory(current_user) or can_manage_rfi(current_user)):
        abort(403)

    asset_type = (request.form.get('asset_type') or '').strip().upper()
    label = (request.form.get('label') or '').strip()
    serial_number = (request.form.get('serial_number') or '').strip().upper()
    rack_number = (request.form.get('rack_number') or '').strip() or None
    radio_identifier = (request.form.get('radio_identifier') or '').strip() or None
    oc_identifier = (request.form.get('oc_identifier') or '').strip() or None
    asset_id = (request.form.get('asset_id') or '').strip()

    if not asset_type or not label or not serial_number:
        flash('Asset type, label, and serial number are required.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    asset = None
    if asset_id.isdigit():
        asset = db.session.get(ArmoryAsset, int(asset_id))
    if asset is None:
        asset = ArmoryAsset.query.filter_by(asset_type=asset_type, serial_number=serial_number).first()

    if asset is None:
        asset = ArmoryAsset(created_by=current_user.id)
        db.session.add(asset)

    asset.asset_type = asset_type
    asset.label = label
    asset.serial_number = serial_number
    asset.rack_number = rack_number
    asset.radio_identifier = radio_identifier
    asset.oc_identifier = oc_identifier
    asset.updated_by = current_user.id

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='armory_asset_save',
            details=f'{asset_type}|serial={serial_number}|rack={rack_number or ""}',
        )
    )
    db.session.commit()
    flash('RFI asset saved.', 'success')
    return redirect(url_for('ops_modules.rfi'))


@bp.route('/rfi/assets', methods=['POST'])
@login_required
def rfi_asset_save():
    return armory_asset_save()


@bp.route('/armory/assets/import', methods=['POST'])
@login_required
def armory_asset_import():
    if not (can_manage_armory(current_user) or can_manage_rfi(current_user)):
        abort(403)

    upload_file = request.files.get('asset_file')
    if not upload_file or not upload_file.filename:
        flash('Select a CSV or XLSX file to import.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    try:
        rows = parse_armory_asset_upload(upload_file)
    except Exception as exc:
        flash(f'Unable to import RFI asset file: {exc}', 'error')
        return redirect(url_for('ops_modules.rfi'))

    inserted_count = 0
    updated_count = 0
    for row in rows:
        asset = ArmoryAsset.query.filter_by(
            asset_type=row['asset_type'],
            serial_number=row['serial_number'],
        ).first()
        if asset is None:
            asset = ArmoryAsset(created_by=current_user.id)
            db.session.add(asset)
            inserted_count += 1
        else:
            updated_count += 1

        asset.asset_type = row['asset_type']
        asset.label = row['label']
        asset.serial_number = row['serial_number']
        asset.rack_number = row['rack_number']
        asset.radio_identifier = row['radio_identifier']
        asset.oc_identifier = row['oc_identifier']
        asset.updated_by = current_user.id

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='armory_asset_import',
            details=f'rows={len(rows)}|inserted={inserted_count}|updated={updated_count}',
        )
    )
    db.session.commit()
    flash(f'RFI import complete. Inserted {inserted_count}, updated {updated_count}.', 'success')
    return redirect(url_for('ops_modules.rfi'))


@bp.route('/rfi/assets/import', methods=['POST'])
@login_required
def rfi_asset_import():
    return armory_asset_import()


@bp.route('/armory/assets/export.csv', methods=['GET'])
@login_required
def armory_asset_export_csv():
    if not (can_access_armory(current_user) or can_access_rfi(current_user)):
        abort(403)
    return redirect(url_for('ops_modules.rfi_asset_export_csv', **request.args.to_dict(flat=True)))


@bp.route('/rfi/assets/export.csv', methods=['GET'])
@login_required
def rfi_asset_export_csv():
    if not (can_access_armory(current_user) or can_access_rfi(current_user)):
        abort(403)

    assets = _armory_assets()
    asset_q = (request.args.get('asset_q') or '').strip()
    asset_status = (request.args.get('asset_status') or '').strip().upper()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            'asset_type',
            'label',
            'rack_number',
            'serial_number',
            'radio_identifier',
            'oc_identifier',
            'status',
            'current_holder',
            'updated_at_et',
        ]
    )
    for asset in assets:
        writer.writerow(
            [
                asset.asset_type,
                asset.label,
                asset.rack_number or '',
                asset.serial_number,
                asset.radio_identifier or '',
                asset.oc_identifier or '',
                asset.status,
                asset.current_holder.display_name if asset.current_holder else '',
                _display_dt(asset.updated_at or asset.created_at),
            ]
        )

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='armory_asset_export_csv',
            details=f'rows={len(assets)}|asset_q={asset_q}|asset_status={asset_status}',
        )
    )
    db.session.commit()
    return current_app.response_class(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=rfi-assets.csv'},
    )


@bp.route('/armory/assets/<int:asset_id>/export.csv', methods=['GET'])
@login_required
def armory_asset_single_export_csv(asset_id):
    if not (can_access_armory(current_user) or can_access_rfi(current_user)):
        abort(403)
    return redirect(url_for('ops_modules.rfi_asset_single_export_csv', asset_id=asset_id))


@bp.route('/rfi/assets/<int:asset_id>/export.csv', methods=['GET'])
@login_required
def rfi_asset_single_export_csv(asset_id):
    if not (can_access_armory(current_user) or can_access_rfi(current_user)):
        abort(403)

    asset = _get_or_404(ArmoryAsset, asset_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            'asset_type',
            'label',
            'rack_number',
            'serial_number',
            'radio_identifier',
            'oc_identifier',
            'status',
            'current_holder',
            'updated_at_et',
        ]
    )
    writer.writerow(
        [
            asset.asset_type,
            asset.label,
            asset.rack_number or '',
            asset.serial_number,
            asset.radio_identifier or '',
            asset.oc_identifier or '',
            asset.status,
            asset.current_holder.display_name if asset.current_holder else '',
            _display_dt(asset.updated_at or asset.created_at),
        ]
    )

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='armory_asset_single_export_csv',
            details=f'asset_id={asset.id}',
        )
    )
    db.session.commit()
    return current_app.response_class(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=rfi-asset-{asset.id}.csv'},
    )


@bp.route('/armory/card', methods=['POST'])
@login_required
def armory_card_issue():
    if not (can_manage_armory(current_user) or can_manage_rfi(current_user)):
        abort(403)

    user_id = (request.form.get('user_id') or '').strip()
    if not user_id.isdigit():
        flash('Select an officer before issuing a card.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    target_user = db.session.get(User, int(user_id))
    if not target_user:
        flash('That officer was not found.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    active_cards = ArmoryOfficerCard.query.filter_by(user_id=target_user.id, status='ACTIVE').all()
    for card in active_cards:
        card.status = 'REVOKED'
        card.revoked_by = current_user.id
        card.revoked_at = _utcnow_naive()

    new_card = ArmoryOfficerCard(
        user_id=target_user.id,
        token_id=uuid.uuid4().hex,
        created_by=current_user.id,
    )
    db.session.add(new_card)
    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='armory_card_issue',
            details=f'user_id={target_user.id}|token={new_card.token_id}',
        )
    )
    db.session.commit()
    flash(f'New RFI card issued for {target_user.display_name}.', 'success')
    return redirect(url_for('ops_modules.rfi'))


@bp.route('/rfi/card', methods=['POST'])
@login_required
def rfi_card_issue():
    return armory_card_issue()


@bp.route('/armory/cards/print', methods=['GET'])
@login_required
def armory_cards_print():
    if not (can_access_armory(current_user) or can_access_rfi(current_user)):
        abort(403)
    redirect_args = []
    for value in request.args.getlist('card_id'):
        redirect_args.append(('card_id', value))
    if request.args.get('all') == '1':
        redirect_args.append(('all', '1'))
    return redirect(url_for('ops_modules.rfi_cards_print', **dict(redirect_args)) if len(redirect_args) <= 1 else url_for('ops_modules.rfi_cards_print') + ('?' + '&'.join([f'{key}={value}' for key, value in redirect_args])))


@bp.route('/rfi/cards/print', methods=['GET'])
@login_required
def rfi_cards_print():
    if not (can_access_armory(current_user) or can_access_rfi(current_user)):
        abort(403)

    cards = _selected_armory_cards()
    if not cards:
        flash('Select one or more RFI cards to print first.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='armory_cards_print',
            details=f'cards={len(cards)}',
        )
    )
    db.session.commit()
    return render_template(
        'armory_cards_print.html',
        title='RFI Cards',
        user=current_user,
        module_title='RFI',
        cards=cards,
        printed_at=_display_now(),
    )


@bp.route('/armory/transaction', methods=['POST'])
@login_required
def armory_transaction_save():
    if not (can_manage_armory(current_user) or can_manage_rfi(current_user)):
        abort(403)

    user_id = (request.form.get('user_id') or '').strip()
    asset_id = (request.form.get('asset_id') or '').strip()
    action = (request.form.get('action') or '').strip().upper()
    officer_pin = (request.form.get('officer_pin') or '').strip()
    rounds_raw = (request.form.get('rounds_count') or '').strip()
    notes = (request.form.get('notes') or '').strip() or None

    if not user_id.isdigit() or not asset_id.isdigit():
        flash('Select both an officer and an asset.', 'error')
        return redirect(url_for('ops_modules.rfi'))
    if action not in {'ISSUE', 'RETURN'}:
        flash('Select a valid RFI action.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    officer = db.session.get(User, int(user_id))
    asset = db.session.get(ArmoryAsset, int(asset_id))
    if not officer or not asset:
        flash('The selected officer or asset was not found.', 'error')
        return redirect(url_for('ops_modules.rfi'))
    if not officer.check_pin(officer_pin):
        flash('Officer PIN verification failed.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    rounds_count = int(rounds_raw) if rounds_raw.isdigit() else None
    active_card = (
        ArmoryOfficerCard.query.filter_by(user_id=officer.id, status='ACTIVE')
        .order_by(ArmoryOfficerCard.created_at.desc(), ArmoryOfficerCard.id.desc())
        .first()
    )

    if action == 'ISSUE':
        if asset.status == 'CHECKED_OUT':
            flash('That asset is already checked out.', 'error')
            return redirect(url_for('ops_modules.rfi'))
        asset.status = 'CHECKED_OUT'
        asset.current_holder_id = officer.id
    else:
        asset.status = 'AVAILABLE'
        asset.current_holder_id = None

    transaction = ArmoryTransaction(
        user_id=officer.id,
        asset_id=asset.id,
        card_id=active_card.id if active_card else None,
        action=action,
        rounds_count=rounds_count,
        notes=notes,
        performed_by=current_user.id,
    )
    db.session.add(transaction)
    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='armory_transaction',
            details=f'{action}|user_id={officer.id}|asset_id={asset.id}|serial={asset.serial_number}',
        )
    )
    db.session.commit()
    flash(f'RFI {action.lower()} recorded for {officer.display_name}.', 'success')
    return redirect(url_for('ops_modules.rfi'))


@bp.route('/rfi/transaction', methods=['POST'])
@login_required
def rfi_transaction_save():
    return armory_transaction_save()


@bp.route('/armory/transaction/void', methods=['POST'])
@login_required
def armory_transaction_void():
    if not (can_manage_armory(current_user) or can_manage_rfi(current_user)):
        abort(403)

    transaction_id = (request.form.get('transaction_id') or '').strip()
    void_reason = (request.form.get('void_reason') or '').strip()
    if not transaction_id.isdigit():
        flash('Select a valid RFI transaction to void.', 'error')
        return redirect(url_for('ops_modules.rfi'))
    if not void_reason:
        flash('A void reason is required.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    transaction = db.session.get(ArmoryTransaction, int(transaction_id))
    if not transaction:
        flash('That RFI transaction was not found.', 'error')
        return redirect(url_for('ops_modules.rfi'))
    if transaction.voided_at is not None:
        flash('That transaction has already been voided.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    transaction.status = 'VOID'
    transaction.voided_at = _utcnow_naive()
    transaction.void_reason = void_reason

    if transaction.asset:
        if transaction.action == 'ISSUE':
            transaction.asset.status = 'AVAILABLE'
            transaction.asset.current_holder_id = None
        elif transaction.action == 'RETURN':
            transaction.asset.status = 'CHECKED_OUT'
            transaction.asset.current_holder_id = transaction.user_id

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='armory_transaction_void',
            details=f'transaction_id={transaction.id}|reason={void_reason}',
        )
    )
    db.session.commit()
    flash('RFI transaction voided.', 'success')
    return redirect(url_for('ops_modules.rfi'))


@bp.route('/rfi/transaction/void', methods=['POST'])
@login_required
def rfi_transaction_void():
    return armory_transaction_void()


@bp.route('/armory/transaction/<int:transaction_id>/export.csv', methods=['GET'])
@login_required
def armory_transaction_export_csv(transaction_id):
    if not (can_access_armory(current_user) or can_access_rfi(current_user)):
        abort(403)
    return redirect(url_for('ops_modules.rfi_transaction_export_csv', transaction_id=transaction_id))


@bp.route('/rfi/transaction/<int:transaction_id>/export.csv', methods=['GET'])
@login_required
def rfi_transaction_export_csv(transaction_id):
    if not (can_access_armory(current_user) or can_access_rfi(current_user)):
        abort(403)

    transaction = _get_or_404(ArmoryTransaction, transaction_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            'created_at_et',
            'officer',
            'action',
            'status',
            'asset_type',
            'asset_label',
            'serial_number',
            'rack_number',
            'radio_identifier',
            'oc_identifier',
            'rounds_count',
            'notes',
            'void_reason',
        ]
    )
    writer.writerow(
        [
            _display_dt(transaction.created_at),
            transaction.user.display_name if transaction.user else '',
            transaction.action or '',
            transaction.status or '',
            transaction.asset.asset_type if transaction.asset else '',
            transaction.asset.label if transaction.asset else '',
            transaction.asset.serial_number if transaction.asset else '',
            transaction.asset.rack_number if transaction.asset else '',
            transaction.asset.radio_identifier if transaction.asset else '',
            transaction.asset.oc_identifier if transaction.asset else '',
            transaction.rounds_count if transaction.rounds_count is not None else '',
            transaction.notes or '',
            transaction.void_reason or '',
        ]
    )

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='armory_transaction_export_csv',
            details=f'transaction_id={transaction.id}',
        )
    )
    db.session.commit()
    return current_app.response_class(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=rfi-transaction-{transaction.id}.csv'},
    )


@bp.route('/armory/export.csv', methods=['GET'])
@login_required
def armory_export_csv():
    if not (can_access_armory(current_user) or can_access_rfi(current_user)):
        abort(403)
    return redirect(url_for('ops_modules.rfi_export_csv_log', **request.args.to_dict(flat=True)))


@bp.route('/rfi/export-log.csv', methods=['GET'])
@login_required
def rfi_export_csv_log():
    if not (can_access_armory(current_user) or can_access_rfi(current_user)):
        abort(403)

    transactions = _armory_transactions()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        'created_at',
        'officer',
        'action',
        'status',
        'asset_type',
        'asset_label',
        'serial_number',
        'rounds_count',
        'notes',
        'void_reason',
    ])
    for transaction in transactions:
        writer.writerow([
            transaction.created_at.strftime('%Y-%m-%d %H:%M:%S') if transaction.created_at else '',
            transaction.user.display_name if transaction.user else '',
            transaction.action,
            transaction.status,
            transaction.asset.asset_type if transaction.asset else '',
            transaction.asset.label if transaction.asset else '',
            transaction.asset.serial_number if transaction.asset else '',
            transaction.rounds_count if transaction.rounds_count is not None else '',
            transaction.notes or '',
            transaction.void_reason or '',
        ])

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='armory_export_csv',
            details=f'rows={len(transactions)}|date_from={(request.args.get("date_from") or "").strip()}|date_to={(request.args.get("date_to") or "").strip()}',
        )
    )
    db.session.commit()
    payload = buffer.getvalue()
    return current_app.response_class(
        payload,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=rfi-transactions.csv',
        },
    )


@bp.route('/vehicle-inspections', methods=['GET'])
@login_required
def vehicle_inspections():
    log_date = _resolve_log_date(request.args.get('date'))
    search_term = (request.args.get('q') or '').strip()
    status_filter = (request.args.get('status') or '').strip().upper()
    inspections = _vehicle_inspections(log_date, search_term=search_term, status_filter=status_filter)
    template_images = list_template_images()
    summary = {
        'total': len(inspections),
        'draft': sum(1 for item in inspections if item.status == 'DRAFT'),
        'returned': sum(1 for item in inspections if item.status == 'RETURNED'),
        'complete': sum(1 for item in inspections if item.status == 'COMPLETE'),
    }
    return render_template(
        'vehicle_inspections.html',
        user=current_user,
        module_title='Vehicle Inspections',
        module_key='VEHICLE_INSPECTIONS',
        last_updated=_display_now(),
        current_log_date=log_date,
        inspections=inspections,
        inspection_summary=summary,
        editing_inspection=_vehicle_inspection_form_state(),
        vehicle_search_term=search_term,
        vehicle_status_filter=status_filter,
        inspection_template_dir=inspection_template_directory(),
        inspection_template_images=template_images,
        inspection_template_calibration=load_calibration(),
    )


@bp.route('/vehicle-inspections/template-calibration', methods=['GET', 'POST'])
@login_required
def vehicle_inspection_template_calibration():
    if request.method == 'POST':
        filename = (request.form.get('filename') or '').strip()
        try:
            x_offset = int((request.form.get('global_x_offset') or '0').strip())
        except ValueError:
            x_offset = 0
        try:
            y_offset = int((request.form.get('global_y_offset') or '0').strip())
        except ValueError:
            y_offset = 0
        try:
            scale = float((request.form.get('global_scale') or '1.0').strip())
        except ValueError:
            scale = 1.0

        updated = update_template_settings(filename, x_offset, y_offset, scale)
        if updated:
            flash(f'Updated calibration for {filename}.', 'success')
        else:
            flash('That template file was not found in the calibration map.', 'error')
        if filename:
            return redirect(url_for('ops_modules.vehicle_inspection_template_calibration', filename=filename))
        return redirect(url_for('ops_modules.vehicle_inspection_template_calibration'))

    calibration = load_calibration()
    only_filename = (request.args.get('filename') or '').strip()
    show_defaults_only = (request.args.get('defaults_only') or '').strip() == '1'
    template_names = [item.get('filename') for item in calibration.get('templates', []) if item.get('filename')]
    total_template_count = len(template_names)
    calibrated_template_count = 0
    for item in calibration.get('templates', []):
        page_index = item.get('page_index', 0)
        x_offset = int(item.get('global_x_offset', 0) or 0)
        y_offset = int(item.get('global_y_offset', 0) or 0)
        scale = float(item.get('global_scale', 1.0) or 1.0)
        if not (x_offset == 0 and y_offset == 0 and abs(scale - 1.0) < 0.0001):
            calibrated_template_count += 1
        if page_index == 0:
            item['field_markers'] = calibrated_field_layout(item)
            item['signature_markers'] = calibrated_signature_layout(item)
        else:
            item['field_markers'] = []
            item['signature_markers'] = []
    visible_templates = [
        item
        for item in calibration.get('templates', [])
        if (
            (not only_filename or item.get('filename') == only_filename)
            and (
                not show_defaults_only
                or (
                    int(item.get('global_x_offset', 0) or 0) == 0
                    and int(item.get('global_y_offset', 0) or 0) == 0
                    and abs(float(item.get('global_scale', 1.0) or 1.0) - 1.0) < 0.0001
                )
            )
        )
    ]
    selected_template = None
    if only_filename:
        for item in calibration.get('templates', []):
            if item.get('filename') == only_filename:
                selected_template = item
                break
    selected_template_previous = None
    selected_template_next = None
    if only_filename and only_filename in template_names:
        index = template_names.index(only_filename)
        if index > 0:
            selected_template_previous = template_names[index - 1]
        if index < len(template_names) - 1:
            selected_template_next = template_names[index + 1]
    selected_template_position = None
    if only_filename and only_filename in template_names:
        selected_template_position = template_names.index(only_filename) + 1
    previous_uncalibrated_template = None
    reverse_templates = list(calibration.get('templates', []))
    if only_filename and only_filename in template_names:
        current_index = template_names.index(only_filename)
        reverse_templates = list(reversed(reverse_templates[:current_index])) + list(reversed(reverse_templates[current_index + 1:]))
    else:
        reverse_templates = list(reversed(reverse_templates))
    for item in reverse_templates:
        filename = item.get('filename')
        if not filename or filename == only_filename:
            continue
        x_offset = int(item.get('global_x_offset', 0) or 0)
        y_offset = int(item.get('global_y_offset', 0) or 0)
        scale = float(item.get('global_scale', 1.0) or 1.0)
        if x_offset == 0 and y_offset == 0 and abs(scale - 1.0) < 0.0001:
            previous_uncalibrated_template = filename
            break
    previous_adjusted_template = None
    reverse_templates = list(calibration.get('templates', []))
    if only_filename and only_filename in template_names:
        current_index = template_names.index(only_filename)
        reverse_templates = list(reversed(reverse_templates[:current_index])) + list(reversed(reverse_templates[current_index + 1:]))
    else:
        reverse_templates = list(reversed(reverse_templates))
    for item in reverse_templates:
        filename = item.get('filename')
        if not filename or filename == only_filename:
            continue
        x_offset = int(item.get('global_x_offset', 0) or 0)
        y_offset = int(item.get('global_y_offset', 0) or 0)
        scale = float(item.get('global_scale', 1.0) or 1.0)
        if not (x_offset == 0 and y_offset == 0 and abs(scale - 1.0) < 0.0001):
            previous_adjusted_template = filename
            break
    next_adjusted_template = None
    ordered_templates = list(calibration.get('templates', []))
    if only_filename and only_filename in template_names:
        current_index = template_names.index(only_filename)
        ordered_templates = ordered_templates[current_index + 1:] + ordered_templates[:current_index]
    for item in ordered_templates:
        filename = item.get('filename')
        if not filename or filename == only_filename:
            continue
        x_offset = int(item.get('global_x_offset', 0) or 0)
        y_offset = int(item.get('global_y_offset', 0) or 0)
        scale = float(item.get('global_scale', 1.0) or 1.0)
        if not (x_offset == 0 and y_offset == 0 and abs(scale - 1.0) < 0.0001):
            next_adjusted_template = filename
            break
    next_uncalibrated_template = None
    ordered_templates = list(calibration.get('templates', []))
    if only_filename and only_filename in template_names:
        current_index = template_names.index(only_filename)
        ordered_templates = ordered_templates[current_index + 1:] + ordered_templates[:current_index]
    for item in ordered_templates:
        filename = item.get('filename')
        if not filename or filename == only_filename:
            continue
        x_offset = int(item.get('global_x_offset', 0) or 0)
        y_offset = int(item.get('global_y_offset', 0) or 0)
        scale = float(item.get('global_scale', 1.0) or 1.0)
        if x_offset == 0 and y_offset == 0 and abs(scale - 1.0) < 0.0001:
            next_uncalibrated_template = filename
            break

    return render_template(
        'vehicle_inspection_calibration.html',
        user=current_user,
        module_title='Vehicle Inspection Calibration',
        module_key='VEHICLE_INSPECTIONS',
        last_updated=_display_now(),
        inspection_template_dir=inspection_template_directory(),
        inspection_template_images=list_template_images(),
        inspection_template_calibration=calibration,
        calibration_visible_templates=visible_templates,
        selected_template_filename=only_filename,
        selected_template=selected_template,
        show_defaults_only=show_defaults_only,
        first_template_filename=(template_names[0] if template_names else None),
        last_template_filename=(template_names[-1] if template_names else None),
        selected_template_position=selected_template_position,
        selected_template_previous=selected_template_previous,
        selected_template_next=selected_template_next,
        previous_uncalibrated_template=previous_uncalibrated_template,
        previous_adjusted_template=previous_adjusted_template,
        next_adjusted_template=next_adjusted_template,
        next_uncalibrated_template=next_uncalibrated_template,
        total_template_count=total_template_count,
        calibrated_template_count=calibrated_template_count,
        uncalibrated_template_count=max(total_template_count - calibrated_template_count, 0),
    )


@bp.route('/vehicle-inspections/template-calibration/reset', methods=['POST'])
@login_required
def vehicle_inspection_template_calibration_reset():
    filename = (request.form.get('filename') or '').strip()
    focus_filename = (request.form.get('focus_filename') or '').strip()
    if filename:
        updated = reset_template_settings(filename)
        if updated:
            flash(f'Reset calibration for {filename}.', 'success')
        else:
            flash('That template file was not found in the calibration map.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspection_template_calibration', filename=filename))
    else:
        reset_all_calibration()
        flash('Reset all vehicle inspection template calibration values.', 'success')
        if focus_filename:
            return redirect(url_for('ops_modules.vehicle_inspection_template_calibration', filename=focus_filename))
        return redirect(url_for('ops_modules.vehicle_inspection_template_calibration'))


@bp.route('/vehicle-inspections/template-calibration/clone-page-one', methods=['POST'])
@login_required
def vehicle_inspection_template_calibration_clone_page_one():
    focus_filename = (request.form.get('focus_filename') or '').strip()
    clone_first_page_settings_to_all()
    flash('Copied page 1 calibration values to all inspection sheet templates.', 'success')
    if focus_filename:
        return redirect(url_for('ops_modules.vehicle_inspection_template_calibration', filename=focus_filename))
    return redirect(url_for('ops_modules.vehicle_inspection_template_calibration'))


@bp.route('/vehicle-inspections/template-calibration/clone-template', methods=['POST'])
@login_required
def vehicle_inspection_template_calibration_clone_template():
    filename = (request.form.get('filename') or '').strip()
    if not filename:
        flash('Select a template first.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspection_template_calibration'))
    elif clone_template_settings_to_all(filename):
        flash(f'Copied calibration values from {filename} to all inspection sheet templates.', 'success')
    else:
        flash('That template file was not found in the calibration map.', 'error')
    return redirect(url_for('ops_modules.vehicle_inspection_template_calibration', filename=filename))


@bp.route('/vehicle-inspections/template-calibration/nudge', methods=['POST'])
@login_required
def vehicle_inspection_template_calibration_nudge():
    filename = (request.form.get('filename') or '').strip()
    try:
        dx = int((request.form.get('dx') or '0').strip())
    except ValueError:
        dx = 0
    try:
        dy = int((request.form.get('dy') or '0').strip())
    except ValueError:
        dy = 0
    try:
        dscale = float((request.form.get('dscale') or '0').strip())
    except ValueError:
        dscale = 0.0

    if not filename:
        flash('Select a template first.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspection_template_calibration'))
    elif nudge_template_settings(filename, dx=dx, dy=dy, dscale=dscale):
        flash(f'Adjusted {filename} by X={dx}, Y={dy}, Scale={dscale:+.2f}.', 'success')
    else:
        flash('That template file was not found in the calibration map.', 'error')
    return redirect(url_for('ops_modules.vehicle_inspection_template_calibration', filename=filename))


@bp.route('/vehicle-inspections/template-calibration/reset-scale', methods=['POST'])
@login_required
def vehicle_inspection_template_calibration_reset_scale():
    filename = (request.form.get('filename') or '').strip()
    if not filename:
        flash('Select a template first.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspection_template_calibration'))
    elif reset_template_scale(filename):
        flash(f'Reset scale for {filename} to 1.00.', 'success')
    else:
        flash('That template file was not found in the calibration map.', 'error')
    return redirect(url_for('ops_modules.vehicle_inspection_template_calibration', filename=filename))


@bp.route('/vehicle-inspections/template-calibration/reset-position', methods=['POST'])
@login_required
def vehicle_inspection_template_calibration_reset_position():
    filename = (request.form.get('filename') or '').strip()
    if not filename:
        flash('Select a template first.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspection_template_calibration'))
    elif reset_template_position(filename):
        flash(f'Reset position for {filename} to X=0, Y=0.', 'success')
    else:
        flash('That template file was not found in the calibration map.', 'error')
    return redirect(url_for('ops_modules.vehicle_inspection_template_calibration', filename=filename))


@bp.route('/vehicle-inspections/template-calibration/import', methods=['POST'])
@login_required
def vehicle_inspection_template_calibration_import():
    upload = request.files.get('calibration_file')
    focus_filename = (request.form.get('focus_filename') or '').strip()
    if not upload or not upload.filename:
        flash('Select a calibration JSON, CSV, or ZIP file first.', 'error')
        if focus_filename:
            return redirect(url_for('ops_modules.vehicle_inspection_template_calibration', filename=focus_filename))
        return redirect(url_for('ops_modules.vehicle_inspection_template_calibration'))

    def _import_payload(payload):
        if import_calibration_config(payload):
            return True
        if isinstance(payload, dict):
            template = payload.get('template')
            if isinstance(template, dict):
                wrapped = {
                    'templates': [
                        {
                            'filename': template.get('filename'),
                            'global_x_offset': template.get('global_x_offset', 0),
                            'global_y_offset': template.get('global_y_offset', 0),
                            'global_scale': template.get('global_scale', 1.0),
                        }
                    ]
                }
                return import_calibration_config(wrapped)
        return False

    try:
        filename = (upload.filename or '').lower()
        if filename.endswith('.zip'):
            with zipfile.ZipFile(upload.stream) as archive:
                names = archive.namelist()
                full_json_name = next((name for name in names if name.endswith('vehicle_inspection_template_map.json')), None)
                single_json_name = next((name for name in names if name.endswith('-map.json')), None)
                csv_name = next((name for name in names if name.endswith('.csv')), None)
                if full_json_name:
                    with archive.open(full_json_name) as handle:
                        payload = json.load(handle)
                    imported = _import_payload(payload)
                elif single_json_name:
                    with archive.open(single_json_name) as handle:
                        payload = json.load(handle)
                    imported = _import_payload(payload)
                elif csv_name:
                    with archive.open(csv_name) as handle:
                        text = handle.read().decode('utf-8-sig', errors='replace')
                    imported = import_calibration_csv_text(text)
                else:
                    flash('That ZIP file does not contain a calibration JSON or CSV file.', 'error')
                    if focus_filename:
                        return redirect(url_for('ops_modules.vehicle_inspection_template_calibration', filename=focus_filename))
                    return redirect(url_for('ops_modules.vehicle_inspection_template_calibration'))
        elif filename.endswith('.csv'):
            text = upload.stream.read().decode('utf-8-sig', errors='replace')
            imported = import_calibration_csv_text(text)
        else:
            payload = json.load(upload.stream)
            imported = _import_payload(payload)
    except Exception:
        flash('That file is not a valid calibration JSON, CSV, or calibration bundle.', 'error')
        if focus_filename:
            return redirect(url_for('ops_modules.vehicle_inspection_template_calibration', filename=focus_filename))
        return redirect(url_for('ops_modules.vehicle_inspection_template_calibration'))

    if imported:
        flash('Vehicle inspection calibration imported.', 'success')
    else:
        flash('That calibration file did not contain usable template calibration rows.', 'error')
    if focus_filename:
        return redirect(url_for('ops_modules.vehicle_inspection_template_calibration', filename=focus_filename))
    return redirect(url_for('ops_modules.vehicle_inspection_template_calibration'))


@bp.route('/vehicle-inspections/template-calibration/test', methods=['GET'])
@login_required
def vehicle_inspection_template_calibration_test():
    calibration = load_calibration()
    only_filename = (request.args.get('filename') or '').strip()
    template_items = []
    for item in calibration.get('templates', []):
        filename = item.get('filename')
        if not filename:
            continue
        if only_filename and filename != only_filename:
            continue
        page_index = item.get('page_index', 0)
        field_markers = calibrated_field_layout(item) if page_index == 0 else []
        signature_markers = calibrated_signature_layout(item) if page_index == 0 else []
        template_items.append(
            {
                'filename': filename,
                'page_index': page_index,
                'x_offset': int(item.get('global_x_offset', 0) or 0),
                'y_offset': int(item.get('global_y_offset', 0) or 0),
                'scale': float(item.get('global_scale', 1.0) or 1.0),
                'field_markers': field_markers,
                'signature_markers': signature_markers,
            }
        )
    return render_template(
        'vehicle_inspection_calibration_test.html',
        user=current_user,
        module_title='Vehicle Inspection Calibration Test',
        module_key='VEHICLE_INSPECTIONS',
        last_updated=_display_now(),
        inspection_template_dir=inspection_template_directory(),
        template_items=template_items,
        selected_template_filename=only_filename,
    )


@bp.route('/vehicle-inspections/template-calibration/map.json', methods=['GET'])
@login_required
def vehicle_inspection_template_calibration_map():
    calibration = load_calibration()
    payload = {
        'template_id': calibration.get('template_id', 'mcpd_vehicle_inspection_v1'),
        'source_directory': inspection_template_directory(),
        'templates': [],
    }
    for item in calibration.get('templates', []):
        filename = item.get('filename')
        if not filename:
            continue
        page_index = item.get('page_index', 0)
        template_payload = {
            'filename': filename,
            'page_index': page_index,
            'global_x_offset': int(item.get('global_x_offset', 0) or 0),
            'global_y_offset': int(item.get('global_y_offset', 0) or 0),
            'global_scale': float(item.get('global_scale', 1.0) or 1.0),
        }
        if page_index == 0:
            template_payload['field_markers'] = calibrated_field_layout(item)
            template_payload['signature_markers'] = calibrated_signature_layout(item)
        else:
            template_payload['field_markers'] = []
            template_payload['signature_markers'] = []
        payload['templates'].append(template_payload)
    return jsonify(payload)


@bp.route('/vehicle-inspections/template-calibration/map.csv', methods=['GET'])
@login_required
def vehicle_inspection_template_calibration_map_csv():
    calibration = load_calibration()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            'filename',
            'page_index',
            'global_x_offset',
            'global_y_offset',
            'global_scale',
            'marker_type',
            'marker_key',
            'marker_label',
            'left',
            'top',
            'width',
            'height',
        ]
    )
    for item in calibration.get('templates', []):
        filename = item.get('filename')
        if not filename:
            continue
        page_index = item.get('page_index', 0)
        base_values = [
            filename,
            page_index,
            int(item.get('global_x_offset', 0) or 0),
            int(item.get('global_y_offset', 0) or 0),
            float(item.get('global_scale', 1.0) or 1.0),
        ]
        if page_index == 0:
            for marker in calibrated_field_layout(item):
                writer.writerow(
                    base_values
                    + [
                        'field',
                        marker.get('key'),
                        marker.get('label'),
                        marker.get('left'),
                        marker.get('top'),
                        '',
                        '',
                    ]
                )
            for marker in calibrated_signature_layout(item):
                writer.writerow(
                    base_values
                    + [
                        'signature',
                        marker.get('key'),
                        marker.get('label'),
                        marker.get('left'),
                        marker.get('top'),
                        marker.get('width'),
                        marker.get('height'),
                    ]
                )
        else:
            writer.writerow(base_values + ['page', '', '', '', '', '', ''])
    return current_app.response_class(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=vehicle-inspection-template-map.csv',
        },
    )


@bp.route('/vehicle-inspections/template-calibration/template.json', methods=['GET'])
@login_required
def vehicle_inspection_template_single_map():
    filename = (request.args.get('filename') or '').strip()
    calibration = load_calibration()
    selected = None
    for item in calibration.get('templates', []):
        if item.get('filename') == filename:
            selected = item
            break
    if selected is None:
        abort(404)

    page_index = selected.get('page_index', 0)
    payload = {
        'template_id': calibration.get('template_id', 'mcpd_vehicle_inspection_v1'),
        'source_directory': inspection_template_directory(),
        'template': {
            'filename': filename,
            'page_index': page_index,
            'global_x_offset': int(selected.get('global_x_offset', 0) or 0),
            'global_y_offset': int(selected.get('global_y_offset', 0) or 0),
            'global_scale': float(selected.get('global_scale', 1.0) or 1.0),
            'field_markers': calibrated_field_layout(selected) if page_index == 0 else [],
            'signature_markers': calibrated_signature_layout(selected) if page_index == 0 else [],
        },
    }
    return current_app.response_class(
        json.dumps(payload, indent=2),
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename=vehicle-inspection-template-{page_index + 1}.json',
        },
    )


@bp.route('/vehicle-inspections/template-calibration/template.csv', methods=['GET'])
@login_required
def vehicle_inspection_template_single_map_csv():
    filename = (request.args.get('filename') or '').strip()
    calibration = load_calibration()
    selected = None
    for item in calibration.get('templates', []):
        if item.get('filename') == filename:
            selected = item
            break
    if selected is None:
        abort(404)

    page_index = selected.get('page_index', 0)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            'filename',
            'page_index',
            'global_x_offset',
            'global_y_offset',
            'global_scale',
            'marker_type',
            'marker_key',
            'marker_label',
            'left',
            'top',
            'width',
            'height',
        ]
    )
    base_values = [
        filename,
        page_index,
        int(selected.get('global_x_offset', 0) or 0),
        int(selected.get('global_y_offset', 0) or 0),
        float(selected.get('global_scale', 1.0) or 1.0),
    ]
    if page_index == 0:
        for marker in calibrated_field_layout(selected):
            writer.writerow(
                base_values
                + [
                    'field',
                    marker.get('key'),
                    marker.get('label'),
                    marker.get('left'),
                    marker.get('top'),
                    '',
                    '',
                ]
            )
        for marker in calibrated_signature_layout(selected):
            writer.writerow(
                base_values
                + [
                    'signature',
                    marker.get('key'),
                    marker.get('label'),
                    marker.get('left'),
                    marker.get('top'),
                    marker.get('width'),
                    marker.get('height'),
                ]
            )
    else:
        writer.writerow(base_values + ['page', '', '', '', '', '', ''])

    return current_app.response_class(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=vehicle-inspection-template-{page_index + 1}.csv',
        },
    )


@bp.route('/vehicle-inspections/template-calibration/template.bundle.zip', methods=['GET'])
@login_required
def vehicle_inspection_template_single_bundle():
    filename = (request.args.get('filename') or '').strip()
    calibration = load_calibration()
    selected = None
    for item in calibration.get('templates', []):
        if item.get('filename') == filename:
            selected = item
            break
    if selected is None:
        abort(404)

    page_index = selected.get('page_index', 0)
    field_markers = calibrated_field_layout(selected) if page_index == 0 else []
    signature_markers = calibrated_signature_layout(selected) if page_index == 0 else []
    payload = {
        'template_id': calibration.get('template_id', 'mcpd_vehicle_inspection_v1'),
        'source_directory': inspection_template_directory(),
        'template': {
            'filename': filename,
            'page_index': page_index,
            'global_x_offset': int(selected.get('global_x_offset', 0) or 0),
            'global_y_offset': int(selected.get('global_y_offset', 0) or 0),
            'global_scale': float(selected.get('global_scale', 1.0) or 1.0),
            'field_markers': field_markers,
            'signature_markers': signature_markers,
        },
    }

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(
        [
            'filename',
            'page_index',
            'global_x_offset',
            'global_y_offset',
            'global_scale',
            'marker_type',
            'marker_key',
            'marker_label',
            'left',
            'top',
            'width',
            'height',
        ]
    )
    base_values = [
        filename,
        page_index,
        int(selected.get('global_x_offset', 0) or 0),
        int(selected.get('global_y_offset', 0) or 0),
        float(selected.get('global_scale', 1.0) or 1.0),
    ]
    if field_markers or signature_markers:
        for marker in field_markers:
            writer.writerow(
                base_values
                + [
                    'field',
                    marker.get('key'),
                    marker.get('label'),
                    marker.get('left'),
                    marker.get('top'),
                    '',
                    '',
                ]
            )
        for marker in signature_markers:
            writer.writerow(
                base_values
                + [
                    'signature',
                    marker.get('key'),
                    marker.get('label'),
                    marker.get('left'),
                    marker.get('top'),
                    marker.get('width'),
                    marker.get('height'),
                ]
            )
    else:
        writer.writerow(base_values + ['page', '', '', '', '', '', ''])

    safe_base = os.path.splitext(os.path.basename(filename))[0] or f'vehicle-inspection-template-{page_index + 1}'
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(
            f'{safe_base}-map.json',
            json.dumps(payload, indent=2),
        )
        bundle.writestr(
            f'{safe_base}-map.csv',
            csv_buffer.getvalue(),
        )
        path = template_image_abspath(filename)
        if path and os.path.isfile(path):
            bundle.write(path, arcname=os.path.join('source_templates', filename))
    archive.seek(0)
    return send_file(
        archive,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{safe_base}-bundle.zip',
    )


@bp.route('/vehicle-inspections/template-calibration/bundle.zip', methods=['GET'])
@login_required
def vehicle_inspection_template_calibration_bundle():
    calibration = load_calibration()
    payload = {
        'template_id': calibration.get('template_id', 'mcpd_vehicle_inspection_v1'),
        'source_directory': inspection_template_directory(),
        'templates': [],
    }
    for item in calibration.get('templates', []):
        filename = item.get('filename')
        if not filename:
            continue
        page_index = item.get('page_index', 0)
        template_payload = {
            'filename': filename,
            'page_index': page_index,
            'global_x_offset': int(item.get('global_x_offset', 0) or 0),
            'global_y_offset': int(item.get('global_y_offset', 0) or 0),
            'global_scale': float(item.get('global_scale', 1.0) or 1.0),
        }
        if page_index == 0:
            template_payload['field_markers'] = calibrated_field_layout(item)
            template_payload['signature_markers'] = calibrated_signature_layout(item)
        else:
            template_payload['field_markers'] = []
            template_payload['signature_markers'] = []
        payload['templates'].append(template_payload)

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(
            'vehicle_inspection_template_map.json',
            json.dumps(payload, indent=2),
        )
        for item in payload['templates']:
            name = item.get('filename')
            path = template_image_abspath(name)
            if path and os.path.isfile(path):
                bundle.write(path, arcname=os.path.join('source_templates', name))
    archive.seek(0)
    return send_file(
        archive,
        mimetype='application/zip',
        as_attachment=True,
        download_name='vehicle-inspection-calibration-bundle.zip',
    )


@bp.route('/vehicle-inspections/save', methods=['POST'])
@login_required
def vehicle_inspection_save():
    inspection_date = _resolve_log_date(request.form.get('inspection_date'))
    vehicle_number = (request.form.get('vehicle_number') or '').strip()
    if not vehicle_number:
        flash('Vehicle number is required.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspections', date=inspection_date))

    inspection_id = (request.form.get('inspection_id') or '').strip()
    inspection = db.session.get(VehicleInspection, int(inspection_id)) if inspection_id.isdigit() else None
    if inspection is None:
        inspection = VehicleInspection(created_by=current_user.id)
        db.session.add(inspection)

    inspection.inspection_date = inspection_date
    inspection.vehicle_number = vehicle_number
    inspection.mileage = (request.form.get('mileage') or '').strip() or None
    inspection.fuel_level = (request.form.get('fuel_level') or '').strip() or None
    inspection.condition_json = (
        f"lights={request.form.get('lights_status','')};"
        f"tires={request.form.get('tires_status','')};"
        f"equipment={request.form.get('equipment_status','')};"
        f"cleanliness={request.form.get('cleanliness_status','')}"
    )
    inspection.remarks = (request.form.get('remarks') or '').strip() or None
    inspection.updated_by = current_user.id

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='vehicle_inspection_save',
            details=f'date={inspection_date}|vehicle={vehicle_number}',
        )
    )
    db.session.commit()
    flash('Vehicle inspection saved.', 'success')
    return redirect(url_for('ops_modules.vehicle_inspections', date=inspection_date))


@bp.route('/vehicle-inspections/sign', methods=['POST'])
@login_required
def vehicle_inspection_sign():
    inspection_id = (request.form.get('inspection_id') or '').strip()
    sign_role = (request.form.get('sign_role') or '').strip().upper()
    signature_data = (request.form.get('signature_data') or '').strip()

    if not inspection_id.isdigit():
        flash('Select a valid inspection first.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspections'))
    if sign_role not in {'OFFICER', 'SGT', 'WATCH_COMMANDER'}:
        flash('Select a valid signature role.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspections'))
    if not signature_data:
        flash('Signature capture is required.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspections', inspection_id=inspection_id))

    inspection = db.session.get(VehicleInspection, int(inspection_id))
    if not inspection:
        flash('That inspection was not found.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspections'))

    now = _utcnow_naive()
    if sign_role == 'OFFICER':
        if inspection.status not in {'DRAFT', 'RETURNED'}:
            flash('Officer signature is only allowed while the sheet is in draft or returned status.', 'error')
            return redirect(url_for('ops_modules.vehicle_inspections', inspection_id=inspection.id, date=inspection.inspection_date))
        inspection.officer_signature = signature_data
        inspection.officer_signed_by = current_user.id
        inspection.officer_signed_at = now
        inspection.sgt_signature = None
        inspection.sgt_signed_by = None
        inspection.sgt_signed_at = None
        inspection.watch_commander_signature = None
        inspection.watch_commander_signed_by = None
        inspection.watch_commander_signed_at = None
        inspection.correction_reason = None
        inspection.returned_at = None
        inspection.status = 'OFFICER_SIGNED'
    elif sign_role == 'SGT':
        if inspection.status != 'OFFICER_SIGNED':
            flash('Patrol Sgt signature is only allowed after the patrol officer signs first.', 'error')
            return redirect(url_for('ops_modules.vehicle_inspections', inspection_id=inspection.id, date=inspection.inspection_date))
        inspection.sgt_signature = signature_data
        inspection.sgt_signed_by = current_user.id
        inspection.sgt_signed_at = now
        inspection.status = 'SGT_SIGNED'
    else:
        if inspection.status != 'SGT_SIGNED':
            flash('Watch Commander signature is only allowed after the Patrol Sgt signs.', 'error')
            return redirect(url_for('ops_modules.vehicle_inspections', inspection_id=inspection.id, date=inspection.inspection_date))
        inspection.watch_commander_signature = signature_data
        inspection.watch_commander_signed_by = current_user.id
        inspection.watch_commander_signed_at = now
        inspection.status = 'COMPLETE'

    inspection.updated_by = current_user.id
    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='vehicle_inspection_sign',
            details=f'inspection_id={inspection.id}|role={sign_role}',
        )
    )
    db.session.commit()
    flash('Vehicle inspection signature saved.', 'success')
    return redirect(url_for('ops_modules.vehicle_inspections', date=inspection.inspection_date))


@bp.route('/vehicle-inspections/return', methods=['POST'])
@login_required
def vehicle_inspection_return():
    inspection_id = (request.form.get('inspection_id') or '').strip()
    correction_reason = (request.form.get('correction_reason') or '').strip()

    if not inspection_id.isdigit():
        flash('Select a valid inspection first.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspections'))
    if not correction_reason:
        flash('A correction reason is required.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspections'))

    inspection = db.session.get(VehicleInspection, int(inspection_id))
    if not inspection:
        flash('That inspection was not found.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspections'))
    if inspection.status == 'COMPLETE':
        flash('Completed inspections cannot be returned through this workflow.', 'error')
        return redirect(url_for('ops_modules.vehicle_inspections', date=inspection.inspection_date))

    inspection.status = 'RETURNED'
    inspection.correction_reason = correction_reason
    inspection.returned_at = _utcnow_naive()
    inspection.sgt_signature = None
    inspection.sgt_signed_by = None
    inspection.sgt_signed_at = None
    inspection.watch_commander_signature = None
    inspection.watch_commander_signed_by = None
    inspection.watch_commander_signed_at = None
    inspection.updated_by = current_user.id

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='vehicle_inspection_return',
            details=f'inspection_id={inspection.id}|reason={correction_reason}',
        )
    )
    db.session.commit()
    flash('Vehicle inspection returned for correction.', 'success')
    return redirect(url_for('ops_modules.vehicle_inspections', date=inspection.inspection_date))


@bp.route('/vehicle-inspections/<int:inspection_id>/print', methods=['GET'])
@login_required
def vehicle_inspection_print(inspection_id):
    inspection = _get_or_404(VehicleInspection, inspection_id)
    template_images = list_template_images()
    calibration_map = calibration_by_filename()
    overlay_preview = []
    overlay_signature_boxes = []
    overlay_template_name = None
    if template_images:
        overlay_template_name = template_images[0]
        active_calibration = calibration_map.get(overlay_template_name, {})
        overlay_preview = calibrated_overlay_fields(
            inspection,
            _vehicle_condition_map(inspection),
            active_calibration,
        )
        overlay_signature_boxes = calibrated_signature_boxes(inspection, active_calibration)
    return render_template(
        'vehicle_inspection_print.html',
        user=current_user,
        inspection=inspection,
        condition_map=_vehicle_condition_map(inspection),
        printed_at=_display_now(),
        batch_mode=False,
        inspection_template_images=template_images,
        inspection_template_calibration_map=calibration_map,
        overlay_preview=overlay_preview,
        overlay_signature_boxes=overlay_signature_boxes,
        overlay_template_name=overlay_template_name,
    )


@bp.route('/vehicle-inspections/print/day', methods=['GET'])
@login_required
def vehicle_inspection_print_day():
    log_date = _resolve_log_date(request.args.get('date'))
    search_term = (request.args.get('q') or '').strip()
    status_filter = (request.args.get('status') or '').strip().upper()
    inspections = _vehicle_inspections(log_date, search_term=search_term, status_filter=status_filter)
    template_images = list_template_images()
    calibration_map = calibration_by_filename()
    batch_overlay_items = []
    overlay_template_name = template_images[0] if template_images else None
    if overlay_template_name:
        active_calibration = calibration_map.get(overlay_template_name, {})
        for item in inspections:
            batch_overlay_items.append(
                {
                    'inspection_id': item.id,
                    'template_name': overlay_template_name,
                    'fields': calibrated_overlay_fields(
                        item,
                        _vehicle_condition_map(item),
                        active_calibration,
                    ),
                    'signatures': calibrated_signature_boxes(item, active_calibration),
                }
            )
    return render_template(
        'vehicle_inspection_print.html',
        user=current_user,
        inspections=inspections,
        current_log_date=log_date,
        printed_at=_display_now(),
        condition_maps={item.id: _vehicle_condition_map(item) for item in inspections},
        batch_mode=True,
        inspection_template_images=template_images,
        inspection_template_calibration_map=calibration_map,
        overlay_preview=[],
        overlay_signature_boxes=[],
        overlay_template_name=overlay_template_name,
        batch_overlay_items=batch_overlay_items,
    )


@bp.route('/vehicle-inspections/templates/<path:filename>', methods=['GET'])
@login_required
def vehicle_inspection_template_file(filename):
    safe_name = os.path.basename(filename or '')
    if not safe_name or safe_name != (filename or ''):
        abort(404)
    path = template_image_abspath(safe_name)
    if not path or not os.path.isfile(path):
        abort(404)
    return send_file(path, as_attachment=False, download_name=safe_name)


@bp.route('/vehicle-inspections/<int:inspection_id>/export-file', methods=['GET'])
@login_required
def vehicle_inspection_export_file(inspection_id):
    inspection = _get_or_404(VehicleInspection, inspection_id)
    path = write_inspection_export(
        inspection,
        _vehicle_condition_map(inspection),
        _display_now(),
        template_names=list_template_images(),
        calibration_map=calibration_by_filename(),
    )
    return send_file(
        path,
        as_attachment=True,
        download_name=os.path.basename(path),
        mimetype='text/html',
    )


@bp.route('/vehicle-inspections/<int:inspection_id>/export.bundle', methods=['GET'])
@login_required
def vehicle_inspection_export_bundle(inspection_id):
    inspection = _get_or_404(VehicleInspection, inspection_id)
    path = build_single_export_bundle(
        inspection,
        _vehicle_condition_map(inspection),
        _display_now(),
        template_names=list_template_images(),
        calibration_map=calibration_by_filename(),
    )
    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='vehicle_inspection_export_bundle',
            details=f'id={inspection.id}|date={inspection.inspection_date}',
        )
    )
    db.session.commit()
    return send_file(
        path,
        as_attachment=True,
        download_name=os.path.basename(path),
        mimetype='application/zip',
    )


@bp.route('/vehicle-inspections/<int:inspection_id>/export.csv', methods=['GET'])
@login_required
def vehicle_inspection_export_csv(inspection_id):
    inspection = _get_or_404(VehicleInspection, inspection_id)
    condition_map = _vehicle_condition_map(inspection)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            'inspection_date',
            'created_at_et',
            'vehicle_number',
            'mileage',
            'fuel_level',
            'lights_status',
            'tires_status',
            'equipment_status',
            'cleanliness_status',
            'remarks',
            'status',
            'officer_signed',
            'sgt_signed',
            'watch_commander_signed',
            'correction_reason',
        ]
    )
    writer.writerow(
        [
            inspection.inspection_date.isoformat() if inspection.inspection_date else '',
            _display_dt(inspection.created_at),
            inspection.vehicle_number or '',
            inspection.mileage or '',
            inspection.fuel_level or '',
            condition_map.get('lights', ''),
            condition_map.get('tires', ''),
            condition_map.get('equipment', ''),
            condition_map.get('cleanliness', ''),
            inspection.remarks or '',
            inspection.status or '',
            'Yes' if inspection.officer_signature else 'No',
            'Yes' if inspection.sgt_signature else 'No',
            'Yes' if inspection.watch_commander_signature else 'No',
            inspection.correction_reason or '',
        ]
    )

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='vehicle_inspection_export_csv',
            details=f'id={inspection.id}|date={inspection.inspection_date}',
        )
    )
    db.session.commit()
    return current_app.response_class(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=vehicle-inspection-{inspection.id}.csv',
        },
    )


@bp.route('/vehicle-inspections/<int:inspection_id>/export.json', methods=['GET'])
@login_required
def vehicle_inspection_export_json(inspection_id):
    inspection = _get_or_404(VehicleInspection, inspection_id)
    condition_map = _vehicle_condition_map(inspection)
    template_images = list_template_images()
    calibration_map = calibration_by_filename()
    overlay_template_name = template_images[0] if template_images else None
    overlay_fields = []
    overlay_signatures = []
    if overlay_template_name:
        active_calibration = calibration_map.get(overlay_template_name, {})
        overlay_fields = calibrated_overlay_fields(inspection, condition_map, active_calibration)
        overlay_signatures = calibrated_signature_boxes(inspection, active_calibration)

    payload = {
        'inspection': {
            'id': inspection.id,
            'inspection_date': str(inspection.inspection_date or ''),
            'created_at_et': _display_dt(inspection.created_at),
            'vehicle_number': inspection.vehicle_number or '',
            'mileage': inspection.mileage or '',
            'fuel_level': inspection.fuel_level or '',
            'remarks': inspection.remarks or '',
            'status': inspection.status or '',
            'correction_reason': inspection.correction_reason or '',
            'officer_signed': bool(inspection.officer_signature),
            'sgt_signed': bool(inspection.sgt_signature),
            'watch_commander_signed': bool(inspection.watch_commander_signature),
        },
        'conditions': condition_map,
        'template_overlay': {
            'template_name': overlay_template_name,
            'calibration': calibration_map.get(overlay_template_name, {}) if overlay_template_name else {},
            'fields': overlay_fields,
            'signatures': [
                {
                    'key': item.get('key'),
                    'label': item.get('label'),
                    'left': item.get('left'),
                    'top': item.get('top'),
                    'width': item.get('width'),
                    'height': item.get('height'),
                    'signed': bool(item.get('image')),
                }
                for item in overlay_signatures
            ],
        },
    }

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='vehicle_inspection_export_json',
            details=f'id={inspection.id}|date={inspection.inspection_date}',
        )
    )
    db.session.commit()
    return current_app.response_class(
        json.dumps(payload, indent=2),
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename=vehicle-inspection-{inspection.id}.json',
        },
    )


@bp.route('/vehicle-inspections/export/day', methods=['GET'])
@login_required
def vehicle_inspection_export_day():
    log_date = _resolve_log_date(request.args.get('date'))
    search_term = (request.args.get('q') or '').strip()
    status_filter = (request.args.get('status') or '').strip().upper()
    inspections = _vehicle_inspections(log_date, search_term=search_term, status_filter=status_filter)
    zip_path = build_day_export_zip(
        log_date,
        inspections,
        {item.id: _vehicle_condition_map(item) for item in inspections},
        _display_now(),
        template_names=list_template_images(),
        calibration_map=calibration_by_filename(),
    )
    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='vehicle_inspection_export_day',
            details=f'date={log_date}|count={len(inspections)}|q={search_term}|status={status_filter}',
        )
    )
    db.session.commit()
    return send_file(
        zip_path,
        as_attachment=True,
        download_name=os.path.basename(zip_path),
        mimetype='application/zip',
    )


@bp.route('/vehicle-inspections/export/day.csv', methods=['GET'])
@login_required
def vehicle_inspection_export_day_csv():
    log_date = _resolve_log_date(request.args.get('date'))
    search_term = (request.args.get('q') or '').strip()
    status_filter = (request.args.get('status') or '').strip().upper()
    inspections = _vehicle_inspections(log_date, search_term=search_term, status_filter=status_filter)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            'inspection_date',
            'created_at_et',
            'vehicle_number',
            'mileage',
            'fuel_level',
            'lights_status',
            'tires_status',
            'equipment_status',
            'cleanliness_status',
            'remarks',
            'status',
            'officer_signed',
            'sgt_signed',
            'watch_commander_signed',
            'correction_reason',
        ]
    )
    for inspection in inspections:
        condition_map = _vehicle_condition_map(inspection)
        writer.writerow(
            [
                inspection.inspection_date.isoformat() if inspection.inspection_date else '',
                _display_dt(inspection.created_at),
                inspection.vehicle_number or '',
                inspection.mileage or '',
                inspection.fuel_level or '',
                condition_map.get('lights', ''),
                condition_map.get('tires', ''),
                condition_map.get('equipment', ''),
                condition_map.get('cleanliness', ''),
                inspection.remarks or '',
                inspection.status or '',
                'Yes' if inspection.officer_signature else 'No',
                'Yes' if inspection.sgt_signature else 'No',
                'Yes' if inspection.watch_commander_signature else 'No',
                inspection.correction_reason or '',
            ]
        )

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='vehicle_inspection_export_day_csv',
            details=f'date={log_date}|count={len(inspections)}|q={search_term}|status={status_filter}',
        )
    )
    db.session.commit()
    return current_app.response_class(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=vehicle-inspections-{log_date}.csv',
        },
    )


@bp.route('/vehicle-inspections/export/day.json', methods=['GET'])
@login_required
def vehicle_inspection_export_day_json():
    log_date = _resolve_log_date(request.args.get('date'))
    search_term = (request.args.get('q') or '').strip()
    status_filter = (request.args.get('status') or '').strip().upper()
    inspections = _vehicle_inspections(log_date, search_term=search_term, status_filter=status_filter)

    template_images = list_template_images()
    calibration_map = calibration_by_filename()
    overlay_template_name = template_images[0] if template_images else None

    rows = []
    for inspection in inspections:
        condition_map = _vehicle_condition_map(inspection)
        active_calibration = calibration_map.get(overlay_template_name, {}) if overlay_template_name else {}
        overlay_fields = (
            calibrated_overlay_fields(inspection, condition_map, active_calibration)
            if overlay_template_name else []
        )
        overlay_signatures = (
            calibrated_signature_boxes(inspection, active_calibration)
            if overlay_template_name else []
        )
        rows.append(
            {
                'inspection': {
                    'id': inspection.id,
                    'inspection_date': str(inspection.inspection_date or ''),
                    'created_at_et': _display_dt(inspection.created_at),
                    'vehicle_number': inspection.vehicle_number or '',
                    'mileage': inspection.mileage or '',
                    'fuel_level': inspection.fuel_level or '',
                    'remarks': inspection.remarks or '',
                    'status': inspection.status or '',
                    'correction_reason': inspection.correction_reason or '',
                    'officer_signed': bool(inspection.officer_signature),
                    'sgt_signed': bool(inspection.sgt_signature),
                    'watch_commander_signed': bool(inspection.watch_commander_signature),
                },
                'conditions': condition_map,
                'template_overlay': {
                    'template_name': overlay_template_name,
                    'calibration': active_calibration,
                    'fields': overlay_fields,
                    'signatures': [
                        {
                            'key': item.get('key'),
                            'label': item.get('label'),
                            'left': item.get('left'),
                            'top': item.get('top'),
                            'width': item.get('width'),
                            'height': item.get('height'),
                            'signed': bool(item.get('image')),
                        }
                        for item in overlay_signatures
                    ],
                },
            }
        )

    payload = {
        'log_date': log_date,
        'query': {
            'q': search_term,
            'status': status_filter,
        },
        'count': len(rows),
        'items': rows,
    }

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='vehicle_inspection_export_day_json',
            details=f'date={log_date}|count={len(rows)}|q={search_term}|status={status_filter}',
        )
    )
    db.session.commit()
    return current_app.response_class(
        json.dumps(payload, indent=2),
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename=vehicle-inspections-{log_date}.json',
        },
    )


@bp.route('/truck-gate/today', methods=['GET'])
@login_required
def truck_gate_today():
    if not can_access_truck_gate(current_user):
        abort(403)
    return redirect(url_for('ops_modules.truck_gate_daily_log', log_date=_current_et_date()))


@bp.route('/truck-gate/logs/<log_date>', methods=['GET'])
@login_required
def truck_gate_daily_log(log_date):
    if not can_access_truck_gate(current_user):
        abort(403)
    resolved = _resolve_log_date(log_date)
    if resolved != log_date:
        return redirect(url_for('ops_modules.truck_gate_daily_log', log_date=resolved))
    return _render_truck_gate_daily_log(resolved)


@bp.route('/truck-gate/database', methods=['GET'])
@login_required
def truck_gate_database():
    if not can_access_truck_gate(current_user):
        abort(403)
    search_term = (request.args.get('q') or '').strip()
    return render_template(
        'truck_gate_database.html',
        user=current_user,
        can_manage_module=can_manage_truck_gate(current_user),
        module_title='Truck Gate Database',
        module_key='TRUCK_GATE',
        last_updated=_display_now(),
        current_log_date=_current_et_date(),
        rows=_truck_gate_database_rows(search_term=search_term),
        search_term=search_term,
    )


@bp.route('/truck-gate/database/export.csv', methods=['GET'])
@login_required
def truck_gate_database_export_csv():
    if not can_access_truck_gate(current_user):
        abort(403)

    search_term = (request.args.get('q') or '').strip()
    rows = _truck_gate_database_rows(limit=5000, search_term=search_term)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            'driver_name',
            'license_number',
            'license_state',
            'company_name',
            'phone_number',
            'vehicle_type',
            'plate_number',
            'plate_state',
            'make_model_color',
            'destination',
            'visit_type',
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row['driver'].full_name,
                row['driver'].license_number or '',
                row['driver'].license_state or '',
                row['company'].name if row['company'] else '',
                row['driver'].phone_number or (row['company'].phone_number if row['company'] else ''),
                row['driver'].vehicle_type or '',
                row['vehicle'].plate_number if row['vehicle'] else '',
                row['vehicle'].plate_state if row['vehicle'] else '',
                row['vehicle'].make_model_color if row['vehicle'] else '',
                row['driver'].destination or '',
                row['driver'].visit_type or '',
            ]
        )

    _write_audit(
        current_user.id,
        'truck_gate_database_export_csv',
        details={'count': len(rows), 'query': search_term},
    )

    data = output.getvalue().encode('utf-8')
    filename = f"truck-gate-database-{datetime.now(ET_ZONE).strftime('%Y-%m-%d')}.csv"
    return send_file(
        io.BytesIO(data),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename,
    )


@bp.route('/truck-gate/workbook', methods=['GET'])
@login_required
def truck_gate_workbook():
    if not can_access_truck_gate(current_user):
        abort(403)
    if not DEFAULT_TRUCK_GATE_SOURCE or not os.path.exists(DEFAULT_TRUCK_GATE_SOURCE):
        flash('The Truck Gate workbook was not found on this PC.', 'error')
        return redirect(url_for('ops_modules.truck_gate'))
    return send_file(
        DEFAULT_TRUCK_GATE_SOURCE,
        as_attachment=False,
        download_name=os.path.basename(DEFAULT_TRUCK_GATE_SOURCE),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@bp.route('/truck-gate/logs/<log_date>/workbook', methods=['GET'])
@login_required
def truck_gate_daily_workbook(log_date):
    if not can_access_truck_gate(current_user):
        abort(403)
    resolved = _resolve_log_date(log_date)
    build_daily_workbook(resolved)
    path = daily_workbook_abspath(resolved)
    return send_file(
        path,
        as_attachment=False,
        download_name=daily_workbook_filename(resolved),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@bp.route('/truck-gate/logs/<log_date>/export.csv', methods=['GET'])
@login_required
def truck_gate_daily_csv(log_date):
    if not can_access_truck_gate(current_user):
        abort(403)

    resolved = _resolve_log_date(log_date)
    search_term = (request.args.get('q') or '').strip()
    inspection_filter = (request.args.get('inspection_type') or '').strip()
    logs = _daily_truck_gate_logs(resolved, search_term=search_term, inspection_filter=inspection_filter)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            'log_date',
            'created_at_et',
            'driver_name',
            'company_name',
            'license_number',
            'license_state',
            'phone_number',
            'vehicle_type',
            'plate_number',
            'plate_state',
            'make_model_color',
            'destination',
            'visit_type',
            'inspection_type',
            'scan_token',
            'notes',
        ]
    )
    for log in logs:
        driver = log.driver
        vehicle = log.vehicle
        company = log.company or (driver.company if driver else None)
        writer.writerow(
            [
                resolved.isoformat(),
                _display_dt(log.created_at),
                driver.full_name if driver else '',
                company.name if company else '',
                driver.license_number if driver else '',
                driver.license_state if driver else '',
                driver.phone_number if driver else '',
                driver.vehicle_type if driver else '',
                vehicle.plate_number if vehicle else '',
                vehicle.plate_state if vehicle else '',
                vehicle.make_model_color if vehicle else '',
                driver.destination if driver else '',
                driver.visit_type if driver else '',
                log.inspection_type or '',
                log.scan_token or '',
                log.notes or '',
            ]
        )

    _write_audit(
        current_user.id,
        'truck_gate_export_csv',
        details={
            'log_date': resolved.isoformat(),
            'count': len(logs),
            'query': search_term,
            'inspection_type': inspection_filter,
        },
    )

    data = output.getvalue().encode('utf-8')
    filename = f"truck-gate-{resolved.isoformat()}.csv"
    return send_file(
        io.BytesIO(data),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename,
    )


@bp.route('/truck-gate/log/<int:log_id>/export.csv', methods=['GET'])
@login_required
def truck_gate_log_export_csv(log_id):
    if not can_access_truck_gate(current_user):
        abort(403)

    log = _get_or_404(TruckGateLog, log_id)
    driver = log.driver
    vehicle = log.vehicle
    company = log.company or (driver.company if driver else None)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            'log_date',
            'created_at_et',
            'driver_name',
            'company_name',
            'license_number',
            'license_state',
            'phone_number',
            'vehicle_type',
            'plate_number',
            'plate_state',
            'make_model_color',
            'destination',
            'visit_type',
            'inspection_type',
            'scan_token',
            'notes',
        ]
    )
    writer.writerow(
        [
            log.log_date.isoformat() if log.log_date else '',
            _display_dt(log.created_at),
            driver.full_name if driver else '',
            company.name if company else '',
            driver.license_number if driver else '',
            driver.license_state if driver else '',
            driver.phone_number if driver else '',
            driver.vehicle_type if driver else '',
            vehicle.plate_number if vehicle else '',
            vehicle.plate_state if vehicle else '',
            vehicle.make_model_color if vehicle else '',
            driver.destination if driver else '',
            driver.visit_type if driver else '',
            log.inspection_type or '',
            log.scan_token or '',
            log.notes or '',
        ]
    )

    _write_audit(
        current_user.id,
        'truck_gate_log_export_csv',
        details={
            'log_id': log.id,
            'log_date': log.log_date.isoformat() if log.log_date else '',
        },
    )

    data = output.getvalue().encode('utf-8')
    filename = f"truck-gate-log-{log.id}.csv"
    return send_file(
        io.BytesIO(data),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename,
    )


@bp.route('/truck-gate/database/add', methods=['POST'])
@login_required
def truck_gate_database_add():
    if not can_manage_truck_gate(current_user):
        abort(403)

    row = prepare_truck_gate_row(
        driver_name=request.form.get('driver_name'),
        license_number=request.form.get('license_number'),
        license_state=request.form.get('license_state'),
        company_name=request.form.get('company_name'),
        phone_number=request.form.get('phone_number'),
        vehicle_type=request.form.get('vehicle_type'),
        plate_number=request.form.get('plate_number'),
        plate_state=request.form.get('plate_state'),
        make_model_color=request.form.get('make_model_color'),
        destination=request.form.get('destination'),
        visit_type=request.form.get('visit_type'),
    )
    if not row['driver_name']:
        flash('Driver name is required for a manual Truck Gate entry.', 'error')
        return redirect(url_for('ops_modules.truck_gate_database'))

    result = upsert_truck_gate_row(row)
    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='truck_gate_manual_upsert',
            details=f"{row['driver_name']}|{row['company_name']}|{row['plate_number']}",
        )
    )
    db.session.commit()

    created_bits = []
    if result['company_created']:
        created_bits.append('company')
    if result['driver_created']:
        created_bits.append('driver')
    if result['vehicle_created']:
        created_bits.append('vehicle')
    if created_bits:
        flash(f"Truck Gate record saved. Created: {', '.join(created_bits)}.", 'success')
    else:
        flash('Truck Gate record updated.', 'success')
    return redirect(url_for('ops_modules.truck_gate_database'))


@bp.route('/truck-gate/qr-labels', methods=['GET'])
@login_required
def truck_gate_qr_labels():
    if not can_access_truck_gate(current_user):
        abort(403)
    print_all = (request.args.get('all') or '').strip() in {'1', 'true', 'yes'}
    selected_ids = [value for value in request.args.getlist('driver_id') if value.strip().isdigit()]
    query = TruckGateDriver.query.order_by(TruckGateDriver.full_name.asc())
    if selected_ids:
        drivers = query.filter(TruckGateDriver.id.in_([int(value) for value in selected_ids])).all()
    elif print_all:
        drivers = query.all()
    else:
        drivers = query.limit(60).all()

    labels = []
    for driver in drivers:
        token = f'TRUCK_GATE:DRIVER:{driver.id}'
        labels.append(
            {
                'driver': driver,
                'token': token,
                'qr_url': f'https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={quote_plus(token)}',
            }
        )

    return render_template(
        'truck_gate_qr_labels.html',
        user=current_user,
        labels=labels,
    )


@bp.route('/truck-gate/import/preview', methods=['POST'])
@login_required
def truck_gate_import_preview():
    if not can_manage_truck_gate(current_user):
        abort(403)
    source_path = (request.form.get('source_path') or '').strip() or DEFAULT_TRUCK_GATE_SOURCE
    try:
        preview = preview_truck_gate_import(source_path)
    except FileNotFoundError:
        flash(f'Truck Gate source file was not found: {source_path}', 'error')
        return _render_truck_gate()
    except Exception as exc:
        flash(f'Unable to preview Truck Gate import: {exc}', 'error')
        return _render_truck_gate()
    return _render_truck_gate(preview=preview)


@bp.route('/truck-gate/import/commit', methods=['POST'])
@login_required
def truck_gate_import_commit():
    if not can_manage_truck_gate(current_user):
        abort(403)
    source_path = (request.form.get('source_path') or '').strip() or DEFAULT_TRUCK_GATE_SOURCE
    try:
        result = commit_truck_gate_import(source_path, actor_id=current_user.id)
    except FileNotFoundError:
        flash(f'Truck Gate source file was not found: {source_path}', 'error')
        return _render_truck_gate()
    except Exception as exc:
        db.session.rollback()
        flash(f'Unable to import Truck Gate workbook: {exc}', 'error')
        return _render_truck_gate()

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='truck_gate_import',
            details=f"{result['source_name']} rows={result['row_count']} inserted={result['inserted_count']} updated={result['updated_count']}",
        )
    )
    db.session.commit()
    flash('Truck Gate import completed successfully.', 'success')
    return _render_truck_gate(import_result=result)


@bp.route('/truck-gate/log', methods=['POST'])
@login_required
def truck_gate_log_create():
    if not can_access_truck_gate(current_user):
        abort(403)

    log_date = _resolve_log_date(request.form.get('log_date'))
    driver_id = (request.form.get('driver_id') or '').strip()
    if not driver_id:
        flash('Select a driver before saving a Truck Gate log entry.', 'error')
        return redirect(url_for('ops_modules.truck_gate_daily_log', log_date=log_date))

    driver = db.session.get(TruckGateDriver, int(driver_id))
    if not driver:
        flash('Selected Truck Gate driver was not found.', 'error')
        return redirect(url_for('ops_modules.truck_gate_daily_log', log_date=log_date))

    vehicle = None
    if driver.vehicles:
        vehicle = sorted(driver.vehicles, key=lambda item: item.updated_at or item.created_at, reverse=True)[0]

    inspection_type = (request.form.get('inspection_type') or '').strip() or None
    scan_token = (request.form.get('scan_token') or '').strip() or None
    notes = (request.form.get('notes') or '').strip() or None

    log = TruckGateLog(
        driver_id=driver.id,
        company_id=driver.company_id,
        vehicle_id=vehicle.id if vehicle else None,
        log_date=log_date,
        daily_file_name=_daily_file_name(log_date),
        inspection_type=inspection_type,
        scan_token=scan_token,
        notes=notes,
        created_by=current_user.id,
    )
    db.session.add(log)
    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='truck_gate_log_create',
            details=f'{driver.full_name}|{inspection_type or "UNSPECIFIED"}',
        )
    )
    db.session.commit()
    build_daily_workbook(log_date)
    flash('Truck Gate log entry saved.', 'success')
    return redirect(url_for('ops_modules.truck_gate_daily_log', log_date=log_date))


@bp.route('/truck-gate/feed')
@login_required
def truck_gate_feed():
    if not can_access_truck_gate(current_user):
        abort(403)
    log_date = _resolve_log_date(request.args.get('log_date'))
    return jsonify(
        {
            'module': 'truck_gate',
            'last_updated': _display_now(),
            'log_date': log_date,
            'daily_file_name': _daily_file_name(log_date),
            'entries': _recent_truck_gate_entries(log_date=log_date),
        }
    )


@bp.route('/rfi')
@login_required
def rfi():
    if not (can_access_rfi(current_user) or can_access_armory(current_user)):
        abort(403)
    return _render_armory()


@bp.route('/rfi/export.csv')
@login_required
def rfi_export_csv():
    if not can_access_rfi(current_user):
        abort(403)

    search_term = (request.args.get('q') or '').strip()
    profiles = _rfi_profiles(limit=5000, search_term=search_term)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            'name',
            'officer_number',
            'role_level',
            'rack_number',
            'weapon_serial_number',
            'weapon_type',
            'oc_identifier',
            'radio_identifier',
            'updated_at_et',
        ]
    )
    for profile in profiles:
        writer.writerow(
            [
                profile.display_name,
                profile.officer_number or '',
                profile.role_level or 'STANDARD',
                profile.rack_number or '',
                profile.weapon_serial_number or '',
                profile.weapon_type or '',
                profile.oc_identifier or '',
                profile.radio_identifier or '',
                _display_dt(profile.updated_at),
            ]
        )

    _write_audit(
        current_user.id,
        'rfi_export_csv',
        details={
            'query': search_term,
            'count': len(profiles),
        },
    )

    data = output.getvalue().encode('utf-8')
    filename = f"rfi-weapons-{datetime.now(ET_ZONE).strftime('%Y-%m-%d')}.csv"
    return send_file(
        io.BytesIO(data),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename,
    )


@bp.route('/rfi/pending/export.csv')
@login_required
def rfi_pending_export_csv():
    if not can_access_rfi(current_user):
        abort(403)

    pending_search_term = (request.args.get('pending_q') or '').strip()
    pending_uploads = _rfi_pending_uploads(limit=5000, search_term=pending_search_term)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            'created_at_et',
            'original_filename',
            'status',
            'first_name',
            'last_name',
            'officer_number',
            'rack_number',
            'weapon_serial_number',
            'committed_profile_id',
        ]
    )
    for item in pending_uploads:
        writer.writerow(
            [
                _display_dt(item.created_at),
                item.original_filename or '',
                item.status or '',
                item.extracted_first_name or '',
                item.extracted_last_name or '',
                item.extracted_officer_number or '',
                item.extracted_rack_number or '',
                item.extracted_weapon_serial_number or '',
                item.committed_profile_id or '',
            ]
        )

    _write_audit(
        current_user.id,
        'rfi_pending_export_csv',
        details={
            'count': len(pending_uploads),
            'query': pending_search_term,
        },
    )

    data = output.getvalue().encode('utf-8')
    filename = f"rfi-pending-{datetime.now(ET_ZONE).strftime('%Y-%m-%d')}.csv"
    return send_file(
        io.BytesIO(data),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename,
    )


@bp.route('/rfi/profile/<int:profile_id>/export.csv')
@login_required
def rfi_profile_export_csv(profile_id):
    if not can_access_rfi(current_user):
        abort(403)

    profile = _get_or_404(RfiWeaponProfile, profile_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            'name',
            'officer_number',
            'role_level',
            'is_command_level',
            'rack_number',
            'weapon_serial_number',
            'weapon_type',
            'oc_identifier',
            'radio_identifier',
            'updated_at_et',
        ]
    )
    writer.writerow(
        [
            profile.display_name,
            profile.officer_number or '',
            profile.role_level or 'STANDARD',
            'Yes' if profile.is_command_level else 'No',
            profile.rack_number or '',
            profile.weapon_serial_number or '',
            profile.weapon_type or '',
            profile.oc_identifier or '',
            profile.radio_identifier or '',
            _display_dt(profile.updated_at),
        ]
    )

    _write_audit(
        current_user.id,
        'rfi_profile_export_csv',
        details={
            'profile_id': profile.id,
            'officer_number': profile.officer_number or '',
        },
    )

    data = output.getvalue().encode('utf-8')
    filename = f"rfi-profile-{profile.id}.csv"
    return send_file(
        io.BytesIO(data),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename,
    )


@bp.route('/rfi/profile', methods=['POST'])
@login_required
def rfi_profile_save():
    if not can_manage_rfi(current_user):
        abort(403)

    first_name = (request.form.get('first_name') or '').strip()
    last_name = (request.form.get('last_name') or '').strip()
    if not first_name or not last_name:
        flash('First name and last name are required for RFI profiles.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    role_level = (request.form.get('role_level') or '').strip().upper()
    rack_number = (request.form.get('rack_number') or '').strip()
    officer_number = (request.form.get('officer_number') or '').strip() or None
    weapon_serial_number = (request.form.get('weapon_serial_number') or '').strip() or None
    weapon_type = (request.form.get('weapon_type') or '').strip() or None

    profile_id = (request.form.get('profile_id') or '').strip()
    profile = None
    if profile_id.isdigit():
        profile = db.session.get(RfiWeaponProfile, int(profile_id))

    if not profile and officer_number:
        profile = RfiWeaponProfile.query.filter_by(officer_number=officer_number).first()

    exclude_profile_id = profile.id if profile else None
    defaults = default_rfi_identifiers(
        rack_number=rack_number,
        first_name=first_name,
        last_name=last_name,
        role_level=role_level,
        exclude_profile_id=exclude_profile_id,
    )

    oc_identifier = (request.form.get('oc_identifier') or '').strip() or defaults['oc_identifier'] or None
    radio_identifier = (request.form.get('radio_identifier') or '').strip() or defaults['radio_identifier'] or None

    if profile is None:
        profile = RfiWeaponProfile(
            created_by=current_user.id,
        )
        db.session.add(profile)

    profile.first_name = first_name
    profile.last_name = last_name
    profile.officer_number = officer_number
    profile.role_level = role_level or None
    profile.rack_number = rack_number or None
    profile.weapon_serial_number = weapon_serial_number
    profile.weapon_type = weapon_type
    profile.oc_identifier = oc_identifier
    profile.radio_identifier = radio_identifier
    profile.is_command_level = is_command_level_role(role_level)
    profile.updated_by = current_user.id

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='rfi_profile_save',
            details=f'{profile.last_name},{profile.first_name}|rack={profile.rack_number or ""}|radio={profile.radio_identifier or ""}|oc={profile.oc_identifier or ""}',
        )
    )
    db.session.commit()
    flash('RFI weapon profile saved.', 'success')
    return redirect(url_for('ops_modules.rfi'))


@bp.route('/rfi/profile/reset-defaults', methods=['POST'])
@login_required
def rfi_profile_reset_defaults():
    if not can_manage_rfi(current_user):
        abort(403)

    profile_id = (request.form.get('profile_id') or '').strip()
    if not profile_id.isdigit():
        flash('Select a valid RFI profile first.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    profile = db.session.get(RfiWeaponProfile, int(profile_id))
    if not profile:
        flash('That RFI profile was not found.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    defaults = default_rfi_identifiers(
        rack_number=profile.rack_number or '',
        first_name=profile.first_name or '',
        last_name=profile.last_name or '',
        role_level=profile.role_level or '',
        exclude_profile_id=profile.id,
    )

    profile.oc_identifier = defaults['oc_identifier'] or None
    profile.radio_identifier = defaults['radio_identifier'] or None
    profile.updated_by = current_user.id

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='rfi_profile_reset_defaults',
            details=f'{profile.last_name},{profile.first_name}|rack={profile.rack_number or ""}|radio={profile.radio_identifier or ""}|oc={profile.oc_identifier or ""}',
        )
    )
    db.session.commit()
    flash('RFI defaults reapplied.', 'success')
    return redirect(url_for('ops_modules.rfi', edit_profile_id=profile.id))


@bp.route('/rfi/appointment-letters/commit', methods=['POST'])
@login_required
def rfi_appointment_letter_commit():
    if not can_manage_rfi(current_user):
        abort(403)

    upload_id = (request.form.get('upload_id') or '').strip()
    if not upload_id.isdigit():
        flash('Select a pending appointment letter record first.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    upload = db.session.get(RfiAppointmentUpload, int(upload_id))
    if not upload:
        flash('That pending appointment letter record was not found.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    first_name = (request.form.get('first_name') or '').strip()
    last_name = (request.form.get('last_name') or '').strip()
    if not first_name or not last_name:
        flash('First name and last name are required before committing a pending upload.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    officer_number = (request.form.get('officer_number') or '').strip() or None
    role_level = (request.form.get('role_level') or '').strip().upper()
    rack_number = (request.form.get('rack_number') or '').strip()
    weapon_serial_number = (request.form.get('weapon_serial_number') or '').strip() or None
    weapon_type = (request.form.get('weapon_type') or '').strip() or None

    profile = None
    if officer_number:
        profile = RfiWeaponProfile.query.filter_by(officer_number=officer_number).first()

    exclude_profile_id = profile.id if profile else None
    defaults = default_rfi_identifiers(
        rack_number=rack_number,
        first_name=first_name,
        last_name=last_name,
        role_level=role_level,
        exclude_profile_id=exclude_profile_id,
    )
    oc_identifier = (request.form.get('oc_identifier') or '').strip() or defaults['oc_identifier'] or None
    radio_identifier = (request.form.get('radio_identifier') or '').strip() or defaults['radio_identifier'] or None

    if profile is None:
        profile = RfiWeaponProfile(created_by=current_user.id)
        db.session.add(profile)

    profile.first_name = first_name
    profile.last_name = last_name
    profile.officer_number = officer_number
    profile.role_level = role_level or None
    profile.rack_number = rack_number or None
    profile.weapon_serial_number = weapon_serial_number
    profile.weapon_type = weapon_type
    profile.oc_identifier = oc_identifier
    profile.radio_identifier = radio_identifier
    profile.is_command_level = is_command_level_role(role_level)
    profile.updated_by = current_user.id
    db.session.flush()

    upload.extracted_first_name = first_name
    upload.extracted_last_name = last_name
    upload.extracted_officer_number = officer_number
    upload.extracted_rack_number = rack_number or None
    upload.extracted_weapon_serial_number = weapon_serial_number
    upload.status = 'COMMITTED'
    upload.committed_profile_id = profile.id

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='rfi_appointment_commit',
            details=f'{upload.original_filename}|{last_name},{first_name}|rack={rack_number}',
        )
    )
    db.session.commit()
    flash('Pending appointment letter committed into the RFI database.', 'success')
    return redirect(url_for('ops_modules.rfi'))


@bp.route('/rfi/appointment-letters/upload', methods=['POST'])
@login_required
def rfi_appointment_letter_upload():
    if not can_manage_rfi(current_user):
        abort(403)

    files = request.files.getlist('appointment_letters')
    if not files:
        flash('Select one or more appointment letters to upload.', 'error')
        return redirect(url_for('ops_modules.rfi'))

    created = 0
    for file in files:
        if not file or not file.filename:
            continue
        safe_name = os.path.basename(file.filename)
        guessed_first_name, guessed_last_name = _guess_name_parts_from_filename(safe_name)
        extracted_hints = _extract_rfi_hints_from_filename(safe_name)
        db.session.add(
            RfiAppointmentUpload(
                original_filename=safe_name,
                file_path='',
                status='PENDING_REVIEW',
                extracted_first_name=guessed_first_name or None,
                extracted_last_name=guessed_last_name or None,
                extracted_officer_number=extracted_hints['officer_number'] or None,
                extracted_weapon_serial_number=extracted_hints['weapon_serial_number'] or None,
                extracted_rack_number=extracted_hints['rack_number'] or None,
                created_by=current_user.id,
            )
        )
        created += 1

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='rfi_appointment_upload',
            details=f'metadata_entries={created}',
        )
    )
    db.session.commit()
    flash(f'{created} appointment letter entrie(s) staged for review. The file is not stored; only the extracted info is queued for the RFI weapons list.', 'success')
    return redirect(url_for('ops_modules.rfi'))


@bp.route('/rfi/feed')
@login_required
def rfi_feed():
    if not can_access_rfi(current_user):
        abort(403)
    return jsonify(
        {
            'module': 'rfi',
            'last_updated': _display_now(),
            'entries': _recent_rfi_activity(),
        }
    )
