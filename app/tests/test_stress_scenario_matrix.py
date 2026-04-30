from itertools import product
from io import BytesIO

from PIL import Image, ImageDraw
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app import create_app
from app.extensions import db
from app.models import Form, User
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


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def _simple_pdf_bytes(label='Attachment'):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.drawString(72, 720, label)
    pdf.save()
    return buffer.getvalue()


def _logged_in_client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
        assert user is not None
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
    return client


def _live_form_title(fragment):
    app = create_app()
    try:
        with app.app_context():
            form = Form.query.filter(Form.title.ilike(f'%{fragment}%')).first()
            assert form is not None
            return form.title
    finally:
        _dispose_app(app)


def _base_incident_state(call_type='domestic-disturbance'):
    return {
        'callType': call_type,
        'incidentBasics': {
            'occurredDate': '2026-04-24',
            'occurredTime': '21:14',
            'location': '123 Example St, Quantico, VA',
            'callSource': 'Dispatch',
            'summary': f'{call_type.replace("-", " ")} investigation',
            'dispatchTime': '21:10',
            'arrivalTime': '21:14',
            'reportingOfficer': 'R. Richards',
        },
        'timeline': [
            {'time': '21:10', 'label': 'Dispatch'},
            {'time': '21:14', 'label': 'Arrival'},
        ],
        'persons': [
            {
                'id': 'victim-1',
                'role': 'Victim',
                'name': 'Jamie Victim',
                'dob': '1993-04-02',
                'address': '123 Example St, Quantico, VA',
                'phone': '555-111-2222',
                'idNumber': 'V1234567',
                'state': 'VA',
                'descriptors': 'No visible impairment',
                'source': 'manual',
            },
            {
                'id': 'suspect-1',
                'role': 'Suspect',
                'name': 'Sam Suspect',
                'dob': '1990-08-12',
                'address': '123 Example St, Quantico, VA',
                'phone': '555-333-4444',
                'idNumber': 'S7654321',
                'state': 'VA',
                'descriptors': 'Smell of alcohol',
                'source': 'manual',
            },
        ],
        'statutes': ['Article 128', 'Domestic Disturbance'],
        'checklist': [{'label': 'Scene secured', 'completed': True}],
        'facts': [
            {'id': 'what_happened', 'value': 'Victim reported suspect pushed victim into a wall during a verbal argument in the kitchen.'},
            {'id': 'complainant', 'value': 'Dispatch advised neighbors heard yelling and banging inside the residence.'},
            {'id': 'victim', 'value': 'Victim stated suspect had been drinking and became aggressive after an argument over finances.'},
            {'id': 'suspect', 'value': 'Suspect admitted there was an argument but denied intentionally assaulting the victim.'},
            {'id': 'officer_actions', 'value': 'Officers separated both parties, photographed the scene, and documented redness to the victim arm.'},
            {'id': 'disposition', 'value': 'Suspect was apprehended and transported for further processing.'},
        ],
        'selectedForms': [],
        'statements': [],
        'formDrafts': {},
        'packetStatus': 'draft',
        'narrative': '',
        'narrativeApproved': True,
    }


def _statement_shape(kind, form_title, variant='standard'):
    base = {
        'id': f'statement-{kind}',
        'variant': variant,
        'formTitle': form_title,
        'speaker': 'Jamie Victim',
        'personName': 'Jamie Victim',
        'statementDate': '2026-04-24',
        'statementTime': '21:20',
        'location': '123 Example St, Quantico, VA',
        'statementSubject': 'domestic disturbance investigation',
        'plainLanguage': 'Sam pushed me into the wall during the argument and I was scared.',
        'officerName': 'Officer Richards',
        'officerBadge': '417',
    }
    if kind == 'reviewed':
        base.update({
            'reviewedDraft': 'Reviewed draft text.',
            'initialsDataUrl': PNG_DATA_URL,
            'signatureDataUrl': PNG_DATA_URL,
            'witnessingSignatureDataUrl': PNG_DATA_URL,
        })
    elif kind == 'formatted':
        base.update({
            'formattedDraft': 'Formatted draft text.',
            'initialsDataUrl': PNG_DATA_URL,
            'signatureDataUrl': PNG_DATA_URL,
            'witnessingSignatureDataUrl': PNG_DATA_URL,
        })
    elif kind == 'legacy':
        base.update({
            'formattedStatement': 'Legacy formatted statement text.',
            'initials': PNG_DATA_URL,
            'signature': PNG_DATA_URL,
            'officerSignature': PNG_DATA_URL,
        })
    elif kind == 'reviewed_statement':
        base.update({
            'reviewedStatement': 'Legacy reviewed statement text.',
            'initials': PNG_DATA_URL,
            'signature': PNG_DATA_URL,
            'officerSignature': PNG_DATA_URL,
        })
    else:
        raise AssertionError(f'Unsupported statement shape: {kind}')
    return base


