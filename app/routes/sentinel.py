import re
from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

bp = Blueprint('sentinel', __name__, url_prefix='/sentinel')

SCENARIOS = {
    'S001': {
        'title': 'Disorderly Person Refusing to Leave',
        'difficulty': 'Intermediate',
        'dispatch': 'Unit 214, respond to Building 7130 for a disorderly individual refusing to leave.',
    },
    'S002': {
        'title': 'Suspicious Vehicle at Main Gate',
        'difficulty': 'Basic',
        'dispatch': 'Main Gate requests patrol assistance with a driver who cannot provide valid installation access credentials and is becoming argumentative.',
    },
}

OFFENSES = [
    {
        'name': 'Damage to Government Property',
        'authority': 'UCMJ Article 108 consideration — verify current law and applicability',
        'aliases': ['damage to government property', 'government property', 'article 108'],
        'elements': [
            ('Government property connection', 'Does the narrative identify the property as government property?', ['government property', 'government-owned', 'government owned']),
            ('Damage / loss', 'Does the narrative describe the actual damage, loss, destruction, or wrongful disposition?', ['damage', 'damaged', 'destroyed', 'lost', 'broken']),
            ('Conduct / mental state', 'Does the narrative describe facts bearing on willful, negligent, accidental, or other conduct without guessing?', ['willful', 'willfully', 'negligent', 'negligence', 'accident', 'accidental', 'reckless']),
        ],
    },
    {
        'name': 'Larceny / Shoplifting',
        'authority': 'Verify current applicable federal/state/local authority and installation policy',
        'aliases': ['larceny', 'shoplifting', 'stole', 'theft', 'concealed merchandise'],
        'elements': [
            ('Property', 'Is the property clearly identified?', ['property', 'item', 'merchandise', 'goods']),
            ('Taking / control', 'Are facts describing taking, concealment, possession, or control documented?', ['took', 'stole', 'concealed', 'possessed', 'carried']),
            ('Owner / value / disposition', 'Are ownership, value, recovery, and disposition documented where applicable?', ['owner', 'value', 'recovered', 'returned', 'evidence']),
        ],
    },
    {
        'name': 'Disorderly / Refusal to Leave',
        'authority': 'Verify current installation policy and applicable law before enforcement action',
        'aliases': ['disorderly', 'refusing to leave', 'refused to leave', 'trespass'],
        'elements': [
            ('Behavior', 'Are the specific actions/words described objectively?', ['yelling', 'threat', 'disorderly', 'refused', 'refusing']),
            ('Notice / direction', 'Does the report document who directed the person to leave and what was communicated?', ['told to leave', 'directed to leave', 'ordered to leave', 'asked to leave']),
            ('Officer action', 'Does the narrative explain detention, removal, citation, arrest, release, or referral?', ['detained', 'escorted', 'removed', 'citation', 'arrested', 'released', 'referred']),
        ],
    },
]


