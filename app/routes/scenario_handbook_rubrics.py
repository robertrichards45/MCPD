"""Deterministic practice rubrics for handbook-grounded synthetic scenarios."""

HANDBOOK_RUBRICS = {
    'S007': [
        {'minimum': 3, 'criteria': [
            ('Traffic / scene safety', ('traffic', 'block', 'lane', 'cones', 'scene safety', 'secondary'), 'Control immediate roadway hazards before focusing on paperwork.'),
            ('Medical assessment', ('injury', 'ems', 'medical', 'hurt', 'ambulance'), 'Determine and address injuries or requests for evaluation.'),
            ('Position / preserve scene', ('final rest', 'position', 'photo', 'photograph', 'before moving', 'scene'), 'Preserve final-rest and scene information before it changes when safe and practical.'),
            ('Dispatch / resources', ('dispatch', 'radio', 'tow', 'backup', 'fire'), 'Coordinate status and needed resources.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Driver / vehicle identification', ('license', 'registration', 'insurance', 'vin', 'plate', 'driver'), 'Verify drivers and vehicles through records/documents.'),
            ('Statements / witnesses', ('statement', 'witness', 'driver one', 'driver two', 'separate', 'interview'), 'Develop separate accounts and any independent witness.'),
            ('Physical evidence', ('debris', 'skid', 'tire', 'fluid', 'damage', 'point of impact', 'roadway'), 'Document physical evidence that supports or contradicts accounts.'),
            ('Photographs / diagram', ('photo', 'photograph', 'diagram', 'sketch', 'measure'), 'Create the visual/measurement record needed to explain the crash.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Reconcile conflicts', ('conflict', 'compare', 'corroborat', 'reconcile', 'inconsistent'), 'Resolve or explicitly preserve material conflicts.'),
            ('Fact-supported sequence', ('facts', 'sequence', 'evidence', 'based on'), 'State only a sequence the evidence supports.'),
            ('Enforcement basis', ('citation', 'warning', 'violation', 'probable cause', 'authority', 'no citation'), 'Tie enforcement or no enforcement to developed facts.'),
            ('Vehicle / occupant disposition', ('tow', 'drive', 'release', 'transport', 'vehicle disposition', 'occupant'), 'Account for every vehicle and involved person.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Required packet', ('report', 'ccn', 'stat sheet', 'sf-91', 'diagram', 'photos'), 'Identify the crash documentation actually required by the run.'),
            ('Database / citation consistency', ('gcic', 'ncic', 'records', '1408', '1805', 'citation'), 'Reconcile records and enforcement products.'),
            ('Tow / transfer details', ('tow', 'impound', 'destination', 'custody', 'time'), 'Document tow/custody transfer where applicable.'),
            ('Final status', ('dispatch', 'clear', 'notify', 'watch commander', 'return to service'), 'Close the call with a complete disposition and notification status.'),
        ]},
    ],
    'S008': [
        {'minimum': 3, 'criteria': [
            ('Identity verification', ('identity', 'dob', 'license', 'verify', 'match'), 'Verify that the return belongs to the person contacted.'),
            ('Safe lawful status', ('detain', 'temporary', 'lawful', 'safety', 'hands'), 'Use a defensible temporary status while confirmation is pending.'),
            ('Dispatch confirmation', ('dispatch', 'confirm', 'entering agency', 'holding agency', 'warrant'), 'Request agency confirmation rather than treating the computer hit as final.'),
            ('No premature transport', ('before transport', 'do not transport', 'confirm first', 'extradition'), 'Do not decide transport before confirmation/extradition information is received.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Warrant number / offense', ('warrant number', 'offense', 'charge'), 'Record the confirmed identifying warrant information.'),
            ('Extradition limits', ('extradition', 'limits', 'will extradite', 'will not extradite', 'declines'), 'Obtain the exact extradition instruction.'),
            ('Agency contact / time', ('agency', 'contact', 'confirmed by', 'time', 'dispatch'), 'Document who confirmed the warrant and when.'),
            ('Caution / safety information', ('caution', 'safety', 'medical', 'warning'), 'Account for confirmation-related cautions or medical information.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Follow confirmation', ('release', 'custody', 'transfer', 'transport', 'extradition'), 'Apply the actual confirmation rather than assuming every hit means arrest/transport.'),
            ('Search basis', ('search incident', 'consent', 'authority', 'search', 'not search'), 'Articulate lawful search authority if a search occurs.'),
            ('Rights timing', ('rights', 'question', 'interrogat', 'waiver', 'not question'), 'Address rights if custodial questioning is conducted.'),
            ('Property / medical', ('property', 'inventory', 'medical', 'medication'), 'Account for property and medical issues during custody/transfer.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Receiving official or release instruction', ('receiving', 'official', 'agency', 'release instruction', 'released'), 'Document who accepted custody or the exact release instruction.'),
            ('Transfer / release time', ('time', 'transfer', 'released'), 'Document when the custody status changed.'),
            ('Records / paperwork', ('gcic', 'ncic', 'warrant confirmation', '2708', 'report', 'ccn'), 'Complete and reconcile the wanted-person packet.'),
            ('Supervisor notification', ('watch commander', 'supervisor', 'notify', 'dispatch'), 'Document required supervisory/command awareness.'),
        ]},
    ],
    'S009': [
        {'minimum': 3, 'criteria': [
            ('Separate parties', ('separate', 'distance', 'different room', 'separate area'), 'Separate involved persons when practical to protect safety and statement integrity.'),
            ('Immediate safety', ('weapon', 'threat', 'safety', 'backup', 'scene'), 'Assess immediate danger and scene safety.'),
            ('Medical needs', ('injury', 'ems', 'medical', 'hurt'), 'Assess injuries and medical needs.'),
            ('Initial observations', ('observe', 'injury', 'emotional', 'condition', 'scene'), 'Document physical/emotional condition and scene facts rather than conclusions.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Separate statements', ('statement', 'interview', 'party one', 'party two', 'separate'), 'Obtain separate fact-based accounts.'),
            ('Spontaneous statements', ('spontaneous', 'excited utterance', 'said', 'quote'), 'Preserve spontaneous/excited statements when they occur.'),
            ('Witness / children', ('witness', 'child', 'neighbor', 'saw', 'heard'), 'Identify direct witnesses and distinguish what they saw from what they heard.'),
            ('Injury / photos', ('photo', 'photograph', 'injury', 'scene'), 'Document visible injuries and relevant scene condition.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Protective-order / records check', ('protective order', 'records', 'dispatch', 'history'), 'Verify records that materially affect the response.'),
            ('Aggressor / self-defense facts', ('primary aggressor', 'self-defense', 'initiated', 'defense', 'facts'), 'Develop facts bearing on initiation, defensive conduct, and material conflicts.'),
            ('Rights / questioning', ('rights', 'custodial', 'question', 'waiver'), 'Address rights before custodial interrogation when applicable.'),
            ('Corroboration', ('evidence', 'photo', 'witness', 'corroborat', 'video'), 'Use available evidence without forcing conflicting accounts into certainty.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Victim resources', ('2701', 'victim', 'resources', 'victim witness'), 'Provide/document required victim information.'),
            ('Notifications', ('cid', 'fap', 'family advocacy', 'watch commander', 'notify'), 'Recognize required investigative/family/command notifications.'),
            ('Fact-based disposition', ('arrest', 'release', 'separate', 'protective order', 'facts', 'probable cause'), 'Tie the disposition to developed facts and current authority.'),
            ('Complete packet', ('domestic violence supplement', 'statement', 'photos', 'report', 'ccn'), 'Complete the domestic packet applicable to the run.'),
        ]},
    ],
    'S010': [
        {'minimum': 3, 'criteria': [
            ('Driving / contact basis', ('weaving', 'stop sign', 'violation', 'driving', 'gate', 'crash'), 'Document the objective reason for contact before impairment conclusions.'),
            ('Officer safety / location', ('position', 'traffic', 'safety', 'backup', 'location'), 'Manage roadside/contact safety.'),
            ('Records', ('license', 'registration', 'records', 'gcic', 'ncic'), 'Verify driver and vehicle information.'),
            ('Objective observations', ('odor', 'speech', 'eyes', 'balance', 'coordination', 'observe'), 'Record specific observations instead of writing only “intoxicated.”'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Medical alternatives', ('medical', 'condition', 'injury', 'ems', 'limitation'), 'Screen facts that could affect or invalidate testing.'),
            ('Relevant questions', ('drink', 'medication', 'sleep', 'food', 'medical', 'ask'), 'Develop relevant history without inventing admissions.'),
            ('Field testing decision', ('field sobriety', 'fst', 'test', 'standardized', 'limitation'), 'Explain whether and how standardized testing is appropriate.'),
            ('Document performance', ('clue', 'performance', 'instruction', 'demonstration', 'document'), 'Document actual performance and limitations.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Probable-cause moment', ('probable cause', 'facts', 'totality', 'arrest point', 'insufficient'), 'Identify the exact factual basis for arrest or no arrest.'),
            ('Rights timing', ('rights', 'question', 'custodial', 'waiver'), 'Address rights when custodial questioning occurs.'),
            ('No threshold guessing', ('current law', 'current authority', 'verify', 'approved warning'), 'Use current controlling authority rather than memorized/sample thresholds.'),
            ('Vehicle disposition', ('tow', 'impound', 'release vehicle', 'driver'), 'Plan lawful vehicle disposition.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Implied consent process', ('implied consent', 'warning', 'read verbatim', 'approved warning'), 'Use the current approved warning/process applicable to the driver.'),
            ('Exact response / refusal', ('refuse', 'exact response', 'quote', 'consent', 'submit'), 'Document the driver’s exact response.'),
            ('Testing / admin documents', ('breath', 'blood', 'urine', 'ds-1150', '1920', 'test'), 'Document the test/refusal and administrative paperwork that actually applies.'),
            ('Timeline consistency', ('time', 'timeline', 'citation', 'report', 'tow', 'release'), 'Reconcile arrest, warning, testing, citation, tow, and release times.'),
        ]},
    ],
    'S011': [
        {'minimum': 3, 'criteria': [
            ('Safe exterior approach', ('approach', 'cover', 'backup', 'safety', 'exterior'), 'Assess from a safe position before assuming the cause.'),
            ('Entry-point condition', ('door', 'latch', 'damage', 'pry', 'tamper', 'entry'), 'Examine and document the entry point.'),
            ('Dispatch / alarm check', ('dispatch', 'alarm', 'radio', 'history'), 'Develop available alarm/call information.'),
            ('Avoid unsupported entry', ('do not enter', 'wait', 'keyholder', 'authority', 'backup'), 'Do not create an unnecessary interior risk without a lawful/operational reason.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Keyholder / facility rep', ('keyholder', 'facility', 'representative', 'contact'), 'Coordinate a responsible facility representative.'),
            ('Photographs if damage', ('photo', 'photograph', 'damage', 'tamper'), 'Preserve forced-entry/damage indicators before the scene changes.'),
            ('Routine vs incident', ('routine', 'incident', 'forced entry', 'crime', 'damage'), 'Recognize when a simple unsecured-building service becomes an incident.'),
            ('Resources', ('backup', 'supervisor', 'dispatch', 'physical security'), 'Use appropriate resources as the facts become more serious.'),
        ]},
        {'minimum': 2, 'criteria': [
            ('Protect scene / lawful assessment', ('protect scene', 'preserve', 'clear building', 'lawful', 'keyholder'), 'Protect the scene and coordinate any interior assessment lawfully and safely.'),
            ('Check disturbed/missing property', ('missing', 'disturbed', 'property', 'inventory', 'facility'), 'Use the facility representative to identify material changes.'),
            ('Evidence / notes', ('evidence', 'notes', 'photo', 'statement'), 'Preserve evidence and firsthand information when the call becomes an incident.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Securing party / time', ('secured', 'keyholder', 'time', 'door'), 'Document who secured the building and when.'),
            ('Notification', ('watch commander', 'command', 'notify', 'dispatch'), 'Document the notifications the facts require.'),
            ('Report product decision', ('ccn', 'report', 'stat sheet', 'unsecured building notice', 'journal'), 'Choose documentation based on whether an incident actually developed.'),
            ('Final disposition', ('clear', 'return to service', 'follow-up', 'work order'), 'State final status and any follow-up.'),
        ]},
    ],
    'S012': [
        {'minimum': 3, 'criteria': [
            ('Recovery location / finder', ('where found', 'location', 'finder', 'reporting person', 'time'), 'Preserve exact recovery circumstances.'),
            ('Describe before moving/opening', ('describe', 'condition', 'serial', 'marking', 'photo', 'before'), 'Document external identifying features and condition.'),
            ('Custody transfer', ('custody', 'received from', 'take possession', 'property receipt'), 'Record how police custody began.'),
            ('No unjustified search', ('do not open', 'authority', 'consent', 'search', 'warrant'), 'Do not open/search closed property without a lawful basis.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Complete item description', ('quantity', 'color', 'size', 'serial', 'brand', 'condition'), 'Describe the item so another person can identify it.'),
            ('Ownership check', ('owner', 'records', 'serial', 'identify', 'verify'), 'Develop ownership without assuming the finder is the owner.'),
            ('Classify handling', ('evidence', 'safekeeping', 'found property', 'sensitive', 'property'), 'Decide the proper custody category based on facts.'),
            ('Special notification if needed', ('supervisor', 'watch commander', 'notify', 'sensitive'), 'Identify special handling/notification when the item requires it.'),
        ]},
        {'minimum': 2, 'criteria': [
            ('Maintain chain', ('chain of custody', 'custody', 'seal', 'locker', 'receipt'), 'Keep the custody history intact.'),
            ('Lawful scope', ('authority', 'consent', 'search', 'not open', 'scope'), 'Stay within lawful authority when examining contents.'),
            ('Owner verification', ('owner', 'claimant', 'describe', 'serial', 'receipt'), 'Require corroborating ownership before release.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Property documentation', ('5580/22', 'property custody', 'receipt', 'stat sheet'), 'Complete the property documentation that applies.'),
            ('Release / evidence disposition', ('release', 'owner', 'evidence', 'locker', 'safekeeping'), 'Document where the item ended up.'),
            ('Consistency', ('description', 'serial', 'condition', 'location', 'match'), 'Keep descriptions consistent across report and custody records.'),
            ('Final report', ('ccn', 'report', 'narrative', 'clear'), 'Complete the report and final status.'),
        ]},
    ],
    'S013': [
        {'minimum': 3, 'criteria': [
            ('Source / objective fact', ('odor', 'source', 'personally', 'reported', 'observe'), 'Distinguish personal observation from another person’s report.'),
            ('Locate possible source', ('vehicle', 'room', 'person', 'source', 'location'), 'Identify what place/person the fact actually relates to.'),
            ('Corroborate', ('corroborat', 'additional facts', 'observe', 'records', 'question'), 'Develop facts before deciding search/enforcement authority.'),
            ('No automatic search', ('authority', 'consent', 'warrant', 'probable cause', 'do not search'), 'Do not convert an odor allegation into an automatic search.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Current legal basis', ('current law', 'authority', 'probable cause', 'warrant', 'consent'), 'Identify and verify the lawful basis, if any.'),
            ('Consent voluntariness', ('voluntary', 'right to refuse', 'consent', 'no threats'), 'If using consent, ensure it is voluntary.'),
            ('Scope', ('scope', 'where search', 'limit', 'containers'), 'Define the place/items within authorized scope.'),
            ('Refusal respected', ('refuse', 'withdraw', 'stop search', 'no consent'), 'Reassess authority when consent is refused or withdrawn.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Stay within scope', ('scope', 'limit', 'stop', 'authority'), 'Do not exceed the legal basis actually established.'),
            ('Evidence documentation', ('photo', 'evidence', '5580/22', 'location found', 'custody'), 'Document any recovered property and exact recovery location.'),
            ('No contraband outcome', ('no contraband', 'nothing found', 'release', 'no evidence'), 'Recognize that a lawful investigation may end without evidence.'),
            ('Rights if questioned', ('rights', 'custodial', 'question', 'waiver'), 'Address suspect rights when applicable.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Search form / authority record', ('5580/16', 'consent form', 'search authorization', 'document authority'), 'Document the search authority actually used.'),
            ('Evidence / lab if applicable', ('evidence receipt', 'field test', 'lab', 'property custody'), 'Complete evidence/testing documents only if evidence exists.'),
            ('Vehicle/tow if applicable', ('tow', 'vehicle search', 'impound'), 'Document related vehicle disposition when it actually applies.'),
            ('Fact-based release/enforcement', ('release', 'citation', 'arrest', 'facts', 'probable cause'), 'Tie final disposition to developed facts.'),
        ]},
    ],
    'S014': [
        {'minimum': 3, 'criteria': [
            ('Time / location / direction', ('time', 'location', 'direction', 'altitude', 'duration'), 'Capture the core observation while it is still fresh.'),
            ('Description / observation', ('describe', 'drone', 'uas', 'color', 'lights', 'movement'), 'Record observable aircraft characteristics without speculation.'),
            ('Dispatch / Watch Commander', ('dispatch', 'watch commander', 'notify', 'radio'), 'Make timely initial notification.'),
            ('Safe observation', ('safe', 'observe', 'do not interfere', 'perimeter'), 'Observe and protect the area without improvised counter-UAS action.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Witness / operator development', ('witness', 'operator', 'identify', 'interview', 'launch'), 'Develop witnesses/operator facts lawfully.'),
            ('Video preservation', ('video', 'camera', 'preserve', 'phone'), 'Preserve relevant video and observation records.'),
            ('Search / sweep facts', ('search area', 'sweep', 'location', 'last seen'), 'Document reasonable efforts and last known location.'),
            ('Updates', ('update', 'dispatch', 'watch commander', 'time lost'), 'Continue command/dispatch updates as the event changes.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Security / mission impact', ('security', 'mission', 'safety', 'restricted area', 'impact'), 'Separate observed impact from speculation.'),
            ('SITREP / UAS product', ('sitrep', 'uas report', 'command report'), 'Recognize the structured UAS reporting product.'),
            ('OPREP screening', ('oprep', 'screen', 'command significant', 'incursion'), 'Screen for OPREP under current command guidance.'),
            ('Command chain', ('operations', 'cdo', 'watch commander', 'notify'), 'Identify the command notification path.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Full incident record', ('ccn', 'narrative', 'report', 'blotter'), 'Complete the incident record in addition to command products.'),
            ('Evidence / video', ('video', 'evidence', 'preserve', 'custodian'), 'Document preservation and custodian/handoff.'),
            ('Operator / witness disposition', ('operator', 'witness', 'release', 'identity', 'statement'), 'Account for people contacted.'),
            ('Final notification / status', ('final', 'update', 'watch commander', 'clear', 'disposition'), 'Close the notification and disposition timeline.'),
        ]},
    ],
}
