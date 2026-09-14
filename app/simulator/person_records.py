import hashlib
import random
import re
from copy import deepcopy

from .world_state import add_known_information, add_timeline, ensure_world_state


_FIRST_NAMES = (
    'Aaron', 'Brianna', 'Caleb', 'Danielle', 'Evan', 'Faith', 'Gabriel', 'Hannah',
    'Isaac', 'Jasmine', 'Kevin', 'Lauren', 'Marcus', 'Natalie', 'Owen', 'Rachel',
    'Samuel', 'Tiffany', 'Victor', 'Whitney', 'Xavier', 'Yolanda', 'Zachary',
)
_LAST_NAMES = (
    'Anderson', 'Bennett', 'Carter', 'Davis', 'Edwards', 'Foster', 'Garcia',
    'Harris', 'Jackson', 'King', 'Lewis', 'Mitchell', 'Nelson', 'Owens', 'Parker',
    'Reed', 'Scott', 'Turner', 'Walker', 'Young',
)
_STREETS = (
    'Pinecrest Dr', 'Oak Ridge Ln', 'Magnolia Ave', 'Creekview Rd', 'Lakeview Dr',
    'Woodland Ct', 'Meadow Park Ln', 'Cedar Grove Rd', 'Riverside Dr', 'Hillcrest Ave',
)
_CITIES = ('Albany', 'Leesburg', 'Sylvester', 'Dawson', 'Camilla')


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _rng(state, actor_id):
    seed = int(((state.get('run_context') or {}).get('seed')) or 1)
    digest = hashlib.sha256(f'{seed}|person-record|{actor_id}'.encode('utf-8')).hexdigest()
    return random.Random(int(digest[:16], 16))


def _identity_truth(state, actor_id, role='Person'):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    truth = world.setdefault('truth', {})
    people_truth = truth.setdefault('people', {})
    profile = people_truth.setdefault(actor_id, {})
    if isinstance(profile.get('identity'), dict):
        return profile['identity']

    rng = _rng(state, actor_id)
    first = rng.choice(_FIRST_NAMES)
    last = rng.choice(_LAST_NAMES)
    year = rng.randint(1968, 2004)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    street_no = rng.randint(100, 4899)
    city = rng.choice(_CITIES)
    phone = f"229-{rng.randint(200, 899):03d}-{rng.randint(1000, 9999):04d}"
    state_id = f"GA{rng.randint(1000000, 9999999)}"
    email = f"{first.lower()}.{last.lower()}{rng.randint(1,99)}@example.test"
    identity = {
        'full_name': f'{first} {last}',
        'first_name': first,
        'last_name': last,
        'dob': f'{year:04d}-{month:02d}-{day:02d}',
        'address': f'{street_no} {rng.choice(_STREETS)}, {city}, GA 31{rng.randint(700, 799):03d}',
        'phone': phone,
        'email': email,
        'state_id': state_id,
        'role': _text(role) or 'Person',
        'synthetic': True,
    }
    profile['identity'] = identity
    people_truth[actor_id] = profile
    truth['people'] = people_truth
    world['truth'] = truth
    return identity


def _targets(actions):
    rows = []
    for action in actions or []:
        target = _text((action or {}).get('target'))
        if target and target not in {'dispatch', 'patrol_unit', 'ems', 'fire', 'supervisor', 'investigations', 'witnesses', 'backup_officer'}:
            if target not in rows:
                rows.append(target)
    return rows


def _identity_request(raw_text):
    low = _text(raw_text).lower()
    return bool(re.search(
        r'\b(identify|identification|name|date of birth|dob|birth date|address|phone|telephone|contact information|contact info|driver.?s license|license|state id|id card)\b',
        low,
    ))


def reveal_requested_identities(state, actions, raw_text):
    """Reveal synthetic identifiers only when the trainee actually develops them."""
    if not _identity_request(raw_text):
        return []
    world = ensure_world_state(state, state.get('scenario_id', ''))
    people = dict(world.get('people') or {})
    changed = []
    for actor_id in _targets(actions):
        person = dict(people.get(actor_id) or {})
        if not person or person.get('status') == 'departed':
            continue
        identity = _identity_truth(state, actor_id, person.get('role') or 'Person')
        if person.get('identity_obtained'):
            continue
        person['identity_obtained'] = True
        person['identity'] = deepcopy(identity)
        person['display_name_before_identification'] = person.get('name')
        person['name'] = identity['full_name']
        people[actor_id] = person
        changed.append(actor_id)
        summary = (
            f"Identifying information obtained for {identity['full_name']} ({person.get('role') or 'Person'}): "
            f"DOB {identity['dob']}; Address {identity['address']}; Phone {identity['phone']}; "
            f"Training ID {identity['state_id']}."
        )
        add_known_information(state, summary, source='identification')
        add_timeline(
            state,
            'person_identified',
            f"Identification obtained for {identity['full_name']} ({person.get('role') or 'Person'}).",
            actor='Trainee',
            channel='scene',
            details={'actor_id': actor_id, 'identity': deepcopy(identity)},
            visible_to_trainee=True,
        )
    world['people'] = people
    return changed


