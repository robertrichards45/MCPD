import base64
import os
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .forms_pdf_renderer import _pdf_classes, render_form_pdf


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _forms_root() -> Path:
    return _repo_root() / 'data' / 'uploads' / 'forms'

def _sequential_fields(prefix: str, count: int, suffix: str = '') -> list[str]:
    return [f'{prefix}{index}{suffix}' for index in range(1, count + 1)]


TRAFFIC_STATEMENT_QUESTIONS = [
    'Would you please describe the accident?',
    'How fast were you driving when the accident occurred?',
    'Did you wear glasses or corrective lenses?',
    'Did you take any evasive actions to avoid the accident or collision?',
    'Did you experience any dizziness or fatigue while driving?',
    'Do you have any medical conditions that might have contributed to the cause of the accident?',
]


STATEMENT_FORM_CONFIGS = {
    'standard': {
        'variant': 'standard',
        'form_title': 'OPNAV 5580 2 Voluntary Statement',
        'file_name': '1772379338-18-OPNAV_5580_2_Voluntary_Statement.pdf',
        'body_capacity': 37,
        'body_line_length': 58,
        'body_pages': [
            {
                'page_number': 1,
                'title': 'Statement Page',
                'line_fields': _sequential_fields(
                    'I Name SSN  make the following free and voluntary statement to  whom I know to be a police officer with the Marine Corps Police Department MCLB Albany Georgia I make this statement of my own free will and without any threats or promises extended to me I fully understand that this statement is given concerning my knowledge of that occurred on Date  Year at approximately TimeAMPM Row',
                    23,
                ),
                'initial_field': 'Initials of person making statement',
            },
            {
                'page_number': 2,
                'title': 'Statement Continued',
                'line_fields': _sequential_fields(
                    'DEPARTMENT OF THE NAVY VOLUNTARY STATEMENT Name taken at Location on Date  Time  Statement Continued Row',
                    14,
                ),
                'initial_field': 'Initials of person making statement_2',
            },
        ],
        'signature_page': {
            'page_number': 3,
            'title': 'Sworn Signature Page',
            'initial_field': 'Initials of person making statement_3',
            'signature_field': 'Signature',
            'witness_signature_field': 'Signature  Badge',
        },
    },
    'traffic': {
        'variant': 'traffic',
        'form_title': 'OPNAV 5580 2 Voluntary Statement Traffic',
        'file_name': '1772379338-19-OPNAV_5580_2_Voluntary_Statement_Traffic.pdf',
        'body_capacity': 69,
        'body_line_length': 54,
        'interview_answer_fields': [
            'A', 'A_2', 'A_3', 'A_4', 'A_5', 'A_6', 'A_7', 'A_8', 'A_9', 'A_10',
            'A_11', 'A_12', 'A_13', 'A_14', 'A_15', 'A_16', 'A_17', 'A_18',
            'ARow1', 'ARow2', 'ARow3', 'ARow4', 'ARow5', 'ARow6', 'ARow7', 'ARow8',
            'ARow9', 'ARow10', 'ARow11', 'ARow12', 'ARow13',
        ],
        'body_pages': [
            {
                'page_number': 1,
                'title': 'Traffic Interview Page',
                'line_fields': [
                    'A', 'A_2', 'A_3', 'A_4', 'A_5', 'A_6', 'A_7', 'A_8', 'A_9', 'A_10',
                    'A_11', 'A_12', 'A_13', 'A_14', 'A_15', 'A_16', 'A_17', 'A_18',
                    'ARow1', 'ARow2', 'ARow3', 'ARow4', 'ARow5', 'ARow6', 'ARow7', 'ARow8',
                    'ARow9', 'ARow10', 'ARow11', 'ARow12', 'ARow13',
                ],
                'initial_field': 'Initials of person making statement',
            },
            {
                'page_number': 2,
                'title': 'Statement Continued',
                'line_fields': _sequential_fields(
                    'DEPARTMENT OF THE NAVY VOLUNTARY STATEMENT Name taken at Location on Date  Time  Statement Continued Row',
                    24,
                ),
                'initial_field': 'Initials of person making statement_2',
            },
            {
                'page_number': 3,
                'title': 'Statement Continued',
                'line_fields': _sequential_fields(
                    'DEPARTMENT OF THE NAVY VOLUNTARY STATEMENT Name taken at Location on Date  Time  Statement Continued Row',
                    13,
                    '_2',
                ),
                'initial_field': 'Initials of person making statement_3',
            },
        ],
        'signature_page': {
            'page_number': 4,
            'title': 'Sworn Signature Page',
            'initial_field': 'Initials of person making statement_4',
            'signature_field': 'Signature',
            'witness_signature_field': 'Signature  Badge',
        },
    },
}


