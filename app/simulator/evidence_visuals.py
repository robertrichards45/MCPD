from html import escape

from .world_state import ensure_world_state


VISIBLE_STATUSES = {'available', 'discovered', 'preserved', 'collected'}


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _visible(row, evaluator=False):
    status = _text((row or {}).get('status')).lower()
    if evaluator:
        return bool(row)
    return status in VISIBLE_STATUSES


def visual_evidence_cards(state, evaluator=False):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    rows = []
    for evidence_id, row in (world.get('evidence') or {}).items():
        if not _visible(row, evaluator=evaluator):
            continue
        kind = _visual_kind(state.get('scenario_id', ''), evidence_id)
        if not kind:
            continue
        rows.append({
            'id': evidence_id,
            'label': row.get('label') or evidence_id,
            'status': row.get('status') or '',
            'kind': kind,
            'description': row.get('description') or '',
            'location': row.get('location') or '',
        })
    return rows


def _visual_kind(scenario_id, evidence_id):
    mapping = {
        'S001': {'facility_video': 'camera'},
        'S002': {'gate_layout': 'gate'},
        'S003': {'property_damage': 'damage', 'surveillance': 'camera'},
        'S004': {'retail_video': 'retail_camera', 'merchandise': 'merchandise'},
        'S005': {'vehicle_position': 'traffic'},
        'S006': {'scene_layout': 'medical_scene'},
    }
    return (mapping.get(scenario_id) or {}).get(evidence_id)


def render_evidence_svg(state, evidence_id, evaluator=False):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    row = ((world.get('evidence') or {}).get(evidence_id))
    if not row or not _visible(row, evaluator=evaluator):
        return None
    kind = _visual_kind(state.get('scenario_id', ''), evidence_id)
    if not kind:
        return None
    choices = ((state.get('run_context') or {}).get('choices') or {})
    if kind == 'damage':
        body = _damage_svg(row, choices)
    elif kind in {'camera', 'retail_camera'}:
        body = _camera_svg(row, choices, retail=kind == 'retail_camera')
    elif kind == 'merchandise':
        body = _merchandise_svg(row, choices)
    elif kind == 'traffic':
        body = _traffic_svg(row, choices)
    elif kind == 'gate':
        body = _gate_svg(row, choices)
    elif kind == 'medical_scene':
        body = _medical_svg(row, choices)
    else:
        return None
    return _wrap_svg(row, body)


def _wrap_svg(row, body):
    label = escape(_text(row.get('label')) or 'Evidence')
    status = escape(_text(row.get('status')).upper())
    description = escape(_text(row.get('description'))[:140])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" role="img" aria-label="Synthetic training evidence: {label}">
<rect width="960" height="540" fill="#f7f7f5"/>
<rect x="24" y="20" width="912" height="500" rx="16" fill="#ffffff" stroke="#1f2937" stroke-width="2"/>
<text x="48" y="58" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#991b1b">TRAINING / SYNTHETIC — NOT REAL EVIDENCE</text>
<text x="48" y="92" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#111827">{label}</text>
<text x="48" y="120" font-family="Arial, sans-serif" font-size="15" fill="#4b5563">Status: {status}</text>
{body}
<line x1="48" y1="452" x2="912" y2="452" stroke="#d1d5db"/>
<text x="48" y="482" font-family="Arial, sans-serif" font-size="15" fill="#374151">{description}</text>
<text x="48" y="506" font-family="Arial, sans-serif" font-size="13" fill="#6b7280">Visual is generated only from facts already present in this synthetic run.</text>
</svg>'''


def _damage_svg(row, choices):
    prop = escape(_text(choices.get('property') or 'government property'))
    evidence = escape(_text(choices.get('evidence') or row.get('description') or 'physical marks'))
    return f'''
<rect x="88" y="170" width="310" height="210" rx="10" fill="#eef2f7" stroke="#4b5563" stroke-width="3"/>
<text x="120" y="205" font-family="Arial" font-size="18" font-weight="700" fill="#111827">Government {prop}</text>
<path d="M245 238 l-28 36 34 18 -22 42 52-23 -18-36 30-25z" fill="none" stroke="#991b1b" stroke-width="5"/>
<circle cx="256" cy="286" r="74" fill="none" stroke="#ef4444" stroke-width="2" stroke-dasharray="8 8"/>
<text x="166" y="368" font-family="Arial" font-size="15" fill="#991b1b">Observed damage zone</text>
<rect x="535" y="215" width="285" height="115" rx="16" fill="#e5e7eb" stroke="#374151" stroke-width="3"/>
<circle cx="595" cy="337" r="24" fill="#374151"/><circle cx="760" cy="337" r="24" fill="#374151"/>
<text x="578" y="260" font-family="Arial" font-size="18" font-weight="700" fill="#111827">Involved vehicle</text>
<text x="535" y="392" font-family="Arial" font-size="15" fill="#374151">Comparison cue: {evidence}</text>'''


def _camera_svg(row, choices, retail=False):
    coverage = _text(choices.get('video') if retail else choices.get('witness_quality'))
    coverage = escape(coverage or row.get('description') or 'camera coverage varies')
    subject = 'Retail floor / checkout area' if retail else 'Facility public area'
    return f'''
