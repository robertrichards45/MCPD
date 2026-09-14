import hashlib
import random
import re
from copy import deepcopy
from datetime import date, timedelta

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
_STATEMENT_FORM = 'OPNAV 5580 2 Voluntary Statement'


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


def _person_aliases(actor_id, person):
    role = _text(person.get('role')).lower()
    name = _text(person.get('name')).lower()
    pid = _text(actor_id).lower()
    blob = f'{pid} {role} {name}'
    aliases = {value for value in (pid, role, name) if value}
    if any(term in blob for term in ('subject', 'suspect')):
        aliases.update({'subject', 'suspect', 'the subject', 'the suspect'})
    if any(term in blob for term in ('reporting party', 'reporting', 'complainant', 'caller', 'staff')):
        aliases.update({'reporting party', 'complainant', 'complaintant', 'caller', 'staff member', 'staff', 'rp'})
    if 'loss prevention' in blob or pid == 'lp':
        aliases.update({'loss prevention', 'lp', 'witness', 'reporting party'})
    if 'witness' in blob or any(term in pid for term in ('witness', 'coworker', 'employee2')):
        aliases.update({'witness', 'the witness', 'employee witness', 'coworker', 'employee'})
    if 'driver' in blob:
        aliases.update({'driver', 'the driver'})
    if 'patient' in blob:
        aliases.update({'patient', 'the patient'})
    if 'sponsor' in blob:
        aliases.update({'sponsor', 'destination contact'})
    if 'gate' in blob:
        aliases.update({'gate officer', 'gate guard', 'gate personnel'})
    return sorted(aliases, key=len, reverse=True)


def _targets(actions, state=None, raw_text=''):
    rows = []
    excluded = {'dispatch', 'patrol_unit', 'ems', 'fire', 'supervisor', 'investigations', 'witnesses', 'backup_officer'}
    for action in actions or []:
        target = _text((action or {}).get('target'))
        if target and target not in excluded and target not in rows:
            rows.append(target)
    if rows or state is None or not _text(raw_text):
        return rows

    world = ensure_world_state(state, state.get('scenario_id', ''))
    low = _text(raw_text).lower()
    matches = []
    for actor_id, person in (world.get('people') or {}).items():
        if not person.get('discovered') or person.get('status') == 'departed':
            continue
        hit = ''
        for alias in _person_aliases(actor_id, person):
            if alias and re.search(rf'(?<!\w){re.escape(alias)}(?!\w)', low, re.I):
                hit = alias
                break
        if hit:
            matches.append((len(hit), actor_id))
    if not matches:
        return rows
    matches.sort(reverse=True)
    best_len = matches[0][0]
    best = [actor_id for length, actor_id in matches if length == best_len]
    if len(set(best)) == 1:
        rows.append(best[0])
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
    for actor_id in _targets(actions, state=state, raw_text=raw_text):
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


def _initials(full_name):
    return ''.join(part[0].upper() for part in _text(full_name).split() if part)[:4]


def _synthetic_statement_date(state):
    """Return a reproducible training date tied to the run seed."""
    seed = int(((state.get('run_context') or {}).get('seed')) or 1)
    base = date(2026, 1, 1)
    return (base + timedelta(days=seed % 365)).isoformat()


def _statement_form_snapshot(state, identity, statement_text, clock):
    """Build a read-only OPNAV 5580-2 training form from the controlled field registry."""
    from .training_forms import training_form_definition

    definition = training_form_definition(_STATEMENT_FORM)
    values = {}
    fields = []
    run_id = _text(((state.get('run_context') or {}).get('run_id')))
    statement_date = _synthetic_statement_date(state)
    statement_time = f'T+{int(clock or 0)}'
    location = 'MCLB Albany, GA — Synthetic Training'
    initials = _initials(identity.get('full_name'))

    for field in definition.get('fields') or []:
        name = _text(field.get('name'))
        label = _text(field.get('label'))
        low = f'{name} {label}'.lower()
        field_type = _text(field.get('type')).lower()
        sig_role = _text(field.get('sig_role')).lower()
        officer_only = bool(field.get('officer_only'))
        person_field = bool(field.get('person_field'))
        value = ''

        if officer_only:
            value = ''
        elif field_type == 'signature' and sig_role in {'subject', 'victim', 'witness', 'declarant'}:
            value = f"TRAINING SIGNATURE — {identity.get('full_name')}"
        elif field_type == 'initial' and sig_role in {'subject', 'victim', 'witness', 'declarant'}:
            value = initials
        elif 'statement' in low and field_type in {'textarea', 'text'}:
            value = statement_text
        elif person_field and any(term in low for term in ('name', 'vicname', 'declarant')):
            value = identity.get('full_name')
        elif 'date' in low:
            value = statement_date
        elif 'time' in low or 'resptime' in low:
            value = statement_time
        elif 'location' in low or 'place' in low:
            value = location
        elif 'ccn' in low or 'case number' in low or 'reference' in low:
            value = f'TRN-{run_id}' if run_id else 'TRAINING'
        elif 'ssn' in low:
            value = ''
        elif person_field and 'address' in low:
            value = identity.get('address')
        elif person_field and ('phone' in low or 'telephone' in low):
            value = identity.get('phone')
        elif person_field and ('dob' in low or 'birth' in low):
            value = identity.get('dob')

        values[name] = value
        fields.append({
            'name': name,
            'label': label or name,
            'type': field_type or 'text',
            'required': bool(field.get('required')),
            'officer_only': officer_only,
            'person_field': person_field,
            'sig_role': sig_role,
            'mapping_status': field.get('mapping_status'),
            'value': value,
            'locked': True,
        })

    return {
        'document_name': definition.get('document_name') or _STATEMENT_FORM,
        'document_id': definition.get('document_id'),
        'source': definition.get('source'),
        'registry_pattern': definition.get('registry_pattern'),
        'fields': fields,
        'values': values,
        'read_only': True,
        'completed_by': 'simulated_declarant',
    }


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

    for actor_id in _targets(actions, state=state, raw_text=raw_text):
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

        statement_text = _statement_body(state, actor_id, person)
        form_snapshot = _statement_form_snapshot(state, identity, statement_text, clock)
        statement = {
            'id': f"STMT-{len(statements) + 1:03d}",
            'declarant_id': actor_id,
            'declarant_name': identity['full_name'],
            'role': person.get('role') or 'Person',
            'dob': identity['dob'],
            'address': identity['address'],
            'phone': identity['phone'],
            'statement_date': _synthetic_statement_date(state),
            'statement_time': f'T+{clock}',
            'statement_location': 'MCLB Albany, GA — Synthetic Training',
            'statement_text': statement_text,
            'signature': f"TRAINING SIGNATURE — {identity['full_name']}",
            'status': 'received',
            'completed_by': 'simulated_declarant',
            'officer_editable': False,
            'synthetic': True,
            'form_document_name': form_snapshot.get('document_name'),
            'form_document_id': form_snapshot.get('document_id'),
            'form_source': form_snapshot.get('source'),
            'form_fields': form_snapshot.get('fields') or [],
            'form_values': form_snapshot.get('values') or {},
            'form_read_only': True,
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
            details={'statement_id': statement['id'], 'declarant_id': actor_id, 'form': form_snapshot.get('document_name')},
            visible_to_trainee=True,
        )

    world['people'] = people
    world['statements'] = statements
    return created


def obtained_statements(state):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    return deepcopy([row for row in (world.get('statements') or []) if row.get('status') == 'received'])