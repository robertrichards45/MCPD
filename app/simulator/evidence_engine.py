from copy import deepcopy

from .evidence_visuals import initialize_visual_evidence
from .person_records import obtain_requested_statements, reveal_requested_identities
from .statement_truth import enrich_statement_truth
from .world_state import add_known_information, add_timeline, ensure_world_state


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def initialize_truth_and_evidence(state, scenario_id, truth):
    world = ensure_world_state(state, scenario_id)
    enriched_truth = enrich_statement_truth(truth, scenario_id, state.get('run_context') or {})
    if not world.get('truth'):
        world['truth'] = deepcopy(enriched_truth or {})
    environment = ((enriched_truth or {}).get('environment') or {})
    if environment:
        world['environment'].update(deepcopy(environment))
    evidence = dict(world.get('evidence') or {})
    for evidence_id, source in ((enriched_truth or {}).get('evidence') or {}).items():
        if not source.get('exists'):
            continue
        if evidence_id in evidence:
            continue
        evidence[evidence_id] = {
            'id': evidence_id,
            'label': source.get('label') or evidence_id,
            'status': source.get('status') or 'hidden',
            'source': source.get('source') or '',
            'location': source.get('location') or '',
            'description': source.get('description') or '',
            'discover_keywords': list(source.get('discover_keywords') or []),
            'expires_at': source.get('expires_at'),
            'discovered_at': None,
            'preserved_at': None,
        }
    world['evidence'] = evidence
    world.setdefault('statements', [])
    initialize_visual_evidence(state, scenario_id)
    return world


def _matches_evidence(row, raw_text):
    low = _text(raw_text).lower()
    if not low:
        return False
    keywords = [str(value).lower() for value in row.get('discover_keywords') or []]
    if any(keyword and keyword in low for keyword in keywords):
        return True
    label = str(row.get('label') or '').lower()
    return bool(label and any(word in low for word in label.split() if len(word) > 4))


def tick_evidence(state):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    clock = int(world.get('clock', 0))
    evidence = dict(world.get('evidence') or {})
    for evidence_id, row in evidence.items():
        expires_at = row.get('expires_at')
        if expires_at is None or row.get('status') in {'preserved', 'collected', 'lost'}:
            continue
        if clock >= int(expires_at):
            previously_known = row.get('status') in {'available', 'discovered'}
            row['status'] = 'lost'
            evidence[evidence_id] = row
            add_timeline(
                state,
                'evidence_lost',
                f"{row.get('label')} is no longer available.",
                actor='Scene',
                channel='scene',
                details={'evidence_id': evidence_id},
                visible_to_trainee=previously_known,
            )
    world['evidence'] = evidence


def apply_evidence_actions(state, actions, raw_text):
    """Discover/preserve structured evidence and developed person records.

    Synthetic identity information is revealed only when the trainee actually asks
    for identification/contact information. Written statements are completed by the
    simulated declarant and stored as read-only training documents; the officer does
    not fill out another person's statement.
    """
    world = ensure_world_state(state, state.get('scenario_id', ''))
    initialize_visual_evidence(state, state.get('scenario_id', ''))
    tick_evidence(state)

    changed = []
    for actor_id in reveal_requested_identities(state, actions, raw_text):
        changed.append({'id': actor_id, 'change': 'person_identified'})
    for statement in obtain_requested_statements(state, actions, raw_text):
        changed.append({'id': statement.get('id'), 'change': 'statement_received'})

    evidence = dict(world.get('evidence') or {})
    types = {str(row.get('action_type') or '').strip().lower() for row in (actions or [])}
    discovery_action = bool(types & {'observe', 'interview', 'identify_person', 'document_evidence', 'preserve_evidence', 'collect_evidence'})
    if not discovery_action:
        return changed

    for evidence_id, row in evidence.items():
        if row.get('status') == 'lost':
            continue
        match = _matches_evidence(row, raw_text)
        if not match:
            continue

        if row.get('status') in {'hidden', 'available'}:
            row['status'] = 'discovered'
            row['discovered_at'] = int(world.get('clock', 0))
            changed.append({'id': evidence_id, 'change': 'discovered'})
            add_known_information(state, f"Evidence located: {row.get('label')}. {row.get('description')}", source='evidence')
            add_timeline(
                state,
                'evidence_discovered',
                f"Evidence located: {row.get('label')}.",
                actor='Trainee',
                channel='scene',
                details={'evidence_id': evidence_id},
                visible_to_trainee=True,
            )

        if 'preserve_evidence' in types and row.get('status') in {'discovered', 'available'}:
            row['status'] = 'preserved'
            row['preserved_at'] = int(world.get('clock', 0))
            changed.append({'id': evidence_id, 'change': 'preserved'})
            add_timeline(
                state,
                'evidence_preserved',
                f"{row.get('label')} is preserved for the synthetic investigation.",
                actor='Trainee',
                channel='scene',
                details={'evidence_id': evidence_id},
                visible_to_trainee=True,
            )
        elif 'collect_evidence' in types and row.get('status') in {'discovered', 'available', 'preserved'}:
            row['status'] = 'collected'
            changed.append({'id': evidence_id, 'change': 'collected'})
            add_timeline(
                state,
                'evidence_collected',
                f"{row.get('label')} is collected in the synthetic exercise.",
                actor='Trainee',
                channel='scene',
                details={'evidence_id': evidence_id},
                visible_to_trainee=True,
            )
        evidence[evidence_id] = row

    world['evidence'] = evidence
    tick_evidence(state)
    return changed