import re
from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from ..models import Form, Report, TrainingRoster

bp = Blueprint('sentinel', __name__, url_prefix='/sentinel')

SCENARIOS = {
    'S001': {
        'title': 'Disorderly Person Refusing to Leave',
        'difficulty': 'Intermediate',
        'category': 'Calls for Service',
        'dispatch': 'Unit 214, respond to Building 7130 for a disorderly individual refusing to leave.',
        'objective': 'Practice scene approach, de-escalation, investigation, legal articulation, and disposition.',
    },
    'S002': {
        'title': 'Suspicious Vehicle at Main Gate',
        'difficulty': 'Basic',
        'category': 'Access Control',
        'dispatch': 'Main Gate requests patrol assistance with a driver who cannot provide valid installation access credentials and is becoming argumentative.',
        'objective': 'Practice officer safety, identification, access-control decision making, and documentation.',
    },
    'S003': {
        'title': 'Damage to Government Property',
        'difficulty': 'Intermediate',
        'category': 'Investigation',
        'dispatch': 'Respond to a report of a contractor vehicle striking government property near a facility parking area.',
        'objective': 'Practice witness development, damage documentation, evidence collection, and articulation of willful/negligent/accidental facts without guessing.',
    },
    'S004': {
        'title': 'Larceny / Shoplifting Report',
        'difficulty': 'Intermediate',
        'category': 'Investigation',
        'dispatch': 'Respond to a reported theft where staff have identified a possible subject and recovered property may be involved.',
        'objective': 'Practice interviews, statements, property/value documentation, evidence handling, and CID/policy considerations.',
    },
    'S005': {
        'title': 'Traffic Stop — Escalating Driver',
        'difficulty': 'Advanced',
        'category': 'Traffic Enforcement',
        'dispatch': 'Conduct a traffic stop on a vehicle after observing a moving violation. The driver becomes increasingly argumentative after contact.',
        'objective': 'Practice radio traffic, positioning, officer safety, legal authority, communication, enforcement decision making, and report articulation.',
    },
    'S006': {
        'title': 'Medical Assist with Conflicting Information',
        'difficulty': 'Basic',
        'category': 'Calls for Service',
        'dispatch': 'Respond to a workplace medical assist. Coworkers provide conflicting information about what happened before the patient became ill.',
        'objective': 'Practice scene organization, witness separation, fact collection, medical-assist documentation, and disposition.',
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

FTO_AREAS = [
    ('Radio Communication', ['radio', 'dispatch', 'en route', 'on scene', 'status', 'location']),
    ('Officer Safety', ['backup', 'cover', 'distance', 'hands', 'weapon', 'position', 'approach']),
    ('Investigation', ['ask', 'interview', 'witness', 'statement', 'separate', 'identify', 'evidence']),
    ('Legal Authority', ['detain', 'reasonable suspicion', 'probable cause', 'authority', 'consent', 'arrest', 'citation']),
    ('Judgment / Decision Making', ['assess', 'plan', 'priority', 'risk', 'options', 'de-escalat', 'request supervisor']),
    ('Documentation', ['report', 'document', 'statement', 'ccn', 'blotter', 'evidence', 'photograph']),
    ('Professionalism', ['calm', 'professional', 'explain', 'respect', 'de-escalat', 'communication']),
    ('Policy / Procedure Awareness', ['policy', 'pdi', 'sop', 'order', 'procedure', 'notify', 'screening']),
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
    rows = []
    raw_points = 0
    max_points = len(FTO_AREAS) * 20
    for label, terms in FTO_AREAS:
        hits = [term for term in terms if term in low]
        points = 20 if len(hits) >= 2 else 12 if len(hits) == 1 else 5
        raw_points += points
        rows.append({
            'area': label,
            'score': points,
            'max': 20,
            'hits': hits[:4],
            'status': 'good' if points >= 20 else 'partial' if points >= 12 else 'needs-work',
        })

    score = round((raw_points / max_points) * 100) if max_points else 0
    if len(text.split()) < 25:
        score = max(0, score - 8)
    score = min(96, score)

    followups = []
    if not _has_any(low, ['reasonable suspicion', 'probable cause', 'authority', 'consent']):
        followups.append('Explain what legal authority, if any, supports a detention, search, citation, or arrest at this point.')
    if not _has_any(low, ['witness', 'statement', 'interview', 'ask']):
        followups.append('Who should be interviewed first, and what facts are you trying to establish?')
    if not _has_any(low, ['backup', 'position', 'hands', 'distance', 'weapon']):
        followups.append('What officer-safety considerations affect your approach?')
    if not _has_any(low, ['report', 'document', 'ccn', 'blotter', 'statement']):
        followups.append('What documentation or report products would you complete, and why?')
    if not followups:
        followups.append('What new information would make you change your plan, and what would you document?')

    strengths = [row['area'] for row in rows if row['status'] == 'good']
    development = [row['area'] for row in rows if row['status'] != 'good']
    return {
        'score': score,
        'areas': rows,
        'followups': followups[:4],
        'strengths': strengths,
        'development': development,
        'notice': 'Sentinel is a training aid. The assigned FTO/instructor owns the final rating, comments, remediation, and advancement recommendation.',
    }


def _portal_search_results(query):
    """Search safe portal metadata without exposing report content."""
    q = _normalize(query)
    if not q:
        return []
    pattern = f'%{q}%'
    results = []

    report_query = Report.query
    if not current_user.can_manage_team():
        report_query = report_query.filter_by(owner_id=current_user.id)
    for item in report_query.filter(Report.title.ilike(pattern)).order_by(Report.updated_at.desc()).limit(8).all():
        results.append({
            'group': 'Reports',
            'title': item.title,
            'detail': f'Status: {item.status or "Draft"}. Open Reports Center to view only records you are authorized to access.',
            'href': url_for('reports.list_reports', q=q),
        })

    for item in Form.query.filter(Form.is_active.is_(True)).filter(or_(Form.title.ilike(pattern), Form.category.ilike(pattern))).order_by(Form.title.asc()).limit(8).all():
        results.append({
            'group': 'Forms',
            'title': item.title,
            'detail': item.category or 'Official form',
            'href': url_for('forms.list_forms', q=q),
        })

    for item in TrainingRoster.query.filter(or_(TrainingRoster.title.ilike(pattern), TrainingRoster.description.ilike(pattern))).order_by(TrainingRoster.uploaded_at.desc()).limit(8).all():
        results.append({
            'group': 'Training',
            'title': item.title,
            'detail': (item.description or 'Training roster')[:180],
            'href': url_for('training.training_menu', q=q),
        })

    return results


@bp.route('/search')
@login_required
def portal_search():
    query = _normalize(request.args.get('q'))
    results = _portal_search_results(query) if query else []
    shortcuts = [
        {'title': 'Law & Legal Search', 'detail': 'Georgia law, UCMJ, USC, and legal references', 'href': url_for('legal.legal_lookup', q=query, source='ALL', state='GA') if query else url_for('legal.legal_home')},
        {'title': 'Orders & Memos', 'detail': 'Base orders, PDIs/SOPs, memorandums, and references', 'href': url_for('orders.reference_search', q=query) if query else url_for('orders.reference_search')},
        {'title': 'Narrative Creator', 'detail': 'Build and quality-check a fact-based report narrative', 'href': url_for('bodycam.narrative_tool')},
        {'title': 'Forms / Paperwork', 'detail': 'Official forms and call-type paperwork guidance', 'href': url_for('forms.list_forms', q=query) if query else url_for('forms.list_forms')},
        {'title': 'FTO Center', 'detail': 'Field training, Scenario Lab, and evaluation coaching', 'href': url_for('reports.sentinel.fto_center')},
        {'title': 'Accident Tools', 'detail': 'Guided crash documentation and diagrams', 'href': url_for('reports.accidents')},
    ]
    return render_template('sentinel_portal_search.html', user=current_user, query=query, results=results, shortcuts=shortcuts)


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


@bp.route('/fto-center', methods=['GET', 'POST'])
@login_required
def fto_center():
    scenario_id = request.form.get('scenario_id') or request.args.get('scenario_id') or 'S001'
    scenario = SCENARIOS.get(scenario_id, SCENARIOS['S001'])
    response_text = ''
    result = None
    if request.method == 'POST':
        response_text = (request.form.get('response_text') or '').strip()
        if response_text:
            result = _evaluate_fto(response_text)
    return render_template(
        'sentinel_fto_center.html',
        user=current_user,
        scenarios=SCENARIOS,
        scenario_id=scenario_id,
        scenario=scenario,
        response_text=response_text,
        result=result,
        fto_areas=[area for area, _terms in FTO_AREAS],
    )


@bp.route('/fto-instructor', methods=['GET', 'POST'])
@login_required
def fto_instructor():
    """Compatibility route for old bookmarks after the FTO Center rename."""
    if request.method == 'POST':
        return fto_center()
    return redirect(url_for('reports.sentinel.fto_center'))


# Persistent DOR/program management lives inside FTO Center without replacing
# the Scenario Lab or its advisory-only Sentinel coaching workflow.
from . import fto_program as _fto_program
bp.register_blueprint(_fto_program.bp)
