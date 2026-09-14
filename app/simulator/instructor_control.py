from copy import deepcopy

from .world_state import add_known_information, add_timeline, ensure_world_state, record_radio


ALLOWED_INJECT_TYPES = {
    'caller_update',
    'backup_delay',
    'person_arrival',
    'person_departure',
    'subject_behavior',
    'supervisor_request',
    'evidence_available',
    'environment_change',
}


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _configured_people(state):
    truth = (((state or {}).get('world') or {}).get('truth') or {}).get('people') or {}
    return set(truth.keys())


def _configured_evidence(state):
    truth = (((state or {}).get('world') or {}).get('truth') or {}).get('evidence') or {}
    return {key for key, row in truth.items() if isinstance(row, dict) and row.get('exists')}


def inject_event(state, event_type, text='', target_id='', delay=0, environment=None):
    """Apply a human instructor override without bypassing structured scenario truth."""
    if not isinstance(state, dict):
        return {'ok': False, 'message': 'Run state is unavailable.'}
    event_type = _text(event_type).lower()
    if event_type not in ALLOWED_INJECT_TYPES:
        return {'ok': False, 'message': 'Unsupported instructor event type.'}

    world = ensure_world_state(state, state.get('scenario_id', ''))
    text = _text(text)[:1200]
    target_id = _text(target_id)
    clock = int(world.get('clock', 0))

    if event_type == 'caller_update':
        if not text:
            return {'ok': False, 'message': 'Enter the synthetic caller update.'}
        radio_text = f'Caller update: {text}'
        record_radio(state, 'Dispatch', radio_text, direction='inbound', metadata={'type': 'instructor_caller_update'})
        add_known_information(state, radio_text, source='dispatch')
        add_timeline(state, 'instructor_caller_update', radio_text, actor='Dispatch', channel='radio', details={'instructor_injected': True}, visible_to_trainee=True)
        return {'ok': True, 'message': 'Caller update injected.'}

    if event_type == 'supervisor_request':
        if not text:
            return {'ok': False, 'message': 'Enter the supervisor radio message.'}
        record_radio(state, 'Supervisor', text, direction='inbound', metadata={'type': 'instructor_supervisor_request'})
        add_known_information(state, text, source='supervisor')
        add_timeline(state, 'instructor_supervisor_request', text, actor='Supervisor', channel='radio', details={'instructor_injected': True}, visible_to_trainee=True)
        return {'ok': True, 'message': 'Supervisor request injected.'}

    if event_type == 'backup_delay':
        backup = dict((world.get('resources') or {}).get('backup') or {})
        if backup.get('status') != 'enroute' or backup.get('eta') is None:
            return {'ok': False, 'message': 'Backup must already be en route before its ETA can be delayed.'}
        try:
            delay = max(1, min(10, int(delay or 1)))
        except (TypeError, ValueError):
            delay = 1
        backup['eta'] = int(backup['eta']) + delay
        world['resources']['backup'] = backup
        radio_text = text or f'Cover unit is delayed approximately {delay} additional simulation minute(s).'
        record_radio(state, 'Dispatch', radio_text, direction='inbound', metadata={'type': 'instructor_backup_delay'})
        add_timeline(state, 'instructor_backup_delay', radio_text, actor='Dispatch', channel='radio', details={'delay': delay, 'instructor_injected': True}, visible_to_trainee=True)
        return {'ok': True, 'message': 'Backup ETA delayed.'}

    if event_type in {'person_arrival', 'person_departure'}:
        if not target_id or target_id not in _configured_people(state):
            return {'ok': False, 'message': 'Select a person already defined in structured scenario truth.'}
        people = dict(world.get('people') or {})
        row = dict(people.get(target_id) or {})
        profile = ((((world.get('truth') or {}).get('people') or {}).get(target_id)) or {})
        row.setdefault('id', target_id)
        row.setdefault('name', target_id.replace('_', ' ').title())
        row.setdefault('role', profile.get('role') or 'Person')
        row.setdefault('memory', [])
        if event_type == 'person_arrival':
            row['status'] = 'present'
            row['location'] = 'scene'
            row['discovered'] = True
            departed = set(world.get('departed_actor_ids') or [])
            departed.discard(target_id)
            world['departed_actor_ids'] = sorted(departed)
            summary = text or f"{row.get('name')} arrives on scene."
        else:
            row['status'] = 'departed'
            row['location'] = 'left scene'
            row['discovered'] = bool(row.get('discovered'))
            departed = set(world.get('departed_actor_ids') or [])
            departed.add(target_id)
            world['departed_actor_ids'] = sorted(departed)
            summary = text or f"{row.get('name')} leaves the scene."
        people[target_id] = row
        world['people'] = people
        add_timeline(state, event_type, summary, actor=row.get('name'), channel='scene', details={'actor_id': target_id, 'instructor_injected': True}, visible_to_trainee=event_type == 'person_arrival' or bool(row.get('discovered')))
        if event_type == 'person_arrival':
            add_known_information(state, summary, source='scene')
        return {'ok': True, 'message': 'Person state updated.'}

    if event_type == 'subject_behavior':
        if not text:
            return {'ok': False, 'message': 'Describe the observable behavior change.'}
        add_known_information(state, text, source='scene')
        add_timeline(state, 'instructor_subject_behavior', text, actor='Scene', channel='scene', details={'instructor_injected': True}, visible_to_trainee=True)
        return {'ok': True, 'message': 'Observable behavior change injected.'}

    if event_type == 'evidence_available':
        if not target_id or target_id not in _configured_evidence(state):
            return {'ok': False, 'message': 'Select evidence that already exists in structured scenario truth.'}
        evidence = dict(world.get('evidence') or {})
        row = dict(evidence.get(target_id) or {})
        if not row or row.get('status') == 'lost':
            return {'ok': False, 'message': 'That evidence is not available to surface in this run.'}
        if row.get('status') == 'hidden':
            row['status'] = 'available'
        evidence[target_id] = row
        world['evidence'] = evidence
        summary = text or f"A source indicates that {row.get('label') or target_id} may be available if the officer develops it."
        add_known_information(state, summary, source='scene')
        add_timeline(state, 'instructor_evidence_available', summary, actor='Scene', channel='scene', details={'evidence_id': target_id, 'instructor_injected': True}, visible_to_trainee=True)
        return {'ok': True, 'message': 'Existing evidence availability surfaced.'}

    if event_type == 'environment_change':
        updates = {}
        for key in ('weather', 'lighting', 'noise', 'visibility', 'crowd'):
            value = _text((environment or {}).get(key))
            if value:
                updates[key] = value[:120]
        if not updates:
            return {'ok': False, 'message': 'Enter at least one environmental change.'}
        world['environment'].update(deepcopy(updates))
        summary = text or 'Environmental conditions change: ' + ', '.join(f'{key}={value}' for key, value in updates.items())
        add_known_information(state, summary, source='environment')
        add_timeline(state, 'instructor_environment_change', summary, actor='Scene', channel='scene', details={'changes': updates, 'instructor_injected': True}, visible_to_trainee=True)
        return {'ok': True, 'message': 'Environmental conditions updated.'}

    return {'ok': False, 'message': 'No instructor event was applied.'}


def instructor_options(state):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    people = []
    for actor_id, profile in (((world.get('truth') or {}).get('people') or {}).items()):
        current = (world.get('people') or {}).get(actor_id) or {}
        people.append({
            'id': actor_id,
            'label': current.get('name') or actor_id.replace('_', ' ').title(),
            'status': current.get('status') or 'not encountered',
        })
    evidence = []
    for evidence_id, profile in (((world.get('truth') or {}).get('evidence') or {}).items()):
        if not isinstance(profile, dict) or not profile.get('exists'):
            continue
        current = (world.get('evidence') or {}).get(evidence_id) or {}
        evidence.append({
            'id': evidence_id,
            'label': current.get('label') or profile.get('label') or evidence_id,
            'status': current.get('status') or 'hidden',
        })
    return {
        'people': people,
        'evidence': evidence,
        'backup': deepcopy((world.get('resources') or {}).get('backup') or {}),
        'environment': deepcopy(world.get('environment') or {}),
        'clock': int(world.get('clock', 0)),
    }
