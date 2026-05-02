import base64
import json
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / 'data' / 'forms_pdf_templates'
XFA_TEMPLATE_NS = {'xfa': 'http://www.xfa.org/schema/xfa-template/2.8/'}
XFA_FORM_NS = {'xfa': 'http://www.xfa.org/schema/xfa-form/2.8/'}


def _ensure_optional_crypto_runtime() -> None:
    try:
        from cryptography.hazmat.primitives.ciphers.algorithms import AES  # noqa: F401
        from cryptography.hazmat.primitives.ciphers.base import Cipher  # noqa: F401
        return
    except Exception:
        pass
    repo_root = Path(__file__).resolve().parents[2]
    for relative in ('wheel_extract/pycparser', 'wheel_extract/cffi', 'wheel_extract/cryptography'):
        target = repo_root / relative
        if target.exists():
            path_value = str(target)
            if path_value not in sys.path:
                sys.path.insert(0, path_value)
    for module_name in list(sys.modules.keys()):
        if module_name == 'cryptography' or module_name.startswith('cryptography.'):
            del sys.modules[module_name]
    try:
        import cryptography  # noqa: F401
    except Exception:
        pass


def _clear_modules(prefixes: tuple[str, ...]) -> None:
    for module_name in list(sys.modules.keys()):
        if any(module_name == prefix or module_name.startswith(f'{prefix}.') for prefix in prefixes):
            del sys.modules[module_name]


def _rc4_transform(key: bytes, data: bytes) -> bytes:
    state = bytearray(range(256))
    j = 0
    for index in range(256):
        j = (j + state[index] + key[index % len(key)]) % 256
        state[index], state[j] = state[j], state[index]

    output = bytearray(len(data))
    i = 0
    j = 0
    for index, byte in enumerate(data):
        i = (i + 1) % 256
        j = (j + state[i]) % 256
        state[i], state[j] = state[j], state[i]
        mask = state[(state[i] + state[j]) % 256]
        output[index] = byte ^ mask
    return bytes(output)


def _apply_pypdf_crypto_compatibility() -> None:
    from pypdf._crypt_providers import _base as base_module
    from pypdf import _crypt_providers as provider_module
    from pypdf import _encryption as encryption_module
    from pypdf._crypt_providers import _cryptography as cryptography_provider

    class CompatCryptRC4(base_module.CryptBase):
        def __init__(self, key: bytes) -> None:
            self.key = key

        def encrypt(self, data: bytes) -> bytes:
            return _rc4_transform(self.key, data)

        def decrypt(self, data: bytes) -> bytes:
            return _rc4_transform(self.key, data)

    def rc4_encrypt(key: bytes, data: bytes) -> bytes:
        return _rc4_transform(key, data)

    def rc4_decrypt(key: bytes, data: bytes) -> bytes:
        return _rc4_transform(key, data)

    provider_module.CryptAES = cryptography_provider.CryptAES
    provider_module.aes_ecb_encrypt = cryptography_provider.aes_ecb_encrypt
    provider_module.aes_ecb_decrypt = cryptography_provider.aes_ecb_decrypt
    provider_module.aes_cbc_encrypt = cryptography_provider.aes_cbc_encrypt
    provider_module.aes_cbc_decrypt = cryptography_provider.aes_cbc_decrypt
    provider_module.CryptRC4 = CompatCryptRC4
    provider_module.rc4_encrypt = rc4_encrypt
    provider_module.rc4_decrypt = rc4_decrypt
    provider_module.crypt_provider = ('cryptography+local-rc4', getattr(cryptography_provider, '__version__', 'local'))

    encryption_module.CryptAES = provider_module.CryptAES
    encryption_module.aes_ecb_encrypt = provider_module.aes_ecb_encrypt
    encryption_module.aes_ecb_decrypt = provider_module.aes_ecb_decrypt
    encryption_module.aes_cbc_encrypt = provider_module.aes_cbc_encrypt
    encryption_module.aes_cbc_decrypt = provider_module.aes_cbc_decrypt
    encryption_module.CryptRC4 = provider_module.CryptRC4
    encryption_module.rc4_encrypt = provider_module.rc4_encrypt
    encryption_module.rc4_decrypt = provider_module.rc4_decrypt


def _load_pdf_classes(force_compat: bool = False):
    if force_compat:
        _ensure_optional_crypto_runtime()
        _clear_modules(('cryptography', 'pypdf'))
    from pypdf import PdfReader, PdfWriter
    if force_compat:
        _apply_pypdf_crypto_compatibility()
    return PdfReader, PdfWriter


def _pdf_classes(force_compat: bool = False):
    try:
        return _load_pdf_classes(force_compat=force_compat)
    except Exception:
        if force_compat:
            raise
        return _load_pdf_classes(force_compat=True)


def _looks_like_crypto_failure(exc: Exception) -> bool:
    message = str(exc or '')
    return any(token in message for token in (
        'cryptography>=3.1',
        'AES algorithm',
        'RC4',
        'UnsupportedAlgorithm',
    ))


def _reader_for_pdf(pdf_path: str):
    PdfReader, _ = _pdf_classes()
    try:
        return PdfReader(pdf_path)
    except Exception as exc:
        if not _looks_like_crypto_failure(exc):
            raise
        PdfReader, _ = _pdf_classes(force_compat=True)
        return PdfReader(pdf_path)


def _normalize_key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', (value or '').lower())


def _is_user_fillable_field_name(name: str) -> bool:
    raw = (name or '').strip()
    if not raw:
        return False
    lowered = raw.lower()
    if any(token in lowered for token in ('screen_buttons', 'printbutton', 'submitbutton', 'resetbutton', 'savebutton')):
        return False
    if lowered in {'reset', 'currentpage', 'pagecount'}:
        return False
    leaf = _field_leaf_name(raw).lower()
    if leaf in {'reset', 'currentpage', 'pagecount'}:
        return False
    return True


def _is_generic_visible_field(item: dict) -> bool:
    if not isinstance(item, dict):
        return False
    name = str(item.get('name') or '').strip()
    if not name or not _is_user_fillable_field_name(name):
        return False
    pdf_type = str(item.get('type') or '').strip()
    # Properly-typed AcroForm signature fields (/Sig) and fields whose PDF type
    # was detected as 'signature' via XFA inspection are now shown with a canvas
    # widget rather than a text input. Include them in the visible schema.
    # Phase-1 fix: was unconditionally excluded to avoid ugly text input rendering.
    if pdf_type in {'/Sig', 'signature'}:
        return True
    lowered = name.lower()
    if 'signature' in lowered or 'initial' in lowered:
        # Include initial-named text fields (e.g. "Initials of person making statement")
        # — they get an initials canvas widget. Exclude ambiguous date/time helpers like
        # "initial_date" that are not actual capture fields.
        if 'initial' in lowered and pdf_type in {'', '/Tx', 'text'}:
            skip_tokens = ('initial_date', 'initial_time', 'initialdate', 'initialtime')
            if not any(tok in lowered for tok in skip_tokens):
                return True
        return False
    return True


def _field_leaf_name(name: str) -> str:
    raw = str(name or '').strip()
    if not raw:
        return ''
    return raw.rsplit('.', 1)[-1]