def _statement_config(variant: str | None) -> dict:
    return STATEMENT_FORM_CONFIGS.get(str(variant or 'standard').strip().lower(), STATEMENT_FORM_CONFIGS['standard'])


def _clean_whitespace(value) -> str:
    return ' '.join(str(value or '').replace('\r', '\n').replace('\n', ' ').split()).strip()


def _ensure_terminal_punctuation(value: str) -> str:
    text = _clean_whitespace(value)
    if not text:
        return ''
    return text if text[-1] in '.!?' else f'{text}.'


def _format_date_words(value: str) -> str:
    raw = str(value or '').strip()
    parts = raw.split('-')
    if len(parts) == 3:
        return f'{parts[1]}/{parts[2]}/{parts[0]}'
    return raw


def _call_type_label(value: str) -> str:
    return ' '.join(str(value or '').replace('-', ' ').split()).strip().title()


def _clean_statement_sentences(value: str) -> list[str]:
    text = str(value or '')
    chunks = []
    current = ''
    for char in text:
        current += char
        if char in '.!?':
            sentence = _clean_whitespace(current)
            if sentence:
                chunks.append(_ensure_terminal_punctuation(sentence))
            current = ''
    trailing = _clean_whitespace(current)
    if trailing:
        chunks.append(_ensure_terminal_punctuation(trailing))
    return chunks


def _fact_map(state: dict) -> dict:
    facts = state.get('facts') if isinstance(state.get('facts'), list) else []
    mapped = {}
    for entry in facts:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get('id') or '').strip()
        value = _clean_whitespace(entry.get('value') or '')
        if key and value:
            mapped[key] = value
    return mapped


def _person_by_role(state: dict, role_name: str) -> dict:
    people = state.get('persons') if isinstance(state.get('persons'), list) else []
    target = str(role_name or '').strip().lower()
    for item in people:
        if not isinstance(item, dict):
            continue
        if str(item.get('role') or '').strip().lower() == target:
            return item
    return {}


def _prefixed_sentence(prefix: str, text: str) -> str:
    cleaned = _clean_whitespace(text)
    if not cleaned:
        return ''
    if cleaned.lower().startswith(prefix.lower()):
        return _ensure_terminal_punctuation(cleaned)
    return _ensure_terminal_punctuation(f'{prefix} {cleaned}')


def _statement_text(statement: dict) -> str:
    return _clean_whitespace(
        statement.get('reviewedDraft')
        or statement.get('formattedDraft')
        or statement.get('formattedStatement')
        or statement.get('reviewedStatement')
        or ''
    )


def _statement_initials(statement: dict) -> str:
    return str(statement.get('initialsDataUrl') or statement.get('initials') or '').strip()


def _statement_signature(statement: dict) -> str:
    return str(statement.get('signatureDataUrl') or statement.get('signature') or '').strip()


def _statement_witness_signature(statement: dict) -> str:
    return str(
        statement.get('witnessingSignatureDataUrl')
        or statement.get('officerSignature')
        or statement.get('witnessSignature')
        or ''
    ).strip()


