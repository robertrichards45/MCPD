from collections import Counter


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _timeline(state):
    return list(((state or {}).get('world') or {}).get('timeline') or [])


def _actions(state):
    rows = []
    for event in _timeline(state):
        if event.get('event_type') != 'trainee_action':
            continue
        for action in ((event.get('details') or {}).get('actions') or []):
            if isinstance(action, dict) and _text(action.get('action_type')):
                rows.append(action)
    return rows


def summarize_run(state):
    """Return evidence-based simulator metrics, never an official FTO rating."""
    state = state or {}
    world = state.get('world') or {}
    actions = _actions(state)
    action_types = Counter(_text(row.get('action_type')).lower() for row in actions)

    contacted_people = set()
    for event in _timeline(state):
        if event.get('event_type') == 'npc_response':
            actor_id = _text((event.get('details') or {}).get('actor_id')) or _text(event.get('actor'))
            if actor_id:
                contacted_people.add(actor_id)

    evidence = world.get('evidence') or {}
    evidence_status = Counter(_text(row.get('status')).lower() for row in evidence.values() if isinstance(row, dict))
    preserved_ids = [
        key for key, row in evidence.items()
        if isinstance(row, dict) and _text(row.get('status')).lower() in {'preserved', 'collected'}
    ]
    lost_ids = [
        key for key, row in evidence.items()
        if isinstance(row, dict) and _text(row.get('status')).lower() == 'lost'
    ]

    return {
        'scenario_id': _text(state.get('scenario_id')),
        'run_id': _text((state.get('run_context') or {}).get('run_id')),
        'clock': int(world.get('clock', 0) or 0),
        'radio_status': action_types['radio_status'],
        'backup_requests': action_types['request_backup'],
        'medical_requests': action_types['request_ems'],
        'observations': action_types['observe'],
        'interviews': action_types['interview'] + action_types['speak'],
        'people_contacted': len(contacted_people),
        'records_checks': action_types['records_check'],
        'evidence_actions': action_types['preserve_evidence'] + action_types['document_evidence'] + action_types['collect_evidence'],
        'evidence_preserved': len(preserved_ids),
        'evidence_lost': len(lost_ids),
        'legal_articulation': action_types['legal_assessment'],
        'deescalation': action_types['deescalate'],
        'documentation': action_types['document_report'],
        'supervisor_notifications': action_types['notify_supervisor'],
        'investigator_requests': action_types['request_investigator'],
        'no_enforcement': action_types['no_enforcement'],
        'release_actions': action_types['release'],
        'enforcement_actions': action_types['arrest'] + action_types['cite'] + action_types['detain'],
        'interventions': int(state.get('intervention_count', 0) or 0),
        'revisions': int(state.get('revision_count', 0) or 0),
        'actor_interactions': int(state.get('actor_interactions', 0) or 0),
        'terminal': bool(state.get('terminated')),
        'complete': bool(state.get('complete')),
        'preserved_evidence_ids': preserved_ids,
        'lost_evidence_ids': lost_ids,
        'evidence_status': dict(evidence_status),
    }


COMPARISON_FIELDS = (
    ('radio_status', 'Radio status transmissions'),
    ('backup_requests', 'Backup requests'),
    ('people_contacted', 'People contacted'),
    ('interviews', 'Interview / conversation actions'),
    ('records_checks', 'Records checks'),
    ('evidence_preserved', 'Evidence preserved / collected'),
    ('evidence_lost', 'Evidence opportunities lost'),
    ('legal_articulation', 'Legal-basis articulation'),
    ('deescalation', 'De-escalation actions'),
    ('documentation', 'Documentation actions'),
    ('interventions', 'Evaluator interventions'),
    ('revisions', 'Revisions / held decisions'),
)


def compare_runs(first_state, second_state):
    first = summarize_run(first_state)
    second = summarize_run(second_state)
    rows = []
    for key, label in COMPARISON_FIELDS:
        a = int(first.get(key, 0) or 0)
        b = int(second.get(key, 0) or 0)
        rows.append({
            'key': key,
            'label': label,
            'first': a,
            'second': b,
            'delta': b - a,
        })
    return {'first': first, 'second': second, 'rows': rows}


def aggregate_patterns(states):
    summaries = [summarize_run(state) for state in states if isinstance(state, dict)]
    count = len(summaries)
    if not count:
        return {'run_count': 0, 'patterns': [], 'summaries': []}

    def runs_with(field, predicate=lambda value: value > 0):
        return sum(1 for row in summaries if predicate(int(row.get(field, 0) or 0)))

    metrics = [
        ('Radio communication', 'radio_status', 'runs contained a radio status transmission'),
        ('Witness / person development', 'people_contacted', 'runs included contact with two or more involved people'),
        ('Evidence preservation', 'evidence_preserved', 'runs preserved or collected a structured evidence item'),
        ('Records / database use', 'records_checks', 'runs used a synthetic records check'),
        ('Legal articulation', 'legal_articulation', 'runs explicitly articulated a legal basis or lack of one'),
        ('Documentation', 'documentation', 'runs included an explicit documentation action'),
        ('De-escalation', 'deescalation', 'runs included a deliberate de-escalation action'),
        ('Resource use', 'backup_requests', 'runs requested another patrol unit'),
    ]

    patterns = []
    for label, field, phrase in metrics:
        if field == 'people_contacted':
            hits = runs_with(field, lambda value: value >= 2)
        else:
            hits = runs_with(field)
        patterns.append({
            'label': label,
            'hits': hits,
            'runs': count,
            'percent': round((hits / count) * 100),
            'observation': f'{hits} of {count} {phrase}.',
        })

    interventions = sum(int(row.get('interventions', 0) or 0) for row in summaries)
    lost = sum(int(row.get('evidence_lost', 0) or 0) for row in summaries)
    return {
        'run_count': count,
        'patterns': patterns,
        'summaries': summaries,
        'total_interventions': interventions,
        'total_evidence_lost': lost,
        'advisory': 'These are simulator observations for human FTO review, not DOR ratings or automatic training decisions.',
    }
