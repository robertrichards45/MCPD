import re

ENGINE_VERSION = 1


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _low(value):
    return _text(value).lower()


def _has_any(text, terms):
    low = _low(text)
    return any(term in low for term in terms)


def _signal_map(text):
    low = _low(text)
    return {
        'backup': _has_any(low, ('request backup', 'request another unit', 'additional unit', 'another unit', 'cover unit', 'second unit')),
        'deescalation': _has_any(low, ('de-escalat', 'calm', 'professional', 'explain', 'listen', 'rapport', 'lower my voice', 'lower voice')),
        'antagonistic': _has_any(low, ('shut up', 'yell back', 'scream at', 'teach him', 'teach her', 'slam him', 'slam her', 'drag him', 'drag her')),
        'clear_direction': _has_any(low, ('clear direction', 'clear command', 'show me your hands', 'keep your hands', 'hands visible', 'step back', 'do not reach', "don't reach")),
        'witness': _has_any(low, ('witness', 'employee', 'staff member', 'reporting party', 'complainant', 'interview', 'statement')),
        'photos': _has_any(low, ('photo', 'photograph', 'pictures', 'document damage', 'document the damage')),
        'video': _has_any(low, ('video', 'camera', 'surveillance', 'footage')),
        'preserve': _has_any(low, ('preserve', 'secure evidence', 'collect evidence', 'evidence bag', 'maintain evidence', 'copy the video', 'save the video')),
        'records': _has_any(low, ('records check', 'wanted check', 'check the license', 'check the plate', 'run the plate', 'run the license')),
        'force': _has_any(low, ('tase', 'taser', 'pepper spray', 'oc spray', 'go hands on', 'use force', 'physical force')),
        'detain': _has_any(low, ('detain', 'detention', 'handcuff', 'cuff him', 'cuff her')),
        'arrest': _has_any(low, ('arrest', 'take into custody', 'custody')),
        'ems': _has_any(low, ('ems', 'medical', 'paramedic', 'ambulance', 'patient care', 'medical care')),
        'scene_control': _has_any(low, ('separate', 'move people back', 'clear the area', 'control the scene', 'scene control', 'keep coworkers back')),
        'dispatch': _has_any(low, ('dispatch', 'radio', 'on scene', 'status', 'location')),
        'legal_basis': _has_any(low, ('reasonable suspicion', 'probable cause', 'authority', 'policy', 'procedure', 'lawful', 'elements', 'facts support')),
    }


SCENARIO_PROFILES = {
    'S001': {'risk': 42, 'subject_state': 'argumentative', 'backup': 'not_requested'},
    'S002': {'risk': 30, 'subject_state': 'argumentative', 'backup': 'not_requested'},
    'S003': {'risk': 18, 'subject_state': 'neutral', 'backup': 'not_requested'},
    'S004': {'risk': 28, 'subject_state': 'guarded', 'backup': 'not_requested'},
    'S005': {'risk': 52, 'subject_state': 'argumentative', 'backup': 'not_requested'},
    'S006': {'risk': 35, 'subject_state': 'medical', 'backup': 'ems_enroute'},
}