def _clean_pdf_label(label: str, fallback: str = '') -> str:
    text = ' '.join(str(label or '').replace('_', ' ').split()).strip()
    fallback_text = ' '.join(str(fallback or '').replace('_', ' ').split()).strip()
    row_match = re.search(r'\bRow\s*([0-9]+)\b', text, flags=re.IGNORECASE)
    if row_match and len(text) > 80:
        return f'Statement Row {row_match.group(1)}'

    click_match = re.match(
        r'^([0-9]+[.)])?\s*Click here to select\s+"?([^",.]+)"?,?\s*(.*)$',
        text,
        flags=re.IGNORECASE,
    )
    if click_match:
        prefix = (click_match.group(1) or '').strip()
        option = (click_match.group(2) or '').strip()
        context = (click_match.group(3) or '').strip(' .')
        context = re.sub(r'^(as|for)\s+', '', context, flags=re.IGNORECASE)
        context = context.replace('the status of ', '')
        context = context.replace('one of the two appropriate boxes for ', '')
        cleaned = f'{prefix} {option}'.strip()
        if context:
            cleaned = f'{cleaned} - {context}'
        return cleaned.strip(' .') or fallback_text or 'Field'

    return text.rstrip(':') or fallback_text or 'Field'


def _field_sort_key(item: dict):
    return (
        int(item.get('page_index') or 0),
        -float(item.get('y') or 0),
        float(item.get('x') or 0),
        str(item.get('name') or '').lower(),
    )


def _load_template(schema_id: str) -> dict:
    path = TEMPLATE_DIR / f'{schema_id}.json'
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def get_template_payload(schema_id: str) -> dict:
    payload = _load_template(schema_id or '')
    if payload:
        return payload
    return {
        'template_id': schema_id or '',
        'description': 'PDF field mapping template',
        'field_map': {},
    }


def save_template_payload(schema_id: str, payload: dict) -> str:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    safe_schema_id = (schema_id or '').strip() or 'generic_form_v1'
    target = TEMPLATE_DIR / f'{safe_schema_id}.json'
    out = payload if isinstance(payload, dict) else {}
    if 'template_id' not in out:
        out['template_id'] = safe_schema_id
    if 'field_map' not in out or not isinstance(out.get('field_map'), dict):
        out['field_map'] = {}
    target.write_text(json.dumps(out, indent=2), encoding='utf-8')
    return str(target)


def visible_input_keys_for_pdf(schema_id: str, pdf_path: str | None) -> set[str]:
    template = _load_template(schema_id or '')
    field_map = template.get('field_map') if isinstance(template.get('field_map'), dict) else {}
    ui_fields = template.get('ui_fields') if isinstance(template.get('ui_fields'), list) else []
    template_keys = {
        str(item.get('name') or '').strip()
        for item in ui_fields
        if isinstance(item, dict) and str(item.get('name') or '').strip()
    }
    if not template_keys:
        template_keys = {str(key).strip() for key in field_map.keys() if str(key).strip()}
    if not pdf_path or not os.path.exists(pdf_path):
        return template_keys
    try:
        info = inspect_pdf_fields(pdf_path)
        pdf_fields = [item for item in info.get('fields', []) if isinstance(item, dict) and item.get('name')]
    except Exception:
        pdf_fields = []
    if not pdf_fields:
        try:
            info = inspect_xfa_fields(pdf_path)
            pdf_fields = [item for item in info.get('fields', []) if isinstance(item, dict) and item.get('name')]
        except Exception:
            pdf_fields = []
    if not pdf_fields:
        # Static/non-fillable PDFs rely on curated template keys only.
        return template_keys
    if not template_keys:
        return {
            str(item.get('name') or '').strip()
            for item in pdf_fields
            if _is_generic_visible_field(item)
        }
    normalized_pdf = {_normalize_key(str(item.get('name') or '').strip()) for item in pdf_fields}
    visible: set[str] = set()
    for key in template_keys:
        mapped_target = str(field_map.get(key) or key).strip()
        if mapped_target and _normalize_key(mapped_target) in normalized_pdf:
            visible.add(str(key))
    if not visible and template_keys:
        return template_keys
    return visible


def _flatten_payload(schema: dict, payload: dict, blank_mode: bool = False) -> dict[str, str]:
    values: dict[str, str] = {}
    section_map = {}
    for section in schema.get('sections', []):
        for field in section.get('fields', []):
            section_map[field.get('name')] = field.get('label') or field.get('name')
    raw_values = payload.get('values') if isinstance(payload.get('values'), dict) else {}
    for key, label in section_map.items():
        value = '' if blank_mode else str(raw_values.get(key) or '').strip()
        values[key] = value
        values[f'label::{label}'] = value
    if bool(schema.get('show_role_entry')):
        role_rows = payload.get('role_entries') if isinstance(payload.get('role_entries'), list) else []
        for idx, row in enumerate(role_rows[:4], start=1):
            if not isinstance(row, dict):
                continue
            values[f'role_{idx}'] = '' if blank_mode else str(row.get('role') or '').strip()
            values[f'role_name_{idx}'] = '' if blank_mode else str(row.get('full_name') or '').strip()
            values[f'role_identifier_{idx}'] = '' if blank_mode else str(row.get('identifier') or '').strip()
            values[f'role_phone_{idx}'] = '' if blank_mode else str(row.get('phone') or '').strip()
            values[f'role_vehicle_{idx}'] = '' if blank_mode else str(row.get('vehicle') or '').strip()
            values[f'role_notes_{idx}'] = '' if blank_mode else str(row.get('notes') or '').strip()
    if bool(schema.get('show_notes')):
        values['general_notes'] = '' if blank_mode else str(payload.get('notes') or '').strip()
    return values


def _annotation_attr(field_raw, key: str):
    if field_raw is None:
        return None
    value = field_raw.get(key)
    if value is not None:
        return value
    parent = field_raw.get('/Parent')
    if parent is not None:
        parent = parent.get_object() if hasattr(parent, 'get_object') else parent
        if isinstance(parent, dict):
            return parent.get(key)
    return None


def _annotation_fields(reader) -> list[dict]:
    fields = {}
    for page_index, page in enumerate(reader.pages):
        annots = page.get('/Annots')
        annots = annots.get_object() if hasattr(annots, 'get_object') else annots
        for annot_ref in annots or []:
            annot = annot_ref.get_object() if hasattr(annot_ref, 'get_object') else annot_ref
            if not isinstance(annot, dict):
                continue
            subtype = str(_annotation_attr(annot, '/Subtype') or '')
            if subtype != '/Widget':
                continue
            name = str(_annotation_attr(annot, '/T') or '').strip()
            if not name or not _is_user_fillable_field_name(name):
                continue
            field_type = str(_annotation_attr(annot, '/FT') or '')
            value = _annotation_attr(annot, '/V')
            tooltip = str(_annotation_attr(annot, '/TU') or _annotation_attr(annot, '/TM') or '').strip()
            rect = annot.get('/Rect')
            rect_values = [float(item) for item in rect] if isinstance(rect, (list, tuple)) and len(rect) == 4 else []
            if name not in fields:
                fields[name] = {
                    'name': name,
                    'raw_name': name,
                    'label': _clean_pdf_label(tooltip, name),
                    'type': field_type,
                    'value': str(value) if value is not None else '',
                    'page_index': page_index,
                    'rect': rect_values,
                    'x': rect_values[0] if rect_values else None,
                    'y': rect_values[1] if rect_values else None,
                }
    return sorted(fields.values(), key=_field_sort_key)


