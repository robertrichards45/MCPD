import json
from datetime import datetime

from ..extensions import db
from ..fto_models import FTOProgramAssignment, FTOScenarioEvent, FTOScenarioRun


ACTIVE_ASSIGNMENT_STATUSES = ('ACTIVE', 'PAUSED', 'EXTENDED')


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), default=str)


def _load(raw, fallback=None):
    try:
        value = json.loads(raw or '{}')
        return value
    except Exception:
        return {} if fallback is None else fallback


def active_assignment_for(trainee_id):
    return (
        FTOProgramAssignment.query
        .filter(
            FTOProgramAssignment.trainee_id == trainee_id,
            FTOProgramAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES),
        )
        .order_by(FTOProgramAssignment.updated_at.desc(), FTOProgramAssignment.id.desc())
        .first()
    )


def _status_for_state(state):
    world = state.get('world') or {}
    if state.get('terminated'):
        return 'TERMINATED'
    if state.get('complete'):
        return 'COMPLETED'
    if world.get('paused'):
        return 'PAUSED'
    return 'ACTIVE'


def persist_run(state, trainee_id):
    """Persist the exact synthetic run and any new timeline snapshots.

    Read-only renders call this helper too. If the serialized run, mode, and
    status are unchanged, return the existing row without doing another event
    scan or database commit. This keeps routine radio/scene actions responsive
    after their redirect while preserving exact replay for real state changes.
    """
    if not isinstance(state, dict) or not trainee_id:
        return None
    run_context = state.get('run_context') or {}
    run_id = str(run_context.get('run_id') or '').strip()
    if not run_id:
        return None

    desired_mode = 'COACHING' if (state.get('world') or {}).get('coaching_mode') else 'EVALUATION'
    desired_status = _status_for_state(state)
    serialized_state = _json(state)

    row = FTOScenarioRun.query.filter_by(run_id=run_id).first()
    is_new = row is None
    if row is None:
        assignment = active_assignment_for(trainee_id)
        row = FTOScenarioRun(
            run_id=run_id,
            scenario_id=str(state.get('scenario_id') or 'UNKNOWN'),
            seed=int(run_context.get('seed') or 0),
            trainee_id=trainee_id,
            assignment_id=assignment.id if assignment else None,
            assigned_fto_id=assignment.assigned_fto_id if assignment else None,
            supervisor_id=assignment.supervisor_id if assignment else None,
            mode=desired_mode,
            status=desired_status,
            state_json='{}',
        )
        db.session.add(row)
        db.session.flush()
    elif (
        row.trainee_id == trainee_id
        and row.mode == desired_mode
        and row.status == desired_status
        and row.state_json == serialized_state
    ):
        return row

    row.scenario_id = str(state.get('scenario_id') or row.scenario_id)
    row.mode = desired_mode
    row.status = desired_status
    row.state_json = serialized_state
    row.updated_at = datetime.utcnow()
    if row.status in {'COMPLETED', 'TERMINATED'} and row.completed_at is None:
        row.completed_at = datetime.utcnow()

    world = state.get('world') or {}
    timeline = list(world.get('timeline') or [])
    existing_max = 0
    if not is_new:
        existing_max = (
            db.session.query(db.func.max(FTOScenarioEvent.sequence))
            .filter(FTOScenarioEvent.scenario_run_id == row.id)
            .scalar()
            or 0
        )
    for item in timeline:
        sequence = int(item.get('seq') or 0)
        if sequence <= existing_max:
            continue
        fallback_snapshot = {
            'clock': world.get('clock'),
            'officer': world.get('officer'),
            'environment': world.get('environment'),
            'people': world.get('people'),
            'resources': world.get('resources'),
            'evidence': world.get('evidence'),
            'records': world.get('records'),
            'known_information': world.get('known_information'),
            'irreversible_events': world.get('irreversible_events'),
            'pending_radio': world.get('pending_radio'),
            'scheduled_events': world.get('scheduled_events'),
        }
        db.session.add(FTOScenarioEvent(
            scenario_run_id=row.id,
            sequence=sequence,
            event_type=str(item.get('event_type') or 'event')[:50],
            actor=str(item.get('actor') or '')[:120] or None,
            channel=str(item.get('channel') or '')[:30] or None,
            summary=str(item.get('summary') or '')[:10000] or None,
            structured_json=_json(item.get('details') or {}),
            world_snapshot_json=_json(item.get('world_snapshot') or fallback_snapshot),
            visible_to_trainee=bool(item.get('visible_to_trainee', True)),
        ))

    db.session.commit()
    return row


def load_run(run_id):
    return FTOScenarioRun.query.filter_by(run_id=str(run_id or '').strip()).first()


def load_run_state(run):
    return _load(run.state_json, {}) if run else {}


def can_evaluator_view(user, run, can_manage_fn=None):
    if not user or not getattr(user, 'is_authenticated', False) or run is None:
        return False
    if can_manage_fn and can_manage_fn(user):
        return True
    return user.id in {run.assigned_fto_id, run.supervisor_id}


def can_trainee_view(user, run):
    return bool(user and getattr(user, 'is_authenticated', False) and run and user.id == run.trainee_id)


def set_pause(run, paused):
    state = load_run_state(run)
    world = state.setdefault('world', {})
    world['paused'] = bool(paused)
    run.status = 'PAUSED' if paused else 'ACTIVE'
    run.state_json = _json(state)
    run.updated_at = datetime.utcnow()
    db.session.commit()
    return state


def set_coaching_mode(run, enabled):
    state = load_run_state(run)
    world = state.setdefault('world', {})
    world['coaching_mode'] = bool(enabled)
    if not enabled:
        world['fto_message'] = ''
    run.mode = 'COACHING' if enabled else 'EVALUATION'
    run.state_json = _json(state)
    run.updated_at = datetime.utcnow()
    db.session.commit()
    return state


def send_fto_coaching(run, message):
    state = load_run_state(run)
    world = state.setdefault('world', {})
    if not world.get('coaching_mode'):
        return state
    world['fto_message'] = ' '.join(str(message or '').split()).strip()[:1000]
    run.state_json = _json(state)
    run.updated_at = datetime.utcnow()
    db.session.commit()
    return state
