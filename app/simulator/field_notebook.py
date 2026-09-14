from copy import deepcopy
from datetime import datetime, timezone

from .world_state import add_timeline, ensure_world_state


MAX_NOTE_LENGTH = 2500
MAX_CATEGORY_LENGTH = 40


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _utc_iso():
    return datetime.now(timezone.utc).isoformat()


def _notes(state):
    world = ensure_world_state(state, state.get('scenario_id', ''))
    rows = world.get('field_notes')
    if not isinstance(rows, list):
        rows = []
        world['field_notes'] = rows
    return world, rows


def _next_note_id(rows):
    highest = 0
    for row in rows:
        raw = str((row or {}).get('id') or '')
        if raw.startswith('N') and raw[1:].isdigit():
            highest = max(highest, int(raw[1:]))
    return f'N{highest + 1:03d}'


def add_field_note(state, text, category='general'):
    """Append a trainee field note without changing scenario truth.

    Notes are training artifacts created by the trainee. They are intentionally
    append-only so the FTO can later distinguish the original note from a
    correction. Use ``revise_field_note`` to amend an earlier entry.
    """
    world, rows = _notes(state)
    text = _text(text)[:MAX_NOTE_LENGTH]
    category = _text(category).lower()[:MAX_CATEGORY_LENGTH] or 'general'
    if not text:
        return None

    note = {
        'id': _next_note_id(rows),
        'clock': int(world.get('clock', 0)),
        'category': category,
        'text': text,
        'status': 'active',
        'revision_of': None,
        'created_at': _utc_iso(),
    }
    rows.append(note)
    world['field_notes'] = rows[-200:]
    add_timeline(
        state,
        'field_note_added',
        'Field notebook updated.',
        actor='Trainee',
        channel='notebook',
        details={'note_id': note['id'], 'category': category, 'text': text},
        visible_to_trainee=False,
    )
    return deepcopy(note)


def revise_field_note(state, note_id, text, category=None):
    """Supersede a field note while retaining the original entry for review."""
    world, rows = _notes(state)
    note_id = _text(note_id)
    text = _text(text)[:MAX_NOTE_LENGTH]
    if not note_id or not text:
        return None

    original = None
    for row in rows:
        if str((row or {}).get('id') or '') == note_id and row.get('status') == 'active':
            original = row
            break
    if original is None:
        return None

    original['status'] = 'superseded'
    original['superseded_at'] = _utc_iso()
    replacement = {
        'id': _next_note_id(rows),
        'clock': int(world.get('clock', 0)),
        'category': (_text(category).lower()[:MAX_CATEGORY_LENGTH] if category is not None else original.get('category')) or 'general',
        'text': text,
        'status': 'active',
        'revision_of': note_id,
        'created_at': _utc_iso(),
    }
    rows.append(replacement)
    world['field_notes'] = rows[-200:]
    add_timeline(
        state,
        'field_note_revised',
        'Field notebook entry revised; original preserved.',
        actor='Trainee',
        channel='notebook',
        details={
            'original_note_id': note_id,
            'replacement_note_id': replacement['id'],
            'category': replacement['category'],
            'text': text,
        },
        visible_to_trainee=False,
    )
    return deepcopy(replacement)


def field_notes(state, include_superseded=False):
    """Return notebook entries in creation order."""
    _world, rows = _notes(state)
    if include_superseded:
        return deepcopy(rows)
    return [deepcopy(row) for row in rows if row.get('status') == 'active']
