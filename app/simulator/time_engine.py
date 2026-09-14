from .evidence_engine import tick_evidence
from .world_state import add_timeline, ensure_world_state


def apply_time_consequences(state):
    """Apply deterministic consequences caused only by elapsed simulation time."""
    world = ensure_world_state(state, state.get('scenario_id', ''))
    clock = int(world.get('clock', 0))
    tick_evidence(state)

    people = dict(world.get('people') or {})
    for actor_id, person in people.items():
        leaves_at = person.get('leaves_at')
        if leaves_at is None or person.get('status') != 'present':
            continue
        if clock < int(leaves_at):
            continue
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