BRANCH_EVENTS = {
    'subject_escalation': {
        'title': 'Live Event — Subject Escalation',
        'prompt': 'Your communication has increased tension. The subject steps closer, raises his voice, and bystanders begin recording. What do you do now?',
        'minimum': 3,
        'criteria': [
            ('Position / reaction gap', ('distance', 'position', 'reaction gap', 'cover', 'step back'), 'Create or maintain a defensible position and reaction gap.'),
            ('Calm, clear communication', ('calm', 'professional', 'de-escalat', 'clear direction', 'clear command', 'explain'), 'Use clear communication that does not unnecessarily intensify the encounter.'),
            ('Resources / backup', ('backup', 'additional unit', 'another unit', 'cover unit', 'dispatch'), 'Consider available resources as the encounter becomes more volatile.'),
            ('Proportional response', ('proportion', 'necessary', 'reasonable', 'force', 'hands', 'threat'), 'Tie any escalation in control or force to observable behavior and necessity.'),
        ],
        'resolved': 'The subject stops closing distance. The encounter remains tense, but you have regained enough control to continue the investigation.',
    },
    'witness_departing': {
        'title': 'Live Event — Witness Is Leaving',
        'prompt': 'A firsthand witness says they must return to work immediately and is walking away before you have interviewed them. What do you do?',
        'minimum': 2,
        'criteria': [
            ('Identify / preserve contact', ('identify', 'name', 'contact information', 'phone', 'employee', 'badge'), 'Preserve the witness identity and a way to follow up.'),
            ('Obtain or preserve account', ('statement', 'interview', 'what they saw', 'what they heard', 'brief account'), 'Obtain or preserve the firsthand account if reasonably possible.'),
            ('Lawful handling', ('voluntary', 'lawful', 'detain', 'authority', 'not force', 'do not force'), 'Do not invent authority to hold a witness simply for convenience.'),
        ],
        'resolved': 'You preserve enough witness information to prevent the investigation from losing the firsthand account.',
    },
    'vehicle_evidence_departure': {
        'title': 'Live Event — Evidence May Leave the Scene',
        'prompt': 'The contractor supervisor says the truck is needed at another job and the driver is preparing to leave before vehicle damage has been fully documented. What do you do?',
        'minimum': 3,
        'criteria': [
            ('Photograph / document', ('photo', 'photograph', 'document damage', 'pictures'), 'Document transient physical evidence before it changes or leaves.'),
            ('Identify driver / vehicle', ('driver', 'license', 'plate', 'vin', 'vehicle', 'identify'), 'Preserve driver and vehicle identifying information.'),
            ('Preserve lawful evidence', ('preserve', 'evidence', 'measure', 'compare', 'damage'), 'Preserve relevant evidence without exceeding lawful authority.'),
            ('Coordinate', ('supervisor', 'contractor', 'dispatch', 'explain'), 'Communicate why documentation is needed and coordinate the delay professionally.'),
        ],
        'resolved': 'The vehicle remains long enough for necessary identifying information and damage documentation to be preserved.',
    },
    'shoplifting_pressure': {
        'title': 'Live Event — Subject Demands to Leave',
        'prompt': 'The subject says the delay is over and demands to leave while staff still has not preserved the surveillance video. What do you do?',
        'minimum': 3,
        'criteria': [
            ('Legal status / authority', ('detain', 'free to leave', 'reasonable suspicion', 'probable cause', 'authority', 'facts'), 'Know and articulate the subject’s lawful status rather than holding them by assumption.'),
            ('Preserve evidence', ('video', 'surveillance', 'copy', 'preserve', 'secure evidence'), 'Act to preserve material evidence while it is available.'),
            ('Witness / statement', ('loss prevention', 'statement', 'witness', 'interview'), 'Preserve the firsthand witness account.'),
            ('Professional control', ('calm', 'professional', 'explain', 'clear'), 'Control the interaction without unnecessary escalation.'),
        ],
        'resolved': 'The legal status is clarified and the material evidence is preserved before the investigation continues.',
    },
    'rapid_reach': {
        'title': 'Live Event — Sudden Reaching Movement',
        'prompt': 'During the traffic stop, the driver suddenly reaches toward the center console again after previously being told to keep hands visible. No weapon is visible. What do you do now?',
        'minimum': 3,
        'criteria': [
            ('Immediate safety position', ('distance', 'position', 'cover', 'move', 'reaction gap'), 'Use positioning and available cover/reaction distance.'),
            ('Clear commands / hands', ('hands', 'do not reach', "don't reach", 'clear command', 'clear direction', 'show me'), 'Give clear direction tied to the observed behavior.'),
            ('Resources', ('backup', 'additional unit', 'another unit', 'dispatch'), 'Account for available backup/resources as risk increases.'),
            ('Proportionality / observe threat', ('weapon', 'threat', 'force', 'proportion', 'necessary', 'observe'), 'Do not convert an ambiguous reach into an unsupported deadly-threat conclusion.'),
        ],
        'resolved': 'The driver stops reaching and places both hands where you can see them. The stop can continue from the new risk posture.',
    },
    'patient_deterioration': {
        'title': 'Live Event — Patient Condition Changes',
        'prompt': 'The patient becomes less responsive as EMS arrives, and several coworkers crowd closer while trying to explain what happened. What do you do?',
        'minimum': 3,
        'criteria': [
            ('Medical priority', ('ems', 'medical', 'paramedic', 'patient care', 'give space'), 'Prioritize patient access to medical care.'),
            ('Scene control', ('clear the area', 'move people back', 'scene control', 'separate', 'keep coworkers back'), 'Create space for care and maintain an orderly scene.'),
            ('Preserve witness information', ('identify', 'witness', 'name', 'contact', 'separate'), 'Preserve witness identities without interfering with treatment.'),
            ('Radio / status update', ('dispatch', 'radio', 'update', 'status'), 'Update communications when the condition materially changes.'),
        ],
        'resolved': 'EMS has clear access to the patient while witness information remains available for later clarification.',
    },
}


