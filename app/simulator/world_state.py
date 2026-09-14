from copy import deepcopy
from datetime import datetime, timezone


WORLD_VERSION = 1


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _utc_iso():
    return datetime.now(timezone.utc).isoformat()


def _initial_environment(run_context):
    choices = (run_context or {}).get('choices') or {}
    return {
        'time_of_day': choices.get('time_of_day', 'day'),
        'weather': choices.get('weather', 'clear'),
        'lighting': choices.get('lighting', 'normal'),
        'noise': choices.get('noise', 'normal'),
        'visibility': choices.get('visibility', 'normal'),
        'crowd': choices.get('crowd', 'normal'),
    }


def new_world_state(scenario_id, run_context=None):
    run_context = run_context or {}
    return {
        'world_version': WORLD_VERSION,
        'scenario_id': scenario_id,
        'run_id': _text(run_context.get('run_id')),
        'clock': 0,
        'status': 'active',
        'officer': {
            'location': 'enroute',
            'available': False,
        },
        'environment': _initial_environment(run_context),
        'people': {},
        'resources': {
            'backup': {'status': 'not_requested', 'requested_at': None, 'eta': None},
            'ems': {'status': 'not_requested', 'requested_at': None, 'eta': None},
            'fire': {'status': 'not_requested', 'requested_at': None, 'eta': None},
            'supervisor': {'status': 'available_by_radio'},
            'investigations': {'status': 'available_by_request'},
        },
        'evidence': {},
        'statements': [],
        'records': {},
        'known_information': [],
        'outstanding_tasks': [],
        'radio_log': [],
        'timeline': [],
        'irreversible_events': [],
        'last_actions': [],
        'pending_radio': [],
        'scheduled_events': [],
        'coaching_mode': False,
        'fto_message': '',
        'paused': False,
    }


def ensure_world_state(state, scenario_id):
    world = state.get('world')
    run_context = state.get('run_context') or {}
    if not isinstance(world, dict) or int(world.get('world_version', 0) or 0) != WORLD_VERSION:
        world = new_world_state(scenario_id, run_context)
        state['world'] = world
    world['scenario_id'] = scenario_id
    world['run_id'] = _text(run_context.get('run_id')) or world.get('run_id', '')
    world.setdefault('scheduled_events', [])
    world.setdefault('statements', [])
    return world


def replay_snapshot(world):
    """Capture immutable facts available at one timeline instant without recursion."""
    return {
        'clock': int(world.get('clock', 0)),
        'officer': deepcopy(world.get('officer') or {}),
        'environment': deepcopy(world.get('environment') or {}),
        'people': deepcopy(world.get('people') or {}),
        'resources': deepcopy(world.get('resources') or {}),
        'evidence': deepcopy(world.get('evidence') or {}),
        'statements': deepcopy(world.get('statements') or []),
        'records': deepcopy(world.get('records') or {}),
        'known_information': deepcopy(world.get('known_information') or []),
        'irreversible_events': deepcopy(world.get('irreversible_events') or []),
        'pending_radio': deepcopy(world.get('pending_radio') or []),
        'scheduled_events': deepcopy(world.get('scheduled_events') or []),
    }


def add_timeline(state, event_type, summary, actor='', channel='system', details=None, visible_to_trainee=True):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    rows = list(world.get('timeline') or [])
    row = {
        'seq': len(rows) + 1,
        'clock': int(world.get('clock', 0)),
        'event_type': _text(event_type),
        'actor': _text(actor),
        'channel': _text(channel),
        'summary': _text(summary)[:2000],
        'details': deepcopy(details) if isinstance(details, (dict, list)) else {},
        'visible_to_trainee': bool(visible_to_trainee),
        'world_snapshot': replay_snapshot(world),
        'ts': _utc_iso(),
    }
    rows.append(row)
    world['timeline'] = rows[-250:]
    return row


def add_known_information(state, text, source='scene'):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    text = _text(text)
    if not text:
        return
    rows = list(world.get('known_information') or [])
    key = (text.lower(), _text(source).lower())
    if not any((str(row.get('text', '')).lower(), str(row.get('source', '')).lower()) == key for row in rows):
        rows.append({'text': text, 'source': _text(source)})
    world['known_information'] = rows[-40:]


def discover_person(state, actor, location='scene'):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    actor_id = _text(actor.get('id'))
    if not actor_id:
        return None
    people = dict(world.get('people') or {})
    row = dict(people.get(actor_id) or {})
    row.setdefault('id', actor_id)
    row.setdefault('name', _text(actor.get('name')) or actor_id)
    row.setdefault('role', _text(actor.get('role')) or 'Person')
    row.setdefault('location', location)
    row.setdefault('status', 'present')
    row.setdefault('stress', 35)
    row.setdefault('cooperation', 55)
    row.setdefault('emotional_state', 'neutral')
    row.setdefault('memory', [])
    row['discovered'] = True
    people[actor_id] = row
    world['people'] = people
    return row


