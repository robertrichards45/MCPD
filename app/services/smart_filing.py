import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.heic', '.xls', '.xlsx', '.txt'}

CATEGORY_RULES = [
    ('medical', ('medical', 'medpros', 'annual medical', 'physical', 'health', 'dental')),
    ('training', ('training', 'certificate', 'cert', 'course', 'qualification', 'qual')),
    ('counseling', ('counseling', 'counselling', 'disciplinary', 'verbal', 'written')),
    ('award', ('award', 'cash award', 'time off', 'achievement', 'recognition')),
    ('leave', ('leave', 'absence', 'liberty', 'sick', 'annual leave')),
    ('evaluation', ('performance', 'appraisal', 'eval', 'evaluation')),
    ('id_admin', ('license', 'id card', 'cac', 'edipi', 'driver')),
]


def allowed_file(filename: str) -> bool:
    return os.path.splitext(filename or '')[1].lower() in ALLOWED_EXTENSIONS


def classify_document(filename: str, description: str = '') -> str:
    haystack = f'{filename or ""} {description or ""}'.lower()
    for category, terms in CATEGORY_RULES:
        if any(term in haystack for term in terms):
            return category
    return 'general'


def safe_officer_folder(officer_id) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]+', '_', str(officer_id or 'unknown')).strip('_') or 'unknown'


def build_storage_path(base_dir: str, officer_id, category: str, filename: str) -> tuple[str, str]:
    category = re.sub(r'[^a-zA-Z0-9_-]+', '_', category or 'general').strip('_') or 'general'
    original = secure_filename(filename or 'upload.bin')
    stamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    stored_name = f'{stamp}_{original}'
    folder = os.path.join(base_dir, safe_officer_folder(officer_id), category)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, stored_name), stored_name
