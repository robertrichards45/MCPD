from app.simulator.crash_visual import render_s007_crash_svg
from app.simulator.world_state import ensure_world_state


def _state(status='available'):
    state = {
        'scenario_id': 'S007',
        'run_context': {
            'run_id': 'test-s007-visual',
            'location_display': 'Mockingbird Lane at Radford Boulevard',
            'choices': {
                'crash_type': 'POV versus POV',
                'injury': 'one occupant requests EMS evaluation',
                'scene_evidence': 'debris and a possible point of impact',
            },
        },
    }
    world = ensure_world_state(state, 'S007')
    world['evidence']['crash_scene'] = {
        'label': 'Crash scene / final-rest diagram',
        'status': status,
        'source': 'officer scene observation',
        'location': 'installation roadway',
        'description': 'debris and a possible point of impact',
    }
    return state


def test_s007_crash_scene_renders_svg_for_visible_evidence():
    svg = render_s007_crash_svg(_state())
    assert svg is not None
    assert svg.startswith('<svg')
    assert 'Mockingbird Lane at Radford Boulevard' in svg
    assert 'Vehicle A' in svg
    assert 'Vehicle B' in svg
    assert 'debris and a possible point of impact' in svg
    assert 'does not assign crash cause or fault' in svg


def test_s007_crash_scene_stays_hidden_from_trainee_until_discovered():
    state = _state(status='hidden')
    assert render_s007_crash_svg(state, evaluator=False) is None
    assert render_s007_crash_svg(state, evaluator=True) is not None