def test_mobile_packet_stress_matrix_500_plus(monkeypatch):
    client = _logged_in_client()
    domestic_title = _live_form_title('DOMESTIC VIOLENCE')
    standard_statement_title = _live_form_title('Voluntary Statement')
    traffic_statement_title = _live_form_title('Voluntary Statement Traffic')

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
    monkeypatch.setattr(mobile, '_smtp_send_packet', lambda recipient, cc_list, subject, body, attachments: (True, 'sent'))

    call_types = ['domestic-disturbance', 'traffic-accident', 'suspicious-person']
    narrative_modes = ['explicit', 'generated']
    recipient_modes = ['packet_status', 'profile_context']
    statement_modes = ['reviewed', 'formatted', 'legacy', 'reviewed_statement']
    domestic_modes = ['form_drafts', 'legacy_domestic', 'both', 'none']
    domestic_selections = [True, False]
    statement_titles = [
        (standard_statement_title, 'standard'),
        (traffic_statement_title, 'traffic'),
    ]

    total = 0
    for call_type, narrative_mode, recipient_mode, statement_mode, domestic_mode, include_domestic, statement_variant in product(
        call_types,
        narrative_modes,
        recipient_modes,
        statement_modes,
        domestic_modes,
        domestic_selections,
        statement_titles,
    ):
        statement_title, variant = statement_variant
        state = _base_incident_state(call_type)
        if narrative_mode == 'explicit':
            state['narrative'] = 'Responding officers arrived and investigated the reported incident.'
        else:
            state['narrative'] = ''
        state['narrativeApproved'] = True
        state['selectedForms'] = ['Narrative', statement_title]
        if include_domestic:
            state['selectedForms'].append(domestic_title)

        state['statements'] = [_statement_shape(statement_mode, statement_title, variant=variant)]
        if recipient_mode == 'packet_status':
            state['packetStatus'] = {'email': 'field.officer@example.com'}
        else:
            state['packetStatus'] = 'draft'
            monkeypatch.setattr(mobile, '_packet_recipient_context', lambda: ('profile.officer@example.com', []))

        domestic_payload = {
            'form1.Reported': 'Domestic disturbance',
            'form1.Where': 'Residence',
            'form1.Location': 'Primary residence',
        }
        if domestic_mode == 'form_drafts':
            state['formDrafts'] = {'domesticSupplemental': dict(domestic_payload)}
        elif domestic_mode == 'legacy_domestic':
            state['domesticSupplemental'] = dict(domestic_payload)
        elif domestic_mode == 'both':
            state['formDrafts'] = {'domesticSupplemental': dict(domestic_payload)}
            state['domesticSupplemental'] = dict(domestic_payload)

        response = client.post('/mobile/api/incident/send-packet', json={'incident': state})
        try:
            payload = response.get_json()
            total += 1
            assert response.status_code == 200, (total, call_type, narrative_mode, recipient_mode, statement_mode, domestic_mode, include_domestic, payload)
            assert payload['ok'] is True
        finally:
            response.close()

    assert total >= 500
    _dispose_app(client.application)


