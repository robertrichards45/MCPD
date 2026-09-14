from app.routes.scenario_variants import build_run_context
from app.simulator.event_engine import build_scheduled_events, initialize_scheduled_events, tick_scheduled_events
from app.simulator.scenario_truth import build_scenario_truth
from app.simulator.world_state import ensure_world_state, observable_world


def _context_with_event(scenario_id='S001'):
    for seed in range(100000001, 100001000):
        context = build_run_context(scenario_id, seed=seed)
        truth = build_scenario_truth(scenario_id, context)
        events = build_scheduled_events(scenario_id, context, truth=truth)
        if events:
            return context, truth, events
    raise AssertionError('No deterministic timed event found in search range.')


def test_timed_updates_are_seed_reproducible():
    context, truth, first = _context_with_event('S003')
    second = build_scheduled_events('S003', context, truth=truth)
    assert first == second
    assert first[0]['due_clock'] >= 2


def test_timed_update_stays_hidden_until_due_and_runs_once():
    context, truth, events = _context_with_event('S001')
    state = {'scenario_id': 'S001', 'run_context': context}
    world = ensure_world_state(state, 'S001')
    world['truth'] = truth
    initialize_scheduled_events(state, events)
    due = int(events[0]['due_clock'])

    world['clock'] = due - 1
    assert tick_scheduled_events(state) == []
    before = observable_world(state)
    assert all(events[0]['text'] not in row.get('text', '') for row in before['radio_log'])
    assert all(events[0]['text'] not in row.get('text', '') for row in before['known_information'])

    world['clock'] = due
    delivered = tick_scheduled_events(state)
    assert len(delivered) == 1
    visible = observable_world(state)
    assert any(events[0]['text'] in row.get('text', '') for row in visible['radio_log'])
    assert any(events[0]['text'] in row.get('text', '') for row in visible['known_information'])

    assert tick_scheduled_events(state) == []
    matching = [row for row in world['radio_log'] if events[0]['text'] in row.get('text', '')]
    assert len(matching) == 1
