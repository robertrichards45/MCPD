(function () {
  'use strict';

  function byId(id) { return document.getElementById(id); }
  function value(id) { var el = byId(id); return el ? String(el.value || '').trim() : ''; }
  function setValue(id, text) { var el = byId(id); if (el) el.value = text; }

  function firstMatch(text, patterns) {
    for (var i = 0; i < patterns.length; i += 1) {
      var match = text.match(patterns[i]);
      if (match && match[1]) return match[1].trim();
    }
    return '';
  }

  function compact(text) { return String(text || '').replace(/\s+/g, ' ').trim(); }

  function unique(items) {
    var seen = {};
    return items.map(compact).filter(function (item) {
      var key = item.toLowerCase();
      if (!item || seen[key]) return false;
      seen[key] = true;
      return true;
    });
  }

  function splitSentences(text) {
    return compact(text).match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [];
  }

  function sentencesMatching(sentences, pattern) {
    return unique(sentences.filter(function (s) { return pattern.test(s); }));
  }

  function joinFacts(items, fallback) {
    var cleaned = unique(items);
    return cleaned.length ? cleaned.join(' ') : fallback;
  }

  function buildFiveWsFromNotes(notes) {
    var clean = compact(notes);
    if (!clean) {
      return 'Who: [not entered]\n\nWhat: [not entered]\n\nWhen: [not entered]\n\nWhere: [not entered]\n\nWhy / How: [not entered]\n\nOfficer Actions: [not entered]\n\nNarrative Starter: Add incident notes first.';
    }

    var when = firstMatch(clean, [
      /\b(on\s+\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4}(?:\s+at\s+\d{3,4})?)/i,
      /\b(at\s+\d{3,4}\s*(?:hours|hrs)?)/i,
      /\b(today|yesterday|this morning|this afternoon|this evening)\b/i,
    ]);
    var where = firstMatch(clean, [
      /\b(?:at|to|near|inside|outside)\s+(?:the\s+)?([A-Z][A-Za-z0-9\s\/&.-]{2,60}?)(?:\s+for|\s+regarding|\.|,|$)/,
      /\blocation\s*[:\-]\s*([^.;]+)/i,
    ]);
    var sentences = splitSentences(clean);
    var people = sentencesMatching(sentences, /\b(subject|suspect|victim|complainant|witness|driver|passenger|officer|marine|civilian|spouse|husband|wife|child|person|party)\b/i);
    var actions = sentencesMatching(sentences, /\b(I|officer|patrol|unit|we)\s+(responded|arrived|observed|located|detained|searched|recovered|photographed|notified|interviewed|advised|issued|transported|cleared|secured|placed|arrested|cited|completed|requested)\b/i);
    var whatFacts = sentencesMatching(sentences, /(reported|observed|concealed|stole|took|struck|hit|pushed|damaged|entered|refused|returned|crash|collision|accident|larceny|assault|trespass|barred|order|weed|marijuana|domestic|disturbance|theft|property|injury|vehicle|gate|base|installation)/i);
    var howFacts = sentencesMatching(sentences, /(because|after|before|during|while|when|then|by |using|sequence|method|concealed|forced|entered|refused|returned|fled|left|approached|followed|northbound|southbound|eastbound|westbound|direction|traveling|located|found)/i);
    if (!whatFacts.length && sentences.length) whatFacts = [sentences[0]];

    var out = [];
    out.push('Who: ' + joinFacts(people, 'Not clearly stated. Add involved persons, roles, or unit identifiers if known.'));
    out.push('What: ' + joinFacts(whatFacts, 'Not clearly stated. Add the main incident conduct or complaint.'));
    out.push('When: ' + (when || 'Not clearly stated. Add date/time if known.'));
    out.push('Where: ' + (where || 'Not clearly stated. Add location if known.'));
    out.push('Why / How: ' + joinFacts(howFacts, 'Not clearly stated. Use officer-entered sequence, method, and context only.'));
    out.push('Officer Actions: ' + joinFacts(actions, 'Not clearly stated. Add response, detention, evidence, notifications, or disposition if known.'));
    out.push('Narrative Starter: ' + [
      when ? 'On ' + when.replace(/^on\s+/i, '') + ',' : 'On [date/time],',
      where ? 'at ' + where + ',' : 'at [location],',
      compact(whatFacts[0] || clean).replace(/\.$/, '') + '.',
      actions.length ? actions.join(' ') : ''
    ].filter(Boolean).join(' '));
    out.push('Full Officer Notes: ' + clean);
    out.push('Officer Review: Verify all facts before texting, emailing, or adding to a report.');
    return out.join('\n\n');
  }

  function buildNarrativeFromNotes(notes) {
    var clean = compact(notes);
    if (!clean) return 'Narrative Draft:\n\nAdd incident notes first.\n\nOfficer Review: Verify all facts before using this narrative.';
    var summary = buildFiveWsFromNotes(clean);
    var starterMatch = summary.match(/Narrative Starter:\s*([\s\S]*?)(?:\n\nFull Officer Notes:|$)/);
    var starter = starterMatch && starterMatch[1] ? compact(starterMatch[1]) : clean;
    return ['Narrative Draft:', '', starter, '', 'Officer Review:', 'Review and edit this draft before adding it to a report. Do not add facts that were not entered by the officer.', '', 'Source Notes:', clean].join('\n');
  }

  // ── Share links ────────────────────────────────────────────────────
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

  // ── CSRF token helper ──────────────────────────────────────────────
  function getCsrf() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? (meta.getAttribute('content') || '') : '';
  }

  // ── Generate (local for narrative/5w, AI for blotter) ─────────────
  function buildNarrative() {
    var mode = currentMode();
    var notes = value('n5w-intake');

    if (mode === 'blotter') {
      generateBlotter(notes);
      return;
    }

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
      body: JSON.stringify({ text: callLog }),
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

  // ── Quality Check ──────────────────────────────────────────────────
  function hideQualityPanel() {
    var panel = byId('n5w-quality-panel');
    if (panel) panel.style.display = 'none';
  }

  function runQualityCheck() {
    var text = value('n5w-output');
    if (!text) { alert('Generate a narrative first, then run Quality Check.'); return; }

    var checkBtn = byId('n5w-check');
    if (checkBtn) { checkBtn.disabled = true; checkBtn.textContent = 'Checking…'; }

    fetch('/api/tools/narrative/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ text: text }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (checkBtn) { checkBtn.disabled = false; checkBtn.textContent = 'Quality Check'; }
        if (data.ok && data.result) {
          showQualityResult(data.result);
        } else {
          alert('Quality check failed: ' + (data.error || 'Unknown error'));
        }
      })
      .catch(function () {
        if (checkBtn) { checkBtn.disabled = false; checkBtn.textContent = 'Quality Check'; }
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

    function fillList(id, items) {
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
        li.textContent = 'None identified.';
        ul.appendChild(li);
      }
    }

    fillList('n5w-strengths', result.strengths);
    fillList('n5w-issues', result.issues);
    fillList('n5w-suggestions', result.suggestions);

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

  // ── Copy / share ───────────────────────────────────────────────────
  function copyOutput() {
    var output = value('n5w-output');
    if (!output) return;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(output).catch(function () {});
    }
  }

  function clearAll() {
    setValue('n5w-intake', '');
    setValue('n5w-output', '');
    hideQualityPanel();
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

  var build    = byId('n5w-build');
  var clear    = byId('n5w-clear');
  var copy     = byId('n5w-copy');
  var check    = byId('n5w-check');
  if (build)  build.addEventListener('click', buildNarrative);
  if (clear)  clear.addEventListener('click', clearAll);
  if (copy)   copy.addEventListener('click', copyOutput);
  if (check)  check.addEventListener('click', runQualityCheck);
  bindShareFallback();
  updateShareLinks();
}());