def build_narrative_draft(state: dict) -> str:
    basics = state.get('incidentBasics') if isinstance(state.get('incidentBasics'), dict) else {}
    fact_map = _fact_map(state)
    victim = _person_by_role(state, 'Victim')
    suspect = _person_by_role(state, 'Suspect')
    parts = []
    opening = []
    if basics.get('occurredDate'):
        opening.append(f'On {_format_date_words(basics.get("occurredDate"))}')
    if basics.get('occurredTime'):
        opening.append(f'at approximately {basics.get("occurredTime")}')
    if basics.get('location'):
        opening.append(f'at {_clean_whitespace(basics.get("location"))}')
    summary = _clean_whitespace(basics.get('summary') or '') or (_call_type_label(state.get('callType') or '') and f'a {_call_type_label(state.get("callType") or "").lower()} call') or 'the reported incident'
    if opening or summary:
        lead = ' '.join(opening).strip()
        if lead:
            parts.append(_ensure_terminal_punctuation(f'{lead}, MCPD responded regarding {summary}'))
        else:
            parts.append(_ensure_terminal_punctuation(f'MCPD responded regarding {summary}'))
    if fact_map.get('what_happened'):
        parts.append(_ensure_terminal_punctuation(fact_map['what_happened']))
    if fact_map.get('complainant'):
        parts.append(_prefixed_sentence('The complainant stated', fact_map['complainant']))
    if fact_map.get('victim'):
        parts.append(_prefixed_sentence('The victim stated', fact_map['victim']))
    elif str(victim.get('name') or '').strip():
        parts.append(_ensure_terminal_punctuation(f'The identified victim was {_clean_whitespace(victim.get("name"))}'))
    if fact_map.get('suspect'):
        parts.append(_prefixed_sentence('The suspect stated', fact_map['suspect']))
    elif str(suspect.get('name') or '').strip():
        parts.append(_ensure_terminal_punctuation(f'The identified suspect was {_clean_whitespace(suspect.get("name"))}'))
    if fact_map.get('officer_actions'):
        parts.append(_prefixed_sentence('Officers took the following actions', fact_map['officer_actions']))
    if fact_map.get('disposition'):
        parts.append(_prefixed_sentence('The incident was concluded with the following disposition', fact_map['disposition']))
    return '\n\n'.join([part for part in parts if part]).strip()


def infer_statement_subject(statement: dict, incident_state: dict) -> str:
    explicit = _clean_whitespace(statement.get('statementSubject') or '')
    if explicit:
        return explicit
    basics = incident_state.get('incidentBasics') if isinstance(incident_state.get('incidentBasics'), dict) else {}
    return _clean_whitespace(basics.get('summary') or '') or _call_type_label(incident_state.get('callType') or '') or 'the incident'


def build_voluntary_statement_draft(statement: dict, incident_state: dict) -> str:
    basics = incident_state.get('incidentBasics') if isinstance(incident_state.get('incidentBasics'), dict) else {}
    date_text = _format_date_words(statement.get('statementDate') or basics.get('occurredDate') or '')
    time_text = str(statement.get('statementTime') or basics.get('occurredTime') or '').strip()
    location_text = _clean_whitespace(statement.get('location') or basics.get('location') or '')
    subject = infer_statement_subject(statement, incident_state)
    speaker = _clean_whitespace(statement.get('speaker') or statement.get('personName') or '') or 'Unknown Declarant'
    ssn = _clean_whitespace(statement.get('speakerSsn') or '')
    officer_name = _clean_whitespace(statement.get('officerName') or '') or 'the undersigned officer'
    officer_badge = _clean_whitespace(statement.get('officerBadge') or '')
    officer_label = f'{officer_name}, badge {officer_badge}' if officer_badge else officer_name
    incident_subject = 'a traffic accident' if str(statement.get('variant') or '').strip() == 'traffic' else subject
    lead = [
        f'I, {speaker}{f", SSN {ssn}," if ssn else ","} make the following free and voluntary statement to {officer_label}, whom I know to be a police officer with the Marine Corps Police Department, MCLB Albany, Georgia.',
        'I make this statement of my own free will and without any threats or promises extended to me.',
        _ensure_terminal_punctuation(
            ' '.join(
                part for part in [
                    f'I fully understand that this statement is given concerning my knowledge of {incident_subject}',
                    f'that occurred on {date_text}' if date_text else '',
                    f'at approximately {time_text}' if time_text else '',
                    f'at {location_text}' if location_text else '',
                ] if part
            )
        ),
    ]
    body = ' '.join(_clean_statement_sentences(statement.get('plainLanguage') or '')).strip()
    if str(statement.get('variant') or '').strip() == 'traffic':
        answers = statement.get('trafficAnswers') if isinstance(statement.get('trafficAnswers'), dict) else {}
        body = '\n'.join(
            [
                f'Q. {question} A. {_ensure_terminal_punctuation(_clean_whitespace(answers.get(f"q{index}") or ""))}'
                for index, question in enumerate(TRAFFIC_STATEMENT_QUESTIONS, start=1)
                if _clean_whitespace(answers.get(f'q{index}') or '')
            ]
        ).strip()
    return '\n\n'.join([part for part in [' '.join([value for value in lead if value]).strip(), body] if part]).strip()


