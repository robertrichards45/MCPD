from app.routes import reference


def test_filter_handbook_returns_all_when_no_query():
    payload = {
        'title': 'Test',
        'version': '1',
        'sections': [
            {'id': 'a', 'title': 'Alpha', 'summary': 'First'},
            {'id': 'b', 'title': 'Bravo', 'summary': 'Second'},
        ],
    }
    result = reference._filter_handbook(payload, '')
    assert len(result['sections']) == 2


def test_filter_handbook_matches_section_content():
    payload = {
        'title': 'Test',
        'version': '1',
        'sections': [
            {'id': 'a', 'title': 'Haircut Guidance', 'summary': 'Grooming standards'},
            {'id': 'b', 'title': 'Vehicle Policy', 'summary': 'Registration requirements'},
        ],
    }
    result = reference._filter_handbook(payload, 'haircut')
    assert len(result['sections']) == 1
    assert result['sections'][0]['id'] == 'a'


def test_form_reference_for_label_matches_handbook_aliases():
    reference_index = [
        {
            'name': 'Incident Report',
            'summary': 'Primary offense narrative document.',
            'when_used': 'Use for the initial incident package.',
            'field_focus': ['Chronology'],
            'common_mistakes': [],
            'aliases': {'incident report', 'incident accident report'},
        }
    ]
    matched = reference._form_reference_for_label('Incident/Accident Report', reference_index)
    assert matched is not None
    assert matched['name'] == 'Incident Report'


def test_decorate_incident_scenario_adds_handbook_form_guidance():
    scenario = {
        'title': 'Traffic Accident',
        'description': 'Two-car accident with injuries.',
        'required_paperwork': [{'label': 'Incident Report', 'search_term': 'Incident'}],
        'officer_responsibilities': 'Secure scene. Render aid. Document vehicle positions.',
        'notes': 'Notify command if injuries are serious.',
        'slug': 'traffic-accident',
    }
    reference_index = [
        {
            'name': 'Incident Report',
            'summary': 'Primary offense narrative document.',
            'when_used': 'Use for the initial incident package.',
            'field_focus': ['Chronology', 'Witness contact info'],
            'common_mistakes': ['Missing plate numbers'],
            'aliases': {'incident report'},
        }
    ]
    decorated = reference._decorate_incident_scenario(scenario, reference_index)
    assert decorated['paperwork_count'] == 1
    assert decorated['handbook_matches'] == 1
    assert decorated['required_paperwork'][0]['handbook_summary'] == 'Primary offense narrative document.'
    assert decorated['required_paperwork'][0]['when_used'] == 'Use for the initial incident package.'
    assert decorated['required_paperwork'][0]['field_focus'] == ['Chronology', 'Witness contact info']
    assert any('Secure scene' in point for point in decorated['response_points'])