def new_engine_state(scenario_id):
    profile = SCENARIO_PROFILES.get(scenario_id, {})
    return {
        'engine_version': ENGINE_VERSION,
        'clock': 0,
        'risk': int(profile.get('risk', 30)),
        'subject_state': profile.get('subject_state', 'neutral'),
        'backup': profile.get('backup', 'not_requested'),
        'backup_requested_at': None,
        'evidence': {},
        'actors': {},
        'pending_event': None,
        'events_seen': [],
        'branch_count': 0,
        'complaint_risk': False,
        'use_of_force_review': False,
        'scene_updates': [],
        'decision_history': [],
    }


def ensure_engine_state(state, scenario_id):
    engine = state.get('engine')
    if not isinstance(engine, dict) or int(engine.get('engine_version', 0) or 0) != ENGINE_VERSION:
        engine = new_engine_state(scenario_id)
        state['engine'] = engine
    return engine


def _actor_row(engine, actor_id):
    actors = dict(engine.get('actors') or {})
    row = dict(actors.get(actor_id) or {})
    row.setdefault('contacts', 0)
    row.setdefault('contacted', False)
    row.setdefault('status', 'available')
    actors[actor_id] = row
    engine['actors'] = actors
    return row


def actor_available(state, scenario_id, actor_id):
    engine = ensure_engine_state(state, scenario_id)
    row = (engine.get('actors') or {}).get(actor_id) or {}
    return row.get('status', 'available') != 'departed'


def _add_scene_update(engine, message):
    message = _text(message)
    if not message:
        return
    rows = list(engine.get('scene_updates') or [])
    if message not in rows:
        rows.append(message)
    engine['scene_updates'] = rows[-6:]


def _set_pending_event(engine, event_id, consequence=None):
    if engine.get('pending_event') or event_id in (engine.get('events_seen') or []):
        return None
    engine['pending_event'] = event_id
    seen = list(engine.get('events_seen') or [])
    seen.append(event_id)
    engine['events_seen'] = seen
    engine['branch_count'] = int(engine.get('branch_count', 0)) + 1
    if consequence:
        _add_scene_update(engine, consequence)
    return consequence


def _risk_label(value):
    value = int(value or 0)
    if value >= 75:
        return 'Critical'
    if value >= 55:
        return 'Elevated'
    if value >= 35:
        return 'Moderate'
    return 'Controlled'


def _advance_clock(state, scenario_id, turn, amount=1):
    engine = ensure_engine_state(state, scenario_id)
    engine['clock'] = int(engine.get('clock', 0)) + max(1, int(amount or 1))
    requested_at = engine.get('backup_requested_at')
    if engine.get('backup') == 'enroute' and requested_at is not None and engine['clock'] - int(requested_at) >= 2:
        engine['backup'] = 'arrived'
        _add_scene_update(engine, 'Requested backup has arrived and is available on scene.')

    consequences = []
    if engine.get('pending_event'):
        return consequences

    clock = int(engine.get('clock', 0))
    actors = engine.get('actors') or {}

    if scenario_id == 'S001' and turn >= 2 and clock >= 6:
        row = dict(actors.get('employee2') or {})
        if not row.get('contacted') and row.get('status', 'available') != 'departed':
            message = 'A firsthand employee witness says they have to return to work and starts leaving the area.'
            if _set_pending_event(engine, 'witness_departing', message):
                consequences.append(message)

    if scenario_id == 'S003' and turn >= 2 and clock >= 6:
        if not (engine.get('evidence') or {}).get('vehicle_photos'):
            message = 'The contractor is preparing to move the involved truck before its damage has been fully documented.'
            if _set_pending_event(engine, 'vehicle_evidence_departure', message):
                consequences.append(message)

    if scenario_id == 'S004' and turn >= 1 and clock >= 5:
        if not (engine.get('evidence') or {}).get('video_preserved'):
            message = 'The subject is becoming impatient while surveillance evidence still has not been preserved.'
            if _set_pending_event(engine, 'shoplifting_pressure', message):
                consequences.append(message)

    return consequences


def record_actor_interaction(state, scenario_id, turn, actor_id, question=''):
    engine = ensure_engine_state(state, scenario_id)
    row = _actor_row(engine, actor_id)
    row['contacts'] = int(row.get('contacts', 0)) + 1
    row['contacted'] = True
    if actor_id in {'witness', 'employee2', 'fullwitness', 'lp', 'staff', 'reporting'}:
        row['status'] = 'engaged'
    if scenario_id == 'S004' and actor_id == 'lp' and _has_any(question, ('preserve', 'copy', 'save', 'secure')):
        evidence = dict(engine.get('evidence') or {})
        evidence['video_preserved'] = True
        engine['evidence'] = evidence
        _add_scene_update(engine, 'Loss prevention is preserving the surveillance video for the investigation.')
    return _advance_clock(state, scenario_id, turn, 1)