<rect x="100" y="170" width="720" height="235" fill="#111827" rx="8"/>
<rect x="130" y="200" width="660" height="175" fill="#dbeafe" stroke="#93c5fd"/>
<path d="M155 220 L430 315 L155 365 Z" fill="#bfdbfe" opacity="0.7" stroke="#2563eb" stroke-width="2"/>
<rect x="145" y="205" width="54" height="30" fill="#374151"/><circle cx="172" cy="220" r="8" fill="#9ca3af"/>
<circle cx="505" cy="285" r="16" fill="#111827"/><line x1="505" y1="301" x2="505" y2="345" stroke="#111827" stroke-width="6"/><line x1="505" y1="318" x2="480" y2="336" stroke="#111827" stroke-width="5"/><line x1="505" y1="318" x2="530" y2="336" stroke="#111827" stroke-width="5"/>
<text x="456" y="190" font-family="Arial" font-size="17" font-weight="700" fill="#f9fafb">{escape(subject)}</text>
<text x="132" y="430" font-family="Arial" font-size="15" fill="#374151">Coverage condition: {coverage}</text>'''


def _merchandise_svg(row, choices):
    conduct = escape(_text(choices.get('conduct') or row.get('description') or 'reported merchandise handling'))
    return f'''
<rect x="150" y="185" width="280" height="180" rx="18" fill="#f3f4f6" stroke="#4b5563" stroke-width="3"/>
<path d="M235 215 h110 l28 45 -28 70 h-110 l-28-70z" fill="#dbeafe" stroke="#2563eb" stroke-width="3"/>
<rect x="560" y="210" width="190" height="135" rx="8" fill="#fff7ed" stroke="#9a3412" stroke-width="3"/>
<text x="588" y="252" font-family="Arial" font-size="18" font-weight="700">Transaction / item</text>
<text x="588" y="286" font-family="Arial" font-size="15">Preserve value, condition,</text><text x="588" y="308" font-family="Arial" font-size="15">and handling facts.</text>
<text x="150" y="408" font-family="Arial" font-size="15" fill="#374151">Reported conduct: {conduct}</text>'''


def _traffic_svg(row, choices):
    road = escape(_text(choices.get('road') or row.get('description') or 'installation roadway'))
    return f'''
<rect x="105" y="160" width="750" height="245" rx="8" fill="#4b5563"/>
<line x1="480" y1="165" x2="480" y2="400" stroke="#f9fafb" stroke-width="4" stroke-dasharray="24 20"/>
<rect x="520" y="210" width="150" height="66" rx="16" fill="#d1d5db" stroke="#111827" stroke-width="3"/>
<text x="552" y="250" font-family="Arial" font-size="16" font-weight="700">Stopped Vehicle</text>
<rect x="500" y="315" width="160" height="70" rx="16" fill="#dbeafe" stroke="#1d4ed8" stroke-width="3"/>
<text x="540" y="357" font-family="Arial" font-size="16" font-weight="700">Patrol Unit</text>
<path d="M710 238 h90" stroke="#fbbf24" stroke-width="5" marker-end="url(#a)"/>
<defs><marker id="a" markerWidth="10" markerHeight="10" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#fbbf24"/></marker></defs>
<text x="108" y="438" font-family="Arial" font-size="15" fill="#374151">Roadway condition: {road}</text>'''


def _gate_svg(row, choices):
    issue = escape(_text(choices.get('credential_issue') or 'access issue'))
    return f'''
<rect x="100" y="178" width="760" height="205" fill="#e5e7eb" stroke="#4b5563" stroke-width="2"/>
<rect x="132" y="208" width="140" height="92" fill="#dbeafe" stroke="#1d4ed8" stroke-width="3"/>
<text x="158" y="260" font-family="Arial" font-size="17" font-weight="700">Gate Booth</text>
<rect x="350" y="225" width="190" height="72" rx="14" fill="#f3f4f6" stroke="#111827" stroke-width="3"/>
<text x="385" y="267" font-family="Arial" font-size="17" font-weight="700">Subject Vehicle</text>
<rect x="610" y="202" width="190" height="118" fill="#fff7ed" stroke="#9a3412" stroke-width="3" stroke-dasharray="8 6"/>
<text x="640" y="250" font-family="Arial" font-size="16" font-weight="700">Inspection Area</text>
<text x="640" y="276" font-family="Arial" font-size="14">Access pending</text>
<text x="102" y="425" font-family="Arial" font-size="15" fill="#374151">Observed access issue: {issue}</text>'''


def _medical_svg(row, choices):
    issue = escape(_text(choices.get('scene_issue') or 'scene access issue'))
    patient_state = escape(_text(choices.get('patient_state') or 'patient condition'))
    return f'''
<rect x="108" y="170" width="744" height="230" rx="12" fill="#f3f4f6" stroke="#4b5563" stroke-width="2"/>
<circle cx="475" cy="280" r="30" fill="#dbeafe" stroke="#1d4ed8" stroke-width="3"/><text x="440" y="330" font-family="Arial" font-size="15" font-weight="700">Patient</text>
<circle cx="300" cy="245" r="22" fill="#e5e7eb" stroke="#374151" stroke-width="2"/><text x="260" y="285" font-family="Arial" font-size="13">Coworker</text>
<circle cx="650" cy="245" r="22" fill="#e5e7eb" stroke="#374151" stroke-width="2"/><text x="610" y="285" font-family="Arial" font-size="13">Coworker</text>
<path d="M118 350 H390" stroke="#16a34a" stroke-width="12" opacity="0.35"/><text x="140" y="342" font-family="Arial" font-size="14" fill="#166534">EMS access path</text>
<rect x="705" y="320" width="110" height="48" rx="8" fill="#fee2e2" stroke="#b91c1c" stroke-width="2"/><text x="720" y="350" font-family="Arial" font-size="13">Scene issue</text>
<text x="108" y="430" font-family="Arial" font-size="15" fill="#374151">Scene factor: {issue}</text>
<text x="108" y="452" font-family="Arial" font-size="15" fill="#374151">Observed patient state: {patient_state}</text>'''
