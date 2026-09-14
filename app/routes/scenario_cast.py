SCENARIO_META = {
    'S001': {
        'scene': 'Facility entrance / interior disturbance',
        'visual': ['Public-facing facility', 'Reporting party available', 'Subject location initially based on caller information'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('weapon|armed|gun|knife', 'No confirmed weapon information has been developed.'), ('backup|unit|other officer', 'No additional unit has been assigned unless you request one.')]},
            {'id': 'staff', 'name': 'Staff Member', 'role': 'Reporting Party', 'from': 0, 'facts': [('what happened|why|problem|call', 'The person became disruptive and staff wants the behavior stopped.'), ('weapon|armed|threat', 'I have not personally seen a weapon.')]},
            {'id': 'subject', 'name': 'Subject', 'role': 'Subject', 'from': 1, 'facts': [('why|what happened|side|story', 'I think staff is overreacting. I was allowed to be here earlier.'), ('weapon|armed', 'I am not telling you that I have a weapon.')]},
            {'id': 'employee2', 'name': 'Second Employee', 'role': 'Potential Witness', 'from': 2, 'facts': [('see|hear|witness|leave', 'I may have heard part of the exchange. Ask me exactly what I personally observed.'), ('video|camera', 'The facility has cameras, but I do not know whether the relevant area was captured.')]},
        ],
    },
    'S002': {
        'scene': 'Main Gate inspection / access-control area',
        'visual': ['Vehicle in controlled gate area', 'Gate personnel present', 'Installation access decision pending'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('status|location|gate', 'Main Gate has the vehicle in the inspection area.'), ('wanted|records|check', 'No records check has been requested yet.')]},
            {'id': 'gate', 'name': 'Gate Officer', 'role': 'Gate Personnel', 'from': 0, 'facts': [('credential|access|why stopped', 'There is an access-control issue that must be resolved before entry.'), ('behavior|argument|threat', 'The driver is frustrated, but I have not reported a weapon.')]},
            {'id': 'driver', 'name': 'Driver', 'role': 'Driver', 'from': 0, 'facts': [('license|id|identity', 'I can provide government-issued identification.'), ('credential|pass|access', 'I do not have the credential the gate is asking for.')]},
            {'id': 'sponsor', 'name': 'Sponsor / Destination Contact', 'role': 'Phone Contact', 'from': 1, 'facts': [('meeting|expect|confirm', 'I can tell you whether I was expecting this person if you identify them.'), ('preclear|pre-clear|access|sponsor', 'I can tell you what access coordination I completed.')]},
        ],
    },
    'S003': {
        'scene': 'Facility parking area / government property incident',
        'visual': ['Government property may be damaged', 'Vehicle may still be available', 'Physical evidence can change or leave'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('injury|injured|medical', 'No injury has been confirmed in the dispatch information.'), ('vehicle|truck', 'A vehicle was reported in connection with the property damage.')]},
            {'id': 'reporting', 'name': 'Facility Employee', 'role': 'Reporting Party', 'from': 0, 'facts': [('see|witness|collision|hit', 'I learned about the damage, but whether I personally saw the contact depends on the run facts.'), ('when|time', 'The damage was noticed before you arrived.')]},
            {'id': 'witness', 'name': 'Worker', 'role': 'Potential Witness', 'from': 1, 'facts': [('see|witness|what happened', 'I can tell you what I personally observed if you ask me for the sequence.'), ('driver|who', 'I may be able to identify who was operating the vehicle.')]},
            {'id': 'driver', 'name': 'Driver', 'role': 'Driver', 'from': 1, 'facts': [('intent|purpose|damage', 'I did not come here intending to damage property.')]},
        ],
    },
    'S004': {
        'scene': 'Retail / exchange facility investigation',
        'visual': ['Possible recovered merchandise', 'Loss-prevention information available', 'Video availability varies by run'],
        'cast': [
            {'id': 'lp', 'name': 'Loss Prevention', 'role': 'Witness', 'from': 0, 'facts': [('statement|written', 'I can provide a written statement.'), ('value|price', 'Store records can document the merchandise value.')]},
            {'id': 'subject', 'name': 'Subject', 'role': 'Subject', 'from': 1, 'facts': [('why|intent|steal|bag', 'I dispute that I intended to steal anything.'), ('leave|exit', 'Ask me where I was stopped and what I had done before staff contacted me.')]},
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('backup|unit', 'No additional unit has been requested.'), ('records|wanted|check', 'No records check has been requested yet.')]},
        ],
    },
    'S005': {
        'scene': 'Roadside traffic enforcement contact',
        'visual': ['Traffic exposure', 'Stopped vehicle', 'Driver behavior changes based on the officer interaction'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('backup|unit', 'No backup unit has been requested.'), ('records|wanted|license|plate', 'A records check can be run when you provide the identifying information.')]},
            {'id': 'driver', 'name': 'Driver', 'role': 'Driver', 'from': 1, 'facts': [('license|registration', 'I have documents in the vehicle.'), ('weapon|gun|armed', 'You have not established that I have a weapon.')]},
        ],
    },
    'S006': {
        'scene': 'Workplace medical assist / uncertain cause',
        'visual': ['Patient condition requires attention', 'Witness accounts may conflict', 'EMS response varies by timing'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('ems|medical', 'EMS has been started unless later facts change that status.'), ('assault|fight|weapon', 'No confirmed assault or weapon information was included in the initial call.')]},
            {'id': 'coworker1', 'name': 'Coworker One', 'role': 'Witness', 'from': 0, 'facts': [('hit|assault', 'I did not personally see a weapon.')]},
            {'id': 'coworker2', 'name': 'Coworker Two', 'role': 'Witness', 'from': 0, 'facts': [('see|what happened|sit', 'My account may not match the other coworker because I was looking away part of the time.')]},
            {'id': 'patient', 'name': 'Patient', 'role': 'Patient', 'from': 0, 'facts': [('hit|assault', 'I can tell you what I remember if you ask directly, but my memory may be incomplete.')]},
            {'id': 'fullwitness', 'name': 'Additional Witness', 'role': 'Witness', 'from': 2, 'facts': [('see|what happened|full|beginning', 'I arrived early enough that I may have seen more of the event than the others.')]},
        ],
    },
}