def _normalize(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def _has_any(text, terms):
    low = text.lower()
    return any(term.lower() in low for term in terms)


def _identify_offense(text):
    low = _normalize(text).lower()
    best = None
    best_score = 0
    for offense in OFFENSES:
        score = sum(1 for alias in offense['aliases'] if alias in low)
        if score > best_score:
            best, best_score = offense, score
    return best


def _element_matrix(text, offense):
    if not offense:
        return None
    low = _normalize(text).lower()
    rows = []
    supported = 0
    for name, question, signals in offense['elements']:
        hits = [signal for signal in signals if signal in low]
        if hits:
            supported += 1
        rows.append({
            'name': name,
            'question': question,
            'status': 'cue-detected' if hits else 'not-detected',
            'evidence_cues': hits[:4],
            'note': 'Language cues were detected. A supervisor must decide whether the actual facts support this issue.' if hits else 'No matching language cue was detected. Verify the facts; do not add facts merely to satisfy this check.',
        })
    return {
        'offense': offense['name'],
        'authority': offense['authority'],
        'supported': supported,
        'total': len(rows),
        'elements': rows,
        'warning': 'This is a narrative-cue matrix, not an elements-of-proof or probable-cause determination.',
    }


def _report_review(text):
    raw = str(text or '')
    low = raw.lower()
    words = _normalize(raw).split()
    findings = []
    score = 100

    def add(level, title, detail, deduction, category='General'):
        nonlocal score
        findings.append({'level': level, 'title': title, 'detail': detail, 'category': category})
        score -= deduction

    if len(words) < 45:
        add('red', 'Narrative may be too brief', 'Confirm who, what, when, where, officer actions, investigative facts, and disposition are actually documented.', 18, 'Completeness')
    times = re.findall(r'(?<!\d)(?:[01]\d|2[0-3])[0-5]\d(?!\d)', raw)
    if not times:
        add('yellow', 'No military time detected', 'Confirm key incident times are documented where required.', 5, 'Timeline')
    if not _has_any(low, ['location:', 'bldg', 'building', 'gate', 'mclb', 'street', 'road', 'blvd', 'drive', 'parking lot']):
        add('yellow', 'Location may be unclear', 'Confirm the specific incident location is documented.', 6, 'Completeness')
    if not _has_any(low, ['cleared', 'released', 'referred', 'advised', 'arrested', 'citation', 'turned over', 'returned to service', 'departed', 'completed']):
        add('yellow', 'Disposition may be missing', 'Confirm the final officer action and disposition are clear.', 8, 'Disposition')
    if not _has_any(low, ['complainant', 'victim', 'subject', 'suspect', 'witness', 'driver', 'reporting officer']):
        add('yellow', 'Involved-person roles may be unclear', 'Use clear roles for involved persons where applicable.', 5, 'Identity')
    if 'arrested' in low and not _has_any(low, ['probable cause', 'observed', 'witness', 'admitted', 'identified', 'video', 'statement', 'evidence']):
        add('red', 'Arrest basis may need stronger articulation', 'Connect the facts/evidence known to the officer to the enforcement decision. Do not manufacture facts or legal conclusions.', 15, 'Legal articulation')
    if re.search(r'\b(TBD|UNKNOWN|INSERT|PLACEHOLDER)\b', raw, re.I):
        add('yellow', 'Placeholder or unknown information detected', 'Confirm placeholder text is intentional and acceptable before approval.', 4, 'Completeness')

    offense = _identify_offense(raw)
    elements = _element_matrix(raw, offense)
    counts = {
        'red': sum(1 for item in findings if item['level'] == 'red'),
        'yellow': sum(1 for item in findings if item['level'] == 'yellow'),
    }
    return {
        'score': max(0, min(100, score)),
        'findings': findings,
        'counts': counts,
        'elements': elements,
        'sections': [
            {'name': 'Initial notification', 'present': _has_any(low, ['dispatched', 'notified', 'walk-in', 'reported', 'responded'])},
            {'name': 'Arrival / contact', 'present': _has_any(low, ['arrived', 'made contact', 'contacted', 'met with'])},
            {'name': 'Investigation', 'present': _has_any(low, ['stated', 'advised', 'observed', 'interview', 'witness'])},
            {'name': 'Evidence / documentation', 'present': _has_any(low, ['statement', 'photo', 'photograph', 'video', 'evidence'])},
            {'name': 'Disposition', 'present': _has_any(low, ['cleared', 'released', 'referred', 'arrested', 'citation', 'turned over', 'completed'])},
        ],
        'notice': 'Sentinel flags review cues only. It does not establish probable cause, guilt, policy compliance, or legal sufficiency. Never add facts to satisfy software.',
    }


def _evaluate_fto(text):
    low = _normalize(text).lower()
    checks = [
        ('Radio communication', ['radio', 'dispatch', 'en route', 'on scene', '214']),
        ('Officer safety', ['backup', 'cover', 'distance', 'hands', 'weapon', 'position', 'approach']),
        ('Investigation', ['ask', 'interview', 'witness', 'statement', 'separate', 'identify']),
        ('Legal authority', ['detain', 'reasonable suspicion', 'probable cause', 'authority', 'consent', 'arrest']),
        ('Documentation', ['report', 'document', 'statement', 'ccn', 'blotter', 'evidence']),
    ]
    rows = []
    raw = 0
    for label, terms in checks:
        hits = [term for term in terms if term in low]
        points = 20 if len(hits) >= 2 else 12 if len(hits) == 1 else 5
        raw += points
        rows.append({'area': label, 'score': points, 'max': 20, 'hits': hits[:4], 'status': 'good' if points >= 20 else 'partial' if points >= 12 else 'needs-work'})
    if len(text.split()) < 25:
        raw = max(0, raw - 10)
    raw = min(96, raw)
    followups = []
    if not _has_any(low, ['reasonable suspicion', 'probable cause', 'authority', 'consent']):
        followups.append('Explain what legal authority, if any, supports a detention, search, citation, or arrest at this point.')
    if not _has_any(low, ['witness', 'statement', 'interview', 'ask']):
        followups.append('Who should be interviewed first, and what facts are you trying to establish?')
    if not _has_any(low, ['backup', 'position', 'hands', 'distance', 'weapon']):
        followups.append('What officer-safety considerations affect your approach?')
    if not followups:
        followups.append('What new information would make you change your plan, and what would you document?')
    return {'score': raw, 'areas': rows, 'followups': followups[:3], 'notice': 'Training aid only. The assigned FTO/instructor makes the final evaluation.'}


@bp.route('/report-inspector', methods=['GET', 'POST'])
@login_required
def report_inspector():
    narrative = ''
    result = None
    if request.method == 'POST':
        narrative = (request.form.get('narrative') or '').strip()
        if narrative:
            result = _report_review(narrative)
    return render_template('sentinel_report_inspector.html', user=current_user, narrative=narrative, result=result)


@bp.route('/fto-instructor', methods=['GET', 'POST'])
@login_required
def fto_instructor():
    scenario_id = request.form.get('scenario_id') or 'S001'
    scenario = SCENARIOS.get(scenario_id, SCENARIOS['S001'])
    response_text = ''
    result = None
    if request.method == 'POST':
        response_text = (request.form.get('response_text') or '').strip()
        if response_text:
            result = _evaluate_fto(response_text)
    return render_template('sentinel_fto_instructor.html', user=current_user, scenarios=SCENARIOS, scenario_id=scenario_id, scenario=scenario, response_text=response_text, result=result)
