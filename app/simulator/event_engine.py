from copy import deepcopy
import hashlib
import random

from .world_state import add_known_information, add_timeline, ensure_world_state, record_radio


def _rng(run_context, salt='scheduled-events'):
    seed = int((run_context or {}).get('seed') or 1)
    digest = hashlib.sha256(f'{seed}|{salt}'.encode('utf-8')).hexdigest()
    return random.Random(int(digest[:16], 16))


def build_scheduled_events(scenario_id, run_context, truth=None):
    """Create reproducible updates based only on structured run facts."""
    choices = dict((run_context or {}).get('choices') or {})
    rng = _rng(run_context)
    events = []

    # Not every call gets a later update. The absence of an update is itself
    # normal patrol uncertainty and keeps the trainee from gaming the clock.
    if rng.randrange(100) >= 58:
        return events

    due = rng.randint(2, 4)
    if scenario_id == 'S001':
        demeanor = choices.get('demeanor', 'continuing to argue')
        events.append({
            'id': 'caller-update-1',
            'due_clock': due,
            'event_type': 'caller_update',
            'speaker': 'Dispatch',
            'channel': 'radio',
            'text': f'Caller update: the involved person is now described as {demeanor}. No confirmed weapon information has been added.',
        })
    elif scenario_id == 'S002':
        issue = choices.get('credential_issue', 'an unresolved credential issue')
        events.append({
            'id': 'gate-update-1',
            'due_clock': due,
            'event_type': 'gate_update',
            'speaker': 'Dispatch',
            'channel': 'radio',
            'text': f'Gate update: the vehicle remains in the inspection area while personnel work through {issue}.',
        })
    elif scenario_id == 'S003':
        property_name = choices.get('property', 'government property')
        events.append({
            'id': 'property-update-1',
            'due_clock': due,
            'event_type': 'caller_update',
            'speaker': 'Dispatch',
            'channel': 'radio',
            'text': f'Additional caller information: personnel believe the involved vehicle may still be nearby the damaged {property_name}. The caller did not personally see the contact.',
        })
    elif scenario_id == 'S004':
        events.append({
            'id': 'retail-update-1',
            'due_clock': due,
            'event_type': 'caller_update',
            'speaker': 'Dispatch',
            'channel': 'radio',
            'text': 'Loss prevention updates that the involved person is becoming impatient and wants to leave. No enforcement status has been established by Dispatch.',
        })
    elif scenario_id == 'S006':
        patient_state = choices.get('patient_state', 'still being evaluated')
        events.append({
            'id': 'medical-update-1',
            'due_clock': due,
            'event_type': 'caller_update',
            'speaker': 'Dispatch',
            'channel': 'radio',
            'text': f'Caller update: the patient is reported as {patient_state}. EMS is continuing the response.',
        })

    return events


def initialize_scheduled_events(state, events):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    if 'scheduled_events' not in world:
        world['scheduled_events'] = []
    if world['scheduled_events']:
        return world['scheduled_events']
    rows = []
    for index, source in enumerate(events or [], start=1):
        if not isinstance(source, dict):
            continue
        rows.append({
            'id': str(source.get('id') or f'event-{index}'),
            'due_clock': max(0, int(source.get('due_clock') or 0)),
            'event_type': str(source.get('event_type') or 'dispatch_update'),
            'speaker': str(source.get('speaker') or 'Dispatch'),
            'text': ' '.join(str(source.get('text') or '').split()).strip(),
            'channel': str(source.get('channel') or 'radio'),
            'visible_to_trainee': bool(source.get('visible_to_trainee', True)),
            'details': deepcopy(source.get('details') or {}),
            'delivered': False,
            'delivered_at': None,
        })
    world['scheduled_events'] = rows
    return rows


def tick_scheduled_events(state):
    """Deliver truth-owned timed events exactly once when simulation time reaches them."""
    world = ensure_world_state(state, state.get('scenario_id', ''))
    clock = int(world.get('clock', 0))
    rows = list(world.get('scheduled_events') or [])
    delivered = []

    for row in rows:
        if row.get('delivered') or clock < int(row.get('due_clock') or 0):
            continue
        row['delivered'] = True
        row['delivered_at'] = clock
        text = str(row.get('text') or '').strip()
        visible = bool(row.get('visible_to_trainee', True))
        if visible and text:
            if row.get('channel') == 'radio':
                record_radio(
                    state,
                    row.get('speaker') or 'Dispatch',
                    text,
                    direction='inbound',
                    metadata={'type': row.get('event_type'), 'event_id': row.get('id')},
                )
            add_known_information(state, text, source=row.get('speaker') or 'dispatch')
        add_timeline(
            state,
            row.get('event_type') or 'scheduled_event',
            text,
            actor=row.get('speaker') or 'Simulation',
            channel=row.get('channel') or 'system',
            details={'event_id': row.get('id'), **dict(row.get('details') or {})},
            visible_to_trainee=visible,
        )
        delivered.append(deepcopy(row))

    world['scheduled_events'] = rows
    return delivered
