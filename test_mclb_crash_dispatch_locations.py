from app.simulator.location_catalog import (
    PUBLIC_MCLB_ROADS,
    enrich_vehicle_crash_dispatch,
)
from app.simulator.shift_engine import new_shift, set_dispatch_details


def test_generic_crash_dispatch_gets_real_mclb_road():
    shift = new_shift(unit_id='214', seed=12345)
    shift['active_call_seed'] = 24680
    source = (
        'Respond to a vehicle crash aboard the installation. '
        'Injury status and roadway conditions are still being developed.'
    )

    set_dispatch_details(shift, source)

    text = shift['active_dispatch_text']
    assert 'aboard the installation' not in text.lower()
    assert any(road in text for road in PUBLIC_MCLB_ROADS)
    assert 'Injury status and roadway conditions are still being developed.' in text
    assert shift['dispatch_log'][-1]['text'].startswith('214, Respond to a vehicle crash')


def test_crash_dispatch_location_is_seed_stable():
    source = 'Respond to a vehicle crash aboard the installation.'
    first = enrich_vehicle_crash_dispatch(source, seed=314159)
    second = enrich_vehicle_crash_dispatch(source, seed=314159)
    assert first == second


def test_crash_dispatch_with_real_road_is_not_rewritten():
    source = 'Respond to a vehicle crash on Radford Boulevard, MCLB Albany.'
    assert enrich_vehicle_crash_dispatch(source, seed=99) == source
