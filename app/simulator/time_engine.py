from .evidence_engine import tick_evidence
from .event_engine import build_scheduled_events, initialize_scheduled_events, tick_scheduled_events
from .world_state import add_timeline, ensure_world_state


def apply_time_consequences(state):
    """Apply deterministic consequences caused only by elapsed simulation time."""
    world = ensure_world_state(state, state.get('scenario_id', ''))
    clock = int(world.get('clock', 0))
    if 'scheduled_events' not in world:
        initialize_scheduled_events(
            state,
            build_scheduled_events(
                state.get('scenario_id', ''),
                state.get('run_context') or {},
                truth=world.get('truth') or {},
            ),
        )
    tick_scheduled_events(state)
    tick_evidence(state)

    people = dict(world.get('people') or {})
    departed_ids = set(world.get('departed_actor_ids') or [])
    truth_people = ((world.get('truth') or {}).get('people') or {})

    # Truth-owned departure timers run even if the trainee never discovered the
    # person. An undiscovered departure remains hidden during the live call.
    for actor_id, profile in truth_people.items():
        leaves_at = profile.get('leaves_at')
        if leaves_at is None or actor_id in departed_ids or clock < int(leaves_at):
            continue
        departed_ids.add(actor_id)
        person = dict(people.get(actor_id) or {})
        was_discovered = bool(person.get('discovered'))
        if person:
            person['status'] = 'departed'
            person['location'] = 'left scene'
            people[actor_id] = person
        add_timeline(
            state,
            'person_departed',
            f"{person.get('name') or actor_id} leaves the scene.",
            actor=person.get('name') or actor_id,
            channel='scene',
            details={'actor_id': actor_id},
            visible_to_trainee=was_discovered,
        )

    # People can also receive a live departure timer from an instructor or event.
    for actor_id, person in list(people.items()):
        leaves_at = person.get('leaves_at')
        if leaves_at is None or actor_id in departed_ids or person.get('status') != 'present':
            continue
        if clock < int(leaves_at):
            continue
        departed_ids.add(actor_id)
        was_discovered = bool(person.get('discovered'))
        person['status'] = 'departed'
        person['location'] = 'left scene'
        people[actor_id] = person
        add_timeline(
            state,
            'person_departed',
            f"{person.get('name') or actor_id} leaves the scene.",
            actor=person.get('name') or actor_id,
            channel='scene',
            details={'actor_id': actor_id},
            visible_to_trainee=was_discovered,
        )

    world['people'] = people
    world['departed_actor_ids'] = sorted(departed_ids)