def _annotation_field_map(reader) -> dict[str, dict]:
    fields = {}
    for page in reader.pages:
        annots = page.get('/Annots')
        annots = annots.get_object() if hasattr(annots, 'get_object') else annots
        for annot_ref in annots or []:
            annot = annot_ref.get_object() if hasattr(annot_ref, 'get_object') else annot_ref
            if not isinstance(annot, dict):
                continue
            subtype = str(_annotation_attr(annot, '/Subtype') or '')
            if subtype != '/Widget':
                continue
            name = str(_annotation_attr(annot, '/T') or '').strip()
            if not name or not _is_user_fillable_field_name(name):
                continue
            fields.setdefault(name, annot)
    return fields


def inspect_pdf_fields(pdf_path: str) -> dict:
    reader = _reader_for_pdf(pdf_path)
    annotation_rows = _annotation_fields(reader)
    annotation_by_name = {str(item.get('name') or '').strip(): item for item in annotation_rows}
    annotation_by_leaf = {}
    for item in annotation_rows:
        leaf = _field_leaf_name(item.get('name'))
        if leaf and leaf not in annotation_by_leaf:
            annotation_by_leaf[leaf] = item
    try:
        raw_fields = reader.get_fields() or {}
    except Exception:
        raw_fields = {}
    out = []
    for name, raw in raw_fields.items():
        clean_name = str(name or '').strip()
        if not clean_name or not _is_user_fillable_field_name(clean_name):
            continue
        annotation = annotation_by_name.get(clean_name) or annotation_by_leaf.get(_field_leaf_name(clean_name)) or {}
        rect = annotation.get('rect') if isinstance(annotation.get('rect'), list) else []
        tooltip = str(annotation.get('label') or raw.get('/TU') or raw.get('/TM') or '').strip()
        out.append({
            'name': clean_name,
            'raw_name': annotation.get('raw_name') or _field_leaf_name(clean_name) or clean_name,
            'label': _clean_pdf_label(tooltip, clean_name),
            'type': str(raw.get('/FT', '')),
            'value': str(raw.get('/V', '')) if raw.get('/V') is not None else '',
            'page_index': annotation.get('page_index', 0),
            'rect': rect,
            'x': annotation.get('x'),
            'y': annotation.get('y'),
        })
    if not out:
        out = annotation_rows
    else:
        out = sorted(out, key=_field_sort_key)
    return {'field_count': len(out), 'fields': out}


def _xfa_chunks(reader) -> dict[str, str]:
    root = reader.trailer.get('/Root')
    if not root:
        return {}
    acro_form = root.get('/AcroForm')
    if not acro_form:
        return {}
    acro_form = acro_form.get_object() if hasattr(acro_form, 'get_object') else acro_form
    xfa = acro_form.get('/XFA')
    if not xfa:
        return {}
    xfa = xfa.get_object() if hasattr(xfa, 'get_object') else xfa
    if not isinstance(xfa, list):
        return {}

    chunks: dict[str, str] = {}
    for index in range(0, len(xfa), 2):
        if index + 1 >= len(xfa):
            break
        chunk_name = str(xfa[index] or '').strip()
        raw_value = xfa[index + 1]
        raw_value = raw_value.get_object() if hasattr(raw_value, 'get_object') else raw_value
        if hasattr(raw_value, 'get_data'):
            data = raw_value.get_data()
            chunks[chunk_name] = data.decode('utf-8', errors='ignore')
        else:
            chunks[chunk_name] = str(raw_value or '')
    return chunks


def _xfa_chunks_for_pdf(pdf_path: str) -> dict[str, str]:
    reader = _reader_for_pdf(pdf_path)
    try:
        return _xfa_chunks(reader)
    except Exception as exc:
        if not _looks_like_crypto_failure(exc):
            raise
        PdfReader, _ = _pdf_classes(force_compat=True)
        return _xfa_chunks(PdfReader(pdf_path))


def _node_tag_name(node) -> str:
    return str(getattr(node, 'tag', '')).rsplit('}', 1)[-1]


def _xfa_control_type(field_node: ET.Element) -> str:
    if field_node.find('.//xfa:checkButton', XFA_TEMPLATE_NS) is not None:
        return 'checkbox'
    if field_node.find('.//xfa:choiceList', XFA_TEMPLATE_NS) is not None:
        return 'select'
    if field_node.find('.//xfa:dateTimeEdit', XFA_TEMPLATE_NS) is not None:
        return 'date'
    if field_node.find('.//xfa:signature', XFA_TEMPLATE_NS) is not None:
        return 'signature'
    if field_node.find('.//xfa:textEdit', XFA_TEMPLATE_NS) is not None:
        return 'text'
    return 'text'


def _xfa_text_value(field_node: ET.Element, xpath: str) -> str:
    text = field_node.findtext(xpath, default='', namespaces=XFA_TEMPLATE_NS)
    return ' '.join(str(text or '').split()).strip()


def _xfa_fields_from_tree(node: ET.Element, ancestry: list[str] | None = None) -> list[dict]:
    ancestry = list(ancestry or [])
    tag_name = _node_tag_name(node)
    next_ancestry = list(ancestry)
    if tag_name in {'subform', 'exclGroup'}:
        name = str(node.get('name') or '').strip()
        if name:
            next_ancestry.append(name)

    fields: list[dict] = []
    if tag_name == 'field':
        raw_name = str(node.get('name') or '').strip()
        if raw_name and _is_user_fillable_field_name(raw_name):
            fields.append({
                'raw_name': raw_name,
                'path': '.'.join(next_ancestry + [raw_name]) if next_ancestry else raw_name,
                'type': _xfa_control_type(node),
                'label': _xfa_text_value(node, './/xfa:caption//xfa:text') or raw_name,
            })

    for child in list(node):
        fields.extend(_xfa_fields_from_tree(child, next_ancestry))
    return fields


def _measurement_points(value) -> float | None:
    raw = str(value or '').strip()
    if not raw:
        return None
    match = re.match(r'^(-?\d+(?:\.\d+)?)(mm|cm|in|pt)?$', raw)
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2) or 'pt'
    if unit == 'mm':
        return amount * 72.0 / 25.4
    if unit == 'cm':
        return amount * 72.0 / 2.54
    if unit == 'in':
        return amount * 72.0
    return amount


def _xfa_layout_fields_from_tree(
    node: ET.Element,
    ancestry: list[str] | None = None,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    page_index: int = 0,
) -> list[dict]:
    ancestry = list(ancestry or [])
    tag_name = _node_tag_name(node)
    node_name = str(node.get('name') or '').strip()
    local_x = _measurement_points(node.get('x')) or 0.0
    local_y = _measurement_points(node.get('y')) or 0.0
    next_x = offset_x + local_x
    next_y = offset_y + local_y
    next_page = page_index
    next_ancestry = list(ancestry)

    if tag_name in {'subform', 'exclGroup'} and node_name:
        next_ancestry.append(node_name)

    if tag_name == 'pageArea':
        try:
            next_page = max(page_index, int(re.sub(r'[^0-9]', '', node_name or '') or '1') - 1)
        except Exception:
            next_page = page_index

    fields: list[dict] = []
    if tag_name == 'field':
        raw_name = node_name
        if raw_name and _is_user_fillable_field_name(raw_name):
            fields.append({
                'raw_name': raw_name,
                'path': '.'.join(next_ancestry + [raw_name]) if next_ancestry else raw_name,
                'type': _xfa_control_type(node),
                'label': _xfa_text_value(node, './/xfa:caption//xfa:text') or raw_name,
                'x': next_x,
                'y': next_y,
                'w': _measurement_points(node.get('w')),
                'h': _measurement_points(node.get('h')),
                'page_index': next_page,
            })

    for child in list(node):
        fields.extend(_xfa_layout_fields_from_tree(child, next_ancestry, next_x, next_y, next_page))
    return fields


