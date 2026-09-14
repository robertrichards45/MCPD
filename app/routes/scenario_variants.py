import random
import secrets

from flask import has_request_context, session


NEXT_SCENARIO = {'S001': 'S002', 'S002': 'S003', 'S003': 'S004', 'S004': 'S005', 'S005': 'S006', 'S006': 'S001'}
SESSION_KEY = 'sentinel_scenario_lab_v2'
SEED_OVERRIDE_KEY = 'sentinel_scenario_seed_override_v1'


VARIANTS = {
    'S001': {
        'location': ('library public area', 'barracks common area', 'customer-service office', 'recreation facility lobby'),
        'subject_status': ('civilian visitor', 'contractor employee', 'active-duty service member', 'retiree with installation access'),
        'access_history': ('invited earlier', 'walked in during business hours', 'previously told to leave today', 'claims an employee invited them'),
        'demeanor': ('loud but stationary', 'argumentative and pacing', 'calm until challenged', 'emotionally upset and recording the encounter'),
        'witness_quality': ('one firsthand witness', 'two conflicting employees', 'only hearsay at first', 'camera coverage may exist'),
    },
    'S002': {
        'purpose': ('contractor meeting', 'delivery', 'job interview', 'family visit', 'service appointment'),
        'credential_issue': ('no installation credential', 'expired credential', 'credential does not match claimed purpose', 'visitor sponsorship not located'),
        'demeanor': ('confused and cooperative', 'argumentative', 'nervous but compliant', 'impatient and filming'),
        'records_twist': ('no initial records information', 'identity requires clarification', 'vehicle registration differs from driver', 'sponsor information is incomplete'),
    },
    'S003': {
        'property': ('light pole', 'parking bollard', 'government fence section', 'facility sign', 'government vehicle mirror'),
        'driver_status': ('civilian contractor', 'active-duty service member', 'government employee', 'delivery driver'),
        'knowledge': ('driver says contact was unnoticed', 'driver admits contact but thought there was no damage', 'driver disputes making contact', 'driver left and returned after being called'),
        'evidence': ('fresh vehicle damage', 'paint transfer only', 'camera may cover the area', 'physical marks are ambiguous'),
    },
    'S004': {
        'conduct': ('item placed in a personal bag', 'price tag allegedly changed', 'merchandise moved between containers', 'self-checkout price discrepancy'),
        'video': ('clear video exists', 'video angle is partial', 'camera was offline', 'video exists but has not been preserved yet'),
        'subject_status': ('civilian', 'contractor employee', 'active-duty service member', 'dependent'),
        'intent_issue': ('subject claims mistake', 'subject claims another person moved the item', 'subject says they intended to pay', 'subject gives an inconsistent explanation'),
    },
    'S005': {
        'violation': ('speeding', 'failure to maintain lane', 'stop-sign violation', 'unsafe lane change'),
        'road': ('two-lane installation road', 'multi-lane arterial near a gate', 'low-light roadway', 'work-zone area'),
        'driver_demeanor': ('argumentative', 'anxious', 'cooperative but distracted', 'records the contact and challenges the reason for stop'),
        'movement': ('reaches toward center console', 'keeps searching through a bag', 'turns repeatedly toward the rear seat', 'keeps hands visible but refuses casual questions'),
    },
    'S006': {
        'presentation': ('dizziness and near-syncope', 'confusion after a collapse', 'possible seizure-like activity reported by a coworker', 'chest discomfort with anxiety', 'weakness after working in heat'),
        'witness_pattern': ('two coworkers give conflicting timelines', 'one witness saw only the aftermath', 'a supervisor repeats hearsay as fact', 'one employee may have seen the entire event but is about to leave'),
        'scene_issue': ('coworkers crowd the patient', 'equipment blocks EMS access', 'patient wants to stand despite dizziness', 'a coworker insists it was an assault without firsthand knowledge'),
        'patient_state': ('conscious but confused', 'alert but anxious', 'intermittently less responsive', 'oriented but unable to remember the event'),
    },
}


def _draw_choices(scenario_id, seed):
    rng = random.Random(int(seed))
    options = VARIANTS.get(scenario_id, {})
    return {key: rng.choice(tuple(values)) for key, values in options.items()}


def _current_request_choices(scenario_id):
    if not has_request_context():
        return {}
    state = session.get(SESSION_KEY)
    if not isinstance(state, dict) or state.get('scenario_id') != scenario_id:
        return {}
    return dict(((state.get('run_context') or {}).get('choices')) or {})


def _consume_seed_override(scenario_id):
    if not has_request_context():
        return None
    override = session.get(SEED_OVERRIDE_KEY)
    if not isinstance(override, dict) or override.get('scenario_id') != scenario_id:
        return None
    session.pop(SEED_OVERRIDE_KEY, None)
    session.modified = True
    try:
        return int(override.get('seed'))
    except (TypeError, ValueError):
        return None


