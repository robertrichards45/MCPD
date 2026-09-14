"""Runtime behavior for handbook-grounded synthetic scenarios."""

from urllib.parse import quote_plus


HANDBOOK_PROFILES = {
    'S007': {'risk': 44, 'subject_state': 'crash_scene', 'backup': 'not_requested'},
    'S008': {'risk': 48, 'subject_state': 'detained_pending_confirmation', 'backup': 'not_requested'},
    'S009': {'risk': 58, 'subject_state': 'conflicted', 'backup': 'not_requested'},
    'S010': {'risk': 52, 'subject_state': 'driver_contact', 'backup': 'not_requested'},
    'S011': {'risk': 46, 'subject_state': 'unknown_building_status', 'backup': 'not_requested'},
    'S012': {'risk': 18, 'subject_state': 'property_custody', 'backup': 'not_requested'},
    'S013': {'risk': 34, 'subject_state': 'investigative_contact', 'backup': 'not_requested'},
    'S014': {'risk': 40, 'subject_state': 'uas_observation', 'backup': 'not_requested'},
}

HANDBOOK_BRANCH_EVENTS = {
    'crash_scene_changing': {
        'title': 'Live Event — Crash Scene Is Changing',
        'prompt': 'A driver wants to move a vehicle and passing traffic is beginning to disturb debris near the apparent collision area. What do you do now?',
        'minimum': 3,
        'criteria': [
            ('Traffic safety', ('traffic', 'block', 'lane', 'safe', 'secondary'), 'Control immediate roadway risk.'),
            ('Preserve scene', ('photo', 'photograph', 'final rest', 'debris', 'mark', 'document'), 'Preserve transient scene facts before they change.'),
            ('Vehicle movement decision', ('move vehicle', 'leave vehicle', 'safe location', 'position'), 'Make and document a safety-based movement decision.'),
            ('Coordinate', ('dispatch', 'tow', 'backup', 'driver'), 'Coordinate resources and involved drivers.'),
        ],
        'resolved': 'The changing crash scene is stabilized and enough transient information is preserved to continue the investigation.',
    },
    'warrant_extradition_conflict': {
        'title': 'Live Event — Extradition Instruction Changes the Custody Plan',
        'prompt': 'The entering agency confirms the warrant but advises that extradition from this location is not authorized. The subject is still being held. What do you do?',
        'minimum': 3,
        'criteria': [
            ('Follow confirmed instruction', ('release', 'not extraditable', 'agency instruction', 'no transport'), 'Do not continue custody solely because the initial hit existed.'),
            ('Document confirmation', ('warrant', 'agency', 'confirm', 'time', 'official'), 'Preserve the confirmation source and time.'),
            ('Property / status', ('property', 'return', 'restraint', 'release'), 'Account for property/restraint status during release.'),
            ('Supervisor / dispatch', ('dispatch', 'supervisor', 'watch commander', 'notify'), 'Update the responsible command/communications chain.'),
        ],
        'resolved': 'The custody status is corrected to match the confirmed extradition instruction and the release/notification trail is documented.',
    },
    'domestic_interference': {
        'title': 'Live Event — Parties Begin Interfering With Each Other',
        'prompt': 'The involved parties remain within speaking distance and begin arguing over each other while you are trying to establish what happened. What do you do?',
        'minimum': 3,
        'criteria': [
            ('Separate parties', ('separate', 'different room', 'distance', 'separate area'), 'Create separation to improve safety and statement integrity.'),
            ('Safety / medical', ('injury', 'medical', 'weapon', 'safety', 'backup'), 'Reassess immediate risk and medical needs.'),
            ('Independent accounts', ('statement', 'interview', 'one at a time', 'separately'), 'Obtain independent accounts.'),
            ('Scene control', ('calm', 'control', 'clear direction', 'professional'), 'Use professional scene control without escalating unnecessarily.'),
        ],
        'resolved': 'The parties are separated and the investigation can continue with safer, independent fact development.',
    },
    'dui_medical_complication': {
        'title': 'Live Event — Possible Medical Explanation',
        'prompt': 'Before additional field testing, the driver reports a medical condition and becomes unsteady in a way that may not be explained by alcohol. What do you do?',
        'minimum': 3,
        'criteria': [
            ('Medical priority', ('ems', 'medical', 'evaluate', 'paramedic'), 'Do not ignore a plausible medical problem.'),
            ('Testing limitation', ('stop test', 'do not continue', 'limitation', 'medical'), 'Do not force testing that is unsafe or invalid under the developed facts.'),
            ('Preserve observations', ('document', 'odor', 'speech', 'driving', 'observation'), 'Keep objective observations separate from medical interpretation.'),
            ('Reassess probable cause', ('probable cause', 'totality', 'reassess', 'facts'), 'Reassess the enforcement basis after the medical development.'),
        ],
        'resolved': 'Medical concerns are addressed without losing the objective impairment investigation, and the enforcement decision remains tied to the totality of verified facts.',
    },
    'unsecured_forced_entry_indicator': {
        'title': 'Live Event — Possible Forced Entry Indicator',
        'prompt': 'A closer exterior check reveals fresh damage near the latch and a facility representative has not arrived yet. What do you do?',
        'minimum': 3,
        'criteria': [
            ('Protect scene', ('protect', 'preserve', 'do not touch', 'scene'), 'Avoid destroying potential entry evidence.'),
            ('Photograph / document', ('photo', 'photograph', 'damage', 'latch', 'document'), 'Preserve the condition before it changes.'),
            ('Resources / coordination', ('backup', 'dispatch', 'supervisor', 'keyholder', 'physical security'), 'Coordinate appropriate resources.'),
            ('No unsupported solo entry', ('wait', 'do not enter', 'lawful', 'safety', 'backup'), 'Do not turn a possible forced entry into an avoidable solo-entry hazard.'),
        ],
        'resolved': 'The possible forced-entry scene is preserved and the response has appropriately escalated from a routine unsecured-building check.',
    },
    'property_claim_conflict': {
        'title': 'Live Event — Competing Property Claim',
        'prompt': 'A person arrives and claims the found property, but the description they provide is incomplete and another identifying record points elsewhere. What do you do?',
        'minimum': 3,
        'criteria': [
            ('Verify ownership', ('serial', 'receipt', 'records', 'describe', 'verify owner'), 'Require corroborating ownership information.'),
            ('Maintain custody', ('retain', 'custody', 'do not release', 'safekeeping'), 'Keep custody until ownership is adequately verified.'),
            ('Document claimant', ('identify', 'claimant', 'statement', 'contact'), 'Document the person and their claim.'),
            ('Avoid unnecessary search', ('do not open', 'authority', 'search', 'consent'), 'Do not search closed property merely to settle the claim without lawful authority.'),
        ],
        'resolved': 'The property remains in controlled custody while ownership is verified through objective identifying information.',
    },
    'consent_withdrawn': {
        'title': 'Live Event — Consent Is Withdrawn',
        'prompt': 'During a consent-based search, the subject clearly withdraws consent. No other search authority has yet been established. What do you do?',
        'minimum': 3,
        'criteria': [
            ('Stop consent search', ('stop', 'cease', 'withdrawn', 'end search'), 'Stop relying on consent once it is clearly withdrawn.'),
            ('Reassess authority', ('warrant', 'probable cause', 'authority', 'legal basis', 'reassess'), 'Identify whether another lawful basis independently exists.'),
            ('Preserve what lawfully occurred', ('document', 'time', 'scope', 'items already', 'evidence'), 'Document the consent scope, withdrawal, and already-lawful observations.'),
            ('No retaliation / coercion', ('professional', 'no coercion', 'do not threaten', 'release'), 'Do not punish or coerce the subject for withdrawing consent.'),
        ],
        'resolved': 'The consent search stops at the withdrawal point and any further action depends on an independently lawful basis.',
    },
    'uas_lost_from_view': {
        'title': 'Live Event — UAS Lost From View',
        'prompt': 'The aircraft leaves your view before an operator is identified. What information and actions do you preserve immediately?',
        'minimum': 3,
        'criteria': [
            ('Last seen data', ('last seen', 'time', 'direction', 'location', 'duration'), 'Preserve the last reliable observation.'),
            ('Notify / update', ('dispatch', 'watch commander', 'update', 'notify'), 'Update command/communications promptly.'),
            ('Witness / video preservation', ('witness', 'video', 'camera', 'preserve'), 'Preserve independent observation/video sources.'),
            ('No invented operator', ('unknown', 'not identified', 'do not assume', 'operator'), 'Do not convert a possible operator into a confirmed operator without facts.'),
        ],
        'resolved': 'The lost-sighting information is preserved and the incident can continue through witness/operator development and command reporting.',
    },
}