def inspect_xfa_fields(pdf_path: str) -> dict:
    chunks = _xfa_chunks_for_pdf(pdf_path)
    template_xml = chunks.get('template')
    if not template_xml:
        return {'field_count': 0, 'fields': [], 'conditional_groups': []}

    template_root = ET.fromstring(template_xml)
    duplicate_counter: dict[str, int] = {}
    fields = []
    conditional_groups = []

    for group_node in template_root.findall('.//xfa:exclGroup', XFA_TEMPLATE_NS):
        options = []
        for option in group_node.findall('./xfa:field', XFA_TEMPLATE_NS):
            name = str(option.get('name') or '').strip()
            if name:
                options.append(name)
        if options:
            conditional_groups.append({
                'name': str(group_node.get('name') or '').strip() or f'group_{len(conditional_groups) + 1}',
                'options': options,
            })

    group_lookup = {}
    for group in conditional_groups:
        for option in group.get('options', []):
            group_lookup.setdefault(option, []).append(group['name'])

    layout_lookup = {}
    for layout_info in _xfa_layout_fields_from_tree(template_root):
        layout_lookup.setdefault(layout_info['path'], []).append(layout_info)

    for field_info in _xfa_fields_from_tree(template_root):
        raw_name = field_info['raw_name']
        candidate_path = field_info['path']
        occurrence = duplicate_counter.get(candidate_path, 0) + 1
        duplicate_counter[candidate_path] = occurrence
        unique_name = candidate_path if occurrence == 1 else f'{candidate_path}__{occurrence}'
        layout_matches = layout_lookup.get(candidate_path) or []
        layout_info = layout_matches[occurrence - 1] if len(layout_matches) >= occurrence else {}
        fields.append({
            'name': unique_name,
            'raw_name': raw_name,
            'path': candidate_path,
            'type': field_info['type'],
            'label': field_info['label'],
            'group_names': group_lookup.get(raw_name, []),
            'x': layout_info.get('x'),
            'y': layout_info.get('y'),
            'w': layout_info.get('w'),
            'h': layout_info.get('h'),
            'page_index': layout_info.get('page_index', 0),
        })

    return {
        'field_count': len(fields),
        'fields': fields,
        'conditional_groups': conditional_groups,
        'chunks': sorted(chunks.keys()),
    }


def source_pdf_has_adobe_wait_shell(pdf_path: str | None) -> bool:
    if not pdf_path or not os.path.exists(pdf_path):
        return False
    try:
        reader = _reader_for_pdf(pdf_path)
        text = '\n'.join((page.extract_text() or '') for page in reader.pages[:2])
    except Exception:
        return False
    normalized = ' '.join(text.split()).lower()
    return (
        'please wait' in normalized
        and 'pdf viewer may not be able to display this type of document' in normalized
    )


def _field_name_map(pdf_fields: list[str], template: dict, flat_values: dict[str, str]) -> dict[str, str]:
    explicit = template.get('field_map') if isinstance(template.get('field_map'), dict) else {}
    normalized_pdf = {_normalize_key(name): name for name in pdf_fields}
    mapped: dict[str, str] = {}

    for src_key, target_name in explicit.items():
        if src_key in flat_values and target_name in pdf_fields:
            mapped[target_name] = flat_values[src_key]

    for src_key, value in flat_values.items():
        if src_key in explicit:
            continue
        if not value:
            continue
        if src_key in pdf_fields and src_key not in mapped:
            mapped[src_key] = value
            continue
        norm_src = _normalize_key(src_key)
        direct = normalized_pdf.get(norm_src)
        if direct and direct not in mapped:
            mapped[direct] = value
            continue
        if src_key.startswith('label::'):
            raw_label = src_key.replace('label::', '')
            if raw_label in pdf_fields and raw_label not in mapped:
                mapped[raw_label] = value
                continue
            norm_label = _normalize_key(src_key.replace('label::', ''))
            direct_label = normalized_pdf.get(norm_label)
            if direct_label and direct_label not in mapped:
                mapped[direct_label] = value
    return mapped


def _truthy(value: str) -> bool:
    return str(value or '').strip().lower() in {'yes', 'true', '1', 'on', 'x', 'checked'}


def _checkbox_on_value(field_raw, override: str | None = None) -> str:
    if override:
        text = str(override).strip()
        return text if text.startswith('/') else f'/{text.lstrip("/")}'
    try:
        states = field_raw.get('/_States')
        if isinstance(states, (list, tuple)):
            for state in states:
                text = str(state)
                if text and text.lower() != '/off':
                    return text if text.startswith('/') else f'/{text.lstrip("/")}'
        ap = field_raw.get('/AP')
        if ap and isinstance(ap, dict):
            normal = ap.get('/N')
            if normal and hasattr(normal, 'keys'):
                for key in normal.keys():
                    text = str(key)
                    if text and text.lower() != '/off':
                        return text if text.startswith('/') else f'/{text.lstrip("/")}'
    except Exception:
        pass
    return '/Yes'


def _coerce_value_for_pdf(field_raw, value: str, checkbox_override: str | None = None) -> tuple[str, dict | None]:
    field_type = str(field_raw.get('/FT', ''))
    if field_type == '/Btn':
        return (_checkbox_on_value(field_raw, checkbox_override) if _truthy(value) else '/Off', None)
    text_value = str(value or '').strip()
    max_len = field_raw.get('/MaxLen')
    if isinstance(max_len, int) and max_len > 0 and len(text_value) > max_len:
        truncated = text_value[:max_len]
        return (
            truncated,
            {
                'original_length': len(text_value),
                'max_length': max_len,
                'truncated_length': len(truncated),
            },
        )
    return (text_value, None)


def _safe_annotation_name(writer, field_raw) -> str:
    try:
        qualified = writer._get_qualified_field_name(field_raw)  # type: ignore[attr-defined]
        if qualified:
            return str(qualified).strip()
    except Exception:
        pass
    return str(_annotation_attr(field_raw, '/T') or '').strip()


def _annotation_state_names(field_raw) -> set[str]:
    states: set[str] = set()
    try:
        ap = field_raw.get('/AP')
        if ap and isinstance(ap, dict):
            normal = ap.get('/N')
            if normal and hasattr(normal, 'keys'):
                for key in normal.keys():
                    text = str(key or '').strip()
                    if text:
                        states.add(text if text.startswith('/') else f'/{text.lstrip("/")}')
    except Exception:
        pass
    return states


def _normalize_checkbox_pdf_value(value: str) -> str:
    text = str(value or '').strip()
    if not text:
        return '/Off'
    return text if text.startswith('/') else f'/{text.lstrip("/")}'


