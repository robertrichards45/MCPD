from app import create_app
from app.simulator.report_consistency import review_training_narrative


def _testing_app():
    app = create_app()
    app.config['TESTING'] = True
    return app


def test_short_narrative_gets_advisory_completeness_cue_without_ai():
    app = _testing_app()
    state = {
        'scenario_id': 'S004',
        'world': {
            'known_information': [],
            'evidence': {},
            'field_notes': [],
            'timeline': [],
        },
        'dialogue': [],
        'training_package': {'submissions': []},
    }
    with app.app_context():
        result = review_training_narrative(state, 'Subject was contacted and the call was completed.')

    assert result['mode'] == 'deterministic'
    assert result['suggestions']
    assert any(item['category'] == 'completeness' for item in result['suggestions'])
    assert all(set(item) == {'category', 'issue', 'evidence', 'confidence'} for item in result['suggestions'])


def test_claimed_unobtained_evidence_is_flagged_for_human_review():
    app = _testing_app()
    state = {
        'scenario_id': 'S004',
        'world': {
            'known_information': [],
            'evidence': {
                'retail_video': {
                    'label': 'Retail surveillance video',
                    'status': 'hidden',
                    'source': 'retail camera system',
                    'description': 'Video exists but was never discovered or preserved.',
                }
            },
            'field_notes': [],
            'timeline': [],
        },
        'dialogue': [],
        'training_package': {'submissions': []},
    }
    narrative = (
        'I contacted the involved parties and collected the retail surveillance video. '
        'The video was reviewed and preserved as part of the investigation. '
        'I then documented the remaining information and completed the synthetic training call.'
    )
    with app.app_context():
        result = review_training_narrative(state, narrative)

    flags = [item for item in result['suggestions'] if item['category'] == 'evidence consistency']
    assert flags
    assert 'does not show that evidence as obtained/preserved' in flags[0]['issue']
    assert flags[0]['confidence'] == 'high'


def test_cid_claim_inconsistent_with_recorded_decision_is_advisory_only():
    app = _testing_app()
    state = {
        'scenario_id': 'S004',
        'world': {
            'known_information': [],
            'evidence': {},
            'field_notes': [],
            'timeline': [],
        },
        'dialogue': [],
        'training_package': {
            'submissions': [
                {'cid_decision': 'not_required'}
            ]
        },
    }
    narrative = (
        'CID was notified and the incident was screened with CID before I completed the report. '
        'The remaining synthetic facts were documented in chronological order for training review.'
    )
    with app.app_context():
        result = review_training_narrative(state, narrative)

    flags = [item for item in result['suggestions'] if item['category'] == 'notification consistency']
    assert flags
    serialized = str(result).lower()
    assert 'pass' not in serialized
    assert 'fail' not in serialized
    assert 'disciplin' not in serialized
    assert 'employment' not in serialized
