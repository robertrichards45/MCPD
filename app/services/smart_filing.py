import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.heic', '.xls', '.xlsx', '.txt'}

ADMIN_AREAS = {
    'officer_files': 'Officer Files',
    'watch_forms': 'Watch Commander Forms',
    'orders': 'Marine Corps Orders',
    'pdi': 'Police Department Instructions',
    'counseling': 'Counseling',
    'awards': 'Awards',
    'medical': 'Medical',
    'training': 'Training',
    'accident_investigation': 'Accident Investigation',
    'srt': 'Special Reaction Team',
    'k9': 'K9',
}

CATEGORY_RULES = [
    ('medical', ('medical', 'medpros', 'annual medical', 'physical', 'health', 'dental', 'immunization')),
    ('training', ('training', 'certificate', 'cert', 'course', 'qualification', 'qual', 'roster')),
    ('counseling', ('counseling', 'counselling', 'disciplinary', 'verbal', 'written', 'ler', 'misconduct')),
    ('award', ('award', 'cash award', 'time off', 'achievement', 'recognition', 'nomination')),
    ('leave', ('leave', 'absence', 'liberty', 'sick', 'annual leave')),
    ('evaluation', ('performance', 'appraisal', 'eval', 'evaluation', 'opm')),
    ('id_admin', ('license', 'id card', 'cac', 'edipi', 'driver')),
    ('pdi', ('pdi', 'police department instruction', 'instruction', 'sop')),
    ('orders', ('mco', 'maradmin', 'order', 'navmc', 'marine corps order', 'base order')),
    ('forms', ('form', 'opnav', 'dd form', 'sf ', 'navmc')),
    ('accident_investigation', ('accident', 'crash', 'collision', 'sketch', 'sf 91', 'reconstruction')),
    ('srt', ('srt', 'special reaction team', 'tactical', 'team training')),
    ('k9', ('k9', 'k-9', 'canine', 'dog', 'handler')),
]

FORM_RECOGNITION_RULES = [
    ('OPNAV 5580/2 Voluntary Statement', ('opnav 5580 2', 'opnav55802', 'voluntary statement', 'witness statement')),
    ('OPNAV 5580/21 Field Interview Card', ('opnav 5580 21', 'opnav558021', 'field interview')),
    ('OPNAV 5580/22 Evidence Custody Document', ('opnav 5580 22', 'opnav558022', 'evidence custody', 'property custody')),
    ('DD Form 1805 Citation', ('dd 1805', 'dd form 1805', 'citation')),
    ('DD Form 1408 Traffic Ticket', ('dd 1408', 'dd form 1408', 'armed forces traffic ticket')),
    ('DD Form 2708 Receipt for Inmate or Detained Person', ('dd 2708', 'dd form 2708', 'detained person')),
    ('SF 91 Motor Vehicle Accident Report', ('sf 91', 'motor vehicle accident', 'crash report')),
    ('DD Form 2506 Vehicle Impoundment Report', ('dd 2506', 'vehicle impoundment', 'impound')),
    ('DD Form 2701 VWAP', ('dd 2701', 'victim witness', 'vwap')),
    ('NAVMC 11130 Statement of Force/Use of Detention', ('navmc 11130', 'use of force', 'detention')),
    ('Domestic Violence Supplemental Report', ('domestic violence', 'domestic supplemental', 'domestic checklist')),
]

ROLE_CONTEXTS = {
    'watch_commander': 'Watch Commander',
    'desk_sgt': 'Desk Sergeant',
    'fto': 'Field Training Officer',
    'accident_investigator': 'Accident Investigator',
    'srt': 'Special Reaction Team',
    'k9': 'K9',
    'assistant_operations_officer': 'Assistant Operations Officer',
    'operations_officer': 'Operations Officer',
    'deputy_chief': 'Deputy Chief',
    'chief': 'Chief',
}


def allowed_file(filename: str) -> bool:
    return os.path.splitext(filename or '')[1].lower() in ALLOWED_EXTENSIONS


def _haystack(filename: str, description: str = '') -> str:
    return f'{filename or ""} {description or ""}'.lower().replace('_', ' ').replace('-', ' ')


def recognize_form(filename: str, description: str = '') -> str:
    haystack = _haystack(filename, description)
    compact = haystack.replace(' ', '')
    for label, terms in FORM_RECOGNITION_RULES:
        if any(term in haystack or term.replace(' ', '') in compact for term in terms):
            return label
    return ''


def classify_document(filename: str, description: str = '', area: str = '') -> str:
    haystack = _haystack(filename, description)
    if area == 'pdi' or 'police department instruction' in haystack or re.search(r'\bpdi\b', haystack):
        return 'pdi'
    if area == 'orders' or 'marine corps order' in haystack or re.search(r'\bmco\b|\bmaradmin\b', haystack):
        return 'orders'
    form_label = recognize_form(filename, description)
    if form_label:
        return 'forms'
    for category, terms in CATEGORY_RULES:
        if any(term in haystack for term in terms):
            return category
    return area if area in ADMIN_AREAS else 'general'


def smart_title(filename: str, description: str = '') -> str:
    form_label = recognize_form(filename, description)
    if form_label:
        return form_label
    base = os.path.splitext(os.path.basename(filename or 'Document'))[0]
    base = re.sub(r'[_\-]+', ' ', base).strip()
    base = re.sub(r'\s+', ' ', base)
    return base.title() or 'Document'


def safe_folder(value) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]+', '_', str(value or 'general')).strip('_') or 'general'


def safe_officer_folder(officer_id) -> str:
    return safe_folder(officer_id or 'unknown')


def build_storage_path(base_dir: str, officer_id, category: str, filename: str, area: str = 'officer_files') -> tuple[str, str]:
    category = safe_folder(category or 'general')
    original = secure_filename(filename or 'upload.bin')
    stamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    stored_name = f'{stamp}_{original}'
    if area == 'officer_files':
        folder = os.path.join(base_dir, safe_officer_folder(officer_id), category)
    else:
        folder = os.path.join(base_dir, safe_folder(area), category)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, stored_name), stored_name
