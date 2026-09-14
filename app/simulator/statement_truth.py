from copy import deepcopy


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _append(profile, value):
    value = _text(value)
    if not value:
        return
    rows = list(profile.get('private_facts') or [])
    if value not in rows:
        rows.append(value)
    profile['private_facts'] = rows


def enrich_statement_truth(truth, scenario_id, run_context=None):
    """Add bounded statement-ready facts without changing scenario outcomes.

    These facts give a simulated declarant enough structured content to complete a
    written statement even when the trainee requests the statement before a lengthy
    oral interview. The function never invents a weapon, offense, confession, legal
    conclusion, or other fact outside the configured scenario/run choices.
    """
    truth = deepcopy(truth or {})
    choices = dict((run_context or {}).get('choices') or {})
    people = truth.setdefault('people', {})

    if scenario_id == 'S003':
        property_name = choices.get('property', 'government property')
        evidence = choices.get('evidence', 'physical marks are present')
        reporting = people.setdefault('reporting', {})
        witness = people.setdefault('witness', {})
        driver = people.setdefault('driver', {})
        _append(reporting, f'I became aware that a government {property_name} had been damaged. I did not personally witness the vehicle make contact.')
        _append(witness, f'I personally observed the vehicle make contact with the government {property_name}.')
        _append(witness, f'The physical condition I observed was consistent with this run description: {evidence}.')
        _append(driver, choices.get('knowledge', 'My knowledge of whether contact occurred is limited to what I personally noticed.'))

    elif scenario_id == 'S004':
        conduct = choices.get('conduct', 'reported handling of merchandise')
        video = choices.get('video', 'video availability is uncertain')
        lp = people.setdefault('lp', {})
        subject = people.setdefault('subject', {})
        _append(lp, f'I personally observed the reported merchandise conduct described in this run as: {conduct}.')
        _append(lp, f'The store video status for this incident is: {video}.')
        _append(lp, 'Store records can document the value of the merchandise involved.')
        _append(subject, choices.get('intent_issue', 'I dispute that I intended to steal the merchandise.'))

    elif scenario_id == 'S006':
        patient = people.setdefault('patient', {})
        fullwitness = people.setdefault('fullwitness', {})
        _append(patient, f"My medical presentation was described as {choices.get('presentation', 'a medical complaint')}; I was {choices.get('patient_state', 'conscious')}.")
        _append(fullwitness, 'I personally observed more of the event sequence than the coworkers who only saw the aftermath.')

    truth['people'] = people
    return truth
