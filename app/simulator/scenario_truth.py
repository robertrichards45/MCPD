import hashlib
import random


def _rng(run_context, salt='truth'):
    seed = int((run_context or {}).get('seed') or 1)
    digest = hashlib.sha256(f'{seed}|{salt}'.encode('utf-8')).hexdigest()
    return random.Random(int(digest[:16], 16))


def _common_environment(rng):
    time_of_day = rng.choice(('day', 'day', 'day', 'evening', 'night'))
    weather = rng.choice(('clear', 'clear', 'clear', 'light rain', 'overcast'))
    lighting = 'low light' if time_of_day in {'evening', 'night'} else 'normal daylight'
    if weather == 'light rain':
        visibility = 'slightly reduced'
    else:
        visibility = 'normal'
    return {
        'time_of_day': time_of_day,
        'weather': weather,
        'lighting': lighting,
        'noise': rng.choice(('normal', 'normal', 'moderate background noise')),
        'visibility': visibility,
        'crowd': rng.choice(('none', 'none', 'small number of bystanders')),
    }


def _profile(rng, reliability_options=None, deception_chance=0):
    reliability_options = reliability_options or ('reliable', 'mostly_reliable', 'limited_observation')
    reliability = rng.choice(tuple(reliability_options))
    deceptive = rng.randrange(100) < int(deception_chance or 0)
    return {
        'reliability': reliability,
        'deceptive': deceptive,
        'incorrect_beliefs': [],
        'private_facts': [],
    }