def _manually_update_page_form_field_values(writer, page, fields: dict[str, str], flags=None) -> None:
    from pypdf.generic import ArrayObject, NameObject, NumberObject, TextStringObject

    annots = page.get('/Annots')
    annots = annots.get_object() if hasattr(annots, 'get_object') else annots
    if not annots:
        return

    for annot_ref in annots:
        annot = annot_ref.get_object() if hasattr(annot_ref, 'get_object') else annot_ref
        if not isinstance(annot, dict):
            continue
        parent = annot.get('/Parent')
        parent = parent.get_object() if hasattr(parent, 'get_object') else parent
        parent = parent if isinstance(parent, dict) else None

        annot_names = {name for name in {str(_annotation_attr(annot, '/T') or '').strip(), _safe_annotation_name(writer, annot)} if name}
        parent_names = {name for name in {str(_annotation_attr(parent, '/T') or '').strip() if parent else '', _safe_annotation_name(writer, parent) if parent else ''} if name}

        matched_name = next((field_name for field_name in fields.keys() if field_name in annot_names or field_name in parent_names), None)
        if not matched_name:
            continue

        value = fields[matched_name]
        target = parent if matched_name in parent_names and parent is not None else annot
        field_type = str(_annotation_attr(target, '/FT') or _annotation_attr(annot, '/FT') or '')

        if isinstance(value, list):
            target[NameObject('/V')] = ArrayObject(TextStringObject(str(item or '')) for item in value)
        elif field_type == '/Btn':
            checkbox_value = _normalize_checkbox_pdf_value(value)
            off_value = NameObject('/Off')
            target[NameObject('/V')] = NameObject(checkbox_value)

            if matched_name in annot_names:
                annot_states = _annotation_state_names(annot)
                annot[NameObject('/AS')] = NameObject(checkbox_value if checkbox_value in annot_states or not annot_states else '/Off')
            if parent is not None:
                kids = parent.get('/Kids')
                kids = kids.get_object() if hasattr(kids, 'get_object') else kids
                for kid_ref in kids or []:
                    kid = kid_ref.get_object() if hasattr(kid_ref, 'get_object') else kid_ref
                    if not isinstance(kid, dict):
                        continue
                    kid_states = _annotation_state_names(kid)
                    desired = checkbox_value if checkbox_value in kid_states or (not kid_states and kid is annot) else '/Off'
                    kid[NameObject('/AS')] = NameObject(desired)
            elif '/AS' not in annot or annot[NameObject('/AS')] != NameObject(checkbox_value):
                annot[NameObject('/AS')] = NameObject(checkbox_value if checkbox_value != '/Off' else '/Off')
        else:
            target[NameObject('/V')] = TextStringObject(str(value or ''))

        if flags:
            target[NameObject('/Ff')] = NumberObject(flags)


def _write_fillable_pdf(source_pdf: str, target_pdf: str, schema: dict, payload: dict, blank_mode: bool = False) -> dict:
    reader = _reader_for_pdf(source_pdf)
    _, PdfWriter = _pdf_classes()
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    try:
        fields = reader.get_fields() or {}
    except Exception:
        fields = _annotation_field_map(reader)
    field_names = list(fields.keys())
    template = _load_template(schema.get('id') or '')
    checkbox_overrides = template.get('checkbox_on_values') if isinstance(template.get('checkbox_on_values'), dict) else {}
    flat_values = _flatten_payload(schema, payload, blank_mode=blank_mode)
    mapped = _field_name_map(field_names, template, flat_values)
    coerced = {}
    # Collect DataURL signature values separately — they are drawn as image overlays
    # after the AcroForm fields are written (DataURLs cannot be stored in text fields).
    dataurl_fields: dict[str, str] = {}
    truncations = []
    for field_name, value in mapped.items():
        str_value = str(value or '').strip()
        if str_value.startswith('data:image/'):
            # Store for post-fill image overlay; skip from AcroForm text values.
            dataurl_fields[field_name] = str_value
            coerced[field_name] = ''
            continue
        raw = fields.get(field_name)
        if isinstance(raw, dict):
            override = checkbox_overrides.get(field_name) if isinstance(checkbox_overrides, dict) else None
            coerced_value, trunc_info = _coerce_value_for_pdf(raw, value, checkbox_override=override)
            coerced[field_name] = coerced_value
            if trunc_info:
                truncations.append({'field': field_name, **trunc_info})
        else:
            coerced[field_name] = str_value
    used_manual_fallback = False
    for page in writer.pages:
        try:
            writer.update_page_form_field_values(page, coerced)
        except KeyError as exc:
            if str(exc) != "'/AP'":
                raise
            _manually_update_page_form_field_values(writer, page, coerced)
            used_manual_fallback = True
    try:
        writer.set_need_appearances_writer(True)
    except Exception:
        pass
    with open(target_pdf, 'wb') as handle:
        writer.write(handle)

    # If any signature/initials DataURLs were captured, overlay them as images on
    # the first page of the generated PDF. AcroForm /Sig fields cannot store image
    # data via update_page_form_field_values, so we stamp the image on top.
    # TODO (Phase 2): map each DataURL to its precise annotation rectangle so the
    #   image lands exactly on the right field; current approach places signatures
    #   sequentially at the bottom of page 1 as a safe fallback.
    if dataurl_fields:
        try:
            _stamp_dataurl_signatures_on_pdf(target_pdf, dataurl_fields)
        except Exception:
            pass  # Never let a signature stamp failure block the download

    return {
        'mode': 'fillable',
        'mapped_count': len(coerced),
        'mapped_fields': sorted(coerced.keys()),
        'truncations': truncations,
        'template_id': template.get('template_id') or '',
        'manual_widget_fallback': used_manual_fallback,
        'unmapped_input_keys': sorted([key for key in flat_values.keys() if key and flat_values.get(key) and key not in (template.get('field_map') or {})]),
        'signature_fields_stamped': sorted(dataurl_fields.keys()),
    }


def _stamp_dataurl_signatures_on_pdf(pdf_path: str, dataurl_map: dict) -> None:
    """Overlay DataURL signature images onto the first page of an existing PDF.

    Each signature is placed sequentially along the bottom margin of page 1.
    This is a Phase-1 safe fallback. Phase-2 should map each field name to the
    actual annotation rectangle so signatures land on the correct field line.
    """
    PdfReader, PdfWriter = _pdf_classes()
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    if not reader.pages:
        return

    overlay_buffer = BytesIO()
    page = reader.pages[0]
    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)
    draw = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

    sig_w, sig_h = 160.0, 40.0
    x = 36.0
    y = 36.0  # start at bottom-left margin
    for _field_name, dataurl in dataurl_map.items():
        img_reader = _decode_dataurl_image(dataurl)
        if img_reader is None:
            continue
        draw.setStrokeColorRGB(0.6, 0.6, 0.6)
        draw.rect(x, y, sig_w, sig_h, stroke=1, fill=0)
        draw.drawImage(img_reader, x + 2, y + 2, width=sig_w - 4, height=sig_h - 4, mask='auto', preserveAspectRatio=True, anchor='sw')
        x += sig_w + 12
        if x + sig_w > page_width - 36:
            x = 36.0
            y += sig_h + 8

    draw.save()
    overlay_reader = PdfReader(BytesIO(overlay_buffer.getvalue()))
    writer.pages[0].merge_page(overlay_reader.pages[0])

    tmp = pdf_path + '.sig_tmp'
    with open(tmp, 'wb') as fh:
        writer.write(fh)
    os.replace(tmp, pdf_path)


