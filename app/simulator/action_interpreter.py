import json
import re
from dataclasses import dataclass, asdict

from ..services.ai_client import (
    ask_openai_with_system,
    configured_openai_api_key,
    is_ai_unavailable_message,
)


ALLOWED_ACTION_TYPES = {
    'radio_status', 'request_backup', 'request_ems', 'request_fire',
    'notify_supervisor', 'request_investigator', 'records_check',
    'move', 'observe', 'speak', 'interview', 'command',
    'identify_person', 'separate_witnesses', 'direct_backup',
    'preserve_evidence', 'document_evidence', 'collect_evidence',
    'detain', 'arrest', 'search', 'cite', 'release',
    'use_force', 'deadly_force',
    'legal_assessment', 'deescalate', 'wait', 'document_report',
    'no_enforcement', 'clear_call', 'unknown',
}


@dataclass
class InterpretedAction:
    action_type: str
    target: str = ''
    priority: str = 'routine'
    reason: str = ''
    utterance: str = ''
    confidence: float = 0.75
    source: str = 'deterministic'

    def as_dict(self):
        row = asdict(self)
        row['confidence'] = round(max(0.0, min(1.0, float(row['confidence']))), 3)
        return row


def _clean(value):
    return ' '.join(str(value or '').split()).strip()


def _low(value):
    return _clean(value).lower()


def _matches(text, patterns):
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def _negated(text, verbs):
    """Catch common statements that discuss an action without taking it."""
    terms = '|'.join(re.escape(term) for term in verbs)
    patterns = (
        rf"\b(?:do not|don't|would not|wouldn't|will not|won't|am not going to|not going to|should not|shouldn't|cannot|can't)\s+(?:\w+\s+){{0,3}}(?:{terms})\b",
        rf"\b(?:no|without)\s+(?:lawful\s+)?(?:basis|authority|cause|reason)\s+(?:to|for)\s+(?:\w+\s+){{0,2}}(?:{terms})\b",
        rf"\b(?:not enough|insufficient)\s+(?:facts|evidence|cause)\s+(?:to|for)\s+(?:\w+\s+){{0,2}}(?:{terms})\b",
    )
    return _matches(text, patterns)


def _target_from_people(text, visible_people):
    low = _low(text)
    for person in visible_people or []:
        pid = _clean(person.get('id'))
        name = _clean(person.get('name'))
        role = _clean(person.get('role'))
        for candidate in (name, role, pid):
            if candidate and candidate.lower() in low:
                return pid or name or role
    return ''


def _append(rows, action_type, text, target='', priority='routine', reason='', confidence=0.82):
    if action_type not in ALLOWED_ACTION_TYPES:
        return
    key = (action_type, _clean(target).lower(), _clean(reason).lower())
    if any((row.action_type, row.target.lower(), row.reason.lower()) == key for row in rows):
        return
    rows.append(InterpretedAction(
        action_type=action_type,
        target=_clean(target),
        priority=_clean(priority) or 'routine',
        reason=_clean(reason),
        utterance=_clean(text)[:1200],
        confidence=confidence,
    ))


