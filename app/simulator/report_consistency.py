import json
import re

from flask import current_app, has_app_context

from ..services.ai_client import (
    ask_openai_with_system,
    configured_openai_api_key,
    is_ai_unavailable_message,
)


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _ledger(state):
    world = (state or {}).get('world') or {}
    known = []
    for item in world.get('known_information') or []:
        if isinstance(item, dict):
            text = _text(item.get('text'))
            source = _text(item.get('source'))
            if text:
                known.append({'source': source or 'unknown', 'text': text})
        elif _text(item):
            known.append({'source': 'unknown', 'text': _text(item)})

    dialogue = []
    for item in (state or {}).get('dialogue') or []:
        if not isinstance(item, dict):
            continue
        dialogue.append({
            'actor': _text(item.get('actor')),
            'role': _text(item.get('role')),
            'officer_question': _text(item.get('question')),
            'answer': _text(item.get('answer')),
        })

    evidence = []
    raw_evidence = world.get('evidence') or {}
    rows = raw_evidence.items() if isinstance(raw_evidence, dict) else []
    for evidence_id, item in rows:
        item = item if isinstance(item, dict) else {}
        evidence.append({
            'id': _text(evidence_id),
            'label': _text(item.get('label')),
            'status': _text(item.get('status')),
            'source': _text(item.get('source')),
            'description': _text(item.get('description')),
        })

    notes = []
    for item in world.get('field_notes') or []:
        if isinstance(item, dict):
            notes.append({
                'id': _text(item.get('id')),
                'status': _text(item.get('status')),
                'text': _text(item.get('text')),
            })

    timeline = []
    for item in world.get('timeline') or []:
        if isinstance(item, dict):
            summary = _text(item.get('summary'))
            if summary:
                timeline.append({
                    'event_type': _text(item.get('event_type')),
                    'actor': _text(item.get('actor')),
                    'summary': summary,
                })

    return {
        'scenario_id': _text((state or {}).get('scenario_id')),
        'known_information': known[-50:],
        'dialogue': dialogue[-40:],
        'evidence': evidence,
        'field_notes': notes[-50:],
        'timeline': timeline[-80:],
    }


def _deterministic_suggestions(state, narrative):
    narrative = str(narrative or '').strip()
    low = narrative.lower()
    suggestions = []

    if len(narrative) < 250:
        suggestions.append({
            'category': 'completeness',
            'issue': 'Narrative is very short for a completed scenario and may omit material chronology or investigative detail.',
            'evidence': f'Narrative length: {len(narrative)} characters.',
            'confidence': 'medium',
        })

    world = (state or {}).get('world') or {}
    for evidence_id, item in (world.get('evidence') or {}).items():
        if not isinstance(item, dict):
            continue
        label = _text(item.get('label')) or _text(evidence_id)
        status = _text(item.get('status')).lower()
        tokens = [token for token in re.findall(r'[a-z0-9]+', label.lower()) if len(token) >= 5]
        referenced = any(token in low for token in tokens[:5])
        possession_claim = any(term in low for term in ('collected', 'obtained', 'preserved', 'secured', 'reviewed', 'photographed'))
        if referenced and possession_claim and status in {'hidden', 'lost', 'expired', 'unavailable'}:
            suggestions.append({
                'category': 'evidence consistency',
                'issue': f'Narrative may claim use or preservation of {label}, but the simulator state does not show that evidence as obtained/preserved.',
                'evidence': f'Configured evidence status at end of run: {status or "unknown"}.',
                'confidence': 'high',
            })

    if 'cid' in low:
        package = (state or {}).get('training_package') or {}
        latest = (package.get('submissions') or [])[-1] if package.get('submissions') else {}
        cid_decision = _text(latest.get('cid_decision')).lower()
        if any(term in low for term in ('cid was notified', 'notified cid', 'contacted cid', 'screened with cid', 'cid was contacted')) and cid_decision not in {'screen', 'notify'}:
            suggestions.append({
                'category': 'notification consistency',
                'issue': 'Narrative documents CID contact/screening, but the trainee package does not record a matching CID decision.',
                'evidence': f'Trainee CID decision: {cid_decision or "not recorded"}.',
                'confidence': 'high',
            })

    return suggestions


def _parse_ai_suggestions(raw):
    text = str(raw or '').strip()
    if not text or is_ai_unavailable_message(text):
        return []
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.I)
        text = re.sub(r'\s*```$', '', text)
    try:
        payload = json.loads(text)
    except Exception:
        return []
    rows = payload.get('suggestions') if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []
    clean = []
    for row in rows[:12]:
        if not isinstance(row, dict):
            continue
        issue = _text(row.get('issue'))
        evidence = _text(row.get('evidence'))
        if not issue:
            continue
        clean.append({
            'category': _text(row.get('category')) or 'factual consistency',
            'issue': issue[:1200],
            'evidence': evidence[:1600],
            'confidence': _text(row.get('confidence')).lower() if _text(row.get('confidence')).lower() in {'high', 'medium', 'low'} else 'medium',
        })
    return clean


def review_training_narrative(state, narrative):
    """Generate advisory consistency cues for the human FTO.

    The model receives only the synthetic run ledger. It is instructed to flag
    possible discrepancies, never to make a DOR rating, legal conclusion, or
    employment decision. Deterministic checks remain available if AI is down.
    """
    narrative = str(narrative or '').strip()
    deterministic = _deterministic_suggestions(state, narrative)

    # CI/tests and explicitly offline installations must stay deterministic and
    # must never require an external model call to submit training paperwork.
    if has_app_context() and current_app.config.get('TESTING'):
        return {'mode': 'deterministic', 'suggestions': deterministic}

    api_key = configured_openai_api_key()
    if not api_key or not narrative:
        return {'mode': 'deterministic', 'suggestions': deterministic}

    ledger = _ledger(state)
    system_prompt = """You are an advisory report-consistency checker for a synthetic police FTO training simulator.
Compare the trainee narrative only against the supplied synthetic run ledger.
Rules:
- Do not grade, score, pass, fail, discipline, or make an employment decision.
- Do not make a legal conclusion or charging decision.
- Flag only a possible factual discrepancy, unsupported assertion, material omission, source-attribution problem, chronology conflict, or evidence/notification inconsistency.
- Do not invent facts that are not in the ledger.
- Distinguish firsthand statements from secondhand information when the ledger supports that distinction.
- If a statement is merely not provable from the ledger, describe it as unsupported/needs human verification, not as false.
- Ignore minor grammar/style unless it changes meaning.
- Return strict JSON only: {"suggestions":[{"category":"...","issue":"...","evidence":"...","confidence":"high|medium|low"}]}.
- Return an empty suggestions array when no reliable issue is identified.
"""
    prompt = json.dumps({'narrative': narrative, 'synthetic_run_ledger': ledger}, ensure_ascii=False)
    raw = ask_openai_with_system(prompt, system_prompt, api_key)
    ai_rows = _parse_ai_suggestions(raw)

    combined = []
    seen = set()
    for row in deterministic + ai_rows:
        key = _text(row.get('issue')).lower()
        if key and key not in seen:
            combined.append(row)
            seen.add(key)
    return {
        'mode': 'ai+deterministic' if ai_rows else 'deterministic',
        'suggestions': combined[:15],
    }
