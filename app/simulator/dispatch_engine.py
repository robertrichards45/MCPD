import hashlib
import random

from .world_state import (
    add_known_information,
    add_timeline,
    ensure_world_state,
    queue_radio_response,
    record_radio,
)


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _seeded_rng(run_context, salt):
    seed = int((run_context or {}).get('seed') or 1)
    digest = hashlib.sha256(f'{seed}|{salt}'.encode('utf-8')).hexdigest()
    return random.Random(int(digest[:16], 16))


def _synthetic_records_result(state, run_context, raw_text):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    key = hashlib.sha1(_text(raw_text).lower().encode('utf-8')).hexdigest()[:12]
    records = dict(world.get('records') or {})
    if key in records:
        return records[key]

    rng = _seeded_rng(run_context, f'records:{key}')
    kind = 'person'
    low = _text(raw_text).lower()
    if any(term in low for term in ('plate', 'tag', 'registration', 'vehicle')):
        kind = 'vehicle'

    if kind == 'vehicle':
        statuses = (
            ('Registration valid; no stolen indication returned.', 72),
            ('Registration valid; registered owner information is available to the officer in this synthetic training record.', 18),
            ('Registration status requires clarification; no stolen indication returned.', 10),
        )
    else:
        statuses = (
            ('Identity returns valid with no wanted indication.', 68),
            ('Identity returns valid; license status is suspended. No wanted indication.', 12),
            ('Identity returns valid; a warrant indicator is returned. Confirm scope, status, and pickup limitations through Dispatch before acting.', 10),
            ('Identity returns valid; no driver-license record is located from the information provided. Verify the identifier.', 10),
        )

    roll = rng.randrange(100)
    running = 0
    result = statuses[0][0]
    for text, weight in statuses:
        running += weight
        if roll < running:
            result = text
            break

    row = {
        'kind': kind,
        'query_key': key,
        'result': result,
        'synthetic': True,
    }
    records[key] = row
    world['records'] = records
    return row


def handle_radio_transmission(state, actions, raw_text, run_context=None):
    """Process trainee radio traffic without giving Dispatch hidden knowledge.

    The trainee transmission is written to the radio log here. The visible call
    timeline entry is owned by ``apply_interpreted_actions`` so one radio
    transmission produces exactly one trainee timeline card.
    """
    world = ensure_world_state(state, state.get('scenario_id', ''))
    run_context = run_context or state.get('run_context') or {}
    text = _text(raw_text)
    record_radio(state, 'Trainee', text, direction='outbound', metadata={'actions': actions or []})

    action_types = {str(row.get('action_type') or '').strip().lower() for row in (actions or [])}
    clock = int(world.get('clock', 0))

    if 'request_backup' in action_types:
        queue_radio_response(state, clock + 1, 'Dispatch', 'Copy. Cover unit started your way.', {'type': 'backup_ack'})
    if 'request_ems' in action_types:
        queue_radio_response(state, clock + 1, 'Dispatch', 'Copy. EMS has been started.', {'type': 'ems_ack'})
    if 'request_fire' in action_types:
        queue_radio_response(state, clock + 1, 'Dispatch', 'Copy. Fire is being notified.', {'type': 'fire_ack'})
    if 'notify_supervisor' in action_types:
        queue_radio_response(state, clock + 1, 'Dispatch', 'Copy. Watch supervisor advised.', {'type': 'supervisor_ack'})
    if 'request_investigator' in action_types:
        queue_radio_response(state, clock + 2, 'Dispatch', 'Copy. Investigations notified; stand by for availability.', {'type': 'investigator_ack'})
    if 'records_check' in action_types:
        row = _synthetic_records_result(state, run_context, text)
        queue_radio_response(state, clock + 2, 'Dispatch', row['result'], {'type': 'records', 'query_key': row['query_key']})
    if 'clear_call' in action_types:
        queue_radio_response(state, clock + 1, 'Dispatch', 'Copy clear. Advise disposition when ready.', {'type': 'clear_ack'})

    if action_types & {'radio_status'} and not action_types & {'request_backup', 'request_ems', 'request_fire', 'records_check'}:
        queue_radio_response(state, clock + 1, 'Dispatch', 'Copy.', {'type': 'status_ack'})

    return list(world.get('pending_radio') or [])


def inject_dispatch_update(state, text, metadata=None):
    """Insert a caller/CAD/unit update that is part of scenario truth."""
    world = ensure_world_state(state, state.get('scenario_id', ''))
    message = _text(text)
    if not message:
        return
    record_radio(state, 'Dispatch', message, direction='inbound', metadata=metadata)
    add_known_information(state, message, source='dispatch')
    add_timeline(state, 'dispatch_update', message, actor='Dispatch', channel='radio', details=metadata or {})
