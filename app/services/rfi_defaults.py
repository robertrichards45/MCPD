from ..models import RfiWeaponProfile


COMMAND_LEVEL_KEYS = {'WEBSITE_CONTROLLER', 'WATCH_COMMANDER', 'RFI_WATCH_COMMANDER'}


def is_command_level_role(role_level):
    return (role_level or '').strip().upper() in COMMAND_LEVEL_KEYS


def _normalize_code(value):
    return ''.join(ch for ch in str(value or '').upper() if ch.isalnum())


def _existing_identifier(code, exclude_profile_id=None):
    if not code:
        return None
    query = RfiWeaponProfile.query.filter_by(radio_identifier=code)
    if exclude_profile_id:
        query = query.filter(RfiWeaponProfile.id != exclude_profile_id)
    return query.first()


def _build_unique_command_code(last_name, first_name, exclude_profile_id=None):
    last = _normalize_code(last_name)
    first = _normalize_code(first_name)
    if not last:
        last = 'X'

    candidates = []
    candidates.append(last[:1])
    if len(last) >= 2:
        candidates.append(last[:2])
    if first:
        candidates.append(last[:1] + first[:1])
    if len(last) >= 2 and first:
        candidates.append(last[:1] + last[1:2])
        candidates.append(last[:1] + first[:1] + last[1:2])

    seen = set()
    for candidate in candidates:
        candidate = candidate[:3]
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if not _existing_identifier(candidate, exclude_profile_id=exclude_profile_id):
            return candidate

    suffix = 1
    base = last[:2] or last[:1] or 'X'
    while True:
        candidate = f'{base}{suffix}'
        if not _existing_identifier(candidate, exclude_profile_id=exclude_profile_id):
            return candidate
        suffix += 1


def default_rfi_identifiers(rack_number, first_name, last_name, role_level, exclude_profile_id=None):
    rack = str(rack_number or '').strip()
    if not is_command_level_role(role_level):
        return {
            'oc_identifier': rack,
            'radio_identifier': rack,
            'is_command_level': False,
        }

    code = _build_unique_command_code(last_name, first_name, exclude_profile_id=exclude_profile_id)
    return {
        'oc_identifier': code,
        'radio_identifier': code,
        'is_command_level': True,
    }
