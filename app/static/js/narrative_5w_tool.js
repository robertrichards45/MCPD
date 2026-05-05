(function () {
  'use strict';

  function byId(id) {
    return document.getElementById(id);
  }

  function value(id) {
    var el = byId(id);
    return el ? String(el.value || '').trim() : '';
  }

  function setValue(id, text) {
    var el = byId(id);
    if (el) el.value = text;
  }

  function firstMatch(text, patterns) {
    for (var i = 0; i < patterns.length; i += 1) {
      var match = text.match(patterns[i]);
      if (match && match[1]) return match[1].trim();
    }
    return '';
  }

  function compact(text) {
    return String(text || '').replace(/\s+/g, ' ').trim();
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
    var who = firstMatch(clean, [
      /\bsubject\s+([A-Z][A-Za-z ,.'-]{2,50})/i,
      /\bsuspect\s+([A-Z][A-Za-z ,.'-]{2,50})/i,
      /\b(?:victim|complainant|witness)\s+([A-Z][A-Za-z ,.'-]{2,50})/i,
    ]);
    var actions = [];
    [
      /\bI\s+(responded[^.]*\.)/i,
      /\bI\s+(detained[^.]*\.)/i,
      /\bI\s+(recovered[^.]*\.)/i,
      /\bI\s+(photographed[^.]*\.)/i,
      /\bI\s+(notified[^.]*\.)/i,
      /\bI\s+(interviewed[^.]*\.)/i,
    ].forEach(function (pattern) {
      var m = clean.match(pattern);
      if (m && m[1]) actions.push('I ' + m[1]);
    });

    var sentences = clean.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [clean];
    var what = sentences.find(function (sentence) {
      return /(reported|observed|concealed|stole|struck|pushed|damaged|entered|refused|returned|crash|collision|accident|larceny|assault|trespass)/i.test(sentence);
    }) || sentences[0] || clean;
    var whyHow = sentences.find(function (sentence) {
      return /(because|after|by |using|while|when|sequence|how|method|concealed|forced|entered|refused)/i.test(sentence) && sentence !== what;
    }) || '';

    var narrative = [];
    narrative.push('Who: ' + (who || 'Review notes for involved parties: ' + clean.slice(0, 140)));
    narrative.push('What: ' + compact(what));
    narrative.push('When: ' + (when || 'Not clearly stated. Add date/time if known.'));
    narrative.push('Where: ' + (where || 'Not clearly stated. Add location if known.'));
    narrative.push('Why / How: ' + (whyHow ? compact(whyHow) : 'Not clearly stated. Use officer-entered facts only.'));
    narrative.push('Officer Actions: ' + (actions.length ? actions.join(' ') : 'Not clearly stated. Add response, detention, evidence, notifications, or disposition if known.'));
    narrative.push('Narrative Starter: ' + [
      when ? 'On ' + when.replace(/^on\s+/i, '') + ',' : 'On [date/time],',
      where ? 'at ' + where + ',' : 'at [location],',
      compact(what).replace(/\.$/, '') + '.',
      actions.length ? actions.join(' ') : ''
    ].filter(Boolean).join(' '));
    narrative.push('Officer Review: Verify all facts before texting, emailing, or adding to a report.');
    return narrative.join('\n\n');
  }

  function updateShareLinks() {
    var output = value('n5w-output');
    var encoded = encodeURIComponent(output || 'No 5W summary generated yet.');
    var textLink = byId('n5w-text');
    var emailLink = byId('n5w-email');
    if (textLink) textLink.href = 'sms:?&body=' + encoded;
    if (emailLink) emailLink.href = 'mailto:?subject=' + encodeURIComponent('MCPD 5W Summary') + '&body=' + encoded;
  }

  function buildNarrative() {
    setValue('n5w-output', buildFiveWsFromNotes(value('n5w-intake')));
    updateShareLinks();
  }

  function clearAll() {
    setValue('n5w-intake', '');
    setValue('n5w-output', '');
    updateShareLinks();
  }

  function copyOutput() {
    var output = value('n5w-output');
    if (!output) return;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(output).catch(function () {});
    }
  }

  function bindShareFallback() {
    var textLink = byId('n5w-text');
    if (!textLink || !navigator.share) return;
    textLink.addEventListener('click', function (event) {
      var output = value('n5w-output');
      if (!output) return;
      event.preventDefault();
      navigator.share({ title: 'MCPD 5W Summary', text: output }).catch(function () {
        window.location.href = textLink.href;
      });
    });
  }

  var build = byId('n5w-build');
  var clear = byId('n5w-clear');
  var copy = byId('n5w-copy');
  if (build) build.addEventListener('click', buildNarrative);
  if (clear) clear.addEventListener('click', clearAll);
  if (copy) copy.addEventListener('click', copyOutput);
  bindShareFallback();
  updateShareLinks();
}());