def deterministic_interpret(text, channel='scene', visible_people=None):
    """Interpret common patrol language without requiring exact wording."""
    text = _clean(text)
    low = text.lower()
    rows = []
    target = _target_from_people(text, visible_people)

    backup_language = _matches(low, (
        r'\b(send|start|get|request|need|want)\b.{0,35}\b(another|cover|second|additional)\b.{0,12}\b(unit|officer)\b',
        r'\bwait\b.{0,25}\bbackup\b', r'\bcover unit\b', r'\banother unit\b',
        r'\bstart somebody else (?:this|my) way\b',
    ))
    if backup_language and not _negated(low, ('backup', 'unit', 'officer')):
        _append(rows, 'request_backup', text, target='patrol_unit', reason='officer_safety')

    if channel == 'radio' or _matches(low, (r'\bdispatch\b', r'^\d{2,4}[a-z]?\b')):
        if _matches(low, (r'\b(on scene|arrived|show me on|10-23)\b',)):
            _append(rows, 'radio_status', text, target='dispatch', reason='on_scene')
        elif _matches(low, (r'\b(en route|responding|10-76)\b',)):
            _append(rows, 'radio_status', text, target='dispatch', reason='enroute')
        elif _matches(low, (r'\b(clear|available|10-8|back in service)\b',)):
            _append(rows, 'clear_call', text, target='dispatch', reason='clear')
        elif not rows:
            _append(rows, 'radio_status', text, target='dispatch', reason='general_transmission', confidence=0.68)

    if _matches(low, (r'\b(start|send|request|call|get)\b.{0,25}\b(ems|ambulance|paramedic|medical)\b',)) and not _negated(low, ('ems', 'ambulance', 'medical')):
        _append(rows, 'request_ems', text, target='ems')
    if _matches(low, (r'\b(start|send|request|call|get)\b.{0,25}\bfire\b',)) and not _negated(low, ('fire',)):
        _append(rows, 'request_fire', text, target='fire')
    if _matches(low, (r'\b(notify|call|advise|get)\b.{0,30}\b(watch commander|supervisor|sergeant|sgt)\b',)) and not _negated(low, ('notify', 'call', 'advise')):
        _append(rows, 'notify_supervisor', text, target='supervisor')
    if _matches(low, (r'\b(notify|call|request|screen)\b.{0,30}\b(cid|investigator|investigations)\b',)) and not _negated(low, ('notify', 'call', 'request', 'screen')):
        _append(rows, 'request_investigator', text, target='investigations')

    if _matches(low, (
        r'\b(run|check)\b.{0,20}\b(oln|license|driver|plate|tag|registration|wanted|warrant|ncic|gcic|records)\b',
        r'\b(wanted|warrant|records) check\b',
    )) and not _negated(low, ('run', 'check')):
        _append(rows, 'records_check', text, target='dispatch')

    if _matches(low, (r'\b(park|move|walk|approach|go|position|stand|enter|step)\b',)) and not _negated(low, ('park', 'move', 'walk', 'approach', 'go', 'enter')):
        _append(rows, 'move', text, target=target)
    if _matches(low, (r'\b(look|observe|check|examine|inspect|scan)\b',)) and not _negated(low, ('look', 'observe', 'check', 'examine', 'inspect', 'scan')):
        _append(rows, 'observe', text, target=target)

    if _matches(low, (r'\b(separate|keep apart|split up)\b.{0,30}\b(witness|people|parties|employees)\b',)) and not _negated(low, ('separate',)):
        _append(rows, 'separate_witnesses', text, target='witnesses')
    if _matches(low, (r'\b(identify|get.*name|get.*id|who is|who are)\b',)):
        _append(rows, 'identify_person', text, target=target)

    quoted_or_question = '?' in text or _matches(low, (r'\b(ask|talk to|speak to|interview|tell me|explain to me|what happened|who saw)\b',))
    if quoted_or_question and not _negated(low, ('ask', 'talk', 'speak', 'interview')):
        kind = 'interview' if _matches(low, (r'\b(interview|what happened|who saw|tell me exactly|statement)\b',)) else 'speak'
        _append(rows, kind, text, target=target)

    if _matches(low, (r'\b(show me your hands|keep your hands|do not reach|don.t reach|step back|stay there|stop moving|put .* down)\b',)):
        _append(rows, 'command', text, target=target)

    if _matches(low, (r'\b(de-escalat|lower my voice|calm him|calm her|build rapport|explain calmly|speak calmly)\b',)):
        _append(rows, 'deescalate', text, target=target)

    if _matches(low, (r'\b(preserve|save|secure|copy)\b.{0,30}\b(video|footage|evidence|photo|receipt|statement|item)\b',)) and not _negated(low, ('preserve', 'save', 'secure', 'copy')):
        _append(rows, 'preserve_evidence', text)
    if _matches(low, (r'\b(photo|photograph|document|measure)\b.{0,30}\b(damage|scene|evidence|vehicle|item)\b',)) and not _negated(low, ('photo', 'photograph', 'document', 'measure')):
        _append(rows, 'document_evidence', text)
    if _matches(low, (r'\b(collect|package|bag|seize)\b.{0,25}\b(evidence|item|property)\b',)) and not _negated(low, ('collect', 'package', 'bag', 'seize')):
        _append(rows, 'collect_evidence', text)

    if _matches(low, (r'\b(shoot|fire (?:my|the) weapon|deadly force)\b',)) and not _negated(low, ('shoot', 'fire', 'deadly force')):
        _append(rows, 'deadly_force', text, target=target, priority='urgent', reason='force_decision', confidence=0.93)
    elif _matches(low, (r'\b(tase|taser|pepper spray|oc spray|strike|go hands on|use force|physical force)\b',)) and not _negated(low, ('tase', 'taser', 'spray', 'strike', 'use force')):
        _append(rows, 'use_force', text, target=target, priority='urgent', reason='control_decision', confidence=0.9)

    if _matches(low, (r'\bdetain\b', r'\btemporary detention\b')) and not _negated(low, ('detain',)):
        _append(rows, 'detain', text, target=target)
    if _matches(low, (r'\barrest\b', r'\btake .* into custody\b')) and not _negated(low, ('arrest', 'custody')):
        _append(rows, 'arrest', text, target=target)
    if _matches(low, (r'\bsearch\b', r'\bfrisk\b')) and not _negated(low, ('search', 'frisk')):
        _append(rows, 'search', text, target=target)
    if _matches(low, (r'\b(cite|citation|ticket)\b',)) and not _negated(low, ('cite', 'citation', 'ticket')):
        _append(rows, 'cite', text, target=target)
    if _matches(low, (r'\b(release|free to leave|let .* go)\b',)) and not _negated(low, ('release',)):
        _append(rows, 'release', text, target=target)

    if _matches(low, (r'\b(probable cause|reasonable suspicion|legal basis|authority|elements|lawful basis)\b',)):
        _append(rows, 'legal_assessment', text)
    if _matches(low, (r'\b(no crime|insufficient facts|not enough evidence|civil matter|no enforcement|warning only|documentation only|do not have probable cause|don.t have probable cause)\b',)):
        _append(rows, 'no_enforcement', text, reason='insufficient_or_non_enforcement_disposition')
    if _matches(low, (r'\b(report|ccn|blotter|document the call|complete.*paperwork|write.*narrative)\b',)) and not _negated(low, ('report', 'document', 'write')):
        _append(rows, 'document_report', text)
    if _matches(low, (r'\b(wait|hold position|stand by)\b',)) and not any(r.action_type == 'request_backup' for r in rows):
        _append(rows, 'wait', text)
    if _matches(low, (r'\b(tell|have|ask)\b.{0,35}\b(backup|cover officer|other officer)\b.{0,35}\b(watch|talk|stay|stand|check)\b',)):
        _append(rows, 'direct_backup', text, target='backup_officer')

    if not rows:
        _append(rows, 'unknown', text, confidence=0.35)
    return [row.as_dict() for row in rows]


