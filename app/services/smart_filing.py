from pathlib import Path


ALLOWED_EXTENSIONS = {
    'pdf',
    'doc',
    'docx',
    'png',
    'jpg',
    'jpeg',
    'gif',
    'webp',
    'xls',
    'xlsx',
    'csv',
    'txt',
}


def allowed_file(filename: str) -> bool:
    return Path(filename or '').suffix.lower().lstrip('.') in ALLOWED_EXTENSIONS


def classify_document(filename: str, description: str = '') -> str:
    text = f'{filename} {description}'.lower()
    rules = [
        (('award', 'nam', 'certificate', 'commend'), 'awards'),
        (('counsel', '6105', 'negative counseling'), 'counseling'),
        (('medical', 'light duty', 'limdu', 'profile'), 'medical'),
        (('training', 'roster', 'certificate', 'qualification'), 'training'),
        (('pdi', 'police department instruction'), 'pdi'),
        (('mco', 'maradmin', 'marine corps order', 'order'), 'marine_corps_orders'),
        (('form', 'pdf'), 'forms'),
        (('accident', 'crash', 'reconstruction', 'diagram'), 'accident_investigation'),
        (('srt', 'special reaction'), 'srt'),
        (('k9', 'k-9', 'canine'), 'k9'),
    ]
    for needles, area in rules:
        if any(needle in text for needle in needles):
            return area
    return 'general'


def smart_title(filename: str, description: str = '') -> str:
    if description:
        return description.strip()[:120]
    stem = Path(filename or 'document').stem.replace('_', ' ').replace('-', ' ')
    return ' '.join(part.capitalize() for part in stem.split()) or 'Document'


def build_storage_path(officer_id: str, area: str, filename: str) -> str:
    safe_officer = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in str(officer_id or 'unassigned'))
    safe_area = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in str(area or 'general'))
    safe_file = Path(filename or 'document').name
    return str(Path(safe_officer or 'unassigned') / (safe_area or 'general') / safe_file)
