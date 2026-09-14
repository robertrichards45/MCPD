import hashlib
import random
import secrets

from .location_catalog import enrich_vehicle_crash_dispatch


SHIFT_VERSION = 2
SHIFT_CALL_POOL = (
    ('S006', 22),  # medical assists / assistance calls
    ('S002', 20),  # gate/access-control calls
    ('S003', 18),  # property / damage complaints
    ('S001', 17),  # disturbances
    ('S004', 12),  # larceny / shoplifting
    ('S005', 11),  # traffic/self-initiated activity
)


def _rng(seed, call_index, salt='shift'):
    digest = hashlib.sha256(f'{int(seed)}|{int(call_index)}|{salt}'.encode('utf-8')).hexdigest()
    return random.Random(int(digest[:16], 16))


def new_shift(unit_id='214', seed=None):
    seed = int(seed if seed is not None else secrets.randbelow(900000000) + 100000000)
    return {
        'version': SHIFT_VERSION,
        'shift_id': f'SHIFT-{seed}',
        'seed': seed,
        'unit_id': str(unit_id or '214').strip()[:20] or '214',
        'status': 'ACTIVE',
        'clock_minutes': 0,
        'call_index': 0,
        'calls_completed': 0,
        'active_scenario_id': None,
        'active_call_seed': None,
        'active_dispatch_text': '',
        'active_run_id': None,
        'active_dispatched_minute': None,
        'last_scenario_id': None,
        'dispatch_log': [
            {'minute': 0, 'speaker': 'Dispatch', 'text': f'{unit_id}, copy you in service for training patrol.'},
        ],
        'history': [],
    }


def _weighted_choice(rng, previous=None):
    pool = [(sid, weight) for sid, weight in SHIFT_CALL_POOL if sid != previous]
    total = sum(weight for _sid, weight in pool)
    pick = rng.uniform(0, total)
    running = 0
    for sid, weight in pool:
        running += weight
        if pick <= running:
            return sid
    return pool[-1][0]


def assign_next_call(shift):
    """Assign a routine-heavy reproducible call without exposing category/difficulty."""
    call_index = int(shift.get('call_index', 0)) + 1
    rng = _rng(shift['seed'], call_index)
    idle_minutes = rng.randint(4, 18)
    shift['clock_minutes'] = int(shift.get('clock_minutes', 0)) + idle_minutes
    scenario_id = _weighted_choice(rng, shift.get('last_scenario_id'))
    scenario_seed = rng.randint(100000000, 999999999)
    shift['call_index'] = call_index
    shift['active_scenario_id'] = scenario_id
    shift['active_call_seed'] = scenario_seed
    shift['active_dispatch_text'] = ''
    shift['active_run_id'] = None
    shift['active_dispatched_minute'] = int(shift['clock_minutes'])
    shift['last_scenario_id'] = scenario_id
    shift['dispatch_log'].append({
        'minute': shift['clock_minutes'],
        'speaker': 'Dispatch',
        'text': f"{shift['unit_id']}, copy your next call.",
    })
    return scenario_id, idle_minutes


def set_dispatch_details(shift, dispatch_text):
    """Attach only the CAD information the trainee should receive for this call."""
    seed = shift.get('active_call_seed') or shift.get('seed') or 1
    text = enrich_vehicle_crash_dispatch(dispatch_text, seed=seed)
    shift['active_dispatch_text'] = text
    if text:
        log = list(shift.get('dispatch_log') or [])
        if log and log[-1].get('minute') == shift.get('active_dispatched_minute'):
            log[-1] = {
                'minute': int(shift.get('active_dispatched_minute') or shift.get('clock_minutes', 0)),
                'speaker': 'Dispatch',
                'text': f"{shift['unit_id']}, {text}",
            }
        else:
            log.append({
                'minute': int(shift.get('clock_minutes', 0)),
                'speaker': 'Dispatch',
                'text': f"{shift['unit_id']}, {text}",
            })
        shift['dispatch_log'] = log
    return shift


def attach_run(shift, scenario_id, run_id, dispatch_text):
    shift['active_scenario_id'] = scenario_id
    shift['active_run_id'] = run_id
    # Re-normalize the active CAD text here as defense in depth so a custom or
    # dynamically generated crash call cannot bypass the public-road enrichment.
    active_text = dispatch_text or shift.get('active_dispatch_text')
    if active_text:
        set_dispatch_details(shift, active_text)
    return shift


def complete_active_call(shift, run_id, outcome='CLEARED', duration_minutes=0):
    if not shift.get('active_run_id') or shift.get('active_run_id') != run_id:
        return shift
    duration_minutes = max(0, int(duration_minutes or 0))
    dispatched_minute = int(shift.get('active_dispatched_minute') or shift.get('clock_minutes', 0))
    shift['clock_minutes'] = max(int(shift.get('clock_minutes', 0)), dispatched_minute) + duration_minutes
    shift['history'].append({
        'call_number': int(shift.get('call_index', 0)),
        'scenario_id': shift.get('active_scenario_id'),
        'run_id': run_id,
        'seed': shift.get('active_call_seed'),
        'outcome': outcome,
        'dispatched_minute': dispatched_minute,
        'duration_minutes': duration_minutes,
        'cleared_minute': int(shift.get('clock_minutes', 0)),
    })
    shift['calls_completed'] = int(shift.get('calls_completed', 0)) + 1
    shift['dispatch_log'].append({
        'minute': int(shift.get('clock_minutes', 0)),
        'speaker': 'Dispatch',
        'text': f"{shift['unit_id']}, copy you clear and available.",
    })
    shift['active_scenario_id'] = None
    shift['active_call_seed'] = None
    shift['active_dispatch_text'] = ''
    shift['active_run_id'] = None
    shift['active_dispatched_minute'] = None
    return shift


def end_shift(shift):
    shift['status'] = 'ENDED'
    shift['dispatch_log'].append({
        'minute': int(shift.get('clock_minutes', 0)),
        'speaker': 'Dispatch',
        'text': f"{shift['unit_id']}, copy you off duty. End of synthetic training shift.",
    })
    return shift