def _write_overlay_pdf(target_pdf: str, schema: dict, payload: dict, blank_mode: bool = False) -> dict:
    c = canvas.Canvas(target_pdf, pagesize=letter)
    width, height = letter
    c.setFont('Helvetica-Bold', 13)
    c.drawString(40, height - 40, schema.get('title') or 'Form Preview')
    c.setFont('Helvetica', 9)
    y = height - 64
    flat = _flatten_payload(schema, payload, blank_mode=blank_mode)
    for section in schema.get('sections', []) or []:
        title = str(section.get('title') or 'Form Fields').strip()
        if y < 64:
            c.showPage()
            y = height - 40
        c.setFont('Helvetica-Bold', 10)
        c.drawString(40, y, title[:90])
        y -= 14
        c.setFont('Helvetica', 9)
        for field in section.get('fields', []) or []:
            key = str(field.get('name') or '').strip()
            if not key:
                continue
            label = str(field.get('label') or key).strip()
            value = flat.get(key) or ('N/A' if not blank_mode else '')
            line = f'{label}: {value}'.strip()
            for chunk in _wrap_overlay_text(line, width - 80, 36, 9) or [line[:140]]:
                c.drawString(40, y, chunk[:150])
                y -= 11
                if y < 40:
                    c.showPage()
                    c.setFont('Helvetica', 9)
                    y = height - 40
            if blank_mode:
                c.line(40, y + 2, width - 40, y + 2)
            y -= 4
    if bool(schema.get('show_notes')):
        notes = flat.get('general_notes') or ('N/A' if not blank_mode else '')
        if y < 64:
            c.showPage()
            y = height - 40
        c.setFont('Helvetica-Bold', 10)
        c.drawString(40, y, 'Notes')
        y -= 14
        c.setFont('Helvetica', 9)
        for chunk in _wrap_overlay_text(f'General Notes: {notes}', width - 80, 60, 9) or []:
            c.drawString(40, y, chunk[:150])
            y -= 11
    c.save()
    return {'mode': 'overlay', 'mapped_count': len(flat), 'mapped_fields': sorted(flat.keys()), 'template_id': ''}


def _wrap_overlay_text(value: str, width_points: float, field_height: float, font_size: int) -> list[str]:
    text = ' '.join(str(value or '').replace('\r', '\n').split()).strip()
    if not text:
        return []
    approx_chars = max(1, int(max(width_points - 4, 12) / max(font_size * 0.55, 1)))
    words = text.split(' ')
    lines = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if current and len(candidate) > approx_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    max_lines = max(1, int(max(field_height - 2, font_size + 2) / max(font_size + 1, 1)))
    return lines[:max_lines]


def _decode_dataurl_image(value: str):
    """Return an ImageReader for a data:image/... DataURL, or None on failure."""
    try:
        if not str(value or '').startswith('data:image/'):
            return None
        header, encoded = value.split(',', 1)
        img_bytes = base64.b64decode(encoded)
        return ImageReader(BytesIO(img_bytes))
    except Exception:
        return None


def _draw_xfa_value(draw, page_height: float, field: dict, value: str) -> None:
    field_type = str(field.get('type') or 'text').strip().lower()
    x = float(field.get('x') or 0.0)
    y_top = float(field.get('y') or 0.0)
    width = float(field.get('w') or 64.0)
    height = float(field.get('h') or 12.0)
    y = page_height - y_top - height
    if field_type == 'checkbox':
        if _truthy(value):
            draw.setFont('Helvetica-Bold', 10)
            draw.drawCentredString(x + (width / 2.0), y + max((height / 2.0) - 4, 2), 'X')
        return

    text_value = str(value or '').strip()
    if not text_value:
        return

    # Signature/initial canvas DataURL — draw as image at the field's coordinates.
    img_reader = _decode_dataurl_image(text_value)
    if img_reader is not None:
        pad = 2.0
        draw.drawImage(img_reader, x + pad, y + pad, width=max(width - pad * 2, 10), height=max(height - pad * 2, 8), mask='auto', preserveAspectRatio=True, anchor='sw')
        return

    font_size = 8 if field_type in {'text', 'date', 'signature'} else 7
    draw.setFont('Helvetica', font_size)
    lines = _wrap_overlay_text(text_value, width, height, font_size)
    if not lines:
        return
    line_height = font_size + 1
    baseline = y + height - line_height
    for index, line in enumerate(lines):
        draw.drawString(x + 2, max(baseline - (index * line_height), y + 1), line)


def _write_xfa_overlay_pdf(source_pdf: str, target_pdf: str, schema: dict, payload: dict, blank_mode: bool = False) -> dict:
    xfa_info = inspect_xfa_fields(source_pdf)
    fields = xfa_info.get('fields') if isinstance(xfa_info.get('fields'), list) else []
    if not fields:
        return _write_overlay_pdf(target_pdf, schema, payload, blank_mode=blank_mode)

    reader = _reader_for_pdf(source_pdf)
    field_names = [str(item.get('name') or '').strip() for item in fields if str(item.get('name') or '').strip()]
    template = _load_template(schema.get('id') or '')
    flat_values = _flatten_payload(schema, payload, blank_mode=blank_mode)
    mapped = _field_name_map(field_names, template, flat_values)
    _, PdfWriter = _pdf_classes()
    writer = PdfWriter()

    pages_by_index = {}
    for field in fields:
        name = str(field.get('name') or '').strip()
        value = str(mapped.get(name) or '').strip()
        if not name or not value:
            continue
        page_index = int(field.get('page_index') or 0)
        pages_by_index.setdefault(page_index, []).append((field, value))

    for page_index, page in enumerate(reader.pages):
        if pages_by_index.get(page_index):
            overlay_buffer = BytesIO()
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)
            draw = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))
            for field, value in pages_by_index.get(page_index, []):
                _draw_xfa_value(draw, page_height, field, value)
            draw.save()
            PdfReader, _ = _pdf_classes()
            overlay_reader = PdfReader(BytesIO(overlay_buffer.getvalue()))
            page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)

    with open(target_pdf, 'wb') as handle:
        writer.write(handle)
    return {
        'mode': 'xfa_overlay',
        'mapped_count': len(mapped),
        'mapped_fields': sorted(mapped.keys()),
        'conditional_group_count': len(xfa_info.get('conditional_groups', [])),
        'template_id': template.get('template_id') or '',
    }


def _page_size_for_xfa_layout(source_pdf: str, fields: list[dict]) -> tuple[float, float]:
    try:
        reader = _reader_for_pdf(source_pdf)
        if reader.pages:
            return (float(reader.pages[0].mediabox.width), float(reader.pages[0].mediabox.height))
    except Exception:
        pass
    max_x = max((float(field.get('x') or 0) + float(field.get('w') or 0) for field in fields), default=612.0)
    max_y = max((float(field.get('y') or 0) + float(field.get('h') or 0) for field in fields), default=792.0)
    return (max(612.0, max_x + 36.0), max(792.0, max_y + 36.0))


def _xfa_field_value_lookup(schema: dict, payload: dict, blank_mode: bool, fields: list[dict]) -> tuple[dict[str, str], dict]:
    field_names = [str(item.get('name') or '').strip() for item in fields if str(item.get('name') or '').strip()]
    template = _load_template(schema.get('id') or '')
    flat_values = _flatten_payload(schema, payload, blank_mode=blank_mode)
    mapped = _field_name_map(field_names, template, flat_values)
    return mapped, template