def _profile(private_facts=None, reliability='mostly_reliable'):
    return {
        'reliability': reliability,
        'deceptive': False,
        'incorrect_beliefs': [],
        'private_facts': list(private_facts or []),
        'deceptive_claims': [],
    }


def extend_truth(truth, scenario_id, run_context):
    """Populate hidden structured truth for S007-S014 without changing old runs."""
    choices = dict((run_context or {}).get('choices') or {})
    people = truth.setdefault('people', {})
    evidence = truth.setdefault('evidence', {})
    records = truth.setdefault('records_truth', {})
    constraints = truth.setdefault('disposition_constraints', [])

    if scenario_id == 'S007':
        people['driver1'] = _profile([f"Crash type: {choices.get('crash_type')}.", f"Injury status: {choices.get('injury')}."])
        people['driver2'] = _profile([f"Roadway: {choices.get('road')}."])
        people['crash_witness'] = _profile([f"Witness condition: {choices.get('witness')}."], 'limited_observation')
        evidence['crash_scene'] = {
            'label': 'Crash scene / final-rest diagram', 'exists': True, 'status': 'hidden',
            'source': 'officer scene observation', 'location': choices.get('road', 'installation roadway'),
            'discover_keywords': ['scene', 'final rest', 'position', 'diagram', 'sketch', 'observe', 'roadway'],
            'expires_at': 7, 'description': choices.get('scene_evidence', 'scene evidence varies'),
        }
        constraints.append('Do not state crash cause or fault beyond the physical evidence, statements, and verified roadway facts.')
    elif scenario_id == 'S008':
        people['wanted_subject'] = _profile([f"Identity condition: {choices.get('identity')}."])
        people['agency'] = _profile([f"Extradition instruction: {choices.get('extradition')}.", f"Caution: {choices.get('caution')}."])
        records['warrant'] = {'status': 'possible_hit', 'source': choices.get('hit_source'), 'extradition': choices.get('extradition'), 'caution': choices.get('caution')}
        evidence['warrant_confirmation'] = {
            'label': 'Confirmed warrant / extradition return', 'exists': True, 'status': 'hidden',
            'source': 'entering agency / dispatch', 'location': 'records system',
            'discover_keywords': ['confirm warrant', 'confirmation', 'extradition', 'entering agency', 'holding agency'],
            'expires_at': None, 'description': 'Run-specific warrant confirmation and extradition instruction.',
        }
        constraints.append('A wanted-person hit is not a substitute for confirming identity, warrant status, and extradition instructions before final disposition.')
    elif scenario_id == 'S009':
        people['party1'] = _profile([f"Relationship: {choices.get('relationship')}.", f"Conflict: {choices.get('conflict')}."])
        people['party2'] = _profile([f"Injury condition: {choices.get('injury')}.", f"Conflict: {choices.get('conflict')}."])
        people['domestic_witness'] = _profile([f"Witness condition: {choices.get('witness')}."], 'limited_observation')
        records['protective_order'] = {'status': choices.get('protective_order')}
        evidence['domestic_scene'] = {
            'label': 'Domestic scene / injury documentation', 'exists': True, 'status': 'hidden',
            'source': 'officer observation', 'location': 'incident scene',
            'discover_keywords': ['injury', 'photo', 'scene', 'condition', 'observe', 'document'],
            'expires_at': 9, 'description': choices.get('injury', 'injury condition varies'),
        }
        constraints.append('The simulator does not decide primary aggressor or guilt; the trainee must develop and articulate the facts and applicable authority.')
    elif scenario_id == 'S010':
        people['dui_driver'] = _profile([f"Contact basis: {choices.get('contact_basis')}.", f"Presentation: {choices.get('presentation')}.", f"Testing response: {choices.get('testing')}.", f"Implied-consent response: {choices.get('implied_response')}. "])
        evidence['dui_observations'] = {
            'label': 'DUI observation / testing record', 'exists': True, 'status': 'hidden',
            'source': 'officer observations and testing', 'location': 'traffic contact',
            'discover_keywords': ['field sobriety', 'fst', 'testing', 'odor', 'speech', 'balance', 'impairment'],
            'expires_at': None, 'description': choices.get('presentation', 'objective impairment observations vary'),
        }
        constraints.append('Do not use a sample threshold, warning, or test result as current authority; verify the current approved Georgia/installation procedure.')
    elif scenario_id == 'S011':
        people['keyholder'] = _profile([f"Keyholder response: {choices.get('keyholder')}."])
        evidence['entry_point'] = {
            'label': 'Unsecured-building entry point', 'exists': True, 'status': 'hidden',
            'source': 'officer scene observation', 'location': 'building entry',
            'discover_keywords': ['door', 'latch', 'entry', 'damage', 'pry', 'tamper', 'photograph'],
            'expires_at': 6, 'description': choices.get('entry', 'entry condition varies'),
        }
        records['alarm'] = {'status': choices.get('alarm')}
        constraints.append('An unsecured building may remain a routine security response or become a criminal/security incident depending on developed facts.')
    elif scenario_id == 'S012':
        people['finder'] = _profile([f"Recovery location: {choices.get('recovery')}."])
        people['claimant'] = _profile([f"Ownership condition: {choices.get('ownership')}."], 'limited_observation')
        evidence['found_property'] = {
            'label': 'Found property', 'exists': True, 'status': 'available',
            'source': 'finder / scene', 'location': choices.get('recovery', 'installation'),
            'discover_keywords': ['property', 'item', 'describe', 'serial', 'condition', 'found'],
            'expires_at': None, 'description': f"{choices.get('item')}; {choices.get('condition')}.",
        }
        constraints.append('Maintain custody and verify ownership; do not open/search closed property merely because police took possession unless lawful authority exists.')
    elif scenario_id == 'S013':
        people['reporting_officer'] = _profile([f"Initial fact: {choices.get('initial_fact')}. "])
        people['search_subject'] = _profile([f"Consent condition: {choices.get('consent')}.", f"Run outcome: {choices.get('outcome')}."])
        evidence['search_result'] = {
            'label': 'Search / observation result', 'exists': True, 'status': 'hidden',
            'source': 'lawful observation/search only', 'location': choices.get('source', 'contact location'),
            'discover_keywords': ['search', 'consent', 'observe', 'evidence', 'contraband'],
            'expires_at': None, 'description': choices.get('outcome', 'result varies'),
        }
        constraints.append('No search authority is assumed. Consent may be refused, limited, or withdrawn, and no-contraband is a valid outcome.')
    elif scenario_id == 'S014':
        people['uas_witness'] = _profile([f"Sighting: {choices.get('sighting')}.", f"Video: {choices.get('video')}."])
        people['possible_operator'] = _profile([f"Operator condition: {choices.get('operator')}."], 'limited_observation')
        evidence['uas_observation'] = {
            'label': 'UAS sighting / video record', 'exists': True, 'status': 'hidden',
            'source': 'officer/witness observation', 'location': 'installation area',
            'discover_keywords': ['drone', 'uas', 'video', 'camera', 'sighting', 'direction', 'last seen'],
            'expires_at': 6, 'description': f"{choices.get('sighting')}; {choices.get('video')}.",
        }
        constraints.append('Do not invent an operator, intent, or counter-UAS authority. Preserve observations and route command/security reporting through current policy.')
    return truth


