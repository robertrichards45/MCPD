from urllib.parse import quote_plus


OFFICIAL_USCODE = {
    '18 USC 13': 'https://uscode.house.gov/view.xhtml?req=(title:18%20section:13%20edition:prelim)',
    '18 USC 1382': 'https://uscode.house.gov/view.xhtml?req=(title:18%20section:1382%20edition:prelim)',
    '18 USC 242': 'https://uscode.house.gov/view.xhtml?req=(title:18%20section:242%20edition:prelim)',
    '10 USC 892': 'https://uscode.house.gov/view.xhtml?req=(title:10%20section:892%20edition:prelim)',
    '10 USC 908': 'https://uscode.house.gov/view.xhtml?req=(title:10%20section:908%20edition:prelim)',
}


def _item(citation, title, jurisdiction, query, why, official_url=''):
    return {
        'citation': citation,
        'title': title,
        'jurisdiction': jurisdiction,
        'why': why,
        'lookup_url': '/legal/search?q=' + quote_plus(query) + '&state=GA&source=ALL',
        'official_url': official_url,
    }


def legal_context_for(scenario_id, run_context, turn, engine=None):
    """Return research cues, not charging decisions. Jurisdiction must still be verified."""
    choices = (run_context or {}).get('choices') or {}
    rows = []

    if scenario_id == 'S001':
        rows.append(_item(
            'OCGA 16-7-21', 'Criminal Trespass', 'Georgia',
            'OCGA 16-7-21 criminal trespass notice remain property',
            'Potential state-law issue if notice, authority, location, and conduct facts support it. Verify installation jurisdiction before relying on state law.'
        ))
        rows.append(_item(
            '18 USC 13', 'Assimilative Crimes Act', 'Federal',
            '18 USC 13 Assimilative Crimes Act Georgia criminal trespass federal installation',
            'Jurisdiction research cue for qualifying federal areas when conduct is not already punishable by a federal enactment.',
            OFFICIAL_USCODE['18 USC 13'],
        ))
        if choices.get('access_history') == 'previously told to leave today':
            rows.append(_item(
                '18 USC 1382', 'Entering Military Property / Reentry', 'Federal',
                '18 USC 1382 military installation ordered not to reenter',
                'May become relevant if the actual facts establish a prior removal/order not to reenter and conduct within the statute.',
                OFFICIAL_USCODE['18 USC 1382'],
            ))
        if choices.get('subject_status') == 'active-duty service member':
            rows.append(_item(
                '10 USC 892', 'UCMJ Article 92', 'UCMJ',
                'UCMJ Article 92 lawful order regulation duty obey',
                'Only if the person is subject to the UCMJ and a lawful order/regulation plus duty to obey are actually established.',
                OFFICIAL_USCODE['10 USC 892'],
            ))

    elif scenario_id == 'S002':
        rows.append(_item(
            'Installation access policy', 'Access-Control Authority / Base Orders', 'Base Order',
            'installation access credential visitor sponsor gate access control',
            'Access decisions should be grounded in current installation orders and credential procedures, not improvised criminal enforcement.'
        ))

    elif scenario_id == 'S003':
        rows.append(_item(
            'OCGA 16-7-23', 'Criminal Damage to Property — Second Degree', 'Georgia',
            'OCGA 16-7-23 criminal damage property intent value',
            'Potential state-law reference when the required property, damage, value, and mental-state facts are supported.'
        ))
        if choices.get('driver_status') == 'active-duty service member':
            rows.append(_item(
                '10 USC 908', 'UCMJ Article 108 — Military Property', 'UCMJ',
                'UCMJ Article 108 military property willful neglect damage',
                'If the property is military property and the person is subject to the UCMJ, Article 108 is a relevant research cue because it addresses willful or neglect-based loss/damage theories.',
                OFFICIAL_USCODE['10 USC 908'],
            ))

    elif scenario_id == 'S004':
        rows.append(_item(
            'OCGA 16-8-14', 'Theft by Shoplifting', 'Georgia',
            'OCGA 16-8-14 theft by shoplifting intent conceal price tag container',
            'Potential Georgia theft reference. The trainee still has to establish conduct and intent rather than treating an accusation or recovery alone as proof.'
        ))
        if choices.get('subject_status') == 'active-duty service member':
            rows.append(_item(
                'UCMJ / command coordination', 'Military Status May Add Separate Consequences', 'UCMJ',
                'UCMJ larceny Article 121 service member theft',
                'Military status can create separate UCMJ and command considerations; verify the applicable article and command process through Law Lookup/legal review.'
            ))

    elif scenario_id == 'S005':
        violation = choices.get('violation', 'traffic violation')
        rows.append(_item(
            'Georgia Title 40', 'Observed Traffic Offense', 'Georgia',
            f'Georgia {violation} traffic law Title 40',
            'The legal basis for the stop must match the violation actually observed in this run.'
        ))
        rows.append(_item(
            'OCGA 40-6-395', 'Fleeing / Attempting to Elude', 'Georgia',
            'OCGA 40-6-395 fleeing attempting elude 2026',
            'Only becomes relevant if the changing run develops an actual failure-to-stop or fleeing branch; verify the current 2026 Georgia text.'
        ))
        if (engine or {}).get('complaint_risk') or (engine or {}).get('use_of_force_review'):
            rows.append(_item(
                '18 USC 242', 'Deprivation of Rights Under Color of Law', 'Federal',
                '18 USC 242 deprivation rights color of law willful',
                'High-level misconduct research cue for clearly willful rights deprivations; not a substitute for policy, constitutional case law, or legal review.',
                OFFICIAL_USCODE['18 USC 242'],
            ))

    elif scenario_id == 'S006':
        rows.append(_item(
            'Policy / documentation', 'Medical Assist / Evidence Preservation', 'Policy',
            'medical assist policy EMS witness documentation injury report',
            'The primary issue is medical priority, scene management, witness reliability, and accurate documentation. Do not force a criminal theory into a medical call without facts.'
        ))

    # Avoid turning legal references into easy answers at the beginning of the call.
    if int(turn or 0) < 1 and not (engine or {}).get('pending_event'):
        return []
    return rows