def wrap_statement_lines(value: str, max_lines: int, max_chars: int) -> list[str]:
    source = _clean_whitespace(value)
    words = source.split(' ') if source else []
    lines = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if current and len(candidate) > max_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:max_lines]


def statement_preview_pages(statement: dict, incident_state: dict) -> dict:
    config = _statement_config(statement.get('variant'))
    draft = build_voluntary_statement_draft(statement, incident_state)
    wrapped = wrap_statement_lines(draft, config['body_capacity'], config['body_line_length'])
    pages = []
    cursor = 0
    for page in config['body_pages']:
        lines = wrapped[cursor:cursor + len(page['line_fields'])]
        cursor += len(page['line_fields'])
        pages.append({
            'page_number': page['page_number'],
            'title': page['title'],
            'line_fields': page['line_fields'],
            'lines': lines,
            'initial_field': page['initial_field'],
            'used': bool(lines) or (page['page_number'] == 1 and not wrapped),
        })
    pages.append({
        'page_number': config['signature_page']['page_number'],
        'title': config['signature_page']['title'],
        'line_fields': [],
        'lines': [],
        'initial_field': config['signature_page']['initial_field'],
        'signature_field': config['signature_page']['signature_field'],
        'witness_signature_field': config['signature_page']['witness_signature_field'],
        'used': True,
    })
    return {'config': config, 'draft': draft, 'pages': pages, 'overflow': len(wrapped) > config['body_capacity']}


def _statement_header_fields(statement: dict, incident_state: dict) -> dict[str, str]:
    config = _statement_config(statement.get('variant'))
    basics = incident_state.get('incidentBasics') if isinstance(incident_state.get('incidentBasics'), dict) else {}
    speaker = _clean_whitespace(statement.get('speaker') or '')
    ssn = _clean_whitespace(statement.get('speakerSsn') or '')
    location_text = _clean_whitespace(statement.get('location') or basics.get('location') or '')
    date_text = _format_date_words(statement.get('statementDate') or basics.get('occurredDate') or '')
    time_text = str(statement.get('statementTime') or basics.get('occurredTime') or '').strip()
    date_time = ' '.join([part for part in [date_text, time_text] if part]).strip()
    values = {
        'I Name': speaker,
        'SSN': ssn,
        '1 PLACE': location_text,
        '2 DATE': date_text,
        'at approximately TimeAMPM': time_text,
        'Date  Time': date_time,
        'Name': speaker,
        'Name_2': speaker,
        'taken at Location': location_text,
        'Location  Time': ' '.join([part for part in [location_text, time_text] if part]).strip(),
        'on Date  Time': date_time,
        'on Date  Time_2': date_time,
        'day of': date_text.split('/')[1] if '/' in date_text else '',
    }
    if config['variant'] == 'traffic':
        values.update({
            'Name_3': speaker,
            'Time': time_text,
            'taken at Location_2': location_text,
            'taken at Location_3': location_text,
            'on Date  Time_3': date_time,
        })
    return {key: value for key, value in values.items() if value}


def _statement_schema(config: dict, values: dict[str, str]) -> dict:
    return {
        'id': f'mobile_statement_{config["variant"]}_packet',
        'title': config['form_title'],
        'sections': [{'title': 'Statement Fields', 'fields': [{'name': key, 'label': key, 'type': 'text'} for key in values.keys()]}],
        'show_role_entry': False,
        'show_notes': False,
    }


