(function () {
  const STORAGE_KEY = 'mcpd.mobile.incident.state';
  let stateCache = null;
  const jsonScriptCache = {};

  const defaultCallTypeRules = {
    'domestic-disturbance': {
      slug: 'domestic-disturbance',
      title: 'Domestic Disturbance',
      shortLabel: 'Domestic',
      description: 'Primary domestic response, scene control, initial statements, and follow-up paperwork prep.',
      statutes: ['Assault / battery review', 'Protective-order review'],
      recommendedForms: [
        'NAVMAC 11337 MILITARY POLICE DOMESTIC VIOLENCE SIPPLEMENT REPORT AND CHECKLIST',
        'OPNAV 5580 2 Voluntary Statement',
        'NAVMC 11130 Statement of Force Use of Detention',
        'OPNAV 5580 22Evidence Custody Document',
      ],
      optionalForms: ['DD Form 2701 VWAP', 'ENCLOSURE CHECKLIST FILLABLE'],
      checklistItems: [
        'Separate involved parties',
        'Document injuries and scene condition',
        'Confirm witness and victim statements',
        'Notify supervisor if escalation or arrest is involved',
      ],
    },
    'traffic-accident': {
      slug: 'traffic-accident',
      title: 'Traffic Accident',
      shortLabel: 'Traffic',
      description: 'Collision response, roadway safety, vehicle data capture, and tow/impound preparation.',
      statutes: ['Traffic enforcement review', 'Installation roadway policy'],
      recommendedForms: [
        'SF 91 MOTOR VEHICLE ACCIDENT CRASH REPORT',
        'OPNAV 5580 2 Voluntary Statement Traffic',
        'TA FIELD SKETCH NEW',
      ],
      optionalForms: ['DD Form 2506Vehicle Impoundment Report', 'OPNAV 5580 12 DON VEHICLE REPORT'],
      checklistItems: [
        'Stabilize traffic and scene hazards',
        'Capture driver and vehicle data',
        'Document injuries and medical response',
        'Identify tow or impound decision',
      ],
    },
    'suspicious-person': {
      slug: 'suspicious-person',
      title: 'Suspicious Person',
      shortLabel: 'Suspicious',
      description: 'Field contact and articulable-facts workflow for suspicious behavior and security concerns.',
      statutes: ['Detention authority review', 'Trespass / access review'],
      recommendedForms: ['OPNAV 5580 21Field Interview Card', 'OPNAV 5580 2 Voluntary Statement'],
      optionalForms: ['OPNAV 5580 22Evidence Custody Document'],
      checklistItems: [
        'Record the reason for contact',
        'Capture identifiers and witness information',
        'Document disposition and release / detention outcome',
      ],
    },
    'trespass-after-warning': {
      slug: 'trespass-after-warning',
      title: 'Trespass After Warning',
      shortLabel: 'Trespass',
      description: 'Return-after-warning workflow with authority review and citation/notice support.',
      statutes: ['Trespass authority review', 'Installation access policy'],
      recommendedForms: ['OPNAV 5580 2 Voluntary Statement', 'UNSECURED BUILDING NOTICE'],
      optionalForms: ['OPNAV 5580 21Field Interview Card'],
      checklistItems: [
        'Confirm prior warning details',
        'Record location restrictions',
        'Document witness confirmation',
        'Capture final enforcement action',
      ],
    },
    'theft': {
      slug: 'theft',
      title: 'Theft',
      shortLabel: 'Theft',
      description: 'Property crime workflow focused on ownership, recovered items, and evidence trail.',
      statutes: ['Property crime review', 'Evidence handling review'],
      recommendedForms: ['OPNAV 5580 22Evidence Custody Document', 'OPNAV 5580 2 Voluntary Statement'],
      optionalForms: ['OPNAV 5580 21Field Interview Card', 'DD Form 2701 VWAP'],
      checklistItems: [
        'Verify owner and value information',
        'Document recovered property',
        'Preserve evidence chain',
        'Capture suspect opportunity and access',
      ],
    },
    'traffic-stop': {
      slug: 'traffic-stop',
      title: 'Traffic Stop',
      shortLabel: 'Traffic Stop',
      description: 'Vehicle stop, driver contact, citation or warning workflow.',
      statutes: ['Traffic enforcement review', 'Installation roadway policy'],
      recommendedForms: ['OPNAV 5580 21Field Interview Card', 'OPNAV 5580 2 Voluntary Statement'],
      optionalForms: ['DD Form 2701 VWAP', 'OPNAV 5580 22Evidence Custody Document'],
      checklistItems: [
        'Document reason for stop',
        'Record driver license, registration, and insurance',
        'Document all occupants',
        'Record outcome — citation, warning, or arrest',
      ],
    },
    'use-of-force': {
      slug: 'use-of-force',
      title: 'Use of Force',
      shortLabel: 'Use of Force',
      description: 'Physical force application with supervisor notification and full documentation requirements.',
      statutes: ['Use of force authority review', 'Detention authority review'],
      recommendedForms: [
        'NAVMC 11130 Statement of Force Use of Detention',
        'OPNAV 5580 2 Voluntary Statement',
      ],
      optionalForms: ['DD Form 1920 ALCOHOL INCIDENT REPORT', 'OPNAV 5580 22Evidence Custody Document'],
      checklistItems: [
        'Render medical aid immediately if needed',
        'Notify watch commander before end of shift',
        'Photograph all injuries from all angles',
        'Submit officer written statement',
        'Preserve body cam and all recording evidence',
      ],
    },
    'general-incident': {
      slug: 'general-incident',
      title: 'General Incident',
      shortLabel: 'General',
      description: 'Catch-all incident type for situations not covered by a specific call type.',
      statutes: ['Review applicable statute or regulation for specific violation'],
      recommendedForms: ['OPNAV 5580 2 Voluntary Statement'],
      optionalForms: [
        'OPNAV 5580 21Field Interview Card',
        'OPNAV 5580 22Evidence Custody Document',
        'DD Form 2701 VWAP',
      ],
      checklistItems: [
        'Document incident type and circumstances',
        'Capture all involved parties',
        'Document resolution and disposition',
      ],
    },
    'arrest': {
      slug: 'arrest',
      title: 'Arrest',
      shortLabel: 'Arrest',
      description: 'Formal apprehension workflow with rights advisement, search, and confinement steps.',
      statutes: ['Arrest authority review', 'Detention authority review'],
      recommendedForms: [
        'OPNAV 5580 2 Voluntary Statement',
        'OPNAV 5580 22Evidence Custody Document',
      ],
      optionalForms: ['NAVMC 11130 Statement of Force Use of Detention', 'DD Form 2701 VWAP'],
      checklistItems: [
        'Advise subject of rights (Miranda) before custodial interrogation',
        'Search incident to arrest — document all items seized',
        'Notify watch commander of arrest',
        'Process through confinement per SOP',
        'Complete property inventory — obtain signature if possible',
      ],
    },
    'search-consent': {
      slug: 'search-consent',
      title: 'Search / Consent',
      shortLabel: 'Search',
      description: 'Consent-based search with scope documentation and evidence handling.',
      statutes: ['Search authority review', 'Consent requirements review'],
      recommendedForms: [
        'OPNAV 5580 2 Voluntary Statement',
        'OPNAV 5580 22Evidence Custody Document',
      ],
      optionalForms: ['OPNAV 5580 21Field Interview Card'],
      checklistItems: [
        'Obtain clear, voluntary, uncoerced consent',
        'Inform subject of right to refuse',
        'Limit search to scope of consent granted',
        'Document all items found and exact location',
        'Notify watch commander if controlled substances or weapons found',
      ],
    },
    'evidence-seizure': {
      slug: 'evidence-seizure',
      title: 'Evidence Seizure',
      shortLabel: 'Evidence',
      description: 'Evidence collection, packaging, and chain of custody initiation.',
      statutes: ['Evidence handling authority review', 'Property seizure review'],
      recommendedForms: [
        'OPNAV 5580 22Evidence Custody Document',
        'OPNAV 5580 2 Voluntary Statement',
      ],
      optionalForms: ['OPNAV 5580 21Field Interview Card'],
      checklistItems: [
        'Photograph evidence in place before collection',
        'Document exact location, condition, and description',
        'Package and seal with proper evidence procedures',
        'Maintain chain of custody from point of collection',
        'Turn in to evidence custodian as soon as practical',
      ],
    },
  };

  const defaultState = {
    callType: null,
    incidentBasics: {
      occurredDate: '',
      occurredTime: '',
      dispatchTime: '',
      arrivalTime: '',
      location: '',
      reportingOfficer: '',
      callSource: '',
      summary: '',
    },
    timeline: [],
    persons: [],
    selectedForms: [],
    statutes: [],
    checklist: [],
    facts: [],
    narrative: '',
    narrativeApproved: false,
    statements: [],
    formDrafts: {},
    packetStatus: 'not_started',
  };

  const callTypeRules = normalizeCallTypeRules(readJsonScript('mobile-call-type-rules-data')) || defaultCallTypeRules;

  const personRoleOptions = [
    'Victim',
    'Suspect',
    'Witness',
    'Reporting Party',
    'Subject',
    'Driver',
    'Passenger',
    'Other',
  ];
  const factSections = [
    { key: 'what_happened', label: 'What happened' },
    { key: 'complainant', label: 'Complainant' },
    { key: 'victim', label: 'Victim' },
    { key: 'suspect', label: 'Suspect' },
    { key: 'officer_actions', label: 'Officer actions' },
    { key: 'disposition', label: 'Disposition' },
  ];
  const legacyFormAliases = {
    incidentreport: 'DD FORM 1920 ALCOHOL INCIDENT REPORT',
    witnessstatement: 'OPNAV 5580 2 Voluntary Statement',
    voluntarystatement: 'OPNAV 5580 2 Voluntary Statement',
    useofforcereport: 'NAVMC 11130 Statement of Force Use of Detention',
    evidencepropertyform: 'OPNAV 5580 22Evidence Custody Document',
    evidenceform: 'OPNAV 5580 22Evidence Custody Document',
    propertyform: 'OPNAV 5580 22Evidence Custody Document',
    victimsassistanceworksheet: 'DD Form 2701 VWAP',
    incidentaccidentreport: 'SF 91 MOTOR VEHICLE ACCIDENT CRASH REPORT',
    vehicleimpoundform: 'DD Form 2506Vehicle Impoundment Report',
    fieldsketch: 'TA FIELD SKETCH NEW',
    donvehiclereport: 'OPNAV 5580 12 DON VEHICLE REPORT',
    fieldinterviewcard: 'OPNAV 5580 21Field Interview Card',
    citationnoticedocumentation: 'UNSECURED BUILDING NOTICE',
  };
  const trafficStatementQuestions = [
    'Would you please describe the accident?',
    'How fast were you driving when the accident occurred?',
    'Did you wear glasses or corrective lenses?',
    'Did you take any evasive actions to avoid the accident or collision?',
    'Did you experience any dizziness or fatigue while driving?',
    'Do you have any medical conditions that might have contributed to the cause of the accident?',
  ];

  function sequentialFieldNames(prefix, count, suffix) {
    return Array.from({ length: count }, (_value, index) => `${prefix}${index + 1}${suffix || ''}`);
  }

  const statementFormConfigs = {
    standard: {
      variant: 'standard',
      title: 'Voluntary Statement',
      formTitle: 'OPNAV 5580 2 Voluntary Statement',
      formId: 11,
      bodyCapacity: 37,
      bodyLineLength: 58,
      bodyPages: [
        {
          pageNumber: 1,
          title: 'Statement Page',
          lineFields: sequentialFieldNames(
            'I Name SSN  make the following free and voluntary statement to  whom I know to be a police officer with the Marine Corps Police Department MCLB Albany Georgia I make this statement of my own free will and without any threats or promises extended to me I fully understand that this statement is given concerning my knowledge of that occurred on Date  Year at approximately TimeAMPM Row',
            23
          ),
          initialField: 'Initials of person making statement',
        },
        {
          pageNumber: 2,
          title: 'Statement Continued',
          lineFields: sequentialFieldNames(
            'DEPARTMENT OF THE NAVY VOLUNTARY STATEMENT Name taken at Location on Date  Time  Statement Continued Row',
            14
          ),
          initialField: 'Initials of person making statement_2',
        },
      ],
      signaturePage: {
        pageNumber: 3,
        title: 'Sworn Signature Page',
        initialField: 'Initials of person making statement_3',
        signatureField: 'Signature',
        witnessSignatureField: 'Signature  Badge',
      },
    },
    traffic: {
      variant: 'traffic',
      title: 'Traffic Voluntary Statement',
      formTitle: 'OPNAV 5580 2 Voluntary Statement Traffic',
      formId: 12,
      bodyCapacity: 69,
      bodyLineLength: 54,
      interviewAnswerFields: [
        'A', 'A_2', 'A_3', 'A_4', 'A_5', 'A_6', 'A_7', 'A_8', 'A_9', 'A_10',
        'A_11', 'A_12', 'A_13', 'A_14', 'A_15', 'A_16', 'A_17', 'A_18',
        'ARow1', 'ARow2', 'ARow3', 'ARow4', 'ARow5', 'ARow6', 'ARow7', 'ARow8',
        'ARow9', 'ARow10', 'ARow11', 'ARow12', 'ARow13',
      ],
      bodyPages: [
        {
          pageNumber: 1,
          title: 'Traffic Interview Page',
          lineFields: [
            'A', 'A_2', 'A_3', 'A_4', 'A_5', 'A_6', 'A_7', 'A_8', 'A_9', 'A_10',
            'A_11', 'A_12', 'A_13', 'A_14', 'A_15', 'A_16', 'A_17', 'A_18',
            'ARow1', 'ARow2', 'ARow3', 'ARow4', 'ARow5', 'ARow6', 'ARow7', 'ARow8',
            'ARow9', 'ARow10', 'ARow11', 'ARow12', 'ARow13',
          ],
          initialField: 'Initials of person making statement',
        },
        {
          pageNumber: 2,
          title: 'Statement Continued',
          lineFields: sequentialFieldNames(
            'DEPARTMENT OF THE NAVY VOLUNTARY STATEMENT Name taken at Location on Date  Time  Statement Continued Row',
            24
          ),
          initialField: 'Initials of person making statement_2',
        },
        {
          pageNumber: 3,
          title: 'Statement Continued',
          lineFields: sequentialFieldNames(
            'DEPARTMENT OF THE NAVY VOLUNTARY STATEMENT Name taken at Location on Date  Time  Statement Continued Row',
            13,
            '_2'
          ),
          initialField: 'Initials of person making statement_3',
        },
      ],
      signaturePage: {
        pageNumber: 4,
        title: 'Sworn Signature Page',
        initialField: 'Initials of person making statement_4',
        signatureField: 'Signature',
        witnessSignatureField: 'Signature  Badge',
      },
    },
  };

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function defaultStatementVariant(state) {
    return state && state.callType === 'traffic-accident' ? 'traffic' : 'standard';
  }

  function statementConfig(variant) {
    return statementFormConfigs[variant] || statementFormConfigs.standard;
  }

  function findPrimaryPerson(current, preferredRoles) {
    const persons = Array.isArray((current || {}).persons) ? current.persons : [];
    const roles = Array.isArray(preferredRoles) ? preferredRoles : [];
    for (const role of roles) {
      const hit = persons.find((entry) => String((entry || {}).role || '').trim().toLowerCase() === String(role || '').trim().toLowerCase());
      if (hit) return hit;
    }
    return persons[0] || null;
  }

  function readState() {
    try {
      if (stateCache) return clone(stateCache);
      const raw = window.sessionStorage.getItem(STORAGE_KEY);
      if (!raw) {
        stateCache = clone(defaultState);
        return clone(stateCache);
      }
      stateCache = Object.assign(clone(defaultState), JSON.parse(raw) || {});
      return clone(stateCache);
    } catch (err) {
      return clone(defaultState);
    }
  }

  function writeState(nextState) {
    stateCache = Object.assign(clone(defaultState), nextState || {});
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stateCache));
    return clone(stateCache);
  }

  function buildDefaultStatement(current, seed) {
    const statementSeed = seed || {};
    const variant = statementSeed.variant || defaultStatementVariant(current);
    const config = statementConfig(variant);
    const seededPerson = (current.persons || []).find((entry) => entry.id === statementSeed.personId) || null;
    const person = seededPerson || findPrimaryPerson(
      current,
      variant === 'traffic'
        ? ['Driver', 'Passenger', 'Witness', 'Victim', 'Reporting Party']
        : ['Victim', 'Witness', 'Reporting Party', 'Complainant', 'Subject', 'Suspect']
    );
    const basics = current.incidentBasics || {};
    return Object.assign(
      {
        id: '',
        variant,
        formTitle: config.formTitle,
        formId: config.formId,
        personId: statementSeed.personId || (person ? person.id || '' : ''),
        speaker: person ? (person.name || '') : '',
        speakerSsn: person ? (person.ssn || '') : '',
        officerName: '',
        officerBadge: '',
        location: basics.location || '',
        statementDate: basics.occurredDate || '',
        statementTime: basics.arrivalTime || basics.dispatchTime || basics.occurredTime || '',
        statementSubject:
          String(basics.summary || '').trim()
          || String((((current.facts || []).find((entry) => entry && entry.id === 'what_happened')) || {}).value || '').trim()
          || '',
        plainLanguage: '',
        formattedDraft: '',
        reviewedDraft: '',
        trafficAnswers: {},
        initialsDataUrl: '',
        signatureDataUrl: '',
        witnessingSignatureDataUrl: '',
        updatedAt: new Date().toISOString(),
      },
      statementSeed,
      {
        variant,
        formTitle: config.formTitle,
        formId: config.formId,
      }
    );
  }

  const incidentStore = {
    getState() {
      return readState();
    },
    resetIncident() {
      return writeState(clone(defaultState));
    },
    setCallType(slug) {
      const current = readState();
      const rule = callTypeRules[slug] || null;
      const baseList = rule ? clone(rule.recommendedForms) : [];
      const selectedForms = ['MCPD Stat Sheet', ...baseList.filter((f) => f !== 'MCPD Stat Sheet')];
      return writeState(
        Object.assign({}, current, {
          callType: slug,
          selectedForms,
          statutes: rule ? clone(rule.statutes || []) : [],
          checklist: rule
            ? rule.checklistItems.map((label, index) => ({
                id: `${slug}-check-${index + 1}`,
                label,
                completed: false,
              }))
            : [],
          packetStatus: 'draft',
        })
      );
    },
    updateIncidentBasics(patch) {
      const current = readState();
      const next = Object.assign({}, current, {
        incidentBasics: Object.assign({}, current.incidentBasics, patch || {}),
      });
      const basics = next.incidentBasics || {};
      if (basics.occurredDate && basics.location && basics.dispatchTime && basics.arrivalTime && basics.reportingOfficer) {
        next.packetStatus = 'basics_complete';
      }
      return writeState(next);
    },
    getFacts() {
      const current = readState();
      return Array.isArray(current.facts) ? current.facts.slice() : [];
    },
    updateFact(sectionKey, label, value) {
      const current = readState();
      const facts = Array.isArray(current.facts) ? current.facts.slice() : [];
      const index = facts.findIndex((entry) => entry.id === sectionKey);
      const nextEntry = {
        id: sectionKey,
        label,
        value,
      };
      if (index >= 0) {
        facts[index] = nextEntry;
      } else {
        facts.push(nextEntry);
      }
      return writeState(Object.assign({}, current, { facts }));
    },
    updateNarrative(value) {
      const current = readState();
      return writeState(Object.assign({}, current, { narrative: value || '', narrativeApproved: false }));
    },
    approveNarrative(value) {
      const current = readState();
      return writeState(
        Object.assign({}, current, {
          narrative: value || current.narrative || '',
          narrativeApproved: true,
          packetStatus: 'narrative_approved',
        })
      );
    },
    getPersonById(personId) {
      const current = readState();
      return (current.persons || []).find((person) => person.id === personId) || null;
    },
    upsertPerson(personPatch) {
      const current = readState();
      const existing = (current.persons || []).slice();
      const nextStatements = Array.isArray(current.statements) ? current.statements.slice() : [];
      const nextDrafts = current.formDrafts && typeof current.formDrafts === 'object'
        ? clone(current.formDrafts)
        : {};
      const person = Object.assign(
        {
          id: '',
          role: 'Witness',
          name: '',
          dob: '',
          ssn: '',
          address: '',
          phone: '',
          idNumber: '',
          state: '',
          descriptors: '',
          source: 'manual',
        },
        personPatch || {}
      );
      if (!person.id) {
        person.id = `person-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
      }
      const index = existing.findIndex((entry) => entry.id === person.id);
      if (index >= 0) {
        existing[index] = person;
      } else {
        existing.push(person);
      }
      nextStatements.forEach((statement, statementIndex) => {
        if (!statement || statement.personId !== person.id) return;
        nextStatements[statementIndex] = Object.assign({}, statement, {
          speaker: person.name || statement.speaker || '',
          speakerSsn: person.ssn || statement.speakerSsn || '',
        });
      });
      const normalizedRole = String(person.role || '').trim().toLowerCase();
      if (normalizedRole === 'victim' || normalizedRole === 'suspect') {
        const domesticDraft = nextDrafts.domesticSupplemental && typeof nextDrafts.domesticSupplemental === 'object'
          ? Object.assign({}, nextDrafts.domesticSupplemental)
          : {};
        if (normalizedRole === 'victim') {
          if (person.name) domesticDraft['form1.VicName'] = person.name;
          domesticDraft['form1.RadioButtonList.Victim'] = 'Yes';
        }
        if (normalizedRole === 'suspect') {
          domesticDraft['form1.RadioButtonList.Suspect'] = 'Yes';
        }
        nextDrafts.domesticSupplemental = domesticDraft;
      }
      return writeState(Object.assign({}, current, { persons: existing, statements: nextStatements, formDrafts: nextDrafts }));
    },
    createStatement(seed) {
      const current = readState();
      const existing = Array.isArray(current.statements) ? current.statements.slice() : [];
      const statement = buildDefaultStatement(current, seed);
      if (!statement.id) {
        statement.id = `statement-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
      }
      existing.push(statement);
      return writeState(Object.assign({}, current, { statements: existing }));
    },
    getStatementById(statementId) {
      const current = readState();
      return (current.statements || []).find((statement) => statement.id === statementId) || null;
    },
    upsertStatement(statementPatch) {
      const current = readState();
      const existing = Array.isArray(current.statements) ? current.statements.slice() : [];
      const fallback = buildDefaultStatement(current, statementPatch);
      const statement = Object.assign({}, fallback, statementPatch || {}, {
        updatedAt: new Date().toISOString(),
      });
      if (!statement.id) {
        statement.id = `statement-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
      }
      const index = existing.findIndex((entry) => entry.id === statement.id);
      if (index >= 0) {
        existing[index] = statement;
      } else {
        existing.push(statement);
      }
      return writeState(Object.assign({}, current, { statements: existing }));
    },
    removeStatement(statementId) {
      const current = readState();
      const remaining = (current.statements || []).filter((statement) => statement.id !== statementId);
      return writeState(Object.assign({}, current, { statements: remaining }));
    },
    getFormDraft(formKey) {
      const current = readState();
      const drafts = current && current.formDrafts && typeof current.formDrafts === 'object' ? current.formDrafts : {};
      const selected = drafts[formKey];
      return selected && typeof selected === 'object' ? Object.assign({}, selected) : {};
    },
    updateFormDraft(formKey, patch) {
      const current = readState();
      const drafts = current && current.formDrafts && typeof current.formDrafts === 'object'
        ? Object.assign({}, current.formDrafts)
        : {};
      drafts[formKey] = Object.assign({}, drafts[formKey] || {}, patch || {});
      return writeState(Object.assign({}, current, { formDrafts: drafts }));
    },
    toggleSelectedForm(formName) {
      if (formName === 'MCPD Stat Sheet') return readState();
      const current = readState();
      const forms = Array.isArray(current.selectedForms) ? current.selectedForms.slice() : [];
      const index = forms.indexOf(formName);
      if (index >= 0) {
        forms.splice(index, 1);
      } else {
        forms.push(formName);
      }
      if (!forms.includes('MCPD Stat Sheet')) forms.unshift('MCPD Stat Sheet');
      return writeState(
        Object.assign({}, current, {
          selectedForms: forms,
          packetStatus: 'forms_reviewed',
        })
      );
    },
    toggleChecklistItem(itemId) {
      const current = readState();
      const nextChecklist = (current.checklist || []).map((item) =>
        item.id === itemId ? Object.assign({}, item, { completed: !item.completed }) : item
      );
      return writeState(Object.assign({}, current, { checklist: nextChecklist }));
    },
    updatePacketStatus(status) {
      const current = readState();
      return writeState(Object.assign({}, current, { packetStatus: status || current.packetStatus || 'draft' }));
    },
  };

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function normalizeLookupKey(value) {
    return String(value || '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '');
  }

  function readJsonScript(scriptId) {
    if (Object.prototype.hasOwnProperty.call(jsonScriptCache, scriptId)) {
      return jsonScriptCache[scriptId];
    }
    const node = document.getElementById(scriptId);
    if (!node) {
      jsonScriptCache[scriptId] = null;
      return null;
    }
    try {
      jsonScriptCache[scriptId] = JSON.parse(node.textContent || 'null');
      return jsonScriptCache[scriptId];
    } catch (_err) {
      jsonScriptCache[scriptId] = null;
      return null;
    }
  }

  function normalizeRuleList(value) {
    if (Array.isArray(value)) {
      return value.map((item) => String(item || '').trim()).filter(Boolean);
    }
    return String(value || '')
      .split(/[\n,]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function normalizeCallTypeRules(rawRules) {
    if (!rawRules || typeof rawRules !== 'object') {
      return null;
    }
    const entries = Array.isArray(rawRules) ? rawRules : Object.values(rawRules);
    const normalized = {};
    entries.forEach((entry) => {
      if (!entry || typeof entry !== 'object' || entry.active === false) {
        return;
      }
      const title = String(entry.title || entry.name || '').trim();
      const slug = String(entry.slug || title)
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
      if (!slug || !title) {
        return;
      }
      normalized[slug] = {
        slug,
        title,
        shortLabel: String(entry.shortLabel || entry.short_label || title).trim(),
        description: String(entry.description || '').trim(),
        statutes: normalizeRuleList(entry.statutes),
        recommendedForms: normalizeRuleList(entry.recommendedForms || entry.recommended_forms),
        optionalForms: normalizeRuleList(entry.optionalForms || entry.optional_forms),
        checklistItems: normalizeRuleList(entry.checklistItems || entry.checklist_items),
      };
    });
    return Object.keys(normalized).length ? normalized : null;
  }

  function readMobileFormCatalog() {
    const parsed = readJsonScript('mobile-form-catalog-data');
    return Array.isArray(parsed) ? parsed : [];
  }

  function readDomesticSchema() {
    const parsed = readJsonScript('mobile-domestic-schema-data');
    return parsed && Array.isArray(parsed.sections) ? parsed : { sections: [] };
  }

  function resolveLegacyFormAlias(title) {
    const normalized = normalizeLookupKey(title);
    return legacyFormAliases[normalized] || title;
  }

  function resolveCatalogRecord(catalog, title) {
    const canonicalTitle = resolveLegacyFormAlias(title);
    const wanted = normalizeLookupKey(canonicalTitle);
    return (
      catalog.find((item) => normalizeLookupKey(item.title) === wanted)
      || null
    );
  }

  function CallTypeCard(rule, isActive) {
    return `
      <button class="mobile-call-type-card ${isActive ? 'is-active' : ''}" type="button" data-call-type="${escapeHtml(rule.slug)}">
        <span class="mobile-call-type-kicker">${escapeHtml(rule.shortLabel)}</span>
        <strong>${escapeHtml(rule.title)}</strong>
      </button>
    `;
  }

  function FormRecommendationCard(formName, variant, isSelected, record) {
    const isLocked = variant === 'always-required';
    const metadata = record
      ? record.category
      : isLocked ? 'Required for every incident' : 'Needs review';
    const labelText = isLocked ? 'Always Required' : variant === 'optional' ? 'Optional' : 'Recommended';
    const cardClass = isLocked
      ? 'is-always-required is-selected'
      : `${variant === 'optional' ? 'is-optional' : 'is-recommended'} ${isSelected ? 'is-selected' : ''}`;
    return `
      <article class="mobile-form-rec-card ${cardClass}">
        <div class="mobile-form-rec-copy">
          <span class="mobile-form-rec-label">${escapeHtml(labelText)}</span>
          <strong>${escapeHtml(formName)}</strong>
          <p>${escapeHtml(metadata)}</p>
        </div>
        ${isLocked
          ? `<span class="mobile-form-toggle is-locked">✓ Always Required</span>`
          : `<button class="mobile-form-toggle" type="button" data-form-name="${escapeHtml(formName)}">${isSelected ? 'Selected' : 'Add To Packet'}</button>`
        }
      </article>
    `;
  }

  function SelectedFormStatusCard(record) {
    const sourceLabel = record.sourceKind === 'xfa' ? 'XFA' : record.sourceKind === 'acroform' ? 'PDF' : 'Static';
    return `
      <article class="mobile-selected-form-card">
        <div class="mobile-selected-form-copy">
          <div class="mobile-selected-form-head">
            <span class="mobile-selected-form-status is-${escapeHtml(record.status.toLowerCase())}">${escapeHtml(record.statusLabel)}</span>
            <span class="mobile-selected-form-source">${escapeHtml(sourceLabel)}</span>
          </div>
          <strong>${escapeHtml(record.title)}</strong>
          <p>${escapeHtml(record.mappingNote)}</p>
          <div class="mobile-highlight-row">
            <span class="mobile-highlight-pill">${escapeHtml(record.category)}</span>
            ${record.isReady ? '<span class="mobile-highlight-pill">Ready</span>' : '<span class="mobile-highlight-pill">Preview</span>'}
          </div>
        </div>
        <div class="mobile-selected-form-actions">
          <a class="mobile-selected-form-link is-primary" href="${escapeHtml(record.editUrl)}">Edit</a>
          <a class="mobile-selected-form-link" href="${escapeHtml(record.previewUrl)}">Preview</a>
        </div>
      </article>
    `;
  }

  function PersonCard(person, editHref) {
    return `
      <article class="mobile-person-card">
        <div class="mobile-person-card-copy">
          <span class="mobile-person-role">${escapeHtml(person.role || 'Role pending')}</span>
          <strong>${escapeHtml(person.name || 'Unnamed person')}</strong>
          <div class="mobile-person-meta">
            ${person.dob ? `<span>DOB ${escapeHtml(person.dob)}</span>` : ''}
            ${person.state ? `<span>${escapeHtml(person.state)}</span>` : ''}
          </div>
          ${person.idNumber ? `<p>${escapeHtml(person.idNumber)}</p>` : ''}
        </div>
        <a class="mobile-person-edit-link" href="${escapeHtml(editHref)}">Edit</a>
      </article>
    `;
  }

  function RoleSelector(selectedRole) {
    return `
      <div class="mobile-field-block">
        <span>Role</span>
        <div class="mobile-role-chip-group">
          ${personRoleOptions.map((role) => `
            <button class="mobile-role-chip ${selectedRole === role ? 'is-active' : ''}" type="button" data-role-choice="${escapeHtml(role)}">
              ${escapeHtml(role)}
            </button>
          `).join('')}
        </div>
        <input type="hidden" name="role" value="${escapeHtml(selectedRole || 'Witness')}" />
      </div>
    `;
  }

  function IdScanLauncher() {
      return `
        <section class="mobile-id-scan-launcher">
          <div class="mobile-id-scan-copy">
            <strong>ID scan</strong>
            <p>Open the live scanner or paste barcode text. Manual correction stays available.</p>
          </div>
          <button class="mobile-scan-button is-camera" type="button" data-id-scan-camera>Open Live ID Scanner</button>
          <input type="file" accept="image/*" capture="environment" data-id-scan-file hidden />
          <section class="mobile-id-live-scanner" data-id-live-scanner hidden>
            <div class="mobile-id-live-scanner-copy">
              <strong>Live scanner</strong>
              <span>Hold the barcode side of the ID inside the frame.</span>
            </div>
            <div class="mobile-id-live-scanner-frame">
              <video class="mobile-id-live-video" data-id-live-video playsinline muted></video>
            </div>
            <div class="mobile-id-live-scanner-actions">
              <button class="mobile-outline-button" type="button" data-id-scan-cancel>Cancel Scanner</button>
            </div>
          </section>
          <textarea class="mobile-text-input mobile-text-area" data-id-scan-raw rows="4" placeholder="Paste AAMVA barcode text here"></textarea>
          <div class="mobile-id-scan-actions">
            <button class="mobile-scan-button" type="button" data-id-scan-apply>Use Scan Text</button>
            <button class="mobile-outline-button" type="button" data-id-scan-clear>Clear</button>
        </div>
        <p class="mobile-inline-note" data-id-scan-status>Reads name, DOB, address, ID number, and state. Manual entry always works.</p>
      </section>
    `;
  }

  function extractAamvaField(text, code) {
    const source = String(text || '').replace(/\r/g, '\n');
    const pattern = new RegExp(`(?:^|\\n)${code}([^\\n]+)`, 'i');
    const match = source.match(pattern);
    return match ? String(match[1] || '').trim() : '';
  }

  function normalizeAamvaDate(value) {
    const digits = String(value || '').replace(/\D/g, '');
    if (digits.length !== 8) return '';
    if (Number(digits.slice(0, 4)) > 1900) {
      return `${digits.slice(0, 4)}-${digits.slice(4, 6)}-${digits.slice(6, 8)}`;
    }
    return `${digits.slice(4, 8)}-${digits.slice(0, 2)}-${digits.slice(2, 4)}`;
  }

  function extractLooseScanField(text, labels) {
    const source = String(text || '').replace(/\r/g, '\n');
    for (const label of labels || []) {
      const pattern = new RegExp(`(?:^|\\n)\\s*${label}\\s*[:#-]?\\s*([^\\n]+)`, 'i');
      const match = source.match(pattern);
      if (match && String(match[1] || '').trim()) return String(match[1] || '').trim();
    }
    return '';
  }

  function normalizeScannedName(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    if (raw.includes(',')) {
      return raw
        .split(',')
        .map((part) => part.trim())
        .filter(Boolean)
        .slice(0, 3)
        .join(' ')
        .replace(/\s+/g, ' ')
        .trim();
    }
    return raw.replace(/\^/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function parseAamvaBarcodeText(rawValue) {
    const raw = String(rawValue || '').trim();
    if (!raw) return null;
    const fullName = extractAamvaField(raw, 'DCT') || extractAamvaField(raw, 'DAA');
    const firstName = extractAamvaField(raw, 'DAC');
    const middleName = extractAamvaField(raw, 'DAD');
    const lastName = extractAamvaField(raw, 'DCS');
    const street = extractAamvaField(raw, 'DAG');
    const city = extractAamvaField(raw, 'DAI');
    const state = extractAamvaField(raw, 'DAJ');
    const postal = extractAamvaField(raw, 'DAK');
    const idNumber = extractAamvaField(raw, 'DAQ');
    const dob = normalizeAamvaDate(extractAamvaField(raw, 'DBB'));
    const looseName = extractLooseScanField(raw, ['NAME', 'CUSTOMER NAME', 'DRIVER NAME']);
    const looseDob = normalizeAamvaDate(extractLooseScanField(raw, ['DOB', 'DATE OF BIRTH', 'BIRTH DATE']));
    const looseId = extractLooseScanField(raw, ['DL', 'DLN', 'ID', 'ID NO', 'LICENSE', 'LICENSE NO']);
    const looseStreet = extractLooseScanField(raw, ['ADDRESS', 'ADDR', 'STREET']);
    const looseCity = extractLooseScanField(raw, ['CITY']);
    const looseState = extractLooseScanField(raw, ['STATE']);
    const loosePostal = extractLooseScanField(raw, ['ZIP', 'ZIPCODE', 'POSTAL']);
    const name = normalizeScannedName(fullName || looseName || [firstName, middleName, lastName].filter(Boolean).join(' '));
    const address = [street || looseStreet, [city || looseCity, state || looseState, postal || loosePostal].filter(Boolean).join(' ')].filter(Boolean).join(', ').trim();
    const parsed = {
      name,
      dob: dob || looseDob,
      address,
      idNumber: idNumber || looseId,
      state: state || looseState,
    };
    const populatedKeys = Object.values(parsed).filter((value) => String(value || '').trim()).length;
    return populatedKeys ? parsed : null;
  }

  function statementReviewedText(statement) {
    return String(
      statement.reviewedDraft
      || statement.formattedDraft
      || statement.formattedStatement
      || statement.reviewedStatement
      || ''
    ).trim();
  }

  function statementInitialsValue(statement) {
    return String(statement.initialsDataUrl || statement.initials || '').trim();
  }

  function statementSignatureValue(statement) {
    return String(statement.signatureDataUrl || statement.signature || '').trim();
  }

  function statementWitnessSignatureValue(statement) {
    return String(statement.witnessingSignatureDataUrl || statement.officerSignature || statement.witnessSignature || '').trim();
  }

  function readZxingResultText(result) {
    if (!result) return '';
    if (typeof result.getText === 'function') return String(result.getText() || '').trim();
    return String(result.text || '').trim();
  }

  let zxingLoadPromise = null;
  function loadZxingLibrary() {
    if (window.ZXingBrowser) return Promise.resolve(window.ZXingBrowser);
    if (zxingLoadPromise) return zxingLoadPromise;
    const src = window.MCPD_ZXING_SRC || '/static/vendor/zxing-browser.min.js';
    zxingLoadPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.async = true;
      script.onload = () => resolve(window.ZXingBrowser || null);
      script.onerror = () => reject(new Error('Scanner library unavailable'));
      document.head.appendChild(script);
    });
    return zxingLoadPromise;
  }

  async function detectBarcodeTextFromImageFile(file) {
    if (!file) return '';
    if (typeof BarcodeDetector !== 'undefined') {
      const detector = new BarcodeDetector({
        formats: ['pdf417', 'qr_code', 'code_128', 'code_39', 'ean_13', 'upc_a'],
      });
      const bitmap = await createImageBitmap(file);
      try {
        const results = await detector.detect(bitmap);
        const hit = Array.isArray(results) ? results.find((item) => String(item.rawValue || '').trim()) : null;
        if (hit && String(hit.rawValue || '').trim()) return String(hit.rawValue || '').trim();
      } finally {
        if (bitmap && typeof bitmap.close === 'function') bitmap.close();
      }
    }

    let zxing = null;
    try {
      zxing = await loadZxingLibrary();
    } catch (_error) {
      zxing = null;
    }
    if (!zxing || typeof zxing.BrowserPDF417Reader !== 'function' || typeof URL === 'undefined' || typeof URL.createObjectURL !== 'function') {
      return '';
    }
    const objectUrl = URL.createObjectURL(file);
    try {
      const reader = new zxing.BrowserPDF417Reader();
      const result = await reader.decodeFromImageUrl(objectUrl);
      if (!result) return '';
      if (typeof result.getText === 'function') return String(result.getText() || '').trim();
      return String(result.text || '').trim();
    } catch (_error) {
      return '';
    } finally {
      if (typeof URL.revokeObjectURL === 'function') URL.revokeObjectURL(objectUrl);
    }
  }

  function VoiceInputControl(sectionKey, supported) {
    return `
      <button class="mobile-voice-button" type="button" data-voice-target="${escapeHtml(sectionKey)}" ${supported ? '' : 'disabled'}>
        ${supported ? 'Speak Facts' : 'Voice Unavailable'}
      </button>
    `;
  }

  function NarrativeEditor(value, editMode) {
    return `
      <div class="mobile-narrative-editor ${editMode ? 'is-editing' : ''}">
        <textarea class="mobile-text-input mobile-text-area mobile-narrative-text" data-narrative-editor ${editMode ? '' : 'readonly'} rows="9">${escapeHtml(value || '')}</textarea>
      </div>
    `;
  }

  function InitialsPad(currentValue) {
    return `
      <article class="mobile-pad-card">
        <div class="mobile-pad-head">
          <strong>Declarant Initials</strong>
          <span>Use the same initials on each used statement page.</span>
        </div>
        <canvas class="mobile-signature-canvas is-initials" data-initials-pad width="520" height="180"></canvas>
        <div class="mobile-pad-actions">
          <button class="mobile-outline-button" type="button" data-pad-clear="initials">Clear Initials</button>
          ${currentValue ? '<span class="mobile-pad-status">Initials captured</span>' : '<span class="mobile-pad-status">Awaiting initials</span>'}
        </div>
      </article>
    `;
  }

  function SignaturePad(label, dataKey, currentValue) {
    return `
      <article class="mobile-pad-card">
        <div class="mobile-pad-head">
          <strong>${escapeHtml(label)}</strong>
          <span>Capture the handwritten mark for the real OPNAV signature block.</span>
        </div>
        <canvas class="mobile-signature-canvas" data-signature-pad="${escapeHtml(dataKey)}" width="520" height="220"></canvas>
        <div class="mobile-pad-actions">
          <button class="mobile-outline-button" type="button" data-pad-clear="${escapeHtml(dataKey)}">Clear</button>
          ${currentValue ? '<span class="mobile-pad-status">Captured</span>' : '<span class="mobile-pad-status">Awaiting signature</span>'}
        </div>
      </article>
    `;
  }

  function cleanStatementSentences(value) {
    return String(value || '')
      .replace(/\r/g, '\n')
      .split(/\n+/)
      .map((entry) => entry.trim())
      .filter(Boolean)
      .map((entry) => {
        const trimmed = entry.replace(/\s+/g, ' ');
        return /[.!?]$/.test(trimmed) ? trimmed : `${trimmed}.`;
      });
  }

  function ensureTerminalPunctuation(value) {
    const text = String(value || '').replace(/\s+/g, ' ').trim();
    if (!text) return '';
    return /[.!?]$/.test(text) ? text : `${text}.`;
  }

  function formatDisplayDate(value) {
    const raw = String(value || '').trim();
    const parts = raw.split('-');
    if (parts.length === 3) {
      return `${parts[1]}/${parts[2]}/${parts[0]}`;
    }
    return raw;
  }

  function prefixedSentence(prefix, value) {
    const cleaned = String(value || '').replace(/\s+/g, ' ').trim();
    if (!cleaned) return '';
    if (cleaned.toLowerCase().startsWith(prefix.toLowerCase())) {
      return ensureTerminalPunctuation(cleaned);
    }
    return ensureTerminalPunctuation(`${prefix} ${cleaned}`);
  }

  function inferStatementSubject(statement, incidentState) {
    const explicit = String(statement.statementSubject || '').trim();
    if (explicit) return explicit;
    return incidentSummaryFallback(incidentState) || 'the incident';
  }

  function buildVoluntaryStatementDraft(statement, incidentState) {
    const basics = incidentState.incidentBasics || {};
    const date = formatDisplayDate(statement.statementDate || basics.occurredDate || '');
    const time = String(statement.statementTime || basics.occurredTime || '').trim();
    const location = String(statement.location || basics.location || '').trim();
    const subject = inferStatementSubject(statement, incidentState);
    const speaker = String(statement.speaker || 'Unknown Declarant').trim();
    const ssn = String(statement.speakerSsn || '').trim();
    const officerName = String(statement.officerName || 'the undersigned officer').trim();
    const officerBadge = String(statement.officerBadge || '').trim();
    const officerLabel = officerBadge ? `${officerName}, badge ${officerBadge}` : officerName;
    const lead = [
      `I, ${speaker}${ssn ? `, SSN ${ssn},` : ','} make the following free and voluntary statement to ${officerLabel}, whom I know to be a police officer with the Marine Corps Police Department, MCLB Albany, Georgia.`,
      'I make this statement of my own free will and without any threats or promises extended to me.',
      statement.variant === 'traffic'
        ? ensureTerminalPunctuation(`I fully understand that this statement is given concerning my knowledge of a traffic accident${date ? ` that occurred on ${date}` : ''}${time ? ` at approximately ${time}` : ''}${location ? ` at ${location}` : ''}`)
        : ensureTerminalPunctuation(`I fully understand that this statement is given concerning my knowledge of ${subject || 'the incident'}${date ? ` that occurred on ${date}` : ''}${time ? ` at approximately ${time}` : ''}${location ? ` at ${location}` : ''}`),
    ].join(' ');

    const bodySentences = cleanStatementSentences(statement.plainLanguage);
    const body = bodySentences.join(' ');
    const trafficSection = statement.variant === 'traffic'
      ? trafficStatementQuestions
          .map((question, index) => {
            const answer = String((statement.trafficAnswers || {})[`q${index + 1}`] || '').trim();
            return answer ? `Q. ${question} A. ${answer}${/[.!?]$/.test(answer) ? '' : '.'}` : '';
          })
          .filter(Boolean)
          .join(' ')
      : '';
    return [lead, body, trafficSection].filter(Boolean).join('\n\n').trim();
  }

  function wrapStatementLines(value, maxLines, maxChars) {
    const source = String(value || '').replace(/\s+/g, ' ').trim();
    const words = source ? source.split(' ') : [];
    const lines = [];
    let currentLine = '';
    words.forEach((word) => {
      const candidate = currentLine ? `${currentLine} ${word}` : word;
      if (candidate.length > maxChars && currentLine) {
        lines.push(currentLine);
        currentLine = word;
      } else {
        currentLine = candidate;
      }
    });
    if (currentLine) {
      lines.push(currentLine);
    }
    return lines.slice(0, maxLines);
  }

  function fillUnusedStatementSpace(lines, pageCapacity) {
    const padded = lines.slice();
    if (!padded.length) {
      padded.push('/// UNUSED SPACE ///');
    }
    while (padded.length < pageCapacity) {
      padded.push('/// UNUSED SPACE ///');
    }
    return padded;
  }

  function statementPreviewPages(statement, incidentState) {
    const config = statementConfig(statement.variant);
    const draft = buildVoluntaryStatementDraft(statement, incidentState);
    const wrappedLines = wrapStatementLines(draft, config.bodyCapacity, config.bodyLineLength);
    const pages = [];
    let cursor = 0;
    config.bodyPages.forEach((page) => {
      const chunk = wrappedLines.slice(cursor, cursor + page.lineFields.length);
      cursor += page.lineFields.length;
      const needsFill = chunk.length > 0 || (pages.length === 0 && !wrappedLines.length);
      pages.push({
        pageNumber: page.pageNumber,
        title: page.title,
        lines: needsFill ? fillUnusedStatementSpace(chunk, page.lineFields.length) : [],
        initialField: page.initialField,
      });
    });
    pages.push({
      pageNumber: config.signaturePage.pageNumber,
      title: config.signaturePage.title,
      lines: [],
      initialField: config.signaturePage.initialField,
      signatureField: config.signaturePage.signatureField,
      witnessSignatureField: config.signaturePage.witnessSignatureField,
    });
    return {
      config,
      draft,
      pages,
      overflow: wrappedLines.length > config.bodyCapacity,
      usedPageCount: pages.filter((page) => page.lines.length || page.signatureField).length,
    };
  }

  function statementStatus(statement, incidentState) {
    const preview = statementPreviewPages(statement, incidentState);
    if (statementSignatureValue(statement) && statementInitialsValue(statement) && statementWitnessSignatureValue(statement)) return 'Signed';
    if (statementReviewedText(statement) || preview.draft) return 'In Review';
    if (statement.plainLanguage) return 'Drafted';
    return 'Not Started';
  }

  function StatementSummaryCard(statement, incidentState, editHref, reviewHref) {
    const preview = statementPreviewPages(statement, incidentState);
    return `
      <article class="mobile-statement-summary-card">
        <div class="mobile-statement-summary-copy">
          <span class="mobile-person-role">${escapeHtml(statementStatus(statement, incidentState))}</span>
          <strong>${escapeHtml(statement.formTitle)}</strong>
          <div class="mobile-person-meta">
              <span>${escapeHtml(statement.speaker || statement.personName || 'Speaker pending')}</span>
              <span>${escapeHtml(`${preview.pages.length} pages`)}</span>
              <span>${escapeHtml(statement.variant === 'traffic' ? 'Traffic format' : 'Standard format')}</span>
            </div>
            <p>${escapeHtml((statementReviewedText(statement) || statement.plainLanguage || 'Not started').slice(0, 120))}</p>
        </div>
        <div class="mobile-selected-form-actions">
          <a class="mobile-selected-form-link is-primary" href="${escapeHtml(editHref)}">Edit</a>
          <a class="mobile-selected-form-link" href="${escapeHtml(reviewHref)}">Review</a>
        </div>
      </article>
    `;
  }

  function StatementPagePreview(page, statement) {
    return `
      <article class="mobile-statement-page-card">
        <div class="mobile-statement-page-head">
          <strong>${escapeHtml(`Page ${page.pageNumber}`)}</strong>
          <span>${escapeHtml(page.title)}</span>
        </div>
        ${
          page.lines && page.lines.length
            ? `<div class="mobile-statement-line-grid">
                ${page.lines.map((line, index) => `
                  <div class="mobile-statement-line">
                    <span class="mobile-statement-line-number">${index + 1}</span>
                    <span class="mobile-statement-line-text">${escapeHtml(line)}</span>
                  </div>
                `).join('')}
              </div>`
            : '<div class="mobile-empty-card">Signature and attestation space only on this page.</div>'
        }
        <div class="mobile-statement-page-footer">
          <span>Initial field: ${escapeHtml(page.initialField)}</span>
          ${statement.initialsDataUrl ? '<span>Initials ready</span>' : '<span>Initials pending</span>'}
          ${page.signatureField ? `<span>Signature field: ${escapeHtml(page.signatureField)}</span>` : ''}
        </div>
      </article>
    `;
  }

  function buildNarrativeDraft(state) {
    const basics = state.incidentBasics || {};
    const facts = Array.isArray(state.facts) ? state.facts : [];
    const persons = Array.isArray(state.persons) ? state.persons : [];
    const victimPerson = persons.find((entry) => String((entry || {}).role || '').trim().toLowerCase() === 'victim') || null;
    const suspectPerson = persons.find((entry) => String((entry || {}).role || '').trim().toLowerCase() === 'suspect') || null;
    const factMap = {};
    facts.forEach((entry) => {
      if (!entry || !entry.id) return;
      const value = String(entry.value || '').trim();
      if (value) {
        factMap[entry.id] = value;
      }
    });

    const lines = [];
    const introParts = [];
    if (basics.occurredDate) introParts.push(`On ${formatDisplayDate(basics.occurredDate)}`);
    if (basics.occurredTime) introParts.push(`at approximately ${basics.occurredTime}`);
    if (basics.location) introParts.push(`at ${basics.location}`);
    const summary = incidentSummaryFallback(state) || 'the reported incident';
    if (introParts.length || summary) {
      const introLead = introParts.join(' ');
      lines.push(ensureTerminalPunctuation(introLead ? `${introLead}, MCPD responded regarding ${summary}` : `MCPD responded regarding ${summary}`));
    }
    if (factMap.what_happened) lines.push(ensureTerminalPunctuation(factMap.what_happened));
    if (factMap.complainant) lines.push(prefixedSentence('The complainant stated', factMap.complainant));
    if (factMap.victim) lines.push(prefixedSentence('The victim stated', factMap.victim));
    else if (victimPerson && String(victimPerson.name || '').trim()) lines.push(ensureTerminalPunctuation(`The identified victim was ${String(victimPerson.name || '').trim()}`));
    if (factMap.suspect) lines.push(prefixedSentence('The suspect stated', factMap.suspect));
    else if (suspectPerson && String(suspectPerson.name || '').trim()) lines.push(ensureTerminalPunctuation(`The identified suspect was ${String(suspectPerson.name || '').trim()}`));
    if (factMap.officer_actions) lines.push(prefixedSentence('Officers took the following actions', factMap.officer_actions));
    if (factMap.disposition) lines.push(prefixedSentence('The incident was concluded with the following disposition', factMap.disposition));
    return lines.join('\n\n').trim();
  }

  function StickyWizardBar(options) {
    return `
      <div class="mobile-wizard-bar">
        <div class="mobile-wizard-copy">
          <strong>${escapeHtml(options.title || 'Incident Flow')}</strong>
          <span>${escapeHtml(options.detail || '')}</span>
        </div>
        <div class="mobile-wizard-actions">
          ${options.backHref ? `<a class="mobile-wizard-link" href="${escapeHtml(options.backHref)}">${escapeHtml(options.backLabel || 'Back')}</a>` : ''}
          ${options.disabled ? `<button class="mobile-wizard-cta is-disabled" type="button" disabled>${escapeHtml(options.nextLabel || 'Next')}</button>` : ''}
          ${!options.disabled && options.nextHref && options.nextHref !== '#' ? `<a class="mobile-wizard-cta" href="${escapeHtml(options.nextHref)}">${escapeHtml(options.nextLabel || 'Next')}</a>` : ''}
          ${!options.disabled && options.nextHref === '#' ? `<button class="mobile-wizard-cta" type="button">${escapeHtml(options.nextLabel || 'Next')}</button>` : ''}
        </div>
      </div>
    `;
  }

  function bindSignatureCanvas(canvas, onChange) {
    if (!canvas) return;
    const context = canvas.getContext('2d');
    if (!context) return;
    context.lineCap = 'round';
    context.lineJoin = 'round';
    context.strokeStyle = '#16210f';
    context.lineWidth = canvas.hasAttribute('data-initials-pad') ? 4 : 3;
    let drawing = false;

    function pointFromEvent(event) {
      const rect = canvas.getBoundingClientRect();
      const source = event.touches ? event.touches[0] : event;
      return {
        x: ((source.clientX - rect.left) / rect.width) * canvas.width,
        y: ((source.clientY - rect.top) / rect.height) * canvas.height,
      };
    }

    function start(event) {
      drawing = true;
      const point = pointFromEvent(event);
      context.beginPath();
      context.moveTo(point.x, point.y);
      event.preventDefault();
    }

    function move(event) {
      if (!drawing) return;
      const point = pointFromEvent(event);
      context.lineTo(point.x, point.y);
      context.stroke();
      event.preventDefault();
    }

    function stop() {
      if (!drawing) return;
      drawing = false;
      if (typeof onChange === 'function') {
        onChange(canvas.toDataURL('image/png'));
      }
    }

    canvas.addEventListener('pointerdown', start);
    canvas.addEventListener('pointermove', move);
    canvas.addEventListener('pointerup', stop);
    canvas.addEventListener('pointerleave', stop);
    canvas.addEventListener('touchstart', start, { passive: false });
    canvas.addEventListener('touchmove', move, { passive: false });
    canvas.addEventListener('touchend', stop, { passive: false });
  }

  function currentRule(state) {
    return state.callType ? callTypeRules[state.callType] || null : null;
  }

  function clearSessionAfterSend() {
    stateCache = null;
    window.sessionStorage.removeItem(STORAGE_KEY);
  }

  function packetValidationCard(title, items, variant) {
    if (!Array.isArray(items) || !items.length) return '';
    return `
      <article class="mobile-packet-validation-card is-${escapeHtml(variant || 'warning')}">
        <div class="mobile-packet-validation-head">
          <strong>${escapeHtml(title)}</strong>
          <span>${escapeHtml(`${items.length} ${items.length === 1 ? 'item' : 'items'}`)}</span>
        </div>
        <div class="mobile-validation-list">
          ${items.map((item) => `
            <div class="mobile-validation-item">
              <strong>${escapeHtml(item.field || 'Packet')}</strong>
              <p>${escapeHtml(item.message || '')}</p>
            </div>
          `).join('')}
        </div>
      </article>
    `;
  }

  function shortText(value, maxLength) {
    const text = String(value || '').replace(/\s+/g, ' ').trim();
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return `${text.slice(0, Math.max(0, maxLength - 1)).trimEnd()}...`;
  }

  function incidentPrimaryFact(state) {
    return String(
      (((state.facts || []).find((entry) => entry && entry.id === 'what_happened')) || {}).value || ''
    ).trim();
  }

  function incidentSummaryFallback(state) {
    const basics = state.incidentBasics || {};
    return (
      String(basics.summary || '').trim()
      || incidentPrimaryFact(state)
      || (state.callType ? `${state.callType.replace(/-/g, ' ')} call` : '')
    );
  }

  function domesticFieldNameKey(field) {
    return String((field && field.name) || '').trim();
  }

  function domesticFieldRawName(field) {
    return String((field && (field.raw_name || field.rawName || field.label || field.name)) || '').trim();
  }

  function domesticRadioGroupKey(field) {
    const groups = field && Array.isArray(field.group_names)
      ? field.group_names
      : field && Array.isArray(field.groupNames)
      ? field.groupNames
      : [];
    if (groups.length) return String(groups[0] || '').trim();
    const name = domesticFieldNameKey(field);
    const match = name.match(/^(.*)\.(?:Victim|Suspect|Child|Other|IncidentOther|Clean|Disarray|Dirty|NotSeen|This\.1|Prior\.1|This\.2|Prior\.2|Current\.1|Expired\.1|Current\.2|Expired\.2|VNN|VR|VFA|VMTF|SNN|SR|SFA|SMTF|VictimInj|SuspecInj|Male|Female|VictimInj1|SuspecInj1|Male1|Female1)$/);
    return match ? match[1] : '';
  }

  function domesticFieldValue(draft, field) {
    const key = domesticFieldNameKey(field);
    if (Object.prototype.hasOwnProperty.call(draft || {}, key)) {
      return draft[key];
    }
    const rawName = domesticFieldRawName(field);
    if (rawName && Object.prototype.hasOwnProperty.call(draft || {}, rawName)) {
      return draft[rawName];
    }
    return field && field.type === 'checkbox' ? false : '';
  }

  function domesticFieldFriendlyLabel(field) {
    const key = domesticFieldNameKey(field).replace(/^form1\./, '');
    const rawLabel = String((field && field.label) || '').trim();
    const friendlyLookup = {
      'VicName': 'Victim Name',
      'SponsorSSN': "Sponsor SSN",
      'RespTime': 'Response Time',
      'ResponseDate': 'Response Date',
      'Reported': 'Initial Incident / Violation Reported',
      'Who': 'By Whom',
      'Describe': 'Victim Condition Notes',
      'Said': 'Victim Excited Utterances',
      'Describe1': 'Suspect Condition Notes',
      'Said1': 'Suspect Spontaneous Admissions',
      'Where': 'Other Location',
      'Details': 'Scene Details',
      'Years': 'Years Together',
      'Months': 'Months Together',
      'Incident.1': 'Incidents Against Victim',
      'Incident.2': 'Incidents Against Suspect',
      'Incident.3': 'Incidents Against Child',
      'No.Separate': 'Separations Over 24 Hours',
      'DesFirstIncident.1': 'Describe The First Marked Incident',
      'DesFirstIncident.2': 'Describe The Second Marked Incident',
      'Present.1': 'Adult Witnesses Present',
      'Present.2': 'Child Witnesses Present',
      'Ages': 'Witness Ages',
      'TotTaken': 'Total Statements Taken',
      'TakenBy': 'Photographs Taken By',
      'TypeEvidence.1': 'Evidence Seized Description',
      'TypeEvidence.2': 'Safekeeping Description',
      'OtherDesc': 'Other Evidence Description',
      'Location': 'Temporary Address / Shelter Location',
      'OtherPhone': 'Temporary Contact Phone',
      'LeaveAdd': 'Leaving Area Address',
      'LeavePhone': 'Leaving Area Phone',
      'FromDate': 'Leaving Area From',
      'ToDate': 'Leaving Area To',
      'FirstAidBy.1': 'Victim First Aid By',
      'Facility.1': 'Victim Treatment Facility',
      'FirstAidBy.2': 'Suspect First Aid By',
      'Facility.2': 'Suspect Treatment Facility',
      'OtherInfo': 'Other Medical / Scene Information',
      'MPName': 'Military Police Officer Name',
      'MPSection': 'Military Police Section',
      'SupName': 'Supervisor Name',
      'SupSection': 'Supervisor Section',
      'InjName': 'Injured Party Name',
      'InjExplain': 'Other Injury Explanation',
      'InjName1': 'Second Injured Party Name',
      'InjExplain1': 'Second Injury Explanation',
    };
    if (friendlyLookup[key]) return friendlyLookup[key];
    if (rawLabel && !/^[A-Za-z0-9_.]+$/.test(rawLabel)) {
      return rawLabel.replace(/\s*:\s*$/, '');
    }
    return key
      .replace(/\.+/g, ' ')
      .replace(/__/g, ' ')
      .replace(/([a-z])([A-Z])/g, '$1 $2')
      .replace(/\s+/g, ' ')
      .trim() || 'Field';
  }

  function domesticFieldPlaceholder(field) {
    return `Enter ${domesticFieldFriendlyLabel(field).toLowerCase()}`;
  }

  function domesticTakeFields(fields, predicate) {
    const picked = [];
    const remaining = [];
    (fields || []).forEach((field) => {
      if (predicate(field)) picked.push(field);
      else remaining.push(field);
    });
    return { picked, remaining };
  }

  function domesticTakeFieldsByNames(fields, names) {
    const wanted = new Set((names || []).map((name) => String(name || '').trim()));
    return domesticTakeFields(fields, (field) => wanted.has(domesticFieldNameKey(field).replace(/^form1\./, '')));
  }

  function buildDomesticGuidedSteps(schema) {
    const allFields = (schema && Array.isArray(schema.sections))
      ? schema.sections.flatMap((section) => Array.isArray(section.fields) ? section.fields : [])
      : [];
    let remaining = allFields.slice();
    const steps = [];
    const addStep = (title, note, names) => {
      const result = domesticTakeFieldsByNames(remaining, names);
      remaining = result.remaining;
      if (result.picked.length) {
        steps.push({ title, note, fields: result.picked });
      }
    };

    addStep('Response details', 'Confirm the dispatch details and domestic header fields.', [
      'SupInitial.1', 'VicName', 'SponsorSSN', 'CCN', 'RespTime', 'ResponseDate', 'Reported',
    ]);
    addStep('Who was involved', 'Identify who the domestic incident involved.', [
      'RadioButtonList.Victim', 'RadioButtonList.Suspect', 'RadioButtonList.Child', 'RadioButtonList.Other', 'Who',
    ]);
    addStep('Victim condition', 'Capture the victim demeanor, appearance, and substance-use indicators.', [
      'SupInitial.2', 'Angry', 'Apologetic', 'Crying', 'Fearfull', 'Hysterical', 'Calm', 'Afraid', 'Irrational',
      'Nervous', 'Threat', 'Breathing', 'Sweating', 'Pregnant', 'Ill', 'Other', 'Torn', 'Disheveled', 'Dirty',
      'Other1', 'Drug', 'Perscript', 'Illicit', 'Unknown', 'Alcohol', 'Light', 'Mod', 'Intox',
    ]);
    addStep('Victim statements', 'Capture the victim notes and excited utterances.', ['Describe', 'Said']);
    addStep('Suspect condition', 'Capture the suspect demeanor, appearance, and substance-use indicators.', [
      'Angry1', 'Apologetic1', 'Crying1', 'Fearful1', 'Hysterical1', 'Calm1', 'Afraid1', 'Irrational1',
      'Nervous1', 'Threat1', 'Breathing1', 'Sweating1', 'Pregnant1', 'Ill1', 'Other2', 'Torn1', 'Disheveled1',
      'Dirty1', 'Other3', 'Drug1', 'Perscript1', 'Illicit1', 'Unknown1', 'Alcohol1', 'Light1', 'Mod1', 'Intox1',
    ]);
    addStep('Suspect statements', 'Capture the suspect notes and spontaneous admissions.', ['Describe1', 'Said1']);
    addStep('Scene and relationship', 'Describe the scene and the relationship history.', [
      'RadioButtonList.FQ', 'RadioButtonList.IncidentOther', 'Where', 'RadioButtonList.Clean',
      'RadioButtonList.Disarray', 'RadioButtonList.Dirty', 'RadioButtonList.NotSeen', 'Details', 'SupInitial.3',
      'Married', 'Divorced', 'Separated', 'CoHab', 'Dating', 'PChild', 'PSChild', 'Years', 'Months',
    ]);
    addStep('Prior violence and weapons', 'Document prior incidents, escalation, and weapon factors.', [
      'Unreported', 'Reported__2', 'Choking', 'PSep', 'Escalating', 'Weapons', 'Knife', 'Handgun', 'Rifle',
      'Shotgun', 'Bat', 'Other__2', 'Incident.1', 'Incident.2', 'Incident.3', 'No.Separate',
      'RadioButtonList.This.1', 'RadioButtonList.Prior.1', 'DesFirstIncident.1', 'RadioButtonList.This.2',
      'RadioButtonList.Prior.2', 'DesFirstIncident.2',
    ]);
    addStep('Witnesses', 'Capture witnesses and witness statements.', [
      'SupInitial.4', 'AdultWit', 'ChildWit', 'Statement', 'Present.1', 'Ages', 'TotTaken', 'Present.2',
    ]);
    addStep('Evidence and photos', 'Document photographs, evidence, and where property was turned in.', [
      'SupInitial.5', 'CrimeScene', 'SusInj', 'VicInj', 'MM', 'Polaroid', 'TakenBy', 'Seized', 'WeaponsSeized',
      'AsEvidence', 'TypeEvidence.1', 'Safekeeping', 'TypeEvidence.2', 'TrunedInTo', 'EvRm', 'PMO', 'UnitArmory',
      'Other__3', 'OtherDesc',
    ]);
    addStep('Victim services and safety', 'Document temporary location, travel plans, and service handouts.', [
      'SupInitial.6', 'Temporary', 'Shelter', 'OtherLoc', 'Location', 'OtherPhone', 'LeavingArea', 'LeaveAdd',
      'LeavePhone', 'FromDate', 'ToDate', 'DVIP', 'VAIC', 'FVUIC',
    ]);
    addStep('Medical response', 'Capture whether treatment was needed, refused, or provided.', [
      'SupInitial.7', 'RadioButtonList.VNN', 'RadioButtonList.VR', 'RadioButtonList.VFA', 'RadioButtonList.VMTF',
      'FirstAidBy.1', 'Facility.1', 'RadioButtonList.SNN', 'RadioButtonList.SR', 'RadioButtonList.SFA',
      'RadioButtonList.SMTF', 'FirstAidBy.2', 'Facility.2',
    ]);
    addStep('Supervisor and officer information', 'Capture officers and supervisors tied to the packet.', [
      'SupInitial.8', 'OtherInfo', 'SupInitial.9', 'MPName', 'MPSection', 'SupName', 'SupSection',
    ]);
    addStep('Injury documentation', 'Document the first injured party and visible injuries.', [
      'RadioButtonList.VictimInj', 'RadioButtonList.SuspecInj', 'InjName', 'InjHeight', 'InjWeight',
      'RadioButtonList.Male', 'RadioButtonList.Female', 'Pain', 'Bruise', 'Abrasion', 'MinorCuts', 'Lacerations',
      'Fractures', 'OtherEx', 'InjExplain',
    ]);
    addStep('Second injury documentation', 'Document the second injured party only if needed.', [
      'RadioButtonList.VictimInj1', 'RadioButtonList.SuspecInj1', 'InjName1', 'InjHeight1', 'InjWeight1',
      'RadioButtonList.Male1', 'RadioButtonList.Female1', 'Pain1', 'Bruise1', 'Abrasion1', 'MinorCuts1',
      'Lacerations1', 'Fractures1', 'OtherEx1', 'InjExplain1',
    ]);

    while (remaining.length) {
      steps.push({
        title: 'Additional domestic details',
        note: 'These remaining original domestic questions still belong to the packet.',
        fields: remaining.splice(0, 8),
      });
    }
    return steps;
  }

  function isDomesticFieldRelevant(field, draft) {
    const key = domesticFieldNameKey(field).replace(/^form1\./, '');
    const truthy = (name) => {
      const value = domesticFieldValue(draft, { name: name.startsWith('form1.') ? name : `form1.${name}`, type: 'checkbox' });
      return value === true || String(value || '').trim().toLowerCase() === 'true';
    };
    const rules = {
      'Who': () => truthy('RadioButtonList.Other'),
      'Where': () => truthy('RadioButtonList.IncidentOther'),
      'Location': () => truthy('OtherLoc'),
      'OtherPhone': () => truthy('Temporary') || truthy('Shelter') || truthy('OtherLoc'),
      'LeaveAdd': () => truthy('LeavingArea'),
      'LeavePhone': () => truthy('LeavingArea'),
      'FromDate': () => truthy('LeavingArea'),
      'ToDate': () => truthy('LeavingArea'),
      'FirstAidBy.1': () => truthy('RadioButtonList.VFA'),
      'Facility.1': () => truthy('RadioButtonList.VMTF'),
      'FirstAidBy.2': () => truthy('RadioButtonList.SFA'),
      'Facility.2': () => truthy('RadioButtonList.SMTF'),
      'InjExplain': () => truthy('OtherEx'),
      'InjExplain1': () => truthy('OtherEx1'),
    };
    return rules[key] ? rules[key]() : true;
  }

  function domesticPrefillPatch(state, currentDraft) {
    const basics = state && state.incidentBasics && typeof state.incidentBasics === 'object' ? state.incidentBasics : {};
    const victim = findPrimaryPerson(state, ['Victim']);
    const suspect = findPrimaryPerson(state, ['Suspect']);
    const draft = currentDraft && typeof currentDraft === 'object' ? currentDraft : {};
    const patch = {};
    const assignIfMissing = (key, value) => {
      if (!String(draft[key] || '').trim() && String(value || '').trim()) patch[key] = value;
    };
    assignIfMissing('form1.VicName', victim && victim.name);
    assignIfMissing('form1.ResponseDate', basics.occurredDate);
    assignIfMissing('form1.RespTime', basics.arrivalTime || basics.dispatchTime || basics.occurredTime);
    assignIfMissing('form1.Reported', basics.summary || (state.callType ? state.callType.replace(/-/g, ' ') : ''));
    assignIfMissing('form1.MPName', basics.reportingOfficer);
    assignIfMissing('form1.InjName', victim && victim.name);
    assignIfMissing('form1.InjName1', suspect && suspect.name);
    return patch;
  }

  function domesticFieldInput(field, draft) {
    const key = domesticFieldNameKey(field);
    const label = domesticFieldFriendlyLabel(field);
    const fieldType = String((field && field.type) || 'text').trim().toLowerCase();
    const value = domesticFieldValue(draft, field);
    const radioGroup = domesticRadioGroupKey(field);
    if (fieldType === 'checkbox') {
      return `
        <button
          class="mobile-check-chip ${value ? 'is-active' : ''}"
          type="button"
          data-domestic-checkbox="${escapeHtml(key)}"
          ${radioGroup ? `data-domestic-radio-group="${escapeHtml(radioGroup)}"` : ''}
        >
          ${escapeHtml(label)}
        </button>
      `;
    }
    const inputType = fieldType === 'date' ? 'date' : 'text';
    if (fieldType === 'textarea') {
      return `
        <label class="mobile-field-block">
          <span>${escapeHtml(label)}</span>
          <textarea
              class="mobile-text-input mobile-text-area"
              rows="3"
              data-domestic-field="${escapeHtml(key)}"
              placeholder="${escapeHtml(domesticFieldPlaceholder(field))}"
            >${escapeHtml(String(value || ''))}</textarea>
          </label>
        `;
      }
    return `
      <label class="mobile-field-block">
        <span>${escapeHtml(label)}</span>
        <input
          class="mobile-text-input"
            type="${escapeHtml(inputType)}"
            data-domestic-field="${escapeHtml(key)}"
            value="${escapeHtml(String(value || ''))}"
            placeholder="${escapeHtml(domesticFieldPlaceholder(field))}"
          />
        </label>
      `;
    }

  function ReviewEditCard(title, summary, href, actionLabel, variant) {
    const dotOk = !variant || variant === '';
    return `
      <article class="mobile-review-card ${variant ? `is-${escapeHtml(variant)}` : ''}">
        <div class="mobile-review-copy">
          <span class="mobile-review-dot ${dotOk ? 'is-ok' : 'is-warn'}"></span>
          <strong>${escapeHtml(title)}</strong>
          <p>${escapeHtml(summary || 'Needs review')}</p>
        </div>
        <a class="mobile-review-link" href="${escapeHtml(href)}">${escapeHtml(actionLabel || 'Edit')}</a>
      </article>
    `;
  }

  function packetFormEntries(state, catalog) {
    const selected = Array.isArray(state.selectedForms) ? state.selectedForms : [];
    const drafts = state && state.formDrafts && typeof state.formDrafts === 'object' ? state.formDrafts : {};
    const statements = Array.isArray(state.statements) ? state.statements : [];
    return selected.map((title) => {
      const requestedTitle = resolveLegacyFormAlias(title);
      const record = resolveCatalogRecord(catalog, title);
      const normalized = normalizeLookupKey(requestedTitle);
      let status = String((record && record.status) || '').toUpperCase();
      let statusLabel = record && record.statusLabel ? record.statusLabel : 'Not Started';
      let sourceMode = 'catalog';
        if (normalized.includes('voluntarystatement')) {
          const statementReady = statements.length && statements.every((statement) =>
            statementReviewedText(statement)
            && statementInitialsValue(statement)
            && statementSignatureValue(statement)
            && statementWitnessSignatureValue(statement)
          );
          sourceMode = 'mobile_statement';
          status = statementReady ? 'COMPLETED' : (statements.length ? 'DRAFT' : 'NOT_STARTED');
          statusLabel = statementReady ? 'Completed' : (statements.length ? 'Draft' : 'Not Started');
        } else if (normalized.includes('domesticviolence')) {
        const domesticDraft = drafts.domesticSupplemental && typeof drafts.domesticSupplemental === 'object'
          ? drafts.domesticSupplemental
          : {};
        const hasAnyAnswer = Object.keys(domesticDraft).some((key) => {
          const value = domesticDraft[key];
          return value === true || String(value || '').trim();
        });
        sourceMode = 'mobile_domestic';
        status = hasAnyAnswer ? 'COMPLETED' : 'NOT_STARTED';
        statusLabel = hasAnyAnswer ? 'Completed' : 'Not Started';
      }
      return {
        requestedTitle,
        record,
        status,
        statusLabel,
        sourceMode,
      };
    });
  }

  function factValueMap(state) {
    const map = {};
    (Array.isArray(state.facts) ? state.facts : []).forEach(function(entry) {
      if (entry && entry.id) {
        map[entry.id] = String(entry.value || '').trim();
      }
    });
    return map;
  }

  function narrativeDetailWarnings(state) {
    const map = factValueMap(state);
    const items = [];
    if (!map.what_happened) {
      items.push({ field: 'What Happened', message: 'Main facts section is empty. Describe what occurred.' });
    }
    if (!map.officer_actions) {
      items.push({ field: 'Officer Actions', message: 'Officer actions section is blank. Document the actions you took.' });
    }
    if (!map.disposition) {
      items.push({ field: 'Disposition', message: 'Incident disposition is not recorded. Document how the call was concluded.' });
    }
    return items;
  }

  function buildPacket(state, catalog) {
    const basics = state.incidentBasics || {};
    const statements = Array.isArray(state.statements) ? state.statements : [];
    const facts = Array.isArray(state.facts) ? state.facts.filter((item) => item && String(item.value || '').trim()) : [];
    const formEntries = packetFormEntries(state, catalog).filter((entry, index, items) => {
      const key = normalizeLookupKey(entry.requestedTitle);
      return items.findIndex((candidate) => normalizeLookupKey(candidate.requestedTitle) === key) === index;
    });
    const narrative = String(state.narrative || buildNarrativeDraft(state) || '').trim();
    const errors = [];
    const warnings = [];
    const persons = Array.isArray(state.persons) ? state.persons : [];
      const domesticDraft = state && state.formDrafts && typeof state.formDrafts === 'object' && state.formDrafts.domesticSupplemental
        ? state.formDrafts.domesticSupplemental
        : (state && state.domesticSupplemental && typeof state.domesticSupplemental === 'object' ? state.domesticSupplemental : {});

    if (!String(state.callType || '').trim()) {
      errors.push({ field: 'Call Type', message: 'Select the incident call type before sending.' });
    }
    if (!String(basics.occurredDate || '').trim()) {
      errors.push({ field: 'Incident Date', message: 'Incident date is missing.' });
    }
    if (!String(basics.dispatchTime || '').trim()) {
      warnings.push({ field: 'Dispatch Time', message: 'Dispatch time is missing.' });
    }
    if (!String(basics.location || '').trim()) {
      errors.push({ field: 'Location', message: 'Incident location is missing.' });
    }
    if (!String(basics.arrivalTime || '').trim()) {
      warnings.push({ field: 'Arrival Time', message: 'Arrival time is missing.' });
    }
    if (!String(basics.reportingOfficer || '').trim()) {
      errors.push({ field: 'Reporting Officer', message: 'Reporting officer is missing.' });
    }
    if (!facts.length) {
      errors.push({ field: 'Facts Capture', message: 'Capture at least one factual section before sending.' });
    }
    if (!narrative) {
      errors.push({ field: 'Narrative', message: 'Narrative review is still blank.' });
    } else if (!state.narrativeApproved) {
      errors.push({ field: 'Narrative', message: 'Approve the narrative review before sending.' });
    }
    if (!formEntries.length) {
      errors.push({ field: 'Forms', message: 'Select at least one form for the packet.' });
    }
    const selectedFormTitles = Array.isArray(state.selectedForms) ? state.selectedForms : [];
    if (!selectedFormTitles.includes('MCPD Stat Sheet')) {
      errors.push({ field: 'MCPD Stat Sheet', message: 'The MCPD Stat Sheet is required for every incident packet and is missing.' });
    }
    if (!persons.length) {
      errors.push({ field: 'People', message: 'Add the involved people before sending.' });
    }
    persons.forEach((person, index) => {
      if (!person || typeof person !== 'object') {
        errors.push({ field: `Person ${index + 1}`, message: 'Person entry is invalid.' });
        return;
      }
      if (!String(person.role || '').trim()) {
        errors.push({ field: `Person ${index + 1}`, message: 'Each involved person must have a role.' });
      }
      if (!String(person.name || '').trim()) {
        errors.push({ field: `Person ${index + 1}`, message: 'Each involved person must have a name.' });
      }
    });

    const needsStatement = formEntries.some((entry) => normalizeLookupKey(entry.requestedTitle).includes('voluntarystatement'));
    if (needsStatement && !statements.length) {
      errors.push({ field: 'Statements', message: 'A voluntary statement form is selected, but no statement has been captured.' });
    }

    formEntries.forEach((entry) => {
      if (!entry.record && entry.sourceMode !== 'mobile_statement' && entry.sourceMode !== 'mobile_domestic') {
        errors.push({
          field: 'Forms',
          message: `Selected form "${entry.requestedTitle}" could not be resolved in the live form library.`,
        });
        return;
      }
      if (!['COMPLETED', 'SUBMITTED'].includes(String(entry.status || '').toUpperCase())) {
        errors.push({
          field: (entry.record && entry.record.title) || entry.requestedTitle,
          message: `Form status is ${entry.statusLabel}. Complete or submit this form before sending the packet.`,
        });
      }
      if (entry.sourceMode === 'mobile_domestic') {
        if (!String(domesticDraft['form1.VicName'] || domesticDraft.VicName || '').trim()) {
          errors.push({ field: 'Domestic Supplemental', message: 'Victim name is missing from the domestic supplemental.' });
        }
        if (!String(domesticDraft['form1.ResponseDate'] || domesticDraft.ResponseDate || '').trim()) {
          errors.push({ field: 'Domestic Supplemental', message: 'Response date is missing from the domestic supplemental.' });
        }
        if (!String(domesticDraft['form1.RespTime'] || domesticDraft.RespTime || '').trim()) {
          errors.push({ field: 'Domestic Supplemental', message: 'Response time is missing from the domestic supplemental.' });
        }
        if (!String(domesticDraft['form1.Reported'] || domesticDraft.Reported || '').trim()) {
          errors.push({ field: 'Domestic Supplemental', message: 'Initial incident or violation reported is missing.' });
        }
      }
    });

    statements.forEach((statement, index) => {
      const label = statement.formTitle || `Statement ${index + 1}`;
        const reviewedText = statementReviewedText(statement);
        if (!reviewedText) {
          errors.push({ field: label, message: 'Statement review text is missing.' });
        }
        if (!statementInitialsValue(statement)) {
          errors.push({ field: label, message: 'Statement initials are missing.' });
        }
        if (!statementSignatureValue(statement)) {
          errors.push({ field: label, message: 'Declarant signature is missing.' });
        }
        if (!statementWitnessSignatureValue(statement)) {
          errors.push({ field: label, message: 'Witnessing officer signature is missing.' });
        }
    });

    (state.checklist || []).forEach((item) => {
      if (!item || item.completed) return;
      warnings.push({ field: 'Checklist', message: item.label || 'Checklist item is still open.' });
    });

    const hasDisposition = facts.some((entry) => entry && entry.id === 'disposition' && String(entry.value || '').trim());
    if (!hasDisposition) {
      warnings.push({ field: 'Disposition', message: 'Incident disposition is not documented. Record how the call concluded (released, arrested, counseled, referred, etc.).' });
    }

    if (narrative) {
      const wordCount = narrative.trim().split(/\s+/).filter(Boolean).length;
      if (wordCount < 40) {
        warnings.push({ field: 'Narrative', message: `Narrative is brief (${wordCount} word${wordCount === 1 ? '' : 's'}). Supervisors expect sufficient detail before review.` });
      }
    }

    return {
      callType: state.callType || '',
      basics,
      facts,
      formEntries,
      narrative,
      statements,
      errors,
      warnings,
      canSend: errors.length === 0,
    };
  }

  function StartIncidentPage(root, urls) {
    const state = incidentStore.getState();
    const selected = state.callType;
    root.innerHTML = `
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>Choose call type</h3>
        </div>
        <div class="mobile-call-type-grid">
          ${Object.values(callTypeRules).map((rule) => CallTypeCard(rule, selected === rule.slug)).join('')}
        </div>
      </section>
      ${StickyWizardBar({
        title: selected ? (callTypeRules[selected] || {}).title || 'Incident selected' : 'No call type selected',
        backHref: urls.home,
        backLabel: 'Home',
        nextHref: urls.basics,
        nextLabel: 'Basics',
        disabled: !selected,
      })}
    `;

    root.querySelectorAll('[data-call-type]').forEach((button) => {
      button.addEventListener('click', () => {
        incidentStore.setCallType(button.getAttribute('data-call-type'));
        StartIncidentPage(root, urls);
      });
    });

    const disabledNext = root.querySelector('.mobile-wizard-cta.is-disabled');
    if (disabledNext) {
      disabledNext.addEventListener('click', (event) => event.preventDefault());
    }
  }

  function SelectedFormsPage(root, urls) {
    const state = incidentStore.getState();
    const rule = currentRule(state);
    if (!rule) {
      window.location.replace(urls.start);
      return;
    }
    const catalog = readMobileFormCatalog();
    const selectedForms = Array.isArray(state.selectedForms) ? state.selectedForms : [];
    if (!selectedForms.includes('MCPD Stat Sheet')) {
      incidentStore.toggleSelectedForm('__ensure_stat_sheet__');
      selectedForms.unshift('MCPD Stat Sheet');
    }
    const statSheetRecord = resolveCatalogRecord(catalog, 'MCPD Stat Sheet');
    const recommended = (rule.recommendedForms || [])
      .filter((title) => title !== 'MCPD Stat Sheet')
      .map((title) => ({
        title,
        variant: 'recommended',
        record: resolveCatalogRecord(catalog, title),
      }));
    const optional = (rule.optionalForms || []).map((title) => ({
      title,
      variant: 'optional',
      record: resolveCatalogRecord(catalog, title),
    }));
    const conditionalCount = selectedForms.filter((f) => f !== 'MCPD Stat Sheet').length;
    root.innerHTML = `
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>Forms used</h3>
        </div>
        <div class="mobile-step-progress">
          <span>${escapeHtml(rule.title)}</span>
          <strong>Select only the forms actually used</strong>
        </div>
        <p class="mobile-forms-section-label">Required Documents</p>
        <div class="mobile-form-rec-grid">
          ${FormRecommendationCard('MCPD Stat Sheet', 'always-required', true, statSheetRecord)}
        </div>
        <p class="mobile-forms-section-label">Recommended Documents</p>
        <div class="mobile-form-rec-grid">
          ${recommended.length
            ? recommended.map((entry) => FormRecommendationCard(
                entry.title,
                entry.variant,
                selectedForms.includes(entry.title),
                entry.record
              )).join('')
            : '<div class="mobile-empty-card">No additional forms required for this call type.</div>'
          }
        </div>
      </section>
      <details class="mobile-disclosure">
        <summary>Optional Forms</summary>
        <div class="mobile-disclosure-copy">
          <div class="mobile-form-rec-grid">
            ${optional.length
              ? optional.map((entry) => FormRecommendationCard(
                entry.title,
                entry.variant,
                selectedForms.includes(entry.title),
                entry.record
              )).join('')
              : '<div class="mobile-empty-card">No optional forms suggested for this call type.</div>'}
          </div>
        </div>
      </details>
      ${StickyWizardBar({
        title: `Stat Sheet + ${conditionalCount} conditional form${conditionalCount === 1 ? '' : 's'} selected`,
        backHref: urls.basics,
        backLabel: 'Basics',
        nextHref: urls.persons,
        nextLabel: 'People',
        disabled: false,
      })}
    `;

    root.querySelectorAll('[data-form-name]').forEach((button) => {
      button.addEventListener('click', () => {
        incidentStore.toggleSelectedForm(button.getAttribute('data-form-name'));
        SelectedFormsPage(root, urls);
      });
    });

    const disabledNext = root.querySelector('.mobile-wizard-cta.is-disabled');
    if (disabledNext) {
      disabledNext.addEventListener('click', (event) => event.preventDefault());
    }
  }

  function IncidentBasicsPage(root, urls) {
    const state = incidentStore.getState();
    const rule = currentRule(state);
    if (!rule) {
      window.location.replace(urls.start);
      return;
    }
    const basics = state.incidentBasics || {};
    root.innerHTML = `
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>Incident basics</h3>
        </div>
        <div class="mobile-step-progress">
          <span>${escapeHtml(rule.title)}</span>
          <strong>Enter only the dispatch essentials</strong>
        </div>
        <div class="mobile-field-stack">
          <label class="mobile-field-block">
            <span>Date</span>
            <input class="mobile-text-input" type="date" name="occurredDate" value="${escapeHtml(basics.occurredDate)}" />
          </label>
          <label class="mobile-field-block">
            <span>Location</span>
            <input class="mobile-text-input" type="text" name="location" value="${escapeHtml(basics.location)}" placeholder="Gate, barracks, lot, building..." />
          </label>
          <label class="mobile-field-block">
            <span>Dispatch Time</span>
            <input class="mobile-text-input" type="time" name="dispatchTime" value="${escapeHtml(basics.dispatchTime)}" />
          </label>
          <label class="mobile-field-block">
            <span>Arrival Time</span>
            <input class="mobile-text-input" type="time" name="arrivalTime" value="${escapeHtml(basics.arrivalTime)}" />
          </label>
          <label class="mobile-field-block">
            <span>Reporting Officer</span>
            <input class="mobile-text-input" type="text" name="reportingOfficer" value="${escapeHtml(basics.reportingOfficer)}" placeholder="Officer name or badge" />
          </label>
        </div>
        <details class="mobile-disclosure">
          <summary>More Details</summary>
          <div class="mobile-disclosure-copy">
            <div class="mobile-field-stack">
              <label class="mobile-field-block">
                <span>Occurred Time</span>
                <input class="mobile-text-input" type="time" name="occurredTime" value="${escapeHtml(basics.occurredTime)}" />
              </label>
              <label class="mobile-field-block">
                <span>Short Summary</span>
                <textarea class="mobile-text-input mobile-text-area" name="summary" rows="3" placeholder="Optional short summary.">${escapeHtml(basics.summary)}</textarea>
              </label>
            </div>
          </div>
        </details>
      </section>
      ${StickyWizardBar({
        title: 'Save the incident basics',
        backHref: urls.start,
        backLabel: 'Call Type',
        nextHref: urls.forms,
        nextLabel: 'Forms',
        disabled: !(basics.occurredDate && basics.location && basics.dispatchTime && basics.arrivalTime && basics.reportingOfficer),
      })}
    `;

    root.querySelectorAll('[name]').forEach((field) => {
      field.addEventListener('input', () => {
        incidentStore.updateIncidentBasics({ [field.name]: field.value });
        const refreshed = incidentStore.getState();
        const ready = refreshed.incidentBasics.occurredDate
          && refreshed.incidentBasics.location
          && refreshed.incidentBasics.dispatchTime
          && refreshed.incidentBasics.arrivalTime
          && refreshed.incidentBasics.reportingOfficer;
        const nextButton = root.querySelector('.mobile-wizard-cta');
        if (nextButton) {
          nextButton.classList.toggle('is-disabled', !ready);
          nextButton.setAttribute('href', ready ? urls.forms : '#');
        }
      });
    });

    const disabledNext = root.querySelector('.mobile-wizard-cta.is-disabled');
    if (disabledNext) {
      disabledNext.addEventListener('click', (event) => event.preventDefault());
    }
  }

  function PersonsListPage(root, urls) {
    const state = incidentStore.getState();
    const persons = Array.isArray(state.persons) ? state.persons : [];
    root.innerHTML = `
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>People on scene</h3>
        </div>
        <a class="mobile-action-button" href="${escapeHtml(urls.personEditor)}">Add Person</a>
        <div class="mobile-person-stack">
          ${persons.length
            ? persons.map((person) => PersonCard(person, `${urls.personEditor}?person_id=${encodeURIComponent(person.id)}`)).join('')
            : '<div class="mobile-empty-card">Add the first person.</div>'}
        </div>
      </section>
      ${StickyWizardBar({
        title: `${persons.length} person${persons.length === 1 ? '' : 's'} attached`,
        backHref: urls.forms,
        backLabel: 'Forms',
        nextHref: urls.statute,
        nextLabel: 'Statute',
        disabled: false,
      })}
    `;
  }

  function PersonEditorPage(root, urls) {
    const search = new URLSearchParams(window.location.search);
    const personId = search.get('person_id') || '';
    const current = personId ? incidentStore.getPersonById(personId) : null;
    const person = Object.assign({
      id: '',
      role: 'Witness',
      name: '',
      dob: '',
      ssn: '',
      address: '',
      phone: '',
      idNumber: '',
      state: '',
      descriptors: '',
      source: 'manual',
    }, current || {});
    root.innerHTML = `
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>${personId ? 'Edit person' : 'Add person'}</h3>
        </div>
        <form class="mobile-person-form" data-person-editor-form>
          ${RoleSelector(person.role)}
          <label class="mobile-field-block"><span>Name</span><input class="mobile-text-input" type="text" name="name" value="${escapeHtml(person.name)}" /></label>
          <label class="mobile-field-block"><span>DOB</span><input class="mobile-text-input" type="date" name="dob" value="${escapeHtml(person.dob)}" /></label>
          <label class="mobile-field-block"><span>ID Number</span><input class="mobile-text-input" type="text" name="idNumber" value="${escapeHtml(person.idNumber)}" /></label>
          <label class="mobile-field-block"><span>ID State</span><input class="mobile-text-input" type="text" name="state" value="${escapeHtml(person.state)}" maxlength="20" /></label>
          <details class="mobile-disclosure">
            <summary>More Details</summary>
            <div class="mobile-disclosure-copy">
              <div class="mobile-field-stack">
                <label class="mobile-field-block"><span>SSN</span><input class="mobile-text-input" type="text" name="ssn" value="${escapeHtml(person.ssn)}" inputmode="numeric" /></label>
                <label class="mobile-field-block"><span>Phone</span><input class="mobile-text-input" type="tel" name="phone" value="${escapeHtml(person.phone)}" /></label>
                <label class="mobile-field-block"><span>Address</span><textarea class="mobile-text-input mobile-text-area" name="address" rows="3">${escapeHtml(person.address)}</textarea></label>
                <label class="mobile-field-block"><span>Descriptors</span><textarea class="mobile-text-input mobile-text-area" name="descriptors" rows="3">${escapeHtml(person.descriptors)}</textarea></label>
                ${IdScanLauncher()}
              </div>
            </div>
          </details>
          <input type="hidden" name="id" value="${escapeHtml(person.id)}" />
          <input type="hidden" name="source" value="${escapeHtml(person.source)}" />
        </form>
      </section>
      ${StickyWizardBar({
        title: 'Save this person for the incident packet',
        backHref: urls.persons,
        backLabel: 'People',
        nextHref: '#',
        nextLabel: 'Save Person',
        disabled: false,
      })}
    `;

    const form = root.querySelector('[data-person-editor-form]');
    const saveButton = root.querySelector('.mobile-wizard-cta');
    const roleInput = form ? form.querySelector('input[name="role"]') : null;
    const sourceInput = form ? form.querySelector('input[name="source"]') : null;
        const scanInput = root.querySelector('[data-id-scan-raw]');
        const scanApply = root.querySelector('[data-id-scan-apply]');
        const scanClear = root.querySelector('[data-id-scan-clear]');
        const scanStatus = root.querySelector('[data-id-scan-status]');
        const scanCamera = root.querySelector('[data-id-scan-camera]');
        const scanFile = root.querySelector('[data-id-scan-file]');
        const liveScanner = root.querySelector('[data-id-live-scanner]');
        const liveVideo = root.querySelector('[data-id-live-video]');
        const scanCancel = root.querySelector('[data-id-scan-cancel]');
        let liveScannerControls = null;
        let liveScannerReader = null;
        let liveScannerOpening = false;
        const applyParsedScan = (rawValue) => {
        const sourceValue = typeof rawValue === 'string' ? rawValue : (scanInput ? scanInput.value : '');
        if (scanInput && typeof rawValue === 'string') scanInput.value = rawValue;
        const parsed = parseAamvaBarcodeText(sourceValue);
        if (!parsed) {
          if (scanStatus) scanStatus.textContent = 'Could not read scan text. Continue with manual entry.';
          return false;
        }
        ['name', 'dob', 'address', 'idNumber', 'state'].forEach((fieldName) => {
          const field = form.querySelector(`[name="${fieldName}"]`);
          const nextValue = String(parsed[fieldName] || '').trim();
          if (field && nextValue) field.value = nextValue;
        });
        if (sourceInput) sourceInput.value = 'scan_text';
        if (scanStatus) scanStatus.textContent = 'Scan text applied. Review and correct any field before saving.';
        return true;
      };
      root.querySelectorAll('[data-role-choice]').forEach((button) => {
        button.addEventListener('click', () => {
          const role = button.getAttribute('data-role-choice') || 'Witness';
          if (roleInput) roleInput.value = role;
          root.querySelectorAll('[data-role-choice]').forEach((chip) => {
          chip.classList.toggle('is-active', chip === button);
        });
      });
      });
      if (scanApply && form) {
        scanApply.addEventListener('click', () => applyParsedScan());
      }
        if (scanInput && form) {
          scanInput.addEventListener('paste', () => {
            window.setTimeout(() => {
              applyParsedScan();
            }, 0);
          });
        }
        const stopLiveScanner = () => {
          if (liveScannerControls && typeof liveScannerControls.stop === 'function') {
            try {
              liveScannerControls.stop();
            } catch (_error) {}
          }
          liveScannerControls = null;
          liveScannerReader = null;
          if (liveVideo) {
            try {
              liveVideo.pause();
            } catch (_error) {}
            if (liveVideo.srcObject) {
              const tracks = liveVideo.srcObject.getTracks ? liveVideo.srcObject.getTracks() : [];
              tracks.forEach((track) => {
                try {
                  track.stop();
                } catch (_error) {}
              });
              liveVideo.srcObject = null;
            }
          }
          if (liveScanner) liveScanner.hidden = true;
        };
        const openCaptureFallback = () => {
          stopLiveScanner();
          if (!scanFile) {
            if (scanStatus) scanStatus.textContent = 'Camera capture is unavailable. Use manual entry or paste scan text.';
            return;
          }
          if (scanStatus) {
            scanStatus.textContent = 'Live scanner is unavailable here. Opening camera capture instead.';
          }
          scanFile.click();
        };
        const startLiveScanner = async () => {
          if (!scanStatus || !liveScanner || !liveVideo || liveScannerOpening) return;
          liveScannerOpening = true;
          stopLiveScanner();
          liveScanner.hidden = false;
          scanStatus.textContent = 'Opening live scanner...';
          try {
            if (!window.isSecureContext) {
              scanStatus.textContent = 'Live scanner requires HTTPS on phones. Use the HTTPS launcher, paste scan text, or use Photo Fallback.';
              stopLiveScanner();
              return;
            }
            const zxing = await loadZxingLibrary().catch(() => null);
            if (!zxing || typeof zxing.BrowserPDF417Reader !== 'function') {
              scanStatus.textContent = 'Live scan not supported on this device. Use photo upload.';
              stopLiveScanner();
              return;
            }
            if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== 'function') {
              scanStatus.textContent = 'Live scan not supported on this device. Use photo upload.';
              stopLiveScanner();
              return;
            }
            liveScannerReader = new zxing.BrowserPDF417Reader();
            liveScannerControls = await liveScannerReader.decodeFromVideoDevice(undefined, liveVideo, (result, error, controls) => {
              if (controls && !liveScannerControls) liveScannerControls = controls;
              const raw = readZxingResultText(result);
              if (raw) {
                applyParsedScan(raw);
                stopLiveScanner();
                return;
              }
              if (error && scanStatus) {
                const errorName = error && error.name ? String(error.name) : '';
                if (errorName && errorName !== 'NotFoundException' && errorName !== 'ChecksumException' && errorName !== 'FormatException') {
                  scanStatus.textContent = 'Scanner is active. Hold the barcode steady inside the frame.';
                }
              }
            });
            scanStatus.textContent = 'Camera ready. Hold the barcode side of the ID steady inside the frame.';
          } catch (error) {
            const errorName = error && error.name ? String(error.name) : '';
            if (errorName === 'NotAllowedError' || errorName === 'PermissionDeniedError') {
              scanStatus.textContent = 'Permission denied. Use upload instead.';
            } else if (errorName === 'NotFoundError' || errorName === 'DevicesNotFoundError') {
              scanStatus.textContent = 'Live scan not supported on this device. Use photo upload.';
            } else {
              scanStatus.textContent = 'Scan failed. Use upload instead.';
            }
            stopLiveScanner();
          } finally {
            liveScannerOpening = false;
          }
        };
        if (scanCamera) {
          scanCamera.addEventListener('click', () => {
            startLiveScanner();
          });
        }
        if (scanCancel) {
          scanCancel.addEventListener('click', () => {
            stopLiveScanner();
            if (scanStatus) scanStatus.textContent = 'Live scanner closed. Manual entry always works.';
          });
        }
        if (scanFile) {
          scanFile.addEventListener('change', async () => {
            const file = scanFile.files && scanFile.files[0] ? scanFile.files[0] : null;
            if (!file) return;
            if (scanStatus) scanStatus.textContent = 'Scanning captured image...';
            try {
              const raw = await detectBarcodeTextFromImageFile(file);
              if (!raw) {
                if (scanStatus) scanStatus.textContent = 'No readable barcode found. Try again or use manual entry.';
                scanFile.value = '';
                return;
              }
              applyParsedScan(raw);
            } catch (_error) {
              if (scanStatus) scanStatus.textContent = 'Camera capture scan failed. Use manual entry or paste scan text.';
            }
            scanFile.value = '';
          });
        }
        if (scanClear && scanInput) {
          scanClear.addEventListener('click', () => {
            scanInput.value = '';
            if (scanStatus) scanStatus.textContent = 'Reads name, DOB, address, ID number, and state. Manual entry always works.';
        });
      }
    if (!form || !saveButton) return;
      saveButton.addEventListener('click', (event) => {
        event.preventDefault();
        stopLiveScanner();
        const formData = new FormData(form);
        const merged = {
        id: String(formData.get('id') || person.id || ''),
        role: String(formData.get('role') || person.role || 'Witness'),
        name: String(formData.get('name') || person.name || '').trim(),
        dob: String(formData.get('dob') || person.dob || ''),
        ssn: String(formData.get('ssn') || person.ssn || '').trim(),
        address: String(formData.get('address') || person.address || '').trim(),
        phone: String(formData.get('phone') || person.phone || '').trim(),
        idNumber: String(formData.get('idNumber') || person.idNumber || '').trim(),
        state: String(formData.get('state') || person.state || '').trim(),
        descriptors: String(formData.get('descriptors') || person.descriptors || '').trim(),
        source: String(formData.get('source') || person.source || 'manual'),
      };
      incidentStore.upsertPerson(merged);
      window.location.assign(urls.persons);
    });
  }

  function StatutePage(root, urls) {
    const state = incidentStore.getState();
    const rule = currentRule(state);
    if (!rule) {
      window.location.replace(urls.start);
      return;
    }
    const selected = Array.isArray(state.statutes) ? state.statutes : [];
    root.innerHTML = `
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>Statute / category</h3>
        </div>
        <div class="mobile-prompt-list">
          ${(rule.statutes || []).map((item) => `
            <button class="mobile-prompt-chip ${selected.some((entry) => entry.toLowerCase() === item.toLowerCase()) ? 'is-active' : ''}" type="button" data-statute-chip="${escapeHtml(item)}">
              ${escapeHtml(item)}
            </button>
          `).join('')}
        </div>
        <label class="mobile-field-block">
          <span>Custom entry</span>
          <input class="mobile-text-input" type="text" data-custom-statute-input placeholder="Example: Article 128 review" />
        </label>
        <button class="mobile-action-button is-secondary" type="button" data-add-custom-statute>Add Custom Entry</button>
        <div class="mobile-prompt-list">
          ${selected.length
            ? selected.map((item) => `<button class="mobile-prompt-chip is-active" type="button" data-statute-chip="${escapeHtml(item)}">${escapeHtml(item)}</button>`).join('')
            : '<div class="mobile-empty-card">No statute selected.</div>'}
        </div>
      </section>
      ${StickyWizardBar({
        title: selected.length ? `${selected.length} authority reference${selected.length === 1 ? '' : 's'} selected` : 'No authority selected yet',
        backHref: urls.persons,
        backLabel: 'People',
        nextHref: urls.checklist,
        nextLabel: 'Checklist',
        disabled: false,
      })}
    `;
    root.querySelectorAll('[data-statute-chip]').forEach((button) => {
      button.addEventListener('click', () => {
        incidentStore.toggleStatute(button.getAttribute('data-statute-chip'));
        StatutePage(root, urls);
      });
    });
    const addButton = root.querySelector('[data-add-custom-statute]');
    const input = root.querySelector('[data-custom-statute-input]');
    if (addButton && input) {
      addButton.addEventListener('click', () => {
        const value = String(input.value || '').trim();
        if (!value) return;
        incidentStore.toggleStatute(value);
        StatutePage(root, urls);
      });
    }
  }

  function ChecklistPage(root, urls) {
    const state = incidentStore.getState();
    const checklist = Array.isArray(state.checklist) ? state.checklist : [];
    root.innerHTML = `
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>Action checklist</h3>
        </div>
        <div class="mobile-checklist-stack">
          ${checklist.length
            ? checklist.map((item) => `
              <label class="mobile-checklist-item ${item.completed ? 'is-complete' : ''}">
                <input type="checkbox" data-checklist-id="${escapeHtml(item.id)}" ${item.completed ? 'checked' : ''} />
                <span>${escapeHtml(item.label)}</span>
              </label>
            `).join('')
            : '<div class="mobile-empty-card">This call type has no extra checklist items configured.</div>'}
        </div>
      </section>
      ${StickyWizardBar({
        title: checklist.length ? `${checklist.filter((item) => item.completed).length} of ${checklist.length} actions marked complete` : 'No checklist items configured',
        backHref: urls.statute,
        backLabel: 'Statute',
        nextHref: urls.facts,
        nextLabel: 'Facts',
        disabled: false,
      })}
    `;
    root.querySelectorAll('[data-checklist-id]').forEach((checkbox) => {
      checkbox.addEventListener('change', () => {
        incidentStore.toggleChecklistItem(checkbox.getAttribute('data-checklist-id'));
        ChecklistPage(root, urls);
      });
    });
  }

  function FactsCapturePage(root, urls) {
    const state = incidentStore.getState();
    const values = factValueMap(state);
    const basics = state.incidentBasics || {};
    const persons = Array.isArray(state.persons) ? state.persons : [];
    const selectedForms = Array.isArray(state.selectedForms) ? state.selectedForms : [];
    const voiceSupported = !!(window.SpeechRecognition || window.webkitSpeechRecognition);

    function readOnlyField(label, value) {
      return `
        <div class="mobile-field-block">
          <span>${escapeHtml(label)}</span>
          <div style="padding:10px 14px;background:#f8f5ef;border-radius:12px;border:1px solid #e2d9c7;font-size:15px;color:${value ? '#1e251d' : '#aaa'};min-height:40px;line-height:1.4;">
            ${escapeHtml(value || '—')}
          </div>
        </div>`;
    }

    const personsSummary = persons.length
      ? persons.map((p) => `
          <div style="padding:10px 14px;background:#f8f5ef;border-radius:12px;border:1px solid #e2d9c7;margin-bottom:6px;">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
              <strong style="font-size:14px;color:#1e251d;">${escapeHtml(p.name || 'Unnamed')}</strong>
              <span style="font-size:12px;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;color:#7a6e5a;background:#ede6d6;padding:2px 8px;border-radius:999px;">${escapeHtml(p.role || 'No role')}</span>
            </div>
            ${p.dob ? `<div style="font-size:12px;color:#888;margin-top:3px;">DOB: ${escapeHtml(p.dob)}</div>` : ''}
            ${p.idNumber ? `<div style="font-size:12px;color:#888;">ID: ${escapeHtml(p.idNumber)}</div>` : ''}
          </div>`).join('')
      : `<p style="color:#aaa;font-size:14px;margin:0;padding:4px 0;">No persons added — return to Step 4 to add them.</p>`;

    const formsListHtml = selectedForms.length
      ? selectedForms.map((f) => `<div style="padding:3px 0;font-size:14px;color:#1e251d;">• ${escapeHtml(f)}</div>`).join('')
      : `<p style="color:#aaa;font-size:14px;margin:0;">No forms selected.</p>`;

    root.innerHTML = `
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>Fact Sheet</h3>
        </div>

        <article class="mobile-fact-card">
          <div class="mobile-fact-head"><strong>Incident Overview</strong></div>
          ${readOnlyField('Incident Type', state.callType)}
          ${readOnlyField('Date', basics.occurredDate)}
          ${readOnlyField('Time of Incident', basics.occurredTime)}
          ${readOnlyField('Location', basics.location)}
          ${readOnlyField('Reporting Officer', basics.reportingOfficer)}
        </article>

        <article class="mobile-fact-card">
          <div class="mobile-fact-head"><strong>Case Information</strong></div>
          <label class="mobile-field-block">
            <span>Case / Report Number</span>
            <input class="mobile-text-input" type="text"
              data-fact-key="case_number"
              data-fact-label="Case / Report Number"
              placeholder="e.g. 2026-001234"
              value="${escapeHtml(values.case_number || '')}">
          </label>
        </article>

        <article class="mobile-fact-card">
          <div class="mobile-fact-head"><strong>Involved Persons</strong></div>
          ${personsSummary}
        </article>

        <article class="mobile-fact-card">
          <div class="mobile-fact-head"><strong>Vehicle Information</strong></div>
          <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:14px;font-weight:600;color:#30362c;">
            <input type="checkbox"
              data-fact-key="vehicle_involved"
              data-fact-label="Vehicle Involved"
              style="width:20px;height:20px;flex-shrink:0;accent-color:#c9a86a;"
              ${values.vehicle_involved === 'yes' ? 'checked' : ''}>
            <span>Vehicle involved in this incident</span>
          </label>
          <label class="mobile-field-block" id="fact-vehicle-block" style="${values.vehicle_involved === 'yes' ? '' : 'display:none'}">
            <span>Vehicle Details</span>
            <textarea class="mobile-text-input mobile-text-area" rows="3"
              data-fact-key="vehicle_info"
              data-fact-label="Vehicle Details"
              placeholder="Year, make, model, plate, state, VIN, owner…"
            >${escapeHtml(values.vehicle_info || '')}</textarea>
          </label>
        </article>

        <article class="mobile-fact-card">
          <div class="mobile-fact-head"><strong>Property / Evidence</strong></div>
          <label class="mobile-field-block">
            <span>Property and evidence involved</span>
            <textarea class="mobile-text-input mobile-text-area" rows="3"
              data-fact-key="property_evidence"
              data-fact-label="Property / Evidence"
              placeholder="Describe property taken, damaged, or evidence collected…"
            >${escapeHtml(values.property_evidence || '')}</textarea>
          </label>
        </article>

        <article class="mobile-fact-card is-focused">
          <div class="mobile-fact-head">
            <strong>Brief Facts Summary</strong>
            ${VoiceInputControl('what_happened', voiceSupported)}
          </div>
          <textarea class="mobile-text-input mobile-text-area" rows="6"
            data-fact-key="what_happened"
            data-fact-label="What happened"
            placeholder="Observed or reported facts only — who, what, when, where, how."
          >${escapeHtml(values.what_happened || '')}</textarea>
        </article>

        <article class="mobile-fact-card">
          <div class="mobile-fact-head"><strong>Probable Cause Facts</strong></div>
          <label class="mobile-field-block">
            <span>Articulable facts establishing probable cause</span>
            <textarea class="mobile-text-input mobile-text-area" rows="4"
              data-fact-key="probable_cause"
              data-fact-label="Probable Cause"
              placeholder="Specific, articulable facts establishing probable cause…"
            >${escapeHtml(values.probable_cause || '')}</textarea>
          </label>
        </article>

        <article class="mobile-fact-card">
          <div class="mobile-fact-head"><strong>Officer Actions Taken</strong></div>
          <textarea class="mobile-text-input mobile-text-area" rows="4"
            data-fact-key="officer_actions"
            data-fact-label="Officer actions"
            placeholder="Detained, arrested, cited, searched, collected evidence…"
          >${escapeHtml(values.officer_actions || '')}</textarea>
        </article>

        <article class="mobile-fact-card">
          <div class="mobile-fact-head"><strong>Disposition</strong></div>
          <textarea class="mobile-text-input mobile-text-area" rows="3"
            data-fact-key="disposition"
            data-fact-label="Disposition"
            placeholder="How was this call resolved? Arrest, released, referred, counseled…"
          >${escapeHtml(values.disposition || '')}</textarea>
        </article>

        <article class="mobile-fact-card">
          <div class="mobile-fact-head"><strong>Required Forms Checklist</strong></div>
          ${formsListHtml}
        </article>

        <article class="mobile-fact-card">
          <div class="mobile-fact-head"><strong>Supervisor Notes</strong></div>
          <label class="mobile-field-block">
            <span>Notes for supervisor review</span>
            <textarea class="mobile-text-input mobile-text-area" rows="3"
              data-fact-key="supervisor_notes"
              data-fact-label="Supervisor Notes"
              placeholder="Flags, context, or anything the reviewing supervisor should know…"
            >${escapeHtml(values.supervisor_notes || '')}</textarea>
          </label>
        </article>

      </section>
      ${StickyWizardBar({
        title: 'Save facts and continue',
        backHref: urls.checklist,
        backLabel: 'Checklist',
        nextHref: urls.narrative,
        nextLabel: 'Narrative',
        disabled: false,
      })}
    `;

    const vehicleCheckbox = root.querySelector('[data-fact-key="vehicle_involved"]');
    const vehicleBlock = root.querySelector('#fact-vehicle-block');
    if (vehicleCheckbox && vehicleBlock) {
      vehicleCheckbox.addEventListener('change', () => {
        const checked = vehicleCheckbox.checked;
        incidentStore.updateFact('vehicle_involved', 'Vehicle Involved', checked ? 'yes' : 'no');
        vehicleBlock.style.display = checked ? '' : 'none';
      });
    }

    let activeRecognition = null;
    root.querySelectorAll('[data-fact-key]:not([type="checkbox"])').forEach((field) => {
      field.addEventListener('input', () => {
        incidentStore.updateFact(field.getAttribute('data-fact-key'), field.getAttribute('data-fact-label'), field.value);
      });
    });
    root.querySelectorAll('[data-voice-target]').forEach((button) => {
      button.addEventListener('click', () => {
        const TargetRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const field = root.querySelector(`[data-fact-key="${button.getAttribute('data-voice-target')}"]`);
        if (!TargetRecognition || !field) return;
        if (activeRecognition) {
          activeRecognition.stop();
          activeRecognition = null;
        }
        const recognition = new TargetRecognition();
        activeRecognition = recognition;
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        button.textContent = 'Listening...';
        recognition.onresult = (event) => {
          const transcript = (((event.results || [])[0] || [])[0] || {}).transcript || '';
          if (transcript) {
            field.value = field.value ? `${field.value.trim()} ${transcript.trim()}` : transcript.trim();
            incidentStore.updateFact(field.getAttribute('data-fact-key'), field.getAttribute('data-fact-label'), field.value);
          }
        };
        recognition.onend = () => {
          button.textContent = 'Speak Facts';
          activeRecognition = null;
        };
        recognition.onerror = () => {
          button.textContent = 'Speak Facts';
          activeRecognition = null;
        };
        recognition.start();
      });
    });
  }

  function NarrativeReviewPage(root, urls) {
    const state = incidentStore.getState();
    const generatedDraft = buildNarrativeDraft(state);
    const currentNarrative = state.narrative || generatedDraft;
    if (!state.narrative && generatedDraft) incidentStore.updateNarrative(generatedDraft);
    const warnings = narrativeDetailWarnings(state);
    root.innerHTML = `
      ${warnings.length ? packetValidationCard('Missing Detail Warnings', warnings, 'warning') : ''}
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>Narrative review</h3>
        </div>
        <div class="mobile-step-progress">
          <span>Review draft</span>
          <strong>Approve the narrative</strong>
        </div>
        ${NarrativeEditor(currentNarrative, true)}
        <details class="mobile-disclosure">
          <summary>More Options</summary>
          <div class="mobile-disclosure-copy">
            <button class="mobile-outline-button" type="button" data-regenerate-narrative>Regenerate Draft</button>
          </div>
        </details>
      </section>
      ${StickyWizardBar({
        title: state.narrativeApproved ? 'Narrative approved for the packet' : currentNarrative ? 'Approve this narrative and continue' : 'Add more facts before relying on the draft',
        backHref: urls.facts,
        backLabel: 'Facts',
        nextHref: urls.statements,
        nextLabel: state.narrativeApproved ? 'Continue' : 'Approve',
        disabled: !currentNarrative,
      })}
    `;
    const editor = root.querySelector('[data-narrative-editor]');
    const regenerate = root.querySelector('[data-regenerate-narrative]');
    const approveButton = root.querySelector('.mobile-wizard-cta');
    if (editor) editor.addEventListener('input', () => incidentStore.updateNarrative(editor.value));
    if (regenerate && editor) {
      regenerate.addEventListener('click', () => {
        const refreshed = buildNarrativeDraft(incidentStore.getState());
        editor.value = refreshed;
        incidentStore.updateNarrative(refreshed);
      });
    }
    if (approveButton && editor) {
      approveButton.addEventListener('click', (event) => {
        event.preventDefault();
        const nextNarrative = String(editor.value || '').trim();
        if (!nextNarrative) {
          return;
        }
        incidentStore.approveNarrative(nextNarrative);
        window.location.assign(urls.statements);
      });
    }
  }

  function StatementLauncherPage(root, urls) {
    const state = incidentStore.getState();
    const statements = Array.isArray(state.statements) ? state.statements : [];
    const variant = defaultStatementVariant(state);
    const variantConfig = statementConfig(variant);
    const alternateVariant = variant === 'traffic' ? 'standard' : 'traffic';
    const alternateConfig = statementConfig(alternateVariant);
    const currentStatement = statements[statements.length - 1] || null;
    root.innerHTML = `
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>Voluntary statements</h3>
        </div>
        <div class="mobile-step-progress">
          <span>Main task</span>
          <strong>${statements.length ? 'Open the current statement' : 'Start a statement only if needed'}</strong>
        </div>
        <article class="mobile-form-rec-card is-recommended">
          <div class="mobile-form-rec-copy">
            <span class="mobile-form-rec-label">${statements.length ? 'Current' : 'Default'}</span>
            <strong>${escapeHtml(currentStatement ? currentStatement.formTitle : variantConfig.formTitle)}</strong>
            <p>${escapeHtml(currentStatement ? statementStatus(currentStatement, state) : 'Use this when the incident needs a statement.')}</p>
          </div>
          ${
            currentStatement
              ? `<a class="mobile-form-toggle" href="${escapeHtml(`${urls.statementReview}?statement_id=${encodeURIComponent(currentStatement.id)}`)}">Open</a>`
              : `<button class="mobile-form-toggle" type="button" data-create-statement="${escapeHtml(variant)}">Start</button>`
          }
        </article>
        <details class="mobile-disclosure">
          <summary>More Options</summary>
          <div class="mobile-disclosure-copy">
            <article class="mobile-form-rec-card is-optional">
              <div class="mobile-form-rec-copy">
                <span class="mobile-form-rec-label">Alternate</span>
                <strong>${escapeHtml(alternateConfig.formTitle)}</strong>
              </div>
              <button class="mobile-form-toggle" type="button" data-create-statement="${escapeHtml(alternateVariant)}">Start</button>
            </article>
            ${
              statements.length > 1
                ? `<div class="mobile-selected-form-stack">${statements.slice(0, -1).reverse().map((statement) => StatementSummaryCard(
                    statement,
                    state,
                    `${urls.statementEntry}?statement_id=${encodeURIComponent(statement.id)}`,
                    `${urls.statementReview}?statement_id=${encodeURIComponent(statement.id)}`
                  )).join('')}</div>`
                : ''
            }
          </div>
        </details>
      </section>
      ${StickyWizardBar({
        title: statements.length ? 'Continue when the statement work is done' : 'Skip this step unless the incident needs a statement',
        backHref: urls.narrative,
        backLabel: 'Narrative',
        nextHref: statements.length && currentStatement ? `${urls.statementReview}?statement_id=${encodeURIComponent(currentStatement.id)}` : urls.domestic,
        nextLabel: statements.length ? 'Open Current' : 'Skip',
        disabled: false,
      })}
    `;
    root.querySelectorAll('[data-create-statement]').forEach((button) => {
      button.addEventListener('click', () => {
        const created = incidentStore.createStatement({ variant: button.getAttribute('data-create-statement') });
        const nextStatement = (created.statements || [])[created.statements.length - 1];
        if (!nextStatement) return;
        window.location.assign(`${urls.statementEntry}?statement_id=${encodeURIComponent(nextStatement.id)}`);
      });
    });
  }

  function StatementEntryPage(root, urls) {
    const state = incidentStore.getState();
    const search = new URLSearchParams(window.location.search);
    const requestedId = search.get('statement_id') || '';
    const requestedStep = search.get('step') || 'person';
    const personId = search.get('person_id') || '';
    let statement = requestedId ? incidentStore.getStatementById(requestedId) : null;
    if (!statement) {
      const created = incidentStore.createStatement({ variant: defaultStatementVariant(state), personId });
      statement = (created.statements || [])[created.statements.length - 1] || null;
    }
    if (!statement) {
      window.location.replace(urls.statements);
      return;
    }
    const steps = ['person', 'details', 'content'];
    const activeStep = steps.includes(requestedStep) ? requestedStep : steps[0];
    const activeIndex = steps.indexOf(activeStep);
    const currentPerson = statement.personId ? incidentStore.getPersonById(statement.personId) : null;
    const contentMarkup = activeStep === 'person'
      ? `
        ${personOptionsMarkup(state, statement.personId || '')}
        <label class="mobile-field-block"><span>Speaker Name</span><input class="mobile-text-input" type="text" name="speaker" value="${escapeHtml(statement.speaker)}" /></label>
        ${currentPerson
          ? `<div class="mobile-inline-note">Using person record: ${escapeHtml(`${currentPerson.role || 'Person'} - ${currentPerson.name || 'Unnamed'}`)}</div>`
          : '<div class="mobile-inline-note">Pick an involved person when possible, or type the speaker name manually.</div>'}
      `
      : activeStep === 'details'
      ? `
        <label class="mobile-field-block"><span>Officer Name</span><input class="mobile-text-input" type="text" name="officerName" value="${escapeHtml(statement.officerName)}" /></label>
        <div class="mobile-mobile-card-grid">
          <label class="mobile-field-block"><span>Statement Date</span><input class="mobile-text-input" type="date" name="statementDate" value="${escapeHtml(statement.statementDate)}" /></label>
          <label class="mobile-field-block"><span>Statement Time</span><input class="mobile-text-input" type="time" name="statementTime" value="${escapeHtml(statement.statementTime)}" /></label>
        </div>
        ${currentPerson ? `<div class="mobile-inline-note">Using person record: ${escapeHtml(`${currentPerson.role || 'Person'} - ${currentPerson.name || 'Unnamed'}`)}</div>` : ''}
        <details class="mobile-disclosure">
          <summary>More Details</summary>
          <div class="mobile-disclosure-copy">
            <label class="mobile-field-block"><span>Speaker SSN</span><input class="mobile-text-input" type="text" name="speakerSsn" value="${escapeHtml(statement.speakerSsn)}" /></label>
            <label class="mobile-field-block"><span>Officer Badge</span><input class="mobile-text-input" type="text" name="officerBadge" value="${escapeHtml(statement.officerBadge)}" /></label>
            <label class="mobile-field-block"><span>Location Taken</span><input class="mobile-text-input" type="text" name="location" value="${escapeHtml(statement.location)}" /></label>
            <label class="mobile-field-block"><span>Statement Subject</span><input class="mobile-text-input" type="text" name="statementSubject" value="${escapeHtml(statement.statementSubject)}" /></label>
          </div>
        </details>
      `
      : `
        ${statement.variant === 'traffic'
          ? trafficStatementQuestions.map((question, index) => `
            <label class="mobile-field-block">
              <span>${escapeHtml(question)}</span>
              <textarea class="mobile-text-input mobile-text-area" rows="3" name="traffic-q${index + 1}">${escapeHtml((statement.trafficAnswers || {})[`q${index + 1}`] || '')}</textarea>
            </label>
          `).join('')
          : `
            <label class="mobile-field-block">
              <span>Plain Language Statement</span>
              <textarea class="mobile-text-input mobile-text-area" rows="8" name="plainLanguage" placeholder="Type or dictate what the person said in plain language.">${escapeHtml(statement.plainLanguage)}</textarea>
            </label>
          `}
      `;

    root.innerHTML = `
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>${escapeHtml(statement.formTitle)}</h3>
        </div>
        ${inlineProgressChips(steps.length, activeIndex)}
        <div class="mobile-step-title">${escapeHtml(
          activeStep === 'person'
            ? 'Choose who is giving the statement'
            : activeStep === 'details'
            ? 'Confirm the statement details'
            : 'Capture the statement content'
        )}</div>
        <form class="mobile-person-form" data-statement-entry-form>
          ${contentMarkup}
        </form>
      </section>
      ${StickyWizardBar({
        title: activeIndex === steps.length - 1 ? 'Save and review the statement draft' : 'Save this step and continue',
        backHref: activeIndex === 0 ? urls.statements : `${urls.statementEntry}?statement_id=${encodeURIComponent(statement.id)}&step=${encodeURIComponent(steps[activeIndex - 1])}`,
        backLabel: activeIndex === 0 ? 'Statements' : 'Back',
        nextHref: '#',
        nextLabel: activeIndex === steps.length - 1 ? 'Review Draft' : 'Next',
        disabled: false,
      })}
    `;
    const form = root.querySelector('[data-statement-entry-form]');
    const saveButton = root.querySelector('.mobile-wizard-cta');
    if (!form || !saveButton) return;
    form.querySelector('[name="personId"]')?.addEventListener('change', (event) => {
      const nextPerson = incidentStore.getPersonById(event.target.value);
      incidentStore.upsertStatement({
        id: statement.id,
        variant: statement.variant,
        personId: event.target.value,
        speaker: nextPerson ? nextPerson.name || '' : statement.speaker,
        speakerSsn: nextPerson ? nextPerson.ssn || '' : statement.speakerSsn,
      });
      StatementEntryPage(root, urls);
    });
    saveButton.addEventListener('click', (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const patch = {
        id: statement.id,
        variant: statement.variant,
        personId: String(formData.get('personId') || statement.personId || ''),
        speaker: String(formData.get('speaker') || statement.speaker || '').trim(),
        speakerSsn: String(formData.get('speakerSsn') || statement.speakerSsn || '').trim(),
        officerName: String(formData.get('officerName') || statement.officerName || '').trim(),
        officerBadge: String(formData.get('officerBadge') || statement.officerBadge || '').trim(),
        location: String(formData.get('location') || statement.location || '').trim(),
        statementDate: String(formData.get('statementDate') || statement.statementDate || ''),
        statementTime: String(formData.get('statementTime') || statement.statementTime || ''),
        statementSubject: String(formData.get('statementSubject') || statement.statementSubject || '').trim(),
        plainLanguage: String(formData.get('plainLanguage') || statement.plainLanguage || '').trim(),
      };
      if (statement.variant === 'traffic') {
        const answers = Object.assign({}, statement.trafficAnswers || {});
        trafficStatementQuestions.forEach((_question, index) => {
          answers[`q${index + 1}`] = String(formData.get(`traffic-q${index + 1}`) || '').trim();
        });
        patch.trafficAnswers = answers;
      }
      incidentStore.upsertStatement(patch);
      if (activeIndex === steps.length - 1) {
        window.location.assign(`${urls.statementReview}?statement_id=${encodeURIComponent(statement.id)}`);
        return;
      }
      window.location.assign(`${urls.statementEntry}?statement_id=${encodeURIComponent(statement.id)}&step=${encodeURIComponent(steps[activeIndex + 1])}`);
    });
  }

  function StatementReviewPage(root, urls) {
    const state = incidentStore.getState();
    const search = new URLSearchParams(window.location.search);
    const statementId = search.get('statement_id') || '';
    const statement = incidentStore.getStatementById(statementId) || (state.statements || [])[0] || null;
    if (!statement) {
      window.location.replace(urls.statements);
      return;
    }
    const preview = statementPreviewPages(statement, state);
      const currentDraft = statementReviewedText(statement) || preview.draft;
    if (!statement.formattedDraft && preview.draft) {
      incidentStore.upsertStatement({ id: statement.id, variant: statement.variant, formattedDraft: preview.draft, reviewedDraft: preview.draft });
    }
    root.innerHTML = `
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>Review statement</h3>
        </div>
        <div class="mobile-step-progress">
          <span>Main task</span>
          <strong>Read and correct the statement draft</strong>
        </div>
        ${NarrativeEditor(currentDraft, true)}
        <details class="mobile-disclosure">
          <summary>More Options</summary>
          <div class="mobile-disclosure-copy">
            <button class="mobile-outline-button" type="button" data-regenerate-statement>Regenerate Draft</button>
            <a class="mobile-outline-button" href="${escapeHtml(`/forms/${statement.formId}/fill`)}">Open Real Form</a>
          </div>
        </details>
      </section>
      ${preview.overflow ? '<div class="mobile-empty-card">Statement needs continuation review before send.</div>' : ''}
      ${StickyWizardBar({
        title: 'Approve this draft and move to signatures',
        backHref: `${urls.statementEntry}?statement_id=${encodeURIComponent(statement.id)}`,
        backLabel: 'Entry',
        nextHref: `${urls.statementSignature}?statement_id=${encodeURIComponent(statement.id)}`,
        nextLabel: 'Approve',
        disabled: false,
      })}
    `;
    const editor = root.querySelector('[data-narrative-editor]');
    const regenerate = root.querySelector('[data-regenerate-statement]');
    if (editor) {
      editor.addEventListener('input', () => {
        incidentStore.upsertStatement({ id: statement.id, variant: statement.variant, reviewedDraft: editor.value, formattedDraft: preview.draft });
      });
    }
    if (regenerate && editor) {
      regenerate.addEventListener('click', () => {
        const refreshedStatement = incidentStore.getStatementById(statement.id) || statement;
        const refreshedPreview = statementPreviewPages(refreshedStatement, incidentStore.getState());
        editor.value = refreshedPreview.draft;
        incidentStore.upsertStatement({ id: statement.id, variant: statement.variant, formattedDraft: refreshedPreview.draft, reviewedDraft: refreshedPreview.draft });
      });
    }
  }

  function SignatureCapturePage(root, urls) {
    const state = incidentStore.getState();
    const search = new URLSearchParams(window.location.search);
    const statementId = search.get('statement_id') || '';
    const statement = incidentStore.getStatementById(statementId) || (state.statements || [])[0] || null;
    if (!statement) {
      window.location.replace(urls.statements);
      return;
    }
    const preview = statementPreviewPages(statement, state);
    root.innerHTML = `
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>Signature capture</h3>
          <p>${escapeHtml(`${preview.pages.length} statement page${preview.pages.length === 1 ? '' : 's'}`)}</p>
        </div>
        <div class="mobile-step-progress">
          <span>Main task</span>
          <strong>Capture the required initials and signatures</strong>
        </div>
      </section>
      <section class="mobile-section-block">
        <div class="mobile-pad-stack">
          ${InitialsPad(statement.initialsDataUrl)}
          ${SignaturePad('Declarant Signature', 'signatureDataUrl', statement.signatureDataUrl)}
          ${SignaturePad('Witnessing Officer Signature', 'witnessingSignatureDataUrl', statement.witnessingSignatureDataUrl)}
        </div>
      </section>
      ${StickyWizardBar({
        title: 'Statement signature blocks',
        backHref: `${urls.statementReview}?statement_id=${encodeURIComponent(statement.id)}`,
        backLabel: 'Review',
        nextHref: urls.domestic,
        nextLabel: 'Domestic Step',
        disabled: false,
      })}
    `;
    bindSignatureCanvas(root.querySelector('[data-initials-pad]'), (value) => {
      incidentStore.upsertStatement({ id: statement.id, variant: statement.variant, initialsDataUrl: value });
    });
    root.querySelectorAll('[data-signature-pad]').forEach((canvas) => {
      bindSignatureCanvas(canvas, (value) => {
        incidentStore.upsertStatement({ id: statement.id, variant: statement.variant, [canvas.getAttribute('data-signature-pad')]: value });
      });
    });
    root.querySelectorAll('[data-pad-clear]').forEach((button) => {
      button.addEventListener('click', () => {
        const key = button.getAttribute('data-pad-clear');
        const canvas = key === 'initials'
          ? root.querySelector('[data-initials-pad]')
          : root.querySelector(`[data-signature-pad="${key}"]`);
        if (canvas) {
          const context = canvas.getContext('2d');
          if (context) context.clearRect(0, 0, canvas.width, canvas.height);
        }
        incidentStore.upsertStatement({ id: statement.id, variant: statement.variant, [key === 'initials' ? 'initialsDataUrl' : key]: '' });
      });
    });
  }

  function DomesticSupplementalPage(root, urls) {
    const state = incidentStore.getState();
    const catalog = readMobileFormCatalog();
    const schema = readDomesticSchema();
    const domesticRecord = resolveCatalogRecord(catalog, 'NAVMAC 11337 MILITARY POLICE DOMESTIC VIOLENCE SIPPLEMENT REPORT AND CHECKLIST');
    let draft = incidentStore.getFormDraft('domesticSupplemental');
    const prefillPatch = domesticPrefillPatch(state, draft);
    if (Object.keys(prefillPatch).length) {
      incidentStore.updateFormDraft('domesticSupplemental', prefillPatch);
      draft = incidentStore.getFormDraft('domesticSupplemental');
    }
    if (!isDomesticSelected(state)) {
      root.innerHTML = `
        <section class="mobile-section-block">
          <div class="mobile-section-head">
            <h3>Domestic supplemental</h3>
          </div>
          <div class="mobile-empty-card">The domestic supplemental is not selected in this packet. You can skip this step.</div>
        </section>
        ${StickyWizardBar({
          title: 'No domestic supplemental selected',
          backHref: urls.statements,
          backLabel: 'Statements',
          nextHref: urls.packetReview,
          nextLabel: 'Packet Review',
          disabled: false,
        })}
        `;
        return;
      }
    const sectionSteps = buildDomesticGuidedSteps(schema);
    const search = new URLSearchParams(window.location.search);
    const requested = Number.parseInt(search.get('step') || '0', 10);
    const activeIndex = Number.isFinite(requested) && requested >= 0 && requested < sectionSteps.length ? requested : 0;
    const activeStep = sectionSteps[activeIndex] || { title: 'Domestic Supplemental', note: '', fields: [] };
    const visibleFields = (activeStep.fields || []).filter((field) => isDomesticFieldRelevant(field, draft));
    const answeredCount = Object.keys(draft).filter((key) => {
      const value = draft[key];
      return value === true || String(value || '').trim();
    }).length;
    root.innerHTML = `
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>${escapeHtml(activeStep.title)}</h3>
        </div>
        ${inlineProgressChips(sectionSteps.length || 1, activeIndex)}
        <div class="mobile-step-title">Step ${activeIndex + 1} of ${sectionSteps.length || 1}</div>
        ${activeStep.note ? `<div class="mobile-inline-note">${escapeHtml(activeStep.note)}</div>` : ''}
        <div class="mobile-domestic-field-stack">
          ${visibleFields.map((field) => domesticFieldInput(field, draft)).join('')}
        </div>
        <div class="mobile-inline-note">${escapeHtml(`${answeredCount} original domestic fields captured`)}</div>
      </section>
      ${StickyWizardBar({
        title: activeIndex === sectionSteps.length - 1 ? 'Finish this domestic form and continue' : 'Answer this section and continue',
        backHref: activeIndex === 0 ? urls.statements : `${urls.domestic}?step=${activeIndex - 1}`,
        backLabel: activeIndex === 0 ? 'Statements' : 'Back',
        nextHref: activeIndex === sectionSteps.length - 1 ? urls.packetReview : `${urls.domestic}?step=${activeIndex + 1}`,
        nextLabel: activeIndex === sectionSteps.length - 1 ? 'Packet Review' : 'Next',
        disabled: false,
      })}
    `;
    root.querySelectorAll('[data-domestic-field]').forEach((field) => {
      field.addEventListener('input', () => {
        incidentStore.updateFormDraft('domesticSupplemental', { [field.getAttribute('data-domestic-field')]: field.value });
      });
    });
      root.querySelectorAll('[data-domestic-checkbox]').forEach((button) => {
        button.addEventListener('click', () => {
          const key = button.getAttribute('data-domestic-checkbox');
          const groupKey = button.getAttribute('data-domestic-radio-group') || '';
          const currentDraft = incidentStore.getFormDraft('domesticSupplemental');
          const nextPatch = {};
          if (groupKey) {
            sectionSteps.forEach((step) => {
              (step.fields || []).forEach((field) => {
                if (domesticRadioGroupKey(field) === groupKey) nextPatch[domesticFieldNameKey(field)] = false;
              });
            });
          }
          nextPatch[key] = !currentDraft[key];
          incidentStore.updateFormDraft('domesticSupplemental', nextPatch);
        DomesticSupplementalPage(root, urls);
      });
    });
  }

  function _reviewDot(ok) {
    return `<span class="mobile-review-dot ${ok ? 'is-ok' : 'is-warn'}"></span>`;
  }

  function PacketReviewPage(root, urls) {
    const state = incidentStore.getState();
    const packet = buildPacket(state, readMobileFormCatalog());
    incidentStore.updatePacketStatus(packet.canSend ? 'packet_ready' : 'forms_reviewed');

    const errorFields = new Set((packet.errors || []).map((e) => e.field));
    const warnFields = new Set((packet.warnings || []).map((w) => w.field));

    const basicsOk = !errorFields.has('Incident Date') && !errorFields.has('Location') && !errorFields.has('Reporting Officer');
    const formsOk = !errorFields.has('Forms') && !errorFields.has('MCPD Stat Sheet');
    const peopleOk = !errorFields.has('People');
    const factsOk = !errorFields.has('Facts Capture');
    const narrativeOk = !errorFields.has('Narrative');
    const statementsOk = !errorFields.has('Statements');

    const statSheetOk = !errorFields.has('MCPD Stat Sheet');
    const statSheetSummary = statSheetOk ? 'Included in packet' : 'Missing — required for all packets';

    const basicsSummary = [
      packet.basics.occurredDate || 'Date missing',
      packet.basics.location || 'Location missing',
      packet.basics.reportingOfficer || 'Officer missing',
    ].join(' · ');
    const formsSummary = packet.formEntries.length ? `${packet.formEntries.length} form${packet.formEntries.length === 1 ? '' : 's'} selected` : 'No forms selected';
    const statementsSummary = packet.statements.length ? `${packet.statements.length} statement${packet.statements.length === 1 ? '' : 's'} attached` : 'No statements attached';
    const domesticSelected = packet.formEntries.some((entry) => normalizeLookupKey(entry.requestedTitle).includes('domesticviolence'));
    const personCount = (state.persons || []).length;
    const primaryFact = incidentPrimaryFact(state);

    const bannerClass = packet.canSend ? 'is-ready' : (packet.errors.length ? 'is-error' : 'is-warn');
    const bannerText = packet.canSend
      ? 'Packet is complete — ready to send'
      : packet.errors.length
        ? `${packet.errors.length} item${packet.errors.length === 1 ? '' : 's'} must be resolved before sending`
        : `${packet.warnings.length} reminder${packet.warnings.length === 1 ? '' : 's'} — packet can still be sent`;

    root.innerHTML = `
      <div class="mobile-packet-status-banner ${bannerClass}">
        <span class="mobile-packet-status-icon">${packet.canSend ? '✓' : packet.errors.length ? '⚠' : '●'}</span>
        <span class="mobile-packet-status-text">${escapeHtml(bannerText)}</span>
      </div>
      ${packet.errors.length ? packetValidationCard('Required — Resolve Before Send', packet.errors, 'error') : ''}
      ${packet.warnings.length ? packetValidationCard('Reminders — Review Before Send', packet.warnings, 'warning') : ''}
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>Packet review</h3>
        </div>
        <div class="mobile-packet-summary-grid">
          <article class="mobile-review-card ${statSheetOk ? '' : 'is-error'}">
            <div class="mobile-review-copy">
              ${_reviewDot(statSheetOk)}
              <strong>Stat Sheet</strong>
              <p>${escapeHtml(statSheetSummary)}</p>
            </div>
            <a class="mobile-review-link" href="${escapeHtml(urls.forms)}">Forms</a>
          </article>
          ${ReviewEditCard('Incident', basicsSummary, urls.basics, 'Edit', basicsOk ? '' : 'warning')}
          ${ReviewEditCard('Forms', formsSummary, urls.forms, 'Edit', formsOk ? '' : 'warning')}
          ${ReviewEditCard('People', `${personCount} ${personCount === 1 ? 'person' : 'people'} attached`, urls.persons, 'Edit', peopleOk ? '' : 'warning')}
          ${ReviewEditCard('Facts', shortText(primaryFact, 96) || 'Main facts missing', urls.facts, 'Edit', factsOk ? '' : 'warning')}
          ${ReviewEditCard('Narrative', shortText(packet.narrative, 96) || 'Narrative missing', urls.narrative, 'Edit', narrativeOk ? '' : 'warning')}
          ${ReviewEditCard('Statements', statementsSummary, urls.statements, 'Open', statementsOk ? '' : 'warning')}
          ${ReviewEditCard('Domestic', domesticSelected ? 'Review domestic supplemental' : 'Not selected for this packet', urls.domestic, domesticSelected ? 'Open' : 'Skip')}
        </div>
      </section>
      ${StickyWizardBar({
        title: packet.canSend ? 'Packet is ready for the send screen' : 'Resolve packet blockers before delivery',
        backHref: urls.domestic,
        backLabel: 'Domestic',
        nextHref: urls.sendPacket,
        nextLabel: 'Send Packet',
        disabled: false,
      })}
    `;
  }

  function SendPacketPage(root, urls) {
    const state = incidentStore.getState();
    const packet = buildPacket(state, readMobileFormCatalog());
    const defaultRecipient = String(root.getAttribute('data-mobile-packet-recipient') || '').trim();
    const ccList = String(root.getAttribute('data-mobile-packet-cc') || '').trim();
    root.innerHTML = `
      ${packet.errors.length ? packetValidationCard('Missing Before Send', packet.errors, 'error') : ''}
      <section class="mobile-section-block">
        <div class="mobile-section-head">
          <h3>Send packet</h3>
        </div>
        <div class="mobile-step-progress">
          <span>Main task</span>
          <strong>Confirm the email and send the packet</strong>
        </div>
        <label class="mobile-field-block">
          <span>Email</span>
          <input class="mobile-text-input" type="email" data-packet-recipient value="${escapeHtml(defaultRecipient)}" placeholder="officer@example.mil" />
        </label>
        ${ccList ? `<div class="mobile-inline-note">CC ${escapeHtml(ccList)}</div>` : ''}
        <div class="mobile-packet-send-actions">
          <button class="mobile-send-button" type="button" data-send-packet ${packet.canSend ? '' : 'disabled'}>Send Packet</button>
          <div class="mobile-send-status" data-send-status>${packet.canSend ? 'Ready to send.' : 'Resolve blockers on the review screen first.'}</div>
        </div>
      </section>
      ${StickyWizardBar({
        title: packet.canSend ? 'Send when the email looks right' : 'Go back and fix the missing items first',
        backHref: urls.packetReview,
        backLabel: 'Review',
        nextHref: '',
        disabled: true,
      })}
    `;

    const sendButton = root.querySelector('[data-send-packet]');
    const recipientField = root.querySelector('[data-packet-recipient]');
    const status = root.querySelector('[data-send-status]');
    if (!sendButton || !recipientField || !status) return;
    sendButton.addEventListener('click', async () => {
      const recipient = String(recipientField.value || '').trim();
      if (!recipient) {
        status.textContent = 'Enter the email before sending.';
        return;
      }
      sendButton.disabled = true;
      status.textContent = 'Sending...';
      try {
        const response = await fetch(urls.packetSendApi, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({
            incident: Object.assign({}, incidentStore.getState(), {
              packetRecipient: recipient,
            }),
          }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || !payload.ok) {
          const firstError = Array.isArray(payload.errors) && payload.errors.length ? payload.errors[0].message : 'Packet send failed.';
          status.textContent = firstError;
          sendButton.disabled = false;
          return;
        }
        clearSessionAfterSend();
        window.location.assign(`${urls.success}?recipient=${encodeURIComponent(payload.recipient || recipient)}`);
      } catch (_error) {
        status.textContent = 'Unable to send right now.';
        sendButton.disabled = false;
      }
    });
  }

  function SuccessPage(root, urls) {
    const search = new URLSearchParams(window.location.search);
    const recipient = search.get('recipient') || '';
    root.innerHTML = `
      <section class="mobile-success-card">
        <strong>Packet sent</strong>
        <p>${escapeHtml(recipient ? `Sent to ${recipient}.` : 'The packet was sent.')}</p>
        <a class="mobile-send-button" href="${escapeHtml(urls.home)}">Back To Home</a>
      </section>
    `;
  }

  function mountIncidentPages() {
    const root = document.querySelector('.mobile-incident-app');
    if (!root) return;
    const page = root.getAttribute('data-mobile-incident-page') || 'start';
    const urls = {
      home: root.getAttribute('data-mobile-home-url') || '/mobile/home',
      start: root.getAttribute('data-mobile-start-url') || '/mobile/incident/start',
      basics: root.getAttribute('data-mobile-basics-url') || '/mobile/incident/basics',
      forms: root.getAttribute('data-mobile-forms-url') || '/mobile/incident/selected-forms',
      persons: root.getAttribute('data-mobile-persons-url') || '/mobile/incident/persons',
      personEditor: root.getAttribute('data-mobile-person-editor-url') || '/mobile/incident/persons/edit',
      statute: root.getAttribute('data-mobile-statute-url') || '/mobile/incident/statute',
      checklist: root.getAttribute('data-mobile-checklist-url') || '/mobile/incident/checklist',
      facts: root.getAttribute('data-mobile-facts-url') || '/mobile/incident/facts',
      narrative: root.getAttribute('data-mobile-narrative-url') || '/mobile/incident/narrative-review',
      statements: root.getAttribute('data-mobile-statements-url') || '/mobile/incident/statements',
      statementEntry: root.getAttribute('data-mobile-statement-entry-url') || '/mobile/incident/statements/entry',
      statementReview: root.getAttribute('data-mobile-statement-review-url') || '/mobile/incident/statements/review',
      statementSignature: root.getAttribute('data-mobile-statement-signature-url') || '/mobile/incident/statements/signature',
      domestic: root.getAttribute('data-mobile-domestic-url') || '/mobile/incident/domestic-supplemental',
      packetReview: root.getAttribute('data-mobile-packet-review-url') || '/mobile/incident/packet-review',
      sendPacket: root.getAttribute('data-mobile-send-packet-url') || '/mobile/incident/send-packet',
      success: root.getAttribute('data-mobile-success-url') || '/mobile/incident/success',
      packetSendApi: root.getAttribute('data-mobile-packet-send-api-url') || '/mobile/api/incident/send-packet',
      reference: root.getAttribute('data-mobile-reference-url') || '/incident-paperwork-guide',
    };
    if (page === 'start') return StartIncidentPage(root, urls);
    if (page === 'basics') return IncidentBasicsPage(root, urls);
    if (page === 'selected-forms' || page === 'recommended-forms') return SelectedFormsPage(root, urls);
    if (page === 'persons-list') return PersonsListPage(root, urls);
    if (page === 'person-editor') return PersonEditorPage(root, urls);
    if (page === 'statute') return StatutePage(root, urls);
    if (page === 'checklist') return ChecklistPage(root, urls);
    if (page === 'facts') return FactsCapturePage(root, urls);
    if (page === 'narrative-review') return NarrativeReviewPage(root, urls);
    if (page === 'statement-launcher') return StatementLauncherPage(root, urls);
    if (page === 'statement-entry') return StatementEntryPage(root, urls);
    if (page === 'statement-review') return StatementReviewPage(root, urls);
    if (page === 'statement-signature') return SignatureCapturePage(root, urls);
    if (page === 'domestic-supplemental') return DomesticSupplementalPage(root, urls);
    if (page === 'packet-review') return PacketReviewPage(root, urls);
    if (page === 'send-packet') return SendPacketPage(root, urls);
    if (page === 'packet-success') return SuccessPage(root, urls);
  }

  window.McpdIncidentStore = incidentStore;
  window.addEventListener('load', mountIncidentPages);
})();
