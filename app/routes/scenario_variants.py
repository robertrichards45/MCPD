import random
import re
import secrets

from flask import has_request_context, session

from ..simulator.location_catalog import (
    ACCESS_CONTROL_LOCATIONS,
    DISORDERLY_LOCATIONS,
    MEDICAL_LOCATIONS,
    PROPERTY_DAMAGE_LOCATIONS,
    RETAIL_LOCATIONS,
    TRAFFIC_LOCATIONS,
    crash_location_for_seed,
)


NEXT_SCENARIO = {'S001': 'S002', 'S002': 'S003', 'S003': 'S004', 'S004': 'S005', 'S005': 'S006', 'S006': 'S001'}
SESSION_KEY = 'sentinel_scenario_lab_v2'
SEED_OVERRIDE_KEY = 'sentinel_scenario_seed_override_v1'


# Location pools come from the handbook-derived, non-sensitive training catalog.
# Do not copy the complete LES Security Checklist into this public repository.
VARIANTS = {
    'S001': {
        'location': DISORDERLY_LOCATIONS,
        'subject_status': ('civilian visitor', 'contractor employee', 'active-duty service member', 'retiree with installation access'),
        'access_history': ('invited earlier', 'walked in during business hours', 'previously told to leave today', 'claims an employee invited them'),
        'demeanor': ('loud but stationary', 'argumentative and pacing', 'calm until challenged', 'emotionally upset and recording the encounter'),
        'witness_quality': ('one firsthand witness', 'two conflicting employees', 'only hearsay at first', 'camera coverage may exist'),
    },
    'S002': {
        'location': ACCESS_CONTROL_LOCATIONS,
        'purpose': ('contractor meeting', 'delivery', 'job interview', 'family visit', 'service appointment'),
        'credential_issue': ('no installation credential', 'expired credential', 'credential does not match claimed purpose', 'visitor sponsorship not located'),
        'demeanor': ('confused and cooperative', 'argumentative', 'nervous but compliant', 'impatient and filming'),
        'records_twist': ('no initial records information', 'identity requires clarification', 'vehicle registration differs from driver', 'sponsor information is incomplete'),
    },
    'S003': {
        'location': PROPERTY_DAMAGE_LOCATIONS,
        'property': ('light pole', 'parking bollard', 'government fence section', 'facility sign', 'government vehicle mirror'),
        'driver_status': ('civilian contractor', 'active-duty service member', 'government employee', 'delivery driver'),
        'knowledge': ('driver says contact was unnoticed', 'driver admits contact but thought there was no damage', 'driver disputes making contact', 'driver left and returned after being called'),
        'evidence': ('fresh vehicle damage', 'paint transfer only', 'camera may cover the area', 'physical marks are ambiguous'),
    },
    'S004': {
        'location': RETAIL_LOCATIONS,
        'conduct': ('item placed in a personal bag', 'price tag allegedly changed', 'merchandise moved between containers', 'self-checkout price discrepancy'),
        'video': ('clear video exists', 'video angle is partial', 'camera was offline', 'video exists but has not been preserved yet'),
        'subject_status': ('civilian', 'contractor employee', 'active-duty service member', 'dependent'),
        'intent_issue': ('subject claims mistake', 'subject claims another person moved the item', 'subject says they intended to pay', 'subject gives an inconsistent explanation'),
    },
    'S005': {
        'stop_location': TRAFFIC_LOCATIONS,
        'violation': ('speeding', 'failure to maintain lane', 'stop-sign violation', 'unsafe lane change'),
        'road': ('two-lane installation road', 'multi-lane arterial', 'low-light roadway', 'work-zone area'),
        'driver_demeanor': ('argumentative', 'anxious', 'cooperative but distracted', 'records the contact and challenges the reason for stop'),
        'movement': ('reaches toward center console', 'keeps searching through a bag', 'turns repeatedly toward the rear seat', 'keeps hands visible but refuses casual questions'),
    },
    'S006': {
        'location': MEDICAL_LOCATIONS,
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


def _location_metadata(location_text):
    text = str(location_text or '').strip()
    match = re.search(r'\bBldg\.\s*([A-Za-z0-9-]+)', text, re.I)
    building_number = match.group(1) if match else ''
    location_name = text
    if '—' in text:
        location_name = text.split('—', 1)[1].strip()
    elif ' - ' in text:
        location_name = text.split(' - ', 1)[1].strip()
    return {
        'location_display': text,
        'building_number': building_number,
        'location_name': location_name,
    }


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
        context.update(_location_metadata(choices['location']))
        context['dispatch_variant'] = (
            f"Unit 214, respond to {choices['location']}, MCLB Albany, for a disorderly person. "
            f"Caller reports the individual is {choices['demeanor']}. Access status is not yet resolved."
        )
    elif scenario_id == 'S002':
        context.update(_location_metadata(choices['location']))
        context['dispatch_variant'] = (
            f"Unit 214, respond to {choices['location']}, MCLB Albany, to assist gate personnel with "
            f"a {choices['purpose']} access issue. Reported problem: {choices['credential_issue']}. "
            f"Driver is {choices['demeanor']}."
        )
    elif scenario_id == 'S003':
        context.update(_location_metadata(choices['location']))
        context['dispatch_variant'] = (
            f"Unit 214, respond to {choices['location']}, MCLB Albany, for reported damage to government property. "
            f"A vehicle is reported in connection with damage to a {choices['property']}. "
            f"Operator is reported as a {choices['driver_status']}."
        )
        context['visual_evidence'] = ['Damage overview image can unlock after scene documentation.', 'Vehicle-to-object comparison can unlock if both remain available.']
    elif scenario_id == 'S004':
        context.update(_location_metadata(choices['location']))
        context['dispatch_variant'] = (
            f"Unit 214, respond to {choices['location']}, MCLB Albany, for a reported larceny/shoplifting incident. "
            f"Staff reports {choices['conduct']}. Video status: {choices['video']}."
        )
        context['visual_evidence'] = ['Surveillance stills appear only when usable video exists and is preserved.', 'Recovered-property imagery appears only when it helps establish a material fact.']
    elif scenario_id == 'S005':
        context.update(_location_metadata(choices['stop_location']))
        context['dispatch_variant'] = (
            f"Traffic enforcement at {choices['stop_location']}, MCLB Albany. You observe a {choices['violation']}. "
            f"The vehicle stops and the driver is initially {choices['driver_demeanor']}."
        )
        context['visual_evidence'] = ['A roadway / vehicle-position diagram can unlock when positioning becomes a decision issue.']
    elif scenario_id == 'S006':
        context.update(_location_metadata(choices['location']))
        context['dispatch_variant'] = (
            f"Unit 214, respond to {choices['location']}, MCLB Albany, for a medical assist. "
            f"Reported condition: {choices['presentation']}. Patient is {choices['patient_state']}; "
            f"{choices['witness_pattern']}."
        )
        context['visual_evidence'] = ['A scene-layout diagram can unlock if crowding, hazards, or EMS access becomes operationally important.']
    elif scenario_id == 'S007':
        crash_location = crash_location_for_seed(chosen_seed)
        context.update(_location_metadata(crash_location))
        # Roadway calls should keep the named road visible everywhere on the CAD
        # screen instead of collapsing the scene-board label to a nearby building.
        context['location_name'] = crash_location
        context['dispatch_variant'] = (
            f"Unit 214, respond to {crash_location}, MCLB Albany, for a vehicle crash. "
            "Injury status and roadway conditions are still being developed."
        )
        context['visual_evidence'] = [
            'A crash-scene / final-rest diagram can unlock as the officer develops the roadway evidence.'
        ]
    return context


def actor_variant_fact(run_context, actor_id, question):
    choices = (run_context or {}).get('choices') or {}
    low = str(question or '').lower()
    scenario_id = str((run_context or {}).get('run_id', '')).split('-', 1)[0]

    if actor_id == 'dispatch' and any(term in low for term in ('initial', 'call', 'information', 'dispatch', 'location', 'address', 'building')):
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
