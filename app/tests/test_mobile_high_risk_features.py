from io import BytesIO

from PIL import Image, ImageDraw
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app import create_app
from app.models import User
from app.routes import mobile
from app.services.mobile_incident_documents import (
    build_narrative_draft,
    build_voluntary_statement_draft,
    render_statement_pdf,
)


def _signature_data_url():
    buffer = BytesIO()
    image = Image.new('RGB', (96, 32), 'white')
    draw = ImageDraw.Draw(image)
    draw.line((6, 24, 28, 8, 48, 22, 72, 10, 90, 20), fill='black', width=3)
    image.save(buffer, format='PNG')
    return 'data:image/png;base64,' + __import__('base64').b64encode(buffer.getvalue()).decode('ascii')


PNG_DATA_URL = _signature_data_url()


def _logged_in_client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='Robertrichards').first() or User.query.first()
        assert user is not None
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
    return client


def _live_form_title(fragment):
    app = create_app()
    with app.app_context():
        from app.models import Form

        form = Form.query.filter(Form.title.ilike(f'%{fragment}%')).first()
        assert form is not None
        return form.title


def _standard_statement_state():
    return {
        'callType': 'domestic-disturbance',
        'incidentBasics': {
            'occurredDate': '2026-04-16',
            'occurredTime': '20:14',
            'location': 'Main Gate Lot C',
            'callSource': 'Dispatch',
            'summary': 'domestic disturbance investigation',
        },
        'facts': [
            {'id': 'what_happened', 'value': 'Officers were dispatched for a reported domestic disturbance in the parking lot.'},
            {'id': 'complainant', 'value': 'The complainant said the argument turned physical before officers arrived.'},
            {'id': 'victim', 'value': 'The victim stated she was pushed against the vehicle door.'},
            {'id': 'suspect', 'value': 'The suspect denied striking anyone and claimed he was trying to leave.'},
            {'id': 'officer_actions', 'value': 'Officers separated the parties, photographed the scene, and collected witness information.'},
            {'id': 'disposition', 'value': 'The suspect was detained for follow-up processing and the victim was given victim assistance information.'},
        ],
        'selectedForms': ['OPNAV 5580 2 Voluntary Statement'],
        'checklist': [{'label': 'Separate involved parties', 'completed': True}],
        'persons': [
            {'id': 'victim-1', 'role': 'Victim', 'name': 'Jane Doe'},
            {'id': 'suspect-1', 'role': 'Suspect', 'name': 'John Doe'},
        ],
        'statements': [],
        'narrative': '',
        'narrativeApproved': True,
    }


def _statement_payload(variant='standard'):
    return {
        'id': 'statement-1',
        'variant': variant,
        'formTitle': 'OPNAV 5580 2 Voluntary Statement' if variant == 'standard' else 'OPNAV 5580 2 Voluntary Statement Traffic',
        'speaker': 'Jane Doe',
        'speakerSsn': '123-45-6789',
        'officerName': 'Officer Richards',
        'officerBadge': '417',
        'statementDate': '2026-04-16',
        'statementTime': '20:20',
        'location': 'Main Gate Lot C',
        'statementSubject': 'domestic disturbance investigation',
        'plainLanguage': 'I saw him shove her against the vehicle. She yelled for help and stepped away before officers arrived.',
        'reviewedDraft': '',
        'formattedDraft': '',
        'trafficAnswers': {
            'q1': 'I was traveling north in the right lane when the vehicle in front stopped suddenly',
            'q2': 'About 25 miles per hour',
        },
        'initialsDataUrl': PNG_DATA_URL,
        'signatureDataUrl': PNG_DATA_URL,
        'witnessingSignatureDataUrl': PNG_DATA_URL,
    }


def _simple_pdf_bytes(label='Attachment'):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.drawString(72, 720, label)
    pdf.save()
    return buffer.getvalue()


def test_narrative_generation_uses_prose_not_section_labels():
    narrative = build_narrative_draft(_standard_statement_state())
    assert 'What happened:' not in narrative
    assert 'Complainant:' not in narrative
    assert 'Victim:' not in narrative
    assert 'On 04/16/2026 at approximately 20:14 at Main Gate Lot C' in narrative
    assert 'The complainant stated' in narrative
    assert 'The incident was concluded with the following disposition' in narrative


def test_narrative_generation_uses_person_roles_when_fact_section_missing():
    state = _standard_statement_state()
    state['facts'] = [entry for entry in state['facts'] if entry['id'] not in {'victim', 'suspect'}]
    narrative = build_narrative_draft(state)
    assert 'The identified victim was Jane Doe.' in narrative
    assert 'The identified suspect was John Doe.' in narrative