def test_document_generation_stress_matrix_500_plus():
    standard_title = 'OPNAV 5580 2 Voluntary Statement'
    traffic_title = 'OPNAV 5580 2 Voluntary Statement Traffic'
    call_types = ['domestic-disturbance', 'traffic-accident', 'suspicious-person', 'theft']
    fact_variants = ['full', 'no_victim', 'no_suspect', 'minimal']
    statement_variants = ['reviewed', 'formatted', 'legacy', 'reviewed_statement']
    traffic_variants = [False, True]
    summary_variants = ['residence disturbance', 'main gate traffic incident', 'suspicious contact investigation', 'property theft complaint']

    total = 0
    pdf_renders = 0
    for call_type, fact_variant, statement_mode, is_traffic, summary in product(
        call_types,
        fact_variants,
        statement_variants,
        traffic_variants,
        summary_variants,
    ):
        state = _base_incident_state(call_type)
        state['incidentBasics']['summary'] = summary
        if fact_variant == 'no_victim':
            state['facts'] = [item for item in state['facts'] if item['id'] != 'victim']
        elif fact_variant == 'no_suspect':
            state['facts'] = [item for item in state['facts'] if item['id'] != 'suspect']
        elif fact_variant == 'minimal':
            state['facts'] = [item for item in state['facts'] if item['id'] in {'what_happened', 'officer_actions'}]

        narrative = build_narrative_draft(state)
        assert 'What happened:' not in narrative
        assert 'Victim:' not in narrative
        assert 'Suspect:' not in narrative
        assert narrative.strip()

        form_title = traffic_title if is_traffic else standard_title
        variant = 'traffic' if is_traffic else 'standard'
        statement = _statement_shape(statement_mode, form_title, variant=variant)
        statement['formattedStatement'] = build_voluntary_statement_draft(statement, state)
        draft = build_voluntary_statement_draft(statement, state)
        assert 'Marine Corps Police Department' in draft
        assert draft.strip()

        if total % 10 == 0:
            pdf_bytes, meta = render_statement_pdf(statement, state)
            reader = PdfReader(BytesIO(pdf_bytes))
            assert len(reader.pages) >= 3
            assert meta['placement_count'] >= 3
            pdf_renders += 1
        total += 1

    assert total >= 500
    assert pdf_renders >= 50


def test_route_smoke_stress_matrix_500_plus():
    app = create_app()
    app.config['TESTING'] = True
    routes = [
        '/dashboard',
        '/forms',
        '/forms/saved',
        '/reports',
        '/incident-paperwork-guide',
        '/legal/search',
        '/orders/reference',
        '/rfi',
        '/truck-gate',
        '/mobile/home',
        '/mobile/incident/start',
        '/mobile/incident/persons',
        '/mobile/incident/packet-review',
        '/mobile/incident/send-packet',
    ]
    query_sets = [
        '',
        '?q=domestic',
        '?q=traffic',
        '?q=leave+policy',
        '?status=ACTIVE',
        '?status=all',
        '?category=Operations',
        '?tab=summary',
        '?view=mobile',
        '?filename=missing-template.pdf',
        '?date=2026-04-24',
        '?date=2026-04-23',
        '?sort=updated',
        '?sort=alpha',
        '?page=1',
        '?page=2',
        '?filter=open',
        '?filter=closed',
        '?mode=quick',
        '?mode=full',
        '?call=domestic-disturbance',
        '?call=traffic-accident',
        '?search=suspect',
        '?search=victim',
        '?search=statement',
        '?search=orders',
        '?search=forms',
        '?search=truck',
        '?search=armory',
        '?search=inspection',
        '?search=gate',
        '?search=handoff',
        '?query=domestic',
        '?query=vehicle',
        '?query=law',
        '?query=policy',
        '?query=checklist',
        '?query=narrative',
        '?query=packet',
        '?query=reference',
    ]

    total = 0
    try:
        with app.app_context():
            user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
            assert user is not None
            client = app.test_client()
            with client.session_transaction() as session:
                session['_user_id'] = str(user.id)
                session['_fresh'] = True
            for route in routes:
                for query in query_sets:
                    response = client.get(f'{route}{query}', follow_redirects=False)
                    try:
                        total += 1
                        assert response.status_code in {200, 302, 303, 403, 404}, (route, query, response.status_code)
                        assert response.status_code != 500, (route, query, response.status_code)
                    finally:
                        response.close()
    finally:
        _dispose_app(app)

    assert total >= 500
