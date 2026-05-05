(function () {
  'use strict';

  function value(id) {
    var el = document.getElementById(id);
    return el ? String(el.value || '').trim() : '';
  }

  function setValue(id, text) {
    var el = document.getElementById(id);
    if (el) el.value = text;
  }

  function sentence(label, text) {
    return text ? label + ': ' + text : '';
  }

  function buildNarrative() {
    var who = value('n5w-who');
    var what = value('n5w-what');
    var when = value('n5w-when');
    var where = value('n5w-where');
    var why = value('n5w-why');
    var actions = value('n5w-actions');
    var lines = [];

    if (when || where) {
      lines.push('On ' + (when || '[date/time]') + ', at ' + (where || '[location]') + ', the following incident was documented.');
    }
    if (who) lines.push(sentence('Involved parties', who) + '.');
    if (what) lines.push(sentence('Incident summary', what) + '.');
    if (why) lines.push(sentence('Known reason, method, or sequence', why) + '.');
    if (actions) lines.push(sentence('Officer actions', actions) + '.');
    lines.push('This draft is based only on the facts entered above and must be reviewed, corrected, and approved by the officer before use.');

    setValue('n5w-output', lines.join('\n\n'));
  }

  function clearAll() {
    ['n5w-who', 'n5w-what', 'n5w-when', 'n5w-where', 'n5w-why', 'n5w-actions', 'n5w-output'].forEach(function (id) {
      setValue(id, '');
    });
  }

  var build = document.getElementById('n5w-build');
  var clear = document.getElementById('n5w-clear');
  if (build) build.addEventListener('click', buildNarrative);
  if (clear) clear.addEventListener('click', clearAll);
}());