def _extract_json(text):
    raw = _clean(text)
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.I)
        raw = re.sub(r'\s*```$', '', raw)
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r'(\{.*\}|\[.*\])', raw, re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except Exception:
            return None


def _validate_ai_actions(payload, original_text):
    rows = payload.get('actions') if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []
    clean_rows = []
    for item in rows[:8]:
        if not isinstance(item, dict):
            continue
        action_type = _clean(item.get('action_type')).lower()
        if action_type not in ALLOWED_ACTION_TYPES:
            continue
        try:
            confidence = float(item.get('confidence', 0.8))
        except (TypeError, ValueError):
            confidence = 0.8
        clean_rows.append(InterpretedAction(
            action_type=action_type,
            target=_clean(item.get('target'))[:80],
            priority=_clean(item.get('priority'))[:30] or 'routine',
            reason=_clean(item.get('reason'))[:180],
            utterance=_clean(original_text)[:1200],
            confidence=max(0.0, min(1.0, confidence)),
            source='ai',
        ).as_dict())
    return clean_rows


def interpret_action(text, channel='scene', visible_people=None, visible_resources=None, use_ai=True):
    """Convert natural-language trainee input into validated canonical actions."""
    text = _clean(text)
    if not text:
        return []

    fallback = deterministic_interpret(text, channel=channel, visible_people=visible_people)
    api_key = configured_openai_api_key() if use_ai else ''
    if not api_key:
        return fallback

    people = [
        {'id': _clean(row.get('id')), 'name': _clean(row.get('name')), 'role': _clean(row.get('role'))}
        for row in (visible_people or [])[:12]
    ]
    resources = [_clean(value) for value in (visible_resources or []) if _clean(value)][:12]
    system_prompt = f"""You are a language parser for a synthetic police field-training simulator.
Your only job is to translate the trainee's words into structured action intent.
You do NOT decide whether an action is lawful, correct, successful, possible, or safe.
You do NOT add facts, evidence, weapons, crimes, warrants, injuries, or people.
You do NOT coach the trainee.
Pay close attention to negation. A trainee who says they will NOT arrest, search, shoot, use force, detain, release, request a resource, or take another action has not performed that action.

Channel: {channel}
Currently visible people: {json.dumps(people)}
Currently visible resources: {json.dumps(resources)}
Allowed action_type values: {sorted(ALLOWED_ACTION_TYPES)}

Return JSON only in this shape:
{{"actions":[{{"action_type":"...","target":"...","priority":"routine|urgent","reason":"short inferred intent","confidence":0.0}}]}}
Use multiple actions when the trainee clearly performs multiple things. If intent is unclear, use unknown.
"""
    answer = ask_openai_with_system(text, system_prompt, api_key)
    if is_ai_unavailable_message(answer):
        return fallback
    parsed = _extract_json(answer)
    ai_rows = _validate_ai_actions(parsed, text)
    return ai_rows or fallback