def _draw_xfa_layout_field(draw, page_height: float, field: dict, value: str, blank_mode: bool = False) -> None:
    raw_x = float(field.get('x') or 0.0)
    raw_y = float(field.get('y') or 0.0)
    raw_w = float(field.get('w') or 120.0)
    raw_h = float(field.get('h') or 18.0)
    field_type = str(field.get('type') or 'text').strip().lower()
    label = _clean_pdf_label(field.get('label'), field.get('raw_name') or field.get('name') or 'Field')

    # Dynamic XFA coordinates are top-origin; ReportLab draws from bottom-origin.
    x = max(raw_x, 18.0)
    box_w = max(raw_w, 16.0)
    box_h = max(raw_h, 12.0)
    y = page_height - raw_y - box_h
    if y < 18:
        y = 18
    if y > page_height - 18:
        y = page_height - 32

    label_y = min(page_height - 14, y + box_h + 3)
    label_size = 5 if len(label) > 42 or box_w < 80 else 6
    draw.setFillColorRGB(0.10, 0.14, 0.18)
    draw.setFont('Helvetica-Bold', label_size)
    for index, line in enumerate(_wrap_overlay_text(label, max(box_w, 72), 16, label_size)[:2]):
        draw.drawString(x, label_y - (index * (label_size + 1)), line[:90])

    draw.setStrokeColorRGB(0.62, 0.68, 0.74)
    draw.setLineWidth(0.45)
    draw.setFillColorRGB(0.99, 1.0, 1.0)
    if field_type == 'checkbox':
        side = max(10.0, min(box_w, box_h, 16.0))
        draw.rect(x, y + max((box_h - side) / 2.0, 0), side, side, stroke=1, fill=0)
        if _truthy(value):
            draw.setFont('Helvetica-Bold', 9)
            draw.drawCentredString(x + side / 2.0, y + max((box_h - side) / 2.0, 0) + 3, 'X')
        return

    draw.rect(x, y, box_w, box_h, stroke=1, fill=0)
    text_value = str(value or '').strip()
    if not text_value:
        return
    font_size = 7 if box_h >= 16 else 6
    draw.setFillColorRGB(0.03, 0.06, 0.09)
    draw.setFont('Helvetica', font_size)
    lines = _wrap_overlay_text(text_value, box_w - 4, box_h - 2, font_size)
    baseline = y + box_h - font_size - 3
    for index, line in enumerate(lines):
        draw.drawString(x + 2, max(y + 2, baseline - (index * (font_size + 1))), line[:150])


def _draw_sectioned_checkbox(draw, x: float, y: float, label: str, value: str, blank_mode: bool = False) -> float:
    draw.setStrokeColorRGB(0.32, 0.39, 0.46)
    draw.rect(x, y - 2, 10, 10, stroke=1, fill=0)
    if _truthy(value):
        draw.setFont('Helvetica-Bold', 8)
        draw.drawCentredString(x + 5, y - 1, 'X')
    draw.setFillColorRGB(0.08, 0.12, 0.17)
    draw.setFont('Helvetica', 8)
    draw.drawString(x + 15, y, label[:88])
    return y - 16


def _draw_sectioned_text_field(
    draw,
    page_width: float,
    x: float,
    y: float,
    label: str,
    value: str,
    field_type: str,
    blank_mode: bool = False,
) -> float:
    label_width = 170
    row_width = page_width - 72
    field_height = 34 if field_type in {'textarea', 'signature'} else 18
    if len(label) > 70:
        field_height += 10

    draw.setFillColorRGB(0.08, 0.12, 0.17)
    draw.setFont('Helvetica-Bold', 7.5)
    label_lines = _wrap_overlay_text(label, label_width, 22, 7) or [label[:80]]
    for index, line in enumerate(label_lines[:2]):
        draw.drawString(x, y - (index * 8), line[:90])

    box_x = x + label_width + 8
    box_y = y - field_height + 7
    box_w = max(120, row_width - label_width - 8)
    draw.setStrokeColorRGB(0.70, 0.75, 0.80)
    draw.setFillColorRGB(1.0, 1.0, 1.0)
    draw.rect(box_x, box_y, box_w, field_height, stroke=1, fill=0)

    text_value = str(value or '').strip()
    if text_value:
        # Signature/initials canvas DataURL — draw as image inside the field box.
        img_reader = _decode_dataurl_image(text_value)
        if img_reader is not None:
            pad = 3.0
            draw.drawImage(img_reader, box_x + pad, box_y + pad, width=max(box_w - pad * 2, 10), height=max(field_height - pad * 2, 8), mask='auto', preserveAspectRatio=True, anchor='sw')
        else:
            draw.setFillColorRGB(0.03, 0.06, 0.09)
            draw.setFont('Helvetica', 8)
            max_lines = 3 if field_height >= 28 else 1
            for index, line in enumerate(_wrap_overlay_text(text_value, box_w - 8, field_height - 4, 8)[:max_lines]):
                draw.drawString(box_x + 4, box_y + field_height - 11 - (index * 9), line[:150])
    elif blank_mode:
        draw.setStrokeColorRGB(0.82, 0.86, 0.90)
        draw.line(box_x + 4, box_y + 6, box_x + box_w - 4, box_y + 6)
    return y - field_height - 7


def _write_xfa_sectioned_pdf(
    source_pdf: str,
    target_pdf: str,
    schema: dict,
    payload: dict,
    blank_mode: bool = False,
) -> dict:
    """Render XFA-only forms as a clean official-question packet.

    Several current military forms are dynamic XFA PDFs that display only the
    Adobe "Please wait" shell in browsers. Their internal coordinates are often
    flowed, repeated, or all at 0,0, so a coordinate render creates visibly
    misaligned pages. This sectioned render preserves every discovered form field
    in schema order while giving officers a printable PDF that aligns cleanly.
    """

    xfa_info = inspect_xfa_fields(source_pdf)
    fields = xfa_info.get('fields') if isinstance(xfa_info.get('fields'), list) else []
    fields = [field for field in fields if str(field.get('name') or '').strip()]
    field_names = [str(item.get('name') or '').strip() for item in fields]
    flat = _flatten_payload(schema, payload, blank_mode=blank_mode)
    mapped, template = _xfa_field_value_lookup(schema, payload, blank_mode, fields)

    width, height = letter
    left = 40
    top = height - 42
    bottom = 44
    title = str(schema.get('title') or 'MCPD Form').strip()
    c = canvas.Canvas(target_pdf, pagesize=letter)

    def start_page(page_number: int) -> float:
        c.setFillColorRGB(0.98, 0.99, 1.0)
        c.rect(0, 0, width, height, stroke=0, fill=1)
        c.setFillColorRGB(0.05, 0.09, 0.14)
        c.setFont('Helvetica-Bold', 12)
        c.drawString(left, height - 28, title[:96])
        c.setFont('Helvetica', 7)
        c.setFillColorRGB(0.38, 0.45, 0.52)
        c.drawRightString(width - left, height - 28, f'Browser-compatible official field render - Page {page_number}')
        c.setStrokeColorRGB(0.78, 0.83, 0.88)
        c.line(left, height - 36, width - left, height - 36)
        return top

    y = start_page(1)
    page_number = 1
    rendered_keys: set[str] = set()
    sections = schema.get('sections') if isinstance(schema.get('sections'), list) else []
    if not sections:
        sections = [{'title': 'Form Fields', 'fields': [
            {'name': item.get('name'), 'label': _clean_pdf_label(item.get('label'), item.get('raw_name') or item.get('name') or 'Field'), 'type': item.get('type')}
            for item in fields
        ]}]

    for section in sections:
        fields_in_section = [field for field in section.get('fields', []) or [] if str(field.get('name') or '').strip()]
        if not fields_in_section:
            continue
        if y < bottom + 38:
            c.showPage()
            page_number += 1
            y = start_page(page_number)
        section_title = str(section.get('title') or 'Form Fields').strip()
        c.setFillColorRGB(0.88, 0.92, 0.96)
        c.roundRect(left - 2, y - 7, width - (left * 2) + 4, 18, 4, stroke=0, fill=1)
        c.setFillColorRGB(0.06, 0.12, 0.18)
        c.setFont('Helvetica-Bold', 9)
        c.drawString(left + 4, y - 2, section_title[:92])
        y -= 24

        checkbox_run: list[dict] = []

        def flush_checkboxes(current_y: float) -> float:
            if not checkbox_run:
                return current_y
            x_positions = [left, left + 184, left + 368]
            col = 0
            for checkbox_field in list(checkbox_run):
                if current_y < bottom + 18:
                    c.showPage()
                    nonlocal_page_number[0] += 1
                    current_y = start_page(nonlocal_page_number[0])
                name = str(checkbox_field.get('name') or '').strip()
                label = str(checkbox_field.get('label') or name).strip().rstrip(':')
                value = flat.get(name)
                if value is None:
                    value = mapped.get(name, '')
                _draw_sectioned_checkbox(c, x_positions[col], current_y, label, str(value or ''), blank_mode=blank_mode)
                col += 1
                if col >= 3:
                    col = 0
                    current_y -= 16
            if col:
                current_y -= 16
            checkbox_run.clear()
            return current_y - 2

        nonlocal_page_number = [page_number]
        for field in fields_in_section:
            name = str(field.get('name') or '').strip()
            if not name:
                continue
            rendered_keys.add(name)
            field_type = str(field.get('type') or 'text').strip().lower()
            label = str(field.get('label') or name).strip().rstrip(':')
            if field_type == 'checkbox':
                checkbox_run.append(field)
                if len(checkbox_run) >= 6:
                    y = flush_checkboxes(y)
                    page_number = nonlocal_page_number[0]
                continue
            y = flush_checkboxes(y)
            page_number = nonlocal_page_number[0]
            if y < bottom + 42:
                c.showPage()
                page_number += 1
                y = start_page(page_number)
            value = flat.get(name)
            if value is None:
                value = mapped.get(name, '')
            y = _draw_sectioned_text_field(c, width, left, y, label, str(value or ''), field_type, blank_mode=blank_mode)
        y = flush_checkboxes(y)
        page_number = nonlocal_page_number[0]
        y -= 8

    missing_xfa_fields = [name for name in field_names if name and name not in rendered_keys]
    if missing_xfa_fields:
        if y < bottom + 42:
            c.showPage()
            page_number += 1
            y = start_page(page_number)
        c.setFillColorRGB(0.06, 0.12, 0.18)
        c.setFont('Helvetica-Bold', 9)
        c.drawString(left, y, 'Additional PDF Fields')
        y -= 18
        for name in missing_xfa_fields:
            if y < bottom + 32:
                c.showPage()
                page_number += 1
                y = start_page(page_number)
            value = mapped.get(name, flat.get(name, ''))
            y = _draw_sectioned_text_field(c, width, left, y, name, str(value or ''), 'text', blank_mode=blank_mode)

    c.save()
    used_values = {
        key: value
        for key, value in {**flat, **mapped}.items()
        if str(value or '').strip() and not str(key).startswith('label::')
    }
    return {
        'mode': 'xfa_sectioned',
        'mapped_count': len(used_values),
        'mapped_fields': sorted(used_values.keys()),
        'xfa_field_count': len(fields),
        'page_count': page_number,
        'conditional_group_count': len(xfa_info.get('conditional_groups', [])),
        'template_id': template.get('template_id') or '',
        'layout_note': 'Dynamic XFA coordinates were bypassed to avoid misaligned browser output.',
    }