def person_memory(state, actor_id, officer_text='', npc_text=''):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    people = dict(world.get('people') or {})
    row = dict(people.get(actor_id) or {'id': actor_id, 'discovered': True, 'memory': []})
    memory = list(row.get('memory') or [])
    if _text(officer_text):
        memory.append({'speaker': 'officer', 'text': _text(officer_text)[:1000], 'clock': world.get('clock', 0)})
    if _text(npc_text):
        memory.append({'speaker': 'npc', 'text': _text(npc_text)[:1000], 'clock': world.get('clock', 0)})
    row['memory'] = memory[-24:]
    people[actor_id] = row
    world['people'] = people


def mark_evidence(state, evidence_id, label, status='discovered', source='', details=None):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    evidence = dict(world.get('evidence') or {})
    row = dict(evidence.get(evidence_id) or {})
    row.update({
        'id': evidence_id,
        'label': _text(label) or evidence_id,
        'status': _text(status) or 'discovered',
        'source': _text(source),
    })
    if isinstance(details, dict):
        row['details'] = deepcopy(details)
    evidence[evidence_id] = row
    world['evidence'] = evidence
    return row


def record_radio(state, speaker, text, direction='outbound', metadata=None):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    rows = list(world.get('radio_log') or [])
    rows.append({
        'clock': int(world.get('clock', 0)),
        'speaker': _text(speaker),
        'text': _text(text)[:1200],
        'direction': _text(direction),
        'metadata': deepcopy(metadata) if isinstance(metadata, dict) else {},
    })
    world['radio_log'] = rows[-60:]


def queue_radio_response(state, due_clock, speaker, text, metadata=None):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    rows = list(world.get('pending_radio') or [])
    rows.append({
        'due_clock': int(due_clock),
        'speaker': _text(speaker),
        'text': _text(text),
        'metadata': deepcopy(metadata) if isinstance(metadata, dict) else {},
    })
    world['pending_radio'] = rows


def _arrive_resources(state):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    clock = int(world.get('clock', 0))
    for key in ('backup', 'ems', 'fire'):
        row = dict((world.get('resources') or {}).get(key) or {})
        if row.get('status') == 'enroute' and row.get('eta') is not None and clock >= int(row['eta']):
            row['status'] = 'arrived'
            world['resources'][key] = row
            label = {'backup': 'Cover unit', 'ems': 'EMS', 'fire': 'Fire'}[key]
            add_timeline(state, 'resource_arrival', f'{label} arrives on scene.', actor=label, channel='scene', visible_to_trainee=True)


def advance_world_clock(state, amount=1):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    if world.get('paused'):
        return []
    world['clock'] = int(world.get('clock', 0)) + max(1, int(amount or 1))
    delivered = []
    pending = []
    for row in list(world.get('pending_radio') or []):
        if int(row.get('due_clock', 0)) <= world['clock']:
            record_radio(state, row.get('speaker') or 'Dispatch', row.get('text'), direction='inbound', metadata=row.get('metadata'))
            add_timeline(state, 'radio_response', row.get('text'), actor=row.get('speaker') or 'Dispatch', channel='radio', visible_to_trainee=True)
            delivered.append(row)
        else:
            pending.append(row)
    world['pending_radio'] = pending
    _arrive_resources(state)
    return delivered


def apply_interpreted_actions(state, actions, raw_text='', channel='scene'):
    """Apply only generic, deterministic world changes.

    Scenario-specific truth and consequences remain owned by the scenario/event
    engines. This function records intent, resources, movement, and irreversible
    dispositions without inventing facts.
    """
    world = ensure_world_state(state, state.get('scenario_id', ''))
    clean_actions = [dict(row) for row in (actions or []) if isinstance(row, dict)]
    world['last_actions'] = clean_actions
    add_timeline(
        state,
        'trainee_action',
        _text(raw_text),
        actor='Trainee',
        channel=channel,
        details={'actions': clean_actions},
        visible_to_trainee=True,
    )

    for row in clean_actions:
        action = _text(row.get('action_type')).lower()
        reason = _text(row.get('reason'))
        if action == 'radio_status':
            if reason == 'on_scene':
                world['officer']['location'] = 'scene'
            elif reason == 'enroute':
                world['officer']['location'] = 'enroute'
        elif action == 'move':
            world['officer']['location'] = _text(row.get('target')) or 'scene_position_changed'
        elif action == 'request_backup':
            backup = world['resources']['backup']
            if backup.get('status') == 'not_requested':
                backup.update({'status': 'enroute', 'requested_at': world['clock'], 'eta': world['clock'] + 3})
        elif action == 'request_ems':
            ems = world['resources']['ems']
            if ems.get('status') == 'not_requested':
                ems.update({'status': 'enroute', 'requested_at': world['clock'], 'eta': world['clock'] + 3})
        elif action == 'request_fire':
            fire = world['resources']['fire']
            if fire.get('status') == 'not_requested':
                fire.update({'status': 'enroute', 'requested_at': world['clock'], 'eta': world['clock'] + 4})
        elif action in {'release', 'arrest', 'cite'}:
            event = {
                'clock': world['clock'],
                'action_type': action,
                'target': _text(row.get('target')),
                'reason': reason,
            }
            irreversible = list(world.get('irreversible_events') or [])
            irreversible.append(event)
            world['irreversible_events'] = irreversible[-40:]
        elif action == 'clear_call':
            world['officer']['available'] = True

    advance_world_clock(state, 1)
    return clean_actions