def test_voluntary_statement_generation_uses_form_language_and_traffic_answers():
    state = _standard_statement_state()
    standard = build_voluntary_statement_draft(_statement_payload('standard'), state)
    traffic = build_voluntary_statement_draft(_statement_payload('traffic'), state)

    assert 'I make this statement of my own free will' in standard
    assert 'Marine Corps Police Department, MCLB Albany, Georgia' in standard
    assert 'Q. Would you please describe the accident?' in traffic
    assert 'A. I was traveling north in the right lane when the vehicle in front stopped suddenly.' in traffic


def test_render_statement_pdf_places_initials_and_signatures_on_real_pdf():
    state = _standard_statement_state()
    statement = _statement_payload('standard')
    pdf_bytes, meta = render_statement_pdf(statement, state)
    reader = PdfReader(BytesIO(pdf_bytes))

    assert len(reader.pages) == 3
    assert meta['placement_count'] >= 4
    assert 'Signature' in meta['placed_fields']
    assert 'Signature  Badge' in meta['placed_fields']
    assert 'Initials of person making statement' in meta['placed_fields']


def test_send_packet_api_rejects_unfaithful_domestic_overlay(monkeypatch):
    client = _logged_in_client()
    state = _standard_statement_state()
    statement = _statement_payload('standard')
    statement['reviewedDraft'] = build_voluntary_statement_draft(statement, state)
    state['statements'] = [statement]

    monkeypatch.setattr(mobile, '_packet_recipient_context', lambda: ('qa@example.com', []))
    monkeypatch.setattr(
        mobile,
        '_packet_form_entries',
        lambda payload: [{
            'requested_title': 'NAVMAC 11337 MILITARY POLICE DOMESTIC VIOLENCE SIPPLEMENT REPORT AND CHECKLIST',
            'form': object(),
            'saved': object(),
            'status': 'COMPLETED',
            'status_label': 'Completed',
            'title': 'NAVMAC 11337 MILITARY POLICE DOMESTIC VIOLENCE SIPPLEMENT REPORT AND CHECKLIST',
            'preview_url': '',
        }],
    )
    monkeypatch.setattr(
        mobile,
        '_render_saved_form_attachment',
        lambda entry: {
            'filename': 'domestic.pdf',
            'content_type': 'application/pdf',
            'bytes': _simple_pdf_bytes('Domestic'),
            'meta': {'mode': 'overlay'},
        },
    )

    response = client.post('/mobile/api/incident/send-packet', json={'incident': state})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['ok'] is False
    assert any('non-faithful overlay export' in item['message'] for item in payload['errors'])


def test_send_packet_api_builds_combined_packet_pdf(monkeypatch):
    client = _logged_in_client()
    state = _standard_statement_state()
    statement = _statement_payload('standard')
    statement['reviewedDraft'] = build_voluntary_statement_draft(statement, state)
    state['statements'] = [statement]

    sent = {}

    monkeypatch.setattr(mobile, '_packet_recipient_context', lambda: ('qa@example.com', ['watch@example.com']))
    monkeypatch.setattr(
        mobile,
        '_packet_form_entries',
        lambda payload: [{
            'requested_title': 'OPNAV 5580 22Evidence Custody Document',
            'form': object(),
            'saved': object(),
            'status': 'COMPLETED',
            'status_label': 'Completed',
            'title': 'OPNAV 5580 22Evidence Custody Document',
            'preview_url': '',
        }],
    )
    monkeypatch.setattr(
        mobile,
        '_render_saved_form_attachment',
        lambda entry: {
            'filename': 'evidence.pdf',
            'content_type': 'application/pdf',
            'bytes': _simple_pdf_bytes('Evidence Attachment'),
            'meta': {'mode': 'fillable'},
        },
    )

    def fake_send(recipient, cc_list, subject, body, attachments):
        sent['recipient'] = recipient
        sent['cc_list'] = cc_list
        sent['subject'] = subject
        sent['body'] = body
        sent['attachments'] = attachments
        return True, 'sent'

    monkeypatch.setattr(mobile, '_smtp_send_packet', fake_send)

    response = client.post('/mobile/api/incident/send-packet', json={'incident': state})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['ok'] is True
    assert sent['recipient'] == 'qa@example.com'
    assert len(sent['attachments']) == 1
    assert sent['attachments'][0]['filename'] == 'mcpd-incident-packet.pdf'

    packet_reader = PdfReader(BytesIO(sent['attachments'][0]['bytes']))
    assert len(packet_reader.pages) >= 4