def _write_xfa_layout_pdf(source_pdf: str, target_pdf: str, schema: dict, payload: dict, blank_mode: bool = False) -> dict:
    xfa_info = inspect_xfa_fields(source_pdf)
    fields = xfa_info.get('fields') if isinstance(xfa_info.get('fields'), list) else []
    fields = [field for field in fields if str(field.get('name') or '').strip()]
    if not fields:
        return _write_overlay_pdf(target_pdf, schema, payload, blank_mode=blank_mode)

    mapped, template = _xfa_field_value_lookup(schema, payload, blank_mode, fields)
    page_width, page_height = _page_size_for_xfa_layout(source_pdf, fields)
    page_count = max((int(field.get('page_index') or 0) for field in fields), default=0) + 1
    by_page: dict[int, list[dict]] = {}
    for field in fields:
        by_page.setdefault(int(field.get('page_index') or 0), []).append(field)

    title = str(schema.get('title') or 'MCPD Form').strip()
    c = canvas.Canvas(target_pdf, pagesize=(page_width, page_height))
    for page_index in range(page_count):
        if page_index:
            c.showPage()
        c.setFillColorRGB(0.95, 0.97, 0.99)
        c.rect(0, 0, page_width, page_height, stroke=0, fill=1)
        c.setFillColorRGB(0.06, 0.12, 0.18)
        c.setFont('Helvetica-Bold', 11)
        c.drawString(18, page_height - 18, title[:95])
        c.setFont('Helvetica', 7)
        c.setFillColorRGB(0.35, 0.42, 0.49)
        c.drawRightString(page_width - 18, page_height - 18, f'Compatible form render - Page {page_index + 1}')
        c.setStrokeColorRGB(0.78, 0.83, 0.88)
        c.line(18, page_height - 26, page_width - 18, page_height - 26)
        for field in sorted(by_page.get(page_index, []), key=_field_sort_key):
            name = str(field.get('name') or '').strip()
            _draw_xfa_layout_field(c, page_height, field, mapped.get(name, ''), blank_mode=blank_mode)
    c.save()
    return {
        'mode': 'xfa_layout',
        'mapped_count': len([name for name, value in mapped.items() if str(value or '').strip()]),
        'mapped_fields': sorted([name for name, value in mapped.items() if str(value or '').strip()]),
        'xfa_field_count': len(fields),
        'page_count': page_count,
        'conditional_group_count': len(xfa_info.get('conditional_groups', [])),
        'template_id': template.get('template_id') or '',
    }


def render_form_pdf(source_pdf: str | None, schema: dict, payload: dict, blank_mode: bool = False) -> tuple[str, dict]:
    fd, out_path = tempfile.mkstemp(prefix='mcpd-form-', suffix='.pdf')
    os.close(fd)
    meta: dict
    template = _load_template(schema.get('id') or '')
    has_explicit_template = bool(
        isinstance(template.get('field_map'), dict) and template.get('field_map')
        or isinstance(template.get('ui_fields'), list) and template.get('ui_fields')
    )
    if source_pdf and os.path.exists(source_pdf):
        if source_pdf_has_adobe_wait_shell(source_pdf):
            meta = _write_xfa_sectioned_pdf(source_pdf, out_path, schema, payload, blank_mode=blank_mode)
            meta['mode'] = 'xfa_sectioned_compatible'
            return out_path, meta
        try:
            field_info = inspect_pdf_fields(source_pdf)
            has_fields = bool(field_info.get('field_count'))
        except Exception:
            has_fields = False
        if has_fields:
            meta = _write_fillable_pdf(source_pdf, out_path, schema, payload, blank_mode=blank_mode)
            if meta.get('mapped_count', 0) == 0 and has_explicit_template and not blank_mode:
                meta = _write_overlay_pdf(out_path, schema, payload, blank_mode=blank_mode)
                meta['mode'] = 'overlay_template_fallback'
                meta['template_id'] = template.get('template_id') or ''
        else:
            try:
                xfa_info = inspect_xfa_fields(source_pdf)
            except Exception:
                xfa_info = {'fields': []}
            if xfa_info.get('fields'):
                meta = _write_xfa_layout_pdf(source_pdf, out_path, schema, payload, blank_mode=blank_mode)
            else:
                meta = _write_overlay_pdf(out_path, schema, payload, blank_mode=blank_mode)
    else:
        meta = _write_overlay_pdf(out_path, schema, payload, blank_mode=blank_mode)
    return out_path, meta