def _render_statement_fillable_pdf(statement: dict, incident_state: dict) -> tuple[bytes, dict]:
    preview = statement_preview_pages(statement, incident_state)
    config = preview['config']
    values = _statement_header_fields(statement, incident_state)
    for page in preview['pages']:
        for index, line in enumerate(page.get('lines') or []):
            values[page['line_fields'][index]] = line
    schema = _statement_schema(config, values)
    payload = {'schema_id': schema['id'], 'values': values, 'role_entries': [], 'notes': ''}
    source_pdf = _forms_root() / config['file_name']
    rendered_path, meta = render_form_pdf(str(source_pdf), schema, payload, blank_mode=False)
    try:
        pdf_bytes = Path(rendered_path).read_bytes()
    finally:
        try:
            os.remove(rendered_path)
        except Exception:
            pass
    meta['preview'] = preview
    return pdf_bytes, meta


def _decode_data_url_image(data_url: str) -> bytes:
    raw = str(data_url or '').strip()
    if not raw:
        return b''
    if ',' not in raw:
        return base64.b64decode(raw)
    return base64.b64decode(raw.split(',', 1)[1])


def _field_rects_for_pdf(pdf_bytes: bytes, field_names: list[str]) -> dict[str, dict]:
    PdfReader, _PdfWriter = _pdf_classes()
    reader = PdfReader(BytesIO(pdf_bytes))
    wanted = set(field_names)
    rects = {}
    for page_index, page in enumerate(reader.pages):
        annots = page.get('/Annots')
        annots = annots.get_object() if hasattr(annots, 'get_object') else annots
        for annot_ref in annots or []:
            annot = annot_ref.get_object() if hasattr(annot_ref, 'get_object') else annot_ref
            field_name = str(annot.get('/T') or '').strip()
            if field_name not in wanted:
                continue
            rect = annot.get('/Rect')
            if rect and len(rect) == 4:
                rects[field_name] = {'page_index': page_index, 'rect': [float(item) for item in rect]}
    return rects


def _signature_placements(statement: dict, preview: dict) -> list[dict]:
    placements = []
    initials_data = _statement_initials(statement)
    signature_data = _statement_signature(statement)
    witness_data = _statement_witness_signature(statement)
    for page in preview['pages']:
        if page.get('used') and initials_data and page.get('initial_field'):
            placements.append({'field_name': page['initial_field'], 'kind': 'initials', 'data': initials_data})
    signature_page = preview['pages'][-1]
    if signature_data:
        placements.append({'field_name': signature_page['signature_field'], 'kind': 'signature', 'data': signature_data})
    if witness_data:
        placements.append({'field_name': signature_page['witness_signature_field'], 'kind': 'witness_signature', 'data': witness_data})
    return placements


def _overlay_signature_images(pdf_bytes: bytes, placements: list[dict]) -> tuple[bytes, dict]:
    if not placements:
        return pdf_bytes, {'placement_count': 0, 'placed_fields': []}
    rect_lookup = _field_rects_for_pdf(pdf_bytes, [item['field_name'] for item in placements])
    PdfReader, PdfWriter = _pdf_classes()
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    by_page = {}
    for placement in placements:
        rect_entry = rect_lookup.get(placement['field_name'])
        if not rect_entry:
            continue
        by_page.setdefault(rect_entry['page_index'], []).append({
            'field_name': placement['field_name'],
            'rect': rect_entry['rect'],
            'image_bytes': _decode_data_url_image(placement['data']),
        })
    placed_fields = []
    for page_index, page in enumerate(reader.pages):
        if by_page.get(page_index):
            overlay_buffer = BytesIO()
            draw = canvas.Canvas(overlay_buffer, pagesize=(float(page.mediabox.width), float(page.mediabox.height)))
            for item in by_page[page_index]:
                if not item['image_bytes']:
                    continue
                x0, y0, x1, y1 = item['rect']
                draw.drawImage(
                    ImageReader(BytesIO(item['image_bytes'])),
                    x0 + 2,
                    y0 + 2,
                    max((x1 - x0) - 4, 1),
                    max((y1 - y0) - 4, 1),
                    preserveAspectRatio=True,
                    mask='auto',
                )
                placed_fields.append(item['field_name'])
            draw.save()
            overlay_reader = PdfReader(BytesIO(overlay_buffer.getvalue()))
            page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)
    out = BytesIO()
    writer.write(out)
    return out.getvalue(), {'placement_count': len(placed_fields), 'placed_fields': placed_fields}