def _evidence_visible_to_trainee(row):
    status = str(row.get('status') or '').strip().lower()
    if status in {'hidden', 'unknown'}:
        return False
    if status == 'lost' and row.get('discovered_at') is None:
        return False
    return True


def _visible_timeline_without_legacy_radio_duplicates(world):
    """Hide only the exact duplicate pair produced by the retired radio writer.

    Older runs may contain a ``radio_transmission`` and a ``trainee_action``
    with identical trainee text at the same simulated clock. A real repeated
    transmission at a later clock remains visible.
    """
    visible = [row for row in (world.get('timeline') or []) if row.get('visible_to_trainee')]
    cleaned = []
    for row in visible:
        if cleaned:
            previous = cleaned[-1]
            same_payload = (
                _text(previous.get('actor')).lower() == 'trainee'
                and _text(row.get('actor')).lower() == 'trainee'
                and _text(previous.get('channel')).lower() == 'radio'
                and _text(row.get('channel')).lower() == 'radio'
                and int(previous.get('clock', -1)) == int(row.get('clock', -2))
                and _text(previous.get('summary')).lower() == _text(row.get('summary')).lower()
            )
            legacy_pair = {
                _text(previous.get('event_type')).lower(),
                _text(row.get('event_type')).lower(),
            } == {'radio_transmission', 'trainee_action'}
            if same_payload and legacy_pair:
                if _text(row.get('event_type')).lower() == 'trainee_action':
                    cleaned[-1] = row
                continue
        cleaned.append(row)
    return [deepcopy(row) for row in cleaned]


def observable_world(state):
    """Return only information an officer could reasonably see/receive."""
    world = ensure_world_state(state, state.get('scenario_id', ''))
    people = []
    for row in (world.get('people') or {}).values():
        if row.get('discovered') and row.get('status') != 'hidden':
            people.append({
                'id': row.get('id'),
                'name': row.get('name'),
                'role': row.get('role'),
                'location': row.get('location'),
                'status': row.get('status'),
                'identity_obtained': bool(row.get('identity_obtained')),
                'identity': deepcopy(row.get('identity') or {}) if row.get('identity_obtained') else {},
            })
    evidence = [
        {'id': row.get('id'), 'label': row.get('label'), 'status': row.get('status'), 'source': row.get('source')}
        for row in (world.get('evidence') or {}).values()
        if _evidence_visible_to_trainee(row)
    ]
    statements = [
        {
            'id': row.get('id'),
            'declarant_name': row.get('declarant_name'),
            'role': row.get('role'),
            'status': row.get('status'),
            'form_document_name': row.get('form_document_name'),
        }
        for row in (world.get('statements') or [])
        if row.get('status') == 'received'
    ]
    resources = []
    for key, row in (world.get('resources') or {}).items():
        if row.get('status') in {'enroute', 'arrived'}:
            resources.append({'id': key, 'status': row.get('status')})
    return {
        'clock': int(world.get('clock', 0)),
        'officer_location': world.get('officer', {}).get('location'),
        'environment': deepcopy(world.get('environment') or {}),
        'people': people,
        'resources': resources,
        'evidence': evidence,
        'statements': statements,
        'known_information': deepcopy(world.get('known_information') or []),
        'radio_log': deepcopy(world.get('radio_log') or []),
        'timeline': _visible_timeline_without_legacy_radio_duplicates(world),
        'paused': bool(world.get('paused')),
        'coaching_mode': bool(world.get('coaching_mode')),
        'fto_message': _text(world.get('fto_message')),
    }


def evaluator_world(state):
    """Full hidden snapshot for authorized FTO/evaluator use."""
    return deepcopy(ensure_world_state(state, state.get('scenario_id', '')))
