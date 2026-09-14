from copy import deepcopy

from .world_state import add_known_information, add_timeline, ensure_world_state, record_radio


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