def build_scenario_truth(scenario_id, run_context):
    """Build immutable core facts for one reproducible synthetic run.

    Dialogue may vary, but these facts are the authoritative reality for the run.
    """
    choices = dict((run_context or {}).get('choices') or {})
    rng = _rng(run_context)
    truth = {
        'scenario_id': scenario_id,
        'run_id': (run_context or {}).get('run_id'),
        'environment': _common_environment(rng),
        'weapon_exists': False,
        'people': {},
        'evidence': {},
        'records_truth': {},
        'disposition_constraints': [],
    }

    if scenario_id == 'S001':
        truth['people']['staff'] = _profile(rng, ('reliable', 'mostly_reliable', 'limited_observation'))
        truth['people']['subject'] = _profile(rng, ('reliable', 'mostly_reliable'), deception_chance=18)
        truth['people']['employee2'] = _profile(rng, ('reliable', 'limited_observation', 'mistaken_on_details'))
        truth['people']['staff']['private_facts'] = [
            f"Access history: {choices.get('access_history', 'unclear')}.",
            f"Observed demeanor: {choices.get('demeanor', 'argumentative')}.",
        ]
        truth['people']['subject']['private_facts'] = [f"Status: {choices.get('subject_status', 'civilian visitor')}. "]
        if choices.get('witness_quality') == 'camera coverage may exist':
            truth['evidence']['facility_video'] = {
                'label': 'Facility surveillance video',
                'exists': True,
                'status': 'hidden',
                'source': 'facility camera system',
                'location': 'facility system',
                'discover_keywords': ['camera', 'video', 'surveillance'],
                'expires_at': 9,
                'description': 'Video may corroborate only the area covered by the camera.',
            }
        truth['disposition_constraints'].append('No enforcement outcome is required if the developed facts do not establish an offense or other lawful basis.')

    elif scenario_id == 'S002':
        truth['people']['gate'] = _profile(rng, ('reliable', 'reliable', 'mostly_reliable'))
        truth['people']['driver'] = _profile(rng, ('reliable', 'mostly_reliable'), deception_chance=10)
        truth['people']['sponsor'] = _profile(rng, ('reliable', 'mostly_reliable'))
        truth['people']['gate']['private_facts'] = [f"Credential issue: {choices.get('credential_issue', 'access issue')}."]
        truth['people']['driver']['private_facts'] = [f"Claimed purpose: {choices.get('purpose', 'visit')}."]
        truth['disposition_constraints'].append('Installation access may be denied without creating a criminal enforcement outcome.')

    elif scenario_id == 'S003':
        truth['people']['reporting'] = _profile(rng, ('limited_observation', 'mostly_reliable'))
        truth['people']['witness'] = _profile(rng, ('reliable', 'mostly_reliable', 'mistaken_on_details'))
        truth['people']['driver'] = _profile(rng, ('reliable', 'mostly_reliable'), deception_chance=12)
        truth['people']['driver']['private_facts'] = [choices.get('knowledge', 'Driver knowledge is unclear.')]
        truth['evidence']['property_damage'] = {
            'label': f"Damage to government {choices.get('property', 'property')}",
            'exists': True,
            'status': 'available',
            'source': 'scene observation',
            'location': 'incident scene',
            'discover_keywords': ['damage', 'pole', 'fence', 'sign', 'mirror', 'property', 'examine', 'look'],
            'expires_at': None,
            'description': choices.get('evidence', 'physical marks are present'),
        }
        if 'camera' in choices.get('evidence', '').lower():
            truth['evidence']['surveillance'] = {
                'label': 'Possible surveillance recording',
                'exists': True,
                'status': 'hidden',
                'source': 'nearby camera system',
                'location': 'facility system',
                'discover_keywords': ['camera', 'video', 'surveillance'],
                'expires_at': 10,
                'description': 'The recording covers only part of the relevant area.',
            }
        truth['disposition_constraints'].append('Damage alone does not establish willfulness, negligence, or criminal culpability.')

    elif scenario_id == 'S004':
        truth['people']['lp'] = _profile(rng, ('reliable', 'mostly_reliable', 'mistaken_on_details'))
        truth['people']['subject'] = _profile(rng, ('reliable', 'mostly_reliable'), deception_chance=28)
        video_status = choices.get('video', 'video availability uncertain')
        exists = 'offline' not in video_status.lower()
        if exists:
            truth['evidence']['retail_video'] = {
                'label': 'Retail surveillance video',
                'exists': True,
                'status': 'hidden',
                'source': 'retail camera system',
                'location': 'loss-prevention system',
                'discover_keywords': ['video', 'camera', 'surveillance', 'footage'],
                'expires_at': 7 if 'not been preserved' in video_status.lower() else 14,
                'description': video_status,
            }
        truth['evidence']['merchandise'] = {
            'label': 'Recovered merchandise / transaction item',
            'exists': True,
            'status': 'available',
            'source': 'loss prevention',
            'location': 'retail office',
            'discover_keywords': ['item', 'merchandise', 'property', 'receipt', 'price'],
            'expires_at': None,
            'description': choices.get('conduct', 'reported merchandise issue'),
        }
        truth['people']['subject']['private_facts'] = [choices.get('intent_issue', 'Subject disputes criminal intent.')]
        truth['disposition_constraints'].append('Arrest is not the default successful disposition; insufficient evidence or referral may be reasonable.')

    elif scenario_id == 'S005':
        truth['people']['driver'] = _profile(rng, ('reliable', 'mostly_reliable'), deception_chance=12)
        truth['people']['driver']['private_facts'] = [
            f"Observed driving issue: {choices.get('violation', 'traffic violation')}.",
            f"Movement tendency: {choices.get('movement', 'ordinary vehicle movement')}.",
        ]
        truth['evidence']['vehicle_position'] = {
            'label': 'Roadway / vehicle position',
            'exists': True,
            'status': 'available',
            'source': 'officer observation',
            'location': 'traffic stop scene',
            'discover_keywords': ['vehicle', 'position', 'road', 'traffic', 'look', 'observe'],
            'expires_at': None,
            'description': choices.get('road', 'installation roadway'),
        }
        truth['disposition_constraints'].append('A warning, citation, or other lawful traffic disposition may be reasonable depending on developed facts.')

    elif scenario_id == 'S006':
        truth['people']['patient'] = _profile(rng, ('limited_observation', 'mostly_reliable'))
        truth['people']['coworker1'] = _profile(rng, ('limited_observation', 'mistaken_on_details', 'mostly_reliable'))
        truth['people']['coworker2'] = _profile(rng, ('limited_observation', 'mistaken_on_details', 'mostly_reliable'))
        truth['people']['fullwitness'] = _profile(rng, ('reliable', 'mostly_reliable'))
        truth['people']['patient']['private_facts'] = [
            f"Presentation: {choices.get('presentation', 'medical complaint')}.",
            f"Current state: {choices.get('patient_state', 'conscious')}.",
        ]
        witness_pattern = choices.get('witness_pattern', '')
        if 'one employee may have seen the entire event but is about to leave' in witness_pattern:
            truth['people']['fullwitness']['leaves_at'] = 6
        truth['disposition_constraints'].append('EMS transport or assistance-only may be the correct disposition when no crime or safety violation is established.')

    return truth


def npc_truth_facts(truth, actor_id):
    profile = ((truth or {}).get('people') or {}).get(actor_id) or {}
    return [str(value).strip() for value in profile.get('private_facts') or [] if str(value).strip()]