def _apply_signals(state, scenario_id, turn, text, accepted):
    engine = ensure_engine_state(state, scenario_id)
    signals = _signal_map(text)
    consequences = []

    if signals['backup'] and engine.get('backup') == 'not_requested':
        engine['backup'] = 'enroute'
        engine['backup_requested_at'] = int(engine.get('clock', 0))
        consequences.append('You requested an additional unit. Backup is now en route and may affect later risk.')
        _add_scene_update(engine, 'Backup has been requested and is en route.')

    risk = int(engine.get('risk', 30))
    if signals['deescalation']:
        risk -= 10
        if engine.get('subject_state') not in {'medical', 'neutral'}:
            engine['subject_state'] = 'calming'
    if signals['antagonistic']:
        risk += 24
        engine['subject_state'] = 'agitated'
        engine['complaint_risk'] = True
        consequences.append('Your communication increases tension. The subject becomes more agitated and the likelihood of a complaint rises.')
    if signals['force']:
        risk += 18
        engine['use_of_force_review'] = True
        if risk < 65:
            engine['complaint_risk'] = True
    if signals['clear_direction']:
        risk -= 5
    if engine.get('backup') == 'arrived':
        risk -= 5
    engine['risk'] = max(0, min(100, risk))

    evidence = dict(engine.get('evidence') or {})
    if signals['photos']:
        evidence['photos'] = True
        if scenario_id == 'S003':
            evidence['vehicle_photos'] = True
    if signals['video'] and signals['preserve']:
        evidence['video_preserved'] = True
    if signals['witness']:
        evidence['witness_developed'] = True
    if signals['records']:
        evidence['records_requested'] = True
    if signals['ems']:
        evidence['medical_priority'] = True
    if signals['scene_control']:
        evidence['scene_control'] = True
    engine['evidence'] = evidence

    history = list(engine.get('decision_history') or [])
    history.append({
        'turn': int(turn),
        'accepted': bool(accepted),
        'signals': sorted(key for key, value in signals.items() if value),
        'risk_after': int(engine.get('risk', 0)),
    })
    engine['decision_history'] = history[-12:]

    return signals, consequences


def _maybe_branch_after_decision(state, scenario_id, turn, signals, accepted):
    engine = ensure_engine_state(state, scenario_id)
    consequences = []
    if engine.get('pending_event'):
        return consequences

    risk = int(engine.get('risk', 0))
    if scenario_id == 'S001' and turn >= 1 and (signals.get('antagonistic') or risk >= 68):
        message = 'The subject reacts to the encounter by stepping closer and raising his voice while bystanders begin recording.'
        if _set_pending_event(engine, 'subject_escalation', message):
            consequences.append(message)

    if scenario_id == 'S005' and turn >= 1 and engine.get('backup') == 'not_requested':
        message = 'The driver makes another sudden reach toward the center console before the stop can continue.'
        if _set_pending_event(engine, 'rapid_reach', message):
            consequences.append(message)

    if scenario_id == 'S006' and turn == 0 and accepted and not signals.get('ems'):
        message = 'The patient becomes less responsive just as EMS arrives, and coworkers crowd toward the patient.'
        if _set_pending_event(engine, 'patient_deterioration', message):
            consequences.append(message)

    return consequences


def apply_core_decision(state, scenario_id, turn, text, accepted):
    engine = ensure_engine_state(state, scenario_id)
    engine['clock'] = int(engine.get('clock', 0)) + 1
    signals, consequences = _apply_signals(state, scenario_id, turn, text, accepted)
    consequences.extend(_maybe_branch_after_decision(state, scenario_id, turn, signals, accepted))
    consequences.extend(_advance_clock(state, scenario_id, turn, 1))
    return consequences


def pending_event(state, scenario_id):
    engine = ensure_engine_state(state, scenario_id)
    event_id = engine.get('pending_event')
    if not event_id:
        return None
    event = dict(BRANCH_EVENTS.get(event_id) or {})
    if not event:
        engine['pending_event'] = None
        return None
    event['id'] = event_id
    event['kind'] = 'Live Branch Event'
    return event