SEMANTIC_TOKENS = {
    'radio_status': 'dispatch radio status location on scene',
    'request_backup': 'backup additional unit cover unit dispatch officer safety',
    'request_ems': 'ems medical patient aid ambulance',
    'request_fire': 'fire emergency resource dispatch',
    'notify_supervisor': 'notify supervisor dispatch status',
    'request_investigator': 'cid investigator screen notify',
    'records_check': 'records check license registration wanted dispatch',
    'move': 'position approach distance scene safety',
    'observe': 'observe assess hands movement scene damage evidence',
    'speak': 'ask interview account communication professional',
    'interview': 'interview ask statement firsthand witness account',
    'command': 'clear direction command hands visible instruction compliance',
    'identify_person': 'identify identity driver witness subject reporting party',
    'separate_witnesses': 'separate witness interview statement',
    'direct_backup': 'backup coordinate additional unit direction',
    'preserve_evidence': 'preserve video evidence surveillance statement',
    'document_evidence': 'photo photograph document damage evidence',
    'collect_evidence': 'collect preserve evidence property',
    'use_force': 'force necessary reasonable proportionate resistance threat control',
    'deadly_force': 'deadly force shoot weapon immediate threat necessary reasonable',
    'detain': 'detain reasonable suspicion authority facts lawful',
    'arrest': 'arrest probable cause authority facts lawful',
    'search': 'search consent warrant probable cause authority lawful',
    'cite': 'citation enforcement disposition facts',
    'release': 'release disposition free to leave',
    'legal_assessment': 'legal basis probable cause reasonable suspicion authority elements facts',
    'deescalate': 'calm professional explain listen de-escalate communication',
    'wait': 'wait position safety',
    'document_report': 'report document ccn blotter statement disposition',
    'no_enforcement': 'no enforcement insufficient facts warning release disposition based on facts',
    'clear_call': 'dispatch radio clear status disposition',
}


def actions_to_semantic_text(actions, original_text=''):
    """Produce deterministic semantic cues for legacy rubric compatibility."""
    parts = []
    for row in actions or []:
        parts.append(SEMANTIC_TOKENS.get(_clean(row.get('action_type')).lower(), ''))
        parts.append(_clean(row.get('reason')))
    if not parts:
        parts.append(_clean(original_text))
    return ' '.join(part for part in parts if part)