def test_send_packet_api_requires_narrative_approval(monkeypatch):
    client = _logged_in_client()
    state = _standard_statement_state()
    state['narrativeApproved'] = False
    state['narrative'] = build_narrative_draft(state)
    statement = _statement_payload('standard')
    statement['reviewedDraft'] = build_voluntary_statement_draft(statement, state)
    state['statements'] = [statement]

    monkeypatch.setattr(mobile, '_packet_recipient_context', lambda: ('qa@example.com', []))
    monkeypatch.setattr(
        mobile,
        '_packet_form_entries',
        lambda payload: [{
            'requested_title': 'OPNAV 5580 2 Voluntary Statement',
            'form': object(),
            'saved': object(),
            'status': 'COMPLETED',
            'status_label': 'Completed',
            'title': 'OPNAV 5580 2 Voluntary Statement',
            'preview_url': '',
        }],
    )

    response = client.post('/mobile/api/incident/send-packet', json={'incident': state})
    assert response.status_code == 400
    payload = response.get_json()
    assert any('Approve the narrative review before sending' in item['message'] for item in payload['errors'])


def test_send_packet_api_handles_live_domestic_mobile_draft(monkeypatch):
    client = _logged_in_client()
    state = _standard_statement_state()
    state['selectedForms'] = [
        _live_form_title('DOMESTIC VIOLENCE'),
        _live_form_title('Voluntary Statement'),
    ]
    statement = _statement_payload('standard')
    statement['reviewedDraft'] = build_voluntary_statement_draft(statement, state)
    state['statements'] = [statement]
    state['formDrafts'] = {
        'domesticSupplemental': {
            'form1.VicName': 'Jane Doe',
            'form1.ResponseDate': '2026-04-16',
            'form1.RespTime': '20:14',
            'form1.Reported': 'Domestic disturbance',
            'form1.Victim': 'Yes',
        }
    }

    sent = {}

    monkeypatch.setattr(mobile, '_packet_recipient_context', lambda: ('qa@example.com', []))

    def fake_send(recipient, cc_list, subject, body, attachments):
        sent['recipient'] = recipient
        sent['cc_list'] = cc_list
        sent['subject'] = subject
        sent['body'] = body
        sent['attachments'] = attachments
        return True, 'sent'

    monkeypatch.setattr(mobile, '_smtp_send_packet', fake_send)

    response = client.post('/mobile/api/incident/send-packet', json={'incident': state})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['ok'] is True
    assert sent['recipient'] == 'qa@example.com'
    assert len(sent['attachments']) == 1
    packet_reader = PdfReader(BytesIO(sent['attachments'][0]['bytes']))
    assert len(packet_reader.pages) >= 4


def test_send_packet_api_accepts_mobile_state_aliases_and_packet_email(monkeypatch):
    client = _logged_in_client()
    state = _standard_statement_state()
    domestic_title = _live_form_title('DOMESTIC VIOLENCE')
    statement_title = _live_form_title('Voluntary Statement')
    state['selectedForms'] = ['Narrative', domestic_title, statement_title]
    state['packetStatus'] = {'email': 'field.officer@example.com'}
    state['domesticSupplemental'] = {
        'form1.Reported': 'Domestic disturbance',
        'form1.Where': 'Residence',
        'form1.Location': 'Primary residence',
    }
    state['statements'] = [
        {
            'id': 'statement-legacy',
            'formTitle': statement_title,
            'personName': 'Jane Doe',
            'formattedStatement': build_voluntary_statement_draft(_statement_payload('standard'), state),
            'initials': PNG_DATA_URL,
            'signature': PNG_DATA_URL,
            'officerSignature': PNG_DATA_URL,
        }
    ]

    sent = {}

    monkeypatch.setattr(mobile, '_packet_recipient_context', lambda: ('', []))
    monkeypatch.setattr(
        mobile,
        '_render_saved_form_attachment',
        lambda entry: {
            'filename': f'{entry["title"]}.pdf',
            'content_type': 'application/pdf',
            'bytes': _simple_pdf_bytes(entry['title']),
            'meta': {'mode': 'fillable'},
        } if entry.get('source_mode') == 'mobile_domestic' else None,
    )
    monkeypatch.setattr(mobile, '_is_unfaithful_packet_render', lambda entry, attachment: False)

    def fake_send(recipient, cc_list, subject, body, attachments):
        sent['recipient'] = recipient
        sent['attachments'] = attachments
        sent['subject'] = subject
        return True, 'sent'

    monkeypatch.setattr(mobile, '_smtp_send_packet', fake_send)

    response = client.post('/mobile/api/incident/send-packet', json={'incident': state})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['ok'] is True
    assert sent['recipient'] == 'field.officer@example.com'
    assert sent['attachments'][0]['filename'] == 'mcpd-incident-packet.pdf'