def _low(text):
    return ' '.join(str(text or '').lower().split())


def handbook_branch_after_core(state, scenario_id, turn, text, accepted, set_event):
    """Create one meaningful changing event for each new scenario family."""
    if not accepted:
        return []
    engine = state.get('engine') or {}
    if engine.get('pending_event'):
        return []
    low = _low(text)
    choices = ((state.get('run_context') or {}).get('choices') or {})
    event_id = None
    message = None
    if scenario_id == 'S007' and turn <= 1 and not any(term in low for term in ('photo', 'photograph', 'final rest', 'diagram')):
        event_id, message = 'crash_scene_changing', 'Traffic and vehicle movement begin changing transient crash-scene evidence.'
    elif scenario_id == 'S008' and turn >= 1 and 'declines extradition' in str(choices.get('extradition', '')).lower():
        event_id, message = 'warrant_extradition_conflict', 'The holding agency confirms the warrant but declines extradition from this location.'
    elif scenario_id == 'S009' and turn == 0 and 'separate' not in low:
        event_id, message = 'domestic_interference', 'The involved parties begin talking over each other and the scene becomes harder to control.'
    elif scenario_id == 'S010' and turn <= 1 and 'medical' in str(choices.get('presentation', '')).lower():
        event_id, message = 'dui_medical_complication', 'A possible medical explanation develops before additional field testing.'
    elif scenario_id == 'S011' and turn <= 1 and ('damage' in str(choices.get('entry', '')).lower() or 'pry' in str(choices.get('entry', '')).lower()):
        event_id, message = 'unsecured_forced_entry_indicator', 'Fresh entry-point damage changes the call from a routine unsecured-door check to a possible incident.'
    elif scenario_id == 'S012' and turn >= 1 and 'multiple people claim' in str(choices.get('ownership', '')).lower():
        event_id, message = 'property_claim_conflict', 'A competing ownership claim develops before the property can be released.'
    elif scenario_id == 'S013' and turn >= 1 and 'withdrawn' in str(choices.get('consent', '')).lower():
        event_id, message = 'consent_withdrawn', 'The subject clearly withdraws previously granted search consent.'
    elif scenario_id == 'S014' and turn <= 1 and ('lost from view' in str(choices.get('sighting', '')).lower() or 'quickly lost' in str(choices.get('sighting', '')).lower()):
        event_id, message = 'uas_lost_from_view', 'The UAS is lost from view before an operator is confirmed.'
    if event_id and set_event(engine, event_id, message):
        return [message]
    return []


