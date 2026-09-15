from html import escape

from .world_state import ensure_world_state


VISIBLE_STATUSES = {'available', 'discovered', 'preserved', 'collected'}


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _visible(row, evaluator=False):
    if evaluator:
        return bool(row)
    return _text((row or {}).get('status')).lower() in VISIBLE_STATUSES


def render_s007_crash_svg(state, evaluator=False):
    """Render S007 crash-scene evidence without inventing crash cause or fault."""
    world = ensure_world_state(state, 'S007')
    row = (world.get('evidence') or {}).get('crash_scene')
    if not row or not _visible(row, evaluator=evaluator):
        return None

    run_context = state.get('run_context') or {}
    choices = run_context.get('choices') or {}
    location = escape(_text(run_context.get('location_display') or run_context.get('location_name') or row.get('location') or 'MCLB Albany roadway'))
    crash_type = escape(_text(choices.get('crash_type') or 'vehicle crash'))
    scene_evidence = escape(_text(choices.get('scene_evidence') or row.get('description') or 'roadway evidence varies'))
    injury = escape(_text(choices.get('injury') or 'injury status under investigation'))
    label = escape(_text(row.get('label')) or 'Crash scene / final-rest diagram')
    status = escape(_text(row.get('status')).upper())
    description = escape(_text(row.get('description'))[:140])

    single_vehicle = 'single vehicle' in _text(choices.get('crash_type')).lower()
    if single_vehicle:
        involved = '''
<g aria-label="Involved vehicle and fixed object">
  <rect x="548" y="240" width="170" height="72" rx="18" fill="#dbeafe" stroke="#1d4ed8" stroke-width="4"/>
  <circle cx="585" cy="316" r="18" fill="#1f2937"/><circle cx="681" cy="316" r="18" fill="#1f2937"/>
  <text x="586" y="282" font-family="Arial" font-size="17" font-weight="700" fill="#111827">Vehicle A</text>
  <rect x="765" y="210" width="34" height="132" rx="6" fill="#d1d5db" stroke="#4b5563" stroke-width="3"/>
  <text x="735" y="372" font-family="Arial" font-size="14" fill="#374151">Fixed object</text>
</g>'''
    else:
        involved = '''
<g aria-label="Involved vehicles">
  <rect x="515" y="205" width="160" height="68" rx="18" fill="#dbeafe" stroke="#1d4ed8" stroke-width="4"/>
  <circle cx="550" cy="277" r="17" fill="#1f2937"/><circle cx="640" cy="277" r="17" fill="#1f2937"/>
  <text x="553" y="246" font-family="Arial" font-size="17" font-weight="700" fill="#111827">Vehicle A</text>
  <rect x="650" y="320" width="160" height="68" rx="18" fill="#e5e7eb" stroke="#374151" stroke-width="4"/>
  <circle cx="685" cy="392" r="17" fill="#1f2937"/><circle cx="775" cy="392" r="17" fill="#1f2937"/>
  <text x="688" y="361" font-family="Arial" font-size="17" font-weight="700" fill="#111827">Vehicle B</text>
</g>'''

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" role="img" aria-label="Synthetic training evidence: {label}">
<rect width="960" height="540" fill="#f7f7f5"/>
<rect x="24" y="20" width="912" height="500" rx="16" fill="#ffffff" stroke="#1f2937" stroke-width="2"/>
<text x="48" y="58" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#991b1b">TRAINING / SYNTHETIC — NOT REAL EVIDENCE</text>
<text x="48" y="92" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#111827">{label}</text>
<text x="48" y="120" font-family="Arial, sans-serif" font-size="15" fill="#4b5563">Status: {status}</text>

<rect x="72" y="150" width="816" height="276" rx="12" fill="#4b5563"/>
<line x1="100" y1="288" x2="860" y2="288" stroke="#f9fafb" stroke-width="4" stroke-dasharray="28 22"/>
<line x1="100" y1="180" x2="860" y2="180" stroke="#fbbf24" stroke-width="3"/>
<line x1="100" y1="396" x2="860" y2="396" stroke="#fbbf24" stroke-width="3"/>
<rect x="92" y="165" width="365" height="88" rx="10" fill="rgba(255,255,255,.94)" stroke="#d1d5db"/>
<text x="112" y="194" font-family="Arial" font-size="16" font-weight="700" fill="#111827">Location</text>
<text x="112" y="219" font-family="Arial" font-size="15" fill="#374151">{location}</text>
<text x="112" y="242" font-family="Arial" font-size="14" fill="#4b5563">Crash type: {crash_type}</text>

{involved}

<g aria-label="Observed roadway evidence">
  <circle cx="390" cy="318" r="8" fill="#fbbf24"/><circle cx="420" cy="338" r="6" fill="#fbbf24"/><circle cx="448" cy="312" r="5" fill="#fbbf24"/>
  <path d="M335 350 C365 334 405 362 447 350" fill="none" stroke="#111827" stroke-width="5" stroke-dasharray="8 7"/>
  <text x="112" y="382" font-family="Arial" font-size="15" font-weight="700" fill="#f9fafb">Observed scene cue:</text>
  <text x="255" y="382" font-family="Arial" font-size="15" fill="#f9fafb">{scene_evidence}</text>
</g>

<line x1="48" y1="452" x2="912" y2="452" stroke="#d1d5db"/>
<text x="48" y="478" font-family="Arial, sans-serif" font-size="15" fill="#374151">{description}</text>
<text x="48" y="501" font-family="Arial, sans-serif" font-size="13" fill="#6b7280">Injury information: {injury}. Diagram is not to scale and does not assign crash cause or fault.</text>
</svg>'''