def developed_people(state):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    rows = []
    for person in (world.get('people') or {}).values():
        if not person.get('discovered'):
            continue
        rows.append({
            'id': person.get('id'),
            'display_name': person.get('name'),
            'role': person.get('role'),
            'status': person.get('status'),
            'identity_obtained': bool(person.get('identity_obtained')),
            'identity': deepcopy(person.get('identity') or {}),
        })
    return rows


def _statement_request(raw_text):
    low = _text(raw_text).lower()
    patterns = (
        r'\bwritten statement\b',
        r'\b(get|obtain|request|take|receive|provide|give me|complete|write)\b.{0,25}\bstatement\b',
        r'\bstatement\b.{0,25}\b(write|written|form|sign|signed)\b',
    )
    return any(re.search(pattern, low) for pattern in patterns)


def _statement_body(state, actor_id, person):
    memory = list(person.get('memory') or [])
    npc_lines = []
    for item in memory:
        if _text(item.get('speaker')).lower() == 'npc' and _text(item.get('text')):
            text = _text(item.get('text'))
            if text not in npc_lines:
                npc_lines.append(text)
    if npc_lines:
        return ' '.join(npc_lines[-8:])[:6000]

    world = ensure_world_state(state, state.get('scenario_id', ''))
    profile = (((world.get('truth') or {}).get('people') or {}).get(actor_id) or {})
    facts = []
    for key in ('private_facts', 'incorrect_beliefs'):
        for fact in profile.get(key) or []:
            fact = _text(fact)
            if fact and fact not in facts:
                facts.append(fact)
    if facts:
        return ' '.join(facts)[:6000]
    return 'I am providing this written statement regarding the incident I discussed with the responding officer.'


def obtain_requested_statements(state, actions, raw_text):
    """Create a declarant-completed synthetic statement when one is actually obtained.

    The statement is not officer-authored and is therefore never presented as an
    editable trainee form. The trainee may receive/review/document it as evidence.
    """
    if not _statement_request(raw_text):
        return []
    world = ensure_world_state(state, state.get('scenario_id', ''))
    people = dict(world.get('people') or {})
    statements = list(world.get('statements') or [])
    created = []
    clock = int(world.get('clock', 0))

    for actor_id in _targets(actions):
        person = dict(people.get(actor_id) or {})
        if not person or person.get('status') == 'departed':
            continue
        if any(_text(item.get('declarant_id')) == actor_id and item.get('status') == 'received' for item in statements):
            continue
        identity = person.get('identity') if person.get('identity_obtained') else _identity_truth(state, actor_id, person.get('role') or 'Person')
        if not person.get('identity_obtained'):
            person['identity_obtained'] = True
            person['identity'] = deepcopy(identity)
            person['display_name_before_identification'] = person.get('name')
            person['name'] = identity['full_name']
            people[actor_id] = person
            add_known_information(
                state,
                f"Identifying information obtained from written statement for {identity['full_name']}: DOB {identity['dob']}; Address {identity['address']}; Phone {identity['phone']}; Training ID {identity['state_id']}.",
                source='written_statement',
            )

        statement = {
            'id': f"STMT-{len(statements) + 1:03d}",
            'declarant_id': actor_id,
            'declarant_name': identity['full_name'],
            'role': person.get('role') or 'Person',
            'dob': identity['dob'],
            'address': identity['address'],
            'phone': identity['phone'],
            'statement_date': 'TRAINING DATE',
            'statement_time': f'T+{clock}',
            'statement_location': 'Synthetic incident location',
            'statement_text': _statement_body(state, actor_id, person),
            'signature': f"TRAINING SIGNATURE — {identity['full_name']}",
            'status': 'received',
            'completed_by': 'simulated_declarant',
            'officer_editable': False,
            'synthetic': True,
        }
        statements.append(statement)
        created.append(statement)
        add_known_information(
            state,
            f"Written statement received from {identity['full_name']} ({person.get('role') or 'Person'}).",
            source='written_statement',
        )
        add_timeline(
            state,
            'written_statement_received',
            f"Written statement received from {identity['full_name']} ({person.get('role') or 'Person'}).",
            actor=identity['full_name'],
            channel='paperwork',
            details={'statement_id': statement['id'], 'declarant_id': actor_id},
            visible_to_trainee=True,
        )

    world['people'] = people
    world['statements'] = statements
    return created


def obtained_statements(state):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    return deepcopy([row for row in (world.get('statements') or []) if row.get('status') == 'received'])