def handbook_legal_rows(scenario_id, run_context, turn, engine=None):
    """Research cues only. They never declare probable cause or guilt."""
    if int(turn or 0) < 1 and not (engine or {}).get('pending_event'):
        return []
    rows = []
    def item(citation, title, jurisdiction, query, why):
        rows.append({
            'citation': citation, 'title': title, 'jurisdiction': jurisdiction,
            'why': why,
            'lookup_url': '/legal/search?q=' + quote_plus(query) + '&state=GA&source=ALL',
            'official_url': '',
        })
    if scenario_id == 'S007':
        item('Georgia Title 40 / installation traffic authority', 'Crash / Traffic Enforcement Research', 'Georgia / Federal Installation', 'Georgia traffic crash law Title 40 installation accident', 'Verify the traffic provision that matches the actual observed conduct and installation jurisdiction; the crash itself does not prove a violation.')
    elif scenario_id == 'S008':
        item('Warrant confirmation / extradition procedure', 'Wanted-Person Confirmation', 'Records / Procedure', 'warrant extradition confirmation GCIC NCIC Georgia', 'Confirmation, identity, extradition limits, and receiving-agency instructions control the custody decision in the exercise.')
    elif scenario_id == 'S009':
        item('Current domestic-violence authority', 'Domestic / Family Violence Research', 'Georgia / Federal / UCMJ as applicable', 'Georgia family violence battery protective order UCMJ domestic violence', 'Research the offense and jurisdiction that match the developed facts and subject status; do not infer an aggressor from the call label.')
    elif scenario_id == 'S010':
        item('O.C.G.A. 40-5-67.1', 'Georgia Implied Consent — Verify Current Text', 'Georgia', 'OCGA 40-5-67.1 implied consent current warning', 'Use the current approved warning and procedure applicable to the driver. The simulator does not hard-code sample thresholds as the legal answer.')
        item('Georgia DUI law', 'DUI / Less-Safe / Per-Se Research', 'Georgia', 'Georgia DUI OCGA 40-6-391 current', 'Match the developed driving, impairment, and test facts to current authority; medical explanations and incomplete tests must be considered.')
    elif scenario_id == 'S011':
        item('MCO 5530.14A / local physical-security direction', 'Physical Security / Unsecured Building', 'Marine Corps / Local', 'MCO 5530.14A unsecured building physical security', 'Use current physical-security and local response procedures to distinguish routine security service from a reportable forced-entry/property incident.')
    elif scenario_id == 'S012':
        item('Property / evidence custody policy', 'Found Property / Evidence Custody', 'Policy / Evidence', 'found property evidence custody OPNAV 5580/22', 'Custody, ownership, lawful examination, and release authority depend on the property and circumstances actually developed.')
    elif scenario_id == 'S013':
        item('Current search-and-seizure authority', 'Consent / Search Authority', 'Federal / Georgia / UCMJ as applicable', 'consent search withdrawal scope probable cause vehicle room current law', 'Verify current search authority and jurisdiction. Consent is voluntary, scope-limited, and may be withdrawn; odor allegations are not treated as an automatic answer.')
    elif scenario_id == 'S014':
        item('Current UAS / command reporting direction', 'UAS / Drone Reporting', 'Marine Corps / Federal', 'Marine Corps UAS drone incident SITREP OPREP installation', 'Use current command guidance for notification, security/mission-impact screening, SITREP/UAS and OPREP decisions; no counter-UAS authority is implied by the simulator.')
    return rows