def evaluate_branch_event(event_id, response_text):
    event = BRANCH_EVENTS.get(event_id) or {}
    text = _low(response_text)
    strengths = []
    gaps = []
    for label, terms, coaching in event.get('criteria', []):
        if any(term in text for term in terms):
            strengths.append(label)
        else:
            gaps.append(label)
    required = int(event.get('minimum', 2))
    accepted = len(strengths) >= required
    return {
        'status': 'accepted' if accepted else 'revision',
        'accepted': accepted,
        'headline': 'Live event stabilized' if accepted else 'Live event unresolved',
        'consequence': event.get('resolved') if accepted else 'The call remains in this live event. Reassess the changing facts and make another decision.',
        'strengths': strengths,
        'gaps': gaps,
        'hints': [],
        'issues': [],
        'met_count': len(strengths),
        'required_count': required,
        'criteria_count': len(event.get('criteria', [])),
    }


def resolve_branch_event(state, scenario_id, event_id, response_text):
    engine = ensure_engine_state(state, scenario_id)
    signals, consequences = _apply_signals(state, scenario_id, -1, response_text, True)
    event = BRANCH_EVENTS.get(event_id) or {}
    resolved = _text(event.get('resolved'))
    if resolved:
        consequences.append(resolved)
        _add_scene_update(engine, resolved)

    if event_id == 'witness_departing':
        row = _actor_row(engine, 'employee2')
        row['status'] = 'engaged'
        row['contacted'] = True
    elif event_id == 'vehicle_evidence_departure':
        evidence = dict(engine.get('evidence') or {})
        if signals.get('photos'):
            evidence['vehicle_photos'] = True
        evidence['vehicle_identified'] = True
        engine['evidence'] = evidence
    elif event_id == 'shoplifting_pressure':
        evidence = dict(engine.get('evidence') or {})
        if signals.get('video') or signals.get('preserve'):
            evidence['video_preserved'] = True
        engine['evidence'] = evidence
    elif event_id == 'rapid_reach':
        engine['subject_state'] = 'compliant' if signals.get('clear_direction') else 'guarded'
        engine['risk'] = max(35, int(engine.get('risk', 50)) - 12)
    elif event_id == 'patient_deterioration':
        evidence = dict(engine.get('evidence') or {})
        evidence['medical_priority'] = True
        engine['evidence'] = evidence

    engine['pending_event'] = None
    _advance_clock(state, scenario_id, 0, 1)
    return consequences


def current_decision(state, scenario_id, turn, core_stage):
    event = pending_event(state, scenario_id)
    if event:
        return {
            'name': event['title'],
            'prompt': event['prompt'],
            'kind': event['kind'],
            'event_id': event['id'],
            'rubric': {'minimum': event['minimum'], 'criteria': event['criteria']},
        }
    if not core_stage:
        return None
    return {
        'name': core_stage['name'],
        'prompt': core_stage['prompt'],
        'kind': 'Core Call Phase',
        'event_id': None,
        'rubric': None,
    }


def dynamic_facts(state, scenario_id):
    engine = ensure_engine_state(state, scenario_id)
    facts = [
        f"Current scene risk: {_risk_label(engine.get('risk'))}.",
        f"Backup status: {str(engine.get('backup', 'not_requested')).replace('_', ' ')}.",
    ]
    subject_state = _text(engine.get('subject_state'))
    if subject_state and subject_state != 'neutral':
        facts.append(f'Current subject/patient state: {subject_state}.')
    facts.extend(list(engine.get('scene_updates') or [])[-4:])
    return facts


def scene_status(state, scenario_id):
    engine = ensure_engine_state(state, scenario_id)
    evidence = engine.get('evidence') or {}
    evidence_rows = []
    labels = {
        'photos': 'Scene photographs documented',
        'vehicle_photos': 'Vehicle damage photographs documented',
        'video_preserved': 'Surveillance video preserved',
        'witness_developed': 'Witness information developed',
        'records_requested': 'Records check requested',
        'medical_priority': 'Medical care prioritized',
        'scene_control': 'Scene control established',
    }
    for key, label in labels.items():
        if evidence.get(key):
            evidence_rows.append(label)

    return {
        'risk_label': _risk_label(engine.get('risk')),
        'subject_state': _text(engine.get('subject_state')).replace('_', ' ').title(),
        'backup': _text(engine.get('backup')).replace('_', ' ').title(),
        'clock': int(engine.get('clock', 0)),
        'branch_count': int(engine.get('branch_count', 0)),
        'complaint_risk': bool(engine.get('complaint_risk')),
        'use_of_force_review': bool(engine.get('use_of_force_review')),
        'evidence': evidence_rows,
        'updates': list(engine.get('scene_updates') or [])[-5:],
    }
