(function () {
  'use strict';

  function byId(id) { return document.getElementById(id); }
  function value(id) { var el = byId(id); return el ? String(el.value || '').trim() : ''; }
  function setValue(id, text) { var el = byId(id); if (el) el.value = text; }
  function compact(text) { return String(text || '').replace(/\s+/g, ' ').trim(); }

  function unique(items) {
    var seen = {};
    return (items || []).map(compact).filter(function (item) {
      var key = item.toLowerCase();
      if (!item || seen[key]) return false;
      seen[key] = true;
      return true;
    });
  }

  function firstMatch(text, patterns) {
    for (var i = 0; i < patterns.length; i += 1) {
      var match = text.match(patterns[i]);
      if (match && match[1]) return match[1].trim();
    }
    return '';
  }

  function splitSentences(text) {
    var prepared = String(text || '')
      .split(/\n+/)
      .map(function (line) { return compact(line); })
      .filter(Boolean)
      .map(function (line) { return /[.!?]$/.test(line) ? line : line + '.'; })
      .join(' ');
    return prepared.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [];
  }

  function sentencesMatching(sentences, pattern) {
    return unique(sentences.filter(function (sentence) { return pattern.test(sentence); }));
  }

  function joinFacts(items, fallback) {
    var cleaned = unique(items);
    return cleaned.length ? cleaned.join(' ') : fallback;
  }

  function detectFactReview(notes) {
    var clean = compact(notes);
    var sentences = splitSentences(notes);
    var checks = [
      { key: 'date', label: 'Incident / response date', pattern: /\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})\b/i },
      { key: 'time', label: 'Dispatch / response time', pattern: /\b(?:at\s+)?\d{3,4}\s*(?:hours|hrs)?\b/i },
      { key: 'location', label: 'Incident location', pattern: /\b(?:building|bldg\.?|gate|road|rd\.?|street|st\.?|avenue|ave\.?|boulevard|blvd\.?|parking|px|mcx|barracks|housing|location)\b/i },
      { key: 'people', label: 'Involved person(s) / role(s)', pattern: /\b(?:subject|suspect|victim|complainant|reporting party|witness|driver|passenger|employee|officer|marine|civilian)\b/i },
      { key: 'response', label: 'Officer response / arrival', pattern: /\b(?:dispatched|responded|arrived|made contact|contacted)\b/i },
      { key: 'observations', label: 'Officer observations or statements', pattern: /\b(?:observed|noticed|saw|stated|advised|reported|told|informed|said)\b/i },
      { key: 'actions', label: 'Officer actions taken', pattern: /\b(?:detained|arrested|cited|issued|searched|recovered|photographed|collected|secured|separated|interviewed|requested|notified|advised|transported)\b/i },
      { key: 'evidence', label: 'Evidence / property handling (if applicable)', pattern: /\b(?:evidence|property|photograph|photo|video|body[- ]?cam|recovered|collected|seized|tagged|submitted|chain of custody)\b/i },
      { key: 'disposition', label: 'Disposition / case outcome', pattern: /\b(?:cleared|released|arrested|transported|referred|forwarded|completed|closed|returned|turned over|citation|summons|no further action|disposition)\b/i },
      { key: 'notification', label: 'Supervisor / required notification (if applicable)', pattern: /\b(?:supervisor|watch commander|desk sergeant|cid|investigator|notified|notification)\b/i }
    ];

    var detected = [];
    var missing = [];
    checks.forEach(function (check) {
      if (check.pattern.test(clean)) detected.push(check.label);
      else missing.push(check.label);
    });

    var consistency = [];
    var dates = unique(clean.match(/\b\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4}\b/g) || []);
    var times = unique(clean.match(/\b\d{3,4}\s*(?:hours|hrs)?\b/gi) || []);
    if (dates.length > 1) consistency.push('Multiple dates are present. Confirm each date is tied to the correct event.');
    if (times.length > 2) consistency.push('Several times are present. Confirm dispatch, arrival, event, and disposition times are clearly distinguished.');
    if (/\b(?:unknown|unidentified)\b/i.test(clean)) consistency.push('An unknown/unidentified person or fact is referenced. Confirm the narrative makes clear what is known versus unknown.');
    if (/\b(?:approximately|approx\.?|about)\b/i.test(clean)) consistency.push('Approximate information is present. Confirm estimates are identified as estimates and are supported by the source of knowledge.');
    if (/\b(?:I think|I believe|probably|maybe|apparently)\b/i.test(clean)) consistency.push('Potentially subjective wording is present. Replace assumptions with observations, statements, or clearly attributed information.');
    if (!consistency.length) consistency.push('No obvious internal consistency cue was detected by the local review. Still verify names, dates, times, locations, vehicles, and dispositions against the source record.');

    return {
      detected: detected,
      missing: missing,
      consistency: consistency,
      sentences: sentences
    };
  }

  function fillList(id, items, fallback) {
    var ul = byId(id);
    if (!ul) return;
    ul.innerHTML = '';
    (items || []).forEach(function (item) {
      var li = document.createElement('li');
      li.textContent = item;
      ul.appendChild(li);
    });
    if (!ul.children.length) {
      var li = document.createElement('li');
      li.textContent = fallback || 'None identified.';
      ul.appendChild(li);
    }
  }

  function showFactReview(notes) {
    var panel = byId('n5w-fact-review');
    if (!panel) return null;
    var review = detectFactReview(notes);
    panel.style.display = '';
    fillList('n5w-facts-detected', review.detected, 'No core fact categories detected yet.');
    fillList('n5w-facts-missing', review.missing, 'No obvious core category is missing. Verify accuracy before use.');
    fillList('n5w-facts-consistency', review.consistency, 'Verify all identifiers and chronology.');
    var badge = byId('n5w-fact-status');
    if (badge) {
      badge.className = 'badge ' + (review.missing.length <= 2 ? 'bg-success' : review.missing.length <= 5 ? 'bg-warning text-dark' : 'bg-danger');
      badge.textContent = review.missing.length ? review.missing.length + ' item' + (review.missing.length === 1 ? '' : 's') + ' to verify' : 'Core facts detected';
    }
    return review;
  }

  function buildFiveWsFromNotes(notes) {
    var clean = compact(notes);
    if (!clean) {
      return 'Who: [not entered]\n\nWhat: [not entered]\n\nWhen: [not entered]\n\nWhere: [not entered]\n\nWhy / How: [not entered]\n\nOfficer Actions: [not entered]\n\nNarrative Starter: Add incident notes first.';
    }

    var when = firstMatch(clean, [
      /\b(on\s+\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4}(?:\s+at\s+\d{3,4})?)/i,
      /\b(at\s+\d{3,4}\s*(?:hours|hrs)?)/i,
      /\b(today|yesterday|this morning|this afternoon|this evening)\b/i
    ]);
    var where = firstMatch(clean, [
      /\b(?:at|to|near|inside|outside)\s+(?:the\s+)?([A-Z][A-Za-z0-9\s\/&.-]{2,60}?)(?:\s+for|\s+regarding|\.|,|$)/,
      /\blocation\s*[:\-]\s*([^.;]+)/i
    ]);
    var sentences = splitSentences(notes);
    var people = sentencesMatching(sentences, /\b(subject|suspect|victim|complainant|witness|driver|passenger|officer|marine|civilian|spouse|husband|wife|child|person|party)\b/i);
    var actions = sentencesMatching(sentences, /\b(I|officer|patrol|unit|we)\s+(responded|arrived|observed|located|detained|searched|recovered|photographed|notified|interviewed|advised|issued|transported|cleared|secured|placed|arrested|cited|completed|requested)\b/i);
    var whatFacts = sentencesMatching(sentences, /(reported|observed|concealed|stole|took|struck|hit|pushed|damaged|entered|refused|returned|crash|collision|accident|larceny|assault|trespass|barred|domestic|disturbance|theft|property|injury|vehicle|gate|base|installation)/i);
    var howFacts = sentencesMatching(sentences, /(because|after|before|during|while|when|then|by |using|sequence|method|concealed|forced|entered|refused|returned|fled|left|approached|followed|northbound|southbound|eastbound|westbound|direction|traveling|located|found)/i);
    if (!whatFacts.length && sentences.length) whatFacts = [sentences[0]];

    return [
      'Who: ' + joinFacts(people, 'Not clearly stated. Add involved persons, roles, or unit identifiers if known.'),
      'What: ' + joinFacts(whatFacts, 'Not clearly stated. Add the main incident conduct or complaint.'),
      'When: ' + (when || 'Not clearly stated. Add date/time if known.'),
      'Where: ' + (where || 'Not clearly stated. Add location if known.'),
      'Why / How: ' + joinFacts(howFacts, 'Not clearly stated. Use officer-entered sequence, method, and context only.'),
      'Officer Actions: ' + joinFacts(actions, 'Not clearly stated. Add response, detention, evidence, notifications, or disposition if known.'),
      'Officer Review: Verify all facts before using this summary.'
    ].join('\n\n');
  }

  function buildNarrativeFromNotes(notes) {
    var sentences = splitSentences(notes);
    if (!sentences.length) return 'Add incident facts first.';
    return sentences.map(compact).join(' ');
  }

  function updateShareLinks() {
    var output = value('n5w-output');
    var encoded = encodeURIComponent(output || 'No output generated yet.');
    var mode = currentMode();
    var title = mode === '5w' ? 'MCPD 5W Summary' : mode === 'blotter' ? 'MCPD Watch Blotter' : 'MCPD Narrative Draft';
    var textLink = byId('n5w-text');
    var emailLink = byId('n5w-email');
    if (textLink) textLink.href = 'sms:?&body=' + encoded;
    if (emailLink) emailLink.href = 'mailto:?subject=' + encodeURIComponent(title) + '&body=' + encoded;
  }

  function currentMode() {
    var build = byId('n5w-build');
    return build ? String(build.getAttribute('data-tool-mode') || 'narrative').toLowerCase() : 'narrative';
  }

  function getCsrf() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? (meta.getAttribute('content') || '') : '';
  }

  function buildNarrative() {
    var mode = currentMode();
    var notes = value('n5w-intake');
    if (!notes) { alert(mode === 'blotter' ? 'Enter your call log first.' : 'Enter the incident facts first.'); return; }

    if (mode === 'blotter') {
      generateBlotter(notes);
      return;
    }

    if (mode === 'narrative') showFactReview(notes);
    setValue('n5w-output', mode === '5w' ? buildFiveWsFromNotes(notes) : buildNarrativeFromNotes(notes));
    updateShareLinks();
    hideQualityPanel();
  }

  function generateBlotter(callLog) {
    if (!callLog) { alert('Enter your call log first.'); return; }
    var buildBtn = byId('n5w-build');
    if (buildBtn) { buildBtn.disabled = true; buildBtn.textContent = 'Generating…'; }

    fetch('/api/tools/blotter/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ text: callLog })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (buildBtn) { buildBtn.disabled = false; buildBtn.textContent = 'Generate Blotter (AI)'; }
        if (data.ok && data.blotter) {
          setValue('n5w-output', data.blotter);
          updateShareLinks();
        } else {
          alert('Blotter generation failed: ' + (data.error || 'Unknown error'));
        }
      })
      .catch(function () {
        if (buildBtn) { buildBtn.disabled = false; buildBtn.textContent = 'Generate Blotter (AI)'; }
        alert('Connection error. Check your network and try again.');
      });
  }

  function hideQualityPanel() {
    var panel = byId('n5w-quality-panel');
    if (panel) panel.style.display = 'none';
  }

  function runQualityCheck() {
    var text = value('n5w-output');
    if (!text) { alert('Generate a narrative first, then run AI Quality Check.'); return; }
    if (currentMode() === 'narrative') showFactReview(value('n5w-intake') || text);

    var checkBtn = byId('n5w-check');
    if (checkBtn) { checkBtn.disabled = true; checkBtn.textContent = 'Checking…'; }

    fetch('/api/tools/narrative/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ text: text, source_notes: value('n5w-intake') })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (checkBtn) { checkBtn.disabled = false; checkBtn.textContent = 'AI Quality Check'; }
        if (data.ok && data.result) showQualityResult(data.result);
        else alert('Quality check failed: ' + (data.error || 'Unknown error'));
      })
      .catch(function () {
        if (checkBtn) { checkBtn.disabled = false; checkBtn.textContent = 'AI Quality Check'; }
        alert('Connection error. Quality check requires an active connection.');
      });
  }

  function showQualityResult(result) {
    var panel = byId('n5w-quality-panel');
    if (!panel) return;
    panel.style.display = '';

    var badge = byId('n5w-score-badge');
    if (badge) {
      var score = parseInt(result.score, 10) || 0;
      var grade = result.grade || '?';
      badge.textContent = grade + ' (' + score + '/10)';
      badge.className = 'n5w-score-badge';
      if (score >= 8) badge.classList.add('score-a');
      else if (score >= 6) badge.classList.add('score-b');
      else if (score >= 4) badge.classList.add('score-c');
      else badge.classList.add('score-f');
    }

    fillList('n5w-strengths', result.strengths, 'No specific strength returned.');
    fillList('n5w-issues', result.issues, 'No specific issue returned.');
    fillList('n5w-suggestions', result.suggestions, 'No specific suggestion returned.');

    var improvedDiv = byId('n5w-improved-opening');
    var improvedText = byId('n5w-improved-text');
    if (improvedDiv && improvedText && result.improved_opening) {
      improvedDiv.style.display = '';
      improvedText.textContent = result.improved_opening;
    } else if (improvedDiv) {
      improvedDiv.style.display = 'none';
    }
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function copyOutput() {
    var output = value('n5w-output');
    if (!output) return;
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(output).catch(function () {});
  }

  function clearAll() {
    setValue('n5w-intake', '');
    setValue('n5w-output', '');
    hideQualityPanel();
    var factPanel = byId('n5w-fact-review');
    if (factPanel) factPanel.style.display = 'none';
    updateShareLinks();
  }

  function bindShareFallback() {
    var textLink = byId('n5w-text');
    if (!textLink || !navigator.share) return;
    textLink.addEventListener('click', function (event) {
      var output = value('n5w-output');
      if (!output) return;
      event.preventDefault();
      navigator.share({ title: currentMode() === '5w' ? 'MCPD 5W Summary' : currentMode() === 'blotter' ? 'MCPD Watch Blotter' : 'MCPD Narrative Draft', text: output }).catch(function () {
        window.location.href = textLink.href;
      });
    });
  }

  var build = byId('n5w-build');
  var clear = byId('n5w-clear');
  var copy = byId('n5w-copy');
  var check = byId('n5w-check');
  if (build) build.addEventListener('click', buildNarrative);
  if (clear) clear.addEventListener('click', clearAll);
  if (copy) copy.addEventListener('click', copyOutput);
  if (check) check.addEventListener('click', runQualityCheck);
  bindShareFallback();
  updateShareLinks();
}());