def build_run_context(scenario_id, seed=None, previous_choices=None):
    if seed is None:
        seed = _consume_seed_override(scenario_id)
    explicit_seed = seed is not None
    if previous_choices is None:
        previous_choices = _current_request_choices(scenario_id)
    previous_choices = dict(previous_choices or {})

    if explicit_seed:
        chosen_seed = int(seed)
        choices = _draw_choices(scenario_id, chosen_seed)
    else:
        chosen_seed = None
        choices = {}
        for _ in range(16):
            candidate_seed = secrets.randbelow(900000000) + 100000000
            candidate = _draw_choices(scenario_id, candidate_seed)
            chosen_seed = candidate_seed
            choices = candidate
            if not previous_choices or candidate != previous_choices:
                break

        if previous_choices and choices == previous_choices and choices:
            options = VARIANTS.get(scenario_id, {})
            first_key = next(iter(options))
            values = tuple(options[first_key])
            if len(values) > 1:
                current = choices.get(first_key)
                index = values.index(current) if current in values else 0
                choices[first_key] = values[(index + 1) % len(values)]

    context = {
        'seed': int(chosen_seed),
        'run_id': f'{scenario_id}-{int(chosen_seed)}',
        'choices': choices,
        'visual_evidence': [],
    }

    if scenario_id == 'S001':
        context['dispatch_variant'] = f"Respond to the {choices['location']} for a disorderly person. Initial demeanor: {choices['demeanor']}. Access history is not yet resolved."
    elif scenario_id == 'S002':
        context['dispatch_variant'] = f"Main Gate requests patrol assistance with a {choices['purpose']} access issue: {choices['credential_issue']}. Driver is {choices['demeanor']}."
    elif scenario_id == 'S003':
        context['dispatch_variant'] = f"Respond to possible damage to a government {choices['property']}. Operator is reported as a {choices['driver_status']}; initial evidence: {choices['evidence']}."
        context['visual_evidence'] = ['Damage overview image can unlock after scene documentation.', 'Vehicle-to-object comparison can unlock if both remain available.']
    elif scenario_id == 'S004':
        context['dispatch_variant'] = f"Respond to a reported retail theft incident involving {choices['conduct']}. Video status: {choices['video']}. Subject status: {choices['subject_status']}."
        context['visual_evidence'] = ['Surveillance stills appear only when usable video exists and is preserved.', 'Recovered-property imagery appears only when it helps establish a material fact.']
    elif scenario_id == 'S005':
        context['dispatch_variant'] = f"You observe a {choices['violation']} on a {choices['road']}. Driver is initially {choices['driver_demeanor']}."
        context['visual_evidence'] = ['A roadway / vehicle-position diagram can unlock when positioning becomes a decision issue.']
    elif scenario_id == 'S006':
        context['dispatch_variant'] = f"Respond to a workplace medical assist: {choices['presentation']}. Patient is {choices['patient_state']}; {choices['witness_pattern']}."
        context['visual_evidence'] = ['A scene-layout diagram can unlock if crowding, hazards, or EMS access becomes operationally important.']
    return context


def actor_variant_fact(run_context, actor_id, question):
    choices = (run_context or {}).get('choices') or {}
    low = str(question or '').lower()
    scenario_id = str((run_context or {}).get('run_id', '')).split('-', 1)[0]

    if actor_id == 'dispatch' and any(term in low for term in ('initial', 'call', 'information', 'dispatch')):
        return (run_context or {}).get('dispatch_variant', '')

    if scenario_id == 'S001':
        if actor_id == 'staff' and any(term in low for term in ('leave', 'told', 'notice', 'invited')):
            return f"The access history I know is: {choices.get('access_history', 'unclear')}. I can only tell you what I personally said or heard."
        if actor_id == 'staff' and any(term in low for term in ('behavior', 'doing', 'demeanor')):
            return f"The person is currently described as {choices.get('demeanor', 'argumentative')}."
        if actor_id == 'subject' and any(term in low for term in ('military', 'status', 'active duty', 'contractor', 'civilian')):
            return f"My status is {choices.get('subject_status', 'civilian visitor')}."
    elif scenario_id == 'S002':
        if actor_id == 'driver' and any(term in low for term in ('why', 'purpose', 'here', 'visit')):
            return f"I am here for a {choices.get('purpose', 'business visit')}."
        if actor_id == 'gate' and any(term in low for term in ('credential', 'access', 'problem')):
            return f"The access issue is: {choices.get('credential_issue', 'credential problem')}."
    elif scenario_id == 'S003':
        if actor_id == 'driver' and any(term in low for term in ('status', 'military', 'contractor', 'employee')):
            return f"I am a {choices.get('driver_status', 'civilian contractor')}."
        if actor_id == 'driver' and any(term in low for term in ('know', 'contact', 'hit', 'damage')):
            return choices.get('knowledge', 'I am not sure whether contact occurred.')
        if actor_id in {'reporting', 'witness'} and any(term in low for term in ('evidence', 'damage', 'mark', 'vehicle')):
            return f"The physical evidence presently looks like: {choices.get('evidence', 'ambiguous marks')}."
    elif scenario_id == 'S004':
        if actor_id == 'lp' and any(term in low for term in ('video', 'camera', 'footage')):
            return choices.get('video', 'Video availability is uncertain.')
        if actor_id == 'lp' and any(term in low for term in ('what', 'conduct', 'observe', 'conceal')):
            return f"The conduct I am reporting is: {choices.get('conduct', 'suspicious handling of merchandise')}."
        if actor_id == 'subject' and any(term in low for term in ('intent', 'why', 'explain')):
            return choices.get('intent_issue', 'I say it was a mistake.')
    elif scenario_id == 'S005':
        if actor_id == 'driver' and any(term in low for term in ('why', 'reason', 'stop')):
            return f"You say the observed violation was {choices.get('violation', 'a traffic violation')}; I want you to explain it."
        if actor_id == 'driver' and any(term in low for term in ('reach', 'hands', 'movement', 'console', 'bag', 'seat')):
            return f"The movement you are reacting to is: {choices.get('movement', 'movement inside the vehicle')}."
    elif scenario_id == 'S006':
        if actor_id == 'patient' and any(term in low for term in ('feel', 'condition', 'happen', 'remember')):
            return f"I am {choices.get('patient_state', 'not feeling well')}; the main complaint is {choices.get('presentation', 'unclear symptoms')}."
        if actor_id.startswith('coworker') and any(term in low for term in ('see', 'what happened', 'witness')):
            return choices.get('witness_pattern', 'My view of the event was incomplete.')
    return ''