def render_statement_pdf(statement: dict, incident_state: dict) -> tuple[bytes, dict]:
    pdf_bytes, meta = _render_statement_fillable_pdf(statement, incident_state)
    preview = meta['preview']
    stamped_bytes, stamp_meta = _overlay_signature_images(pdf_bytes, _signature_placements(statement, preview))
    return stamped_bytes, {
        'mode': meta.get('mode'),
        'mapped_count': meta.get('mapped_count', 0),
        'truncations': meta.get('truncations', []),
        'placement_count': stamp_meta['placement_count'],
        'placed_fields': stamp_meta['placed_fields'],
        'used_page_count': sum(1 for page in preview['pages'] if page.get('used')),
        'overflow': bool(preview.get('overflow')),
    }


def _wrap_pdf_text(value: str, max_chars: int) -> list[str]:
    text = _clean_whitespace(value)
    words = text.split(' ') if text else []
    lines = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if current and len(candidate) > max_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _summary_pdf_bytes(state: dict, form_entries: list[dict]) -> bytes:
    packet = BytesIO()
    pdf = canvas.Canvas(packet, pagesize=letter)
    width, height = letter
    text = pdf.beginText(42, height - 48)
    text.setFont('Helvetica-Bold', 15)
    text.textLine('MCPD Mobile Incident Packet')
    text.textLine('')
    text.setFont('Helvetica', 10)
    basics = state.get('incidentBasics') if isinstance(state.get('incidentBasics'), dict) else {}
    statements = state.get('statements') if isinstance(state.get('statements'), list) else []
    sections = [
        ('Incident Basics', [
            f'Call Type: {_call_type_label(state.get("callType") or "")}',
            f'Date: {_format_date_words(basics.get("occurredDate") or "")}',
            f'Time: {basics.get("occurredTime") or ""}',
            f'Location: {basics.get("location") or ""}',
            f'Call Source: {basics.get("callSource") or ""}',
            f'Summary: {basics.get("summary") or ""}',
        ]),
        ('Narrative', _wrap_pdf_text(build_narrative_draft(state) or 'No narrative captured.', 92)),
        ('Selected Forms', [f'{entry["title"]} ({entry["status_label"]})' for entry in form_entries] or ['No forms selected.']),
        ('Statements', [f'{item.get("formTitle") or "Voluntary Statement"} - {item.get("speaker") or "Unknown declarant"}' for item in statements] or ['No statements captured.']),
    ]
    for title, lines in sections:
        text.setFont('Helvetica-Bold', 11)
        text.textLine(title)
        text.setFont('Helvetica', 10)
        for line in lines:
            for wrapped in _wrap_pdf_text(line, 95) or ['']:
                if text.getY() < 54:
                    pdf.drawText(text)
                    pdf.showPage()
                    text = pdf.beginText(42, height - 48)
                    text.setFont('Helvetica', 10)
                text.textLine(wrapped)
        text.textLine('')
    pdf.drawText(text)
    pdf.save()
    return packet.getvalue()


def build_packet_pdf(state: dict, form_entries: list[dict], rendered_form_attachments: list[dict]) -> tuple[bytes, dict]:
    PdfReader, PdfWriter = _pdf_classes()
    writer = PdfWriter()
    page_count = 0
    for source_bytes in [_summary_pdf_bytes(state, form_entries)] + [item['bytes'] for item in rendered_form_attachments]:
        reader = PdfReader(BytesIO(source_bytes))
        for page in reader.pages:
            writer.add_page(page)
            page_count += 1
    statement_meta = []
    for statement in state.get('statements') if isinstance(state.get('statements'), list) else []:
        statement_bytes, meta = render_statement_pdf(statement, state)
        statement_meta.append(meta)
        reader = PdfReader(BytesIO(statement_bytes))
        for page in reader.pages:
            writer.add_page(page)
            page_count += 1
    output = BytesIO()
    writer.write(output)
    return output.getvalue(), {'page_count': page_count, 'statement_meta': statement_meta}
