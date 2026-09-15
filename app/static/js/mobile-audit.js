(function () {
  'use strict';

  var body = document.body;
  if (!body) return;

  // Header controls can wrap with text enlargement or a safe-area inset.
  // Measure the actual height instead of covering the first page controls.
  var header = document.querySelector('.mcpd-command-header');
  if (header && window.ResizeObserver) {
    new ResizeObserver(function () {
      body.style.setProperty('--responsive-header-height', Math.ceil(header.getBoundingClientRect().height) + 'px');
    }).observe(header);
  }

  // Keep wide data tables independently scrollable and keyboard reachable.
  // Do not create nested scrollers when a page already supplies a wrapper.
  var tableFrame = null;
  function updateTables() {
    tableFrame = null;
    var narrow = window.matchMedia('(max-width: 1020px)').matches;
    document.querySelectorAll('.page-wrap table, main table, .mobile-main table').forEach(function (table) {
      var region = table.closest('.table-responsive') || table;
      var overflow = narrow && region.scrollWidth > region.clientWidth + 2;
      if (overflow && !region.hasAttribute('tabindex')) {
        region.tabIndex = 0;
        region.dataset.mobileTableFocus = 'true';
      } else if (!overflow && region.dataset.mobileTableFocus) {
        region.removeAttribute('tabindex');
        delete region.dataset.mobileTableFocus;
      }
      if (overflow) region.classList.add('mobile-table-scroll');
      else region.classList.remove('mobile-table-scroll');
    });
  }
  function scheduleTables() {
    if (!tableFrame) tableFrame = window.requestAnimationFrame(updateTables);
  }
  scheduleTables();
  window.addEventListener('resize', scheduleTables, { passive: true });
  new MutationObserver(scheduleTables).observe(body, { childList: true, subtree: true });

  function setStoredView(mode) {
    try {
      localStorage.setItem('mcpdViewMode', mode);
      localStorage.setItem('mcpd-view', mode);
    } catch (_err) {}
  }

  /* Entering /mobile is an explicit request for the field interface. Preserve
     that preference when the officer opens responsive desktop-backed tools
     such as FTO Center, Forms, Reports, or Accident Tools. */
  if (body.classList.contains('mobile-foundation')) {
    setStoredView('mobile');
    body.classList.remove('view-desktop');
    body.classList.add('view-mobile');
  }

  document.addEventListener('click', function (event) {
    var mobileLink = event.target.closest('[data-force-mobile]');
    if (mobileLink) {
      setStoredView('mobile');
      body.classList.remove('view-desktop');
      body.classList.add('force-mobile-view', 'view-mobile');
      return;
    }

    var desktopLink = event.target.closest('[data-force-desktop]');
    if (desktopLink) {
      setStoredView('desktop');
      body.classList.remove('force-mobile-view', 'view-mobile');
      body.classList.add('view-desktop');
    }
  }, true);

  if (!body.classList.contains('mobile-foundation')) return;

  var keyboardTimer = null;

  function editableTarget(target) {
    if (!target || !target.matches) return false;
    if (target.matches('textarea, select, [contenteditable="true"]')) return true;
    if (!target.matches('input')) return false;
    var type = String(target.getAttribute('type') || 'text').toLowerCase();
    return ['text', 'search', 'email', 'tel', 'url', 'number', 'password', 'date', 'time', 'datetime-local'].indexOf(type) !== -1;
  }

  function setKeyboardOpen(open) {
    body.classList.toggle('mobile-keyboard-open', !!open);
  }

  function focusedEditor() {
    return editableTarget(document.activeElement) ? document.activeElement : null;
  }

  document.addEventListener('focusin', function (event) {
    if (!editableTarget(event.target)) return;
    window.clearTimeout(keyboardTimer);
    setKeyboardOpen(true);
    window.setTimeout(function () {
      if (!document.body.contains(event.target)) return;
      try {
        event.target.scrollIntoView({ block: 'center', behavior: 'smooth' });
      } catch (_err) {
        event.target.scrollIntoView(false);
      }
    }, 260);
  });

  document.addEventListener('focusout', function () {
    window.clearTimeout(keyboardTimer);
    keyboardTimer = window.setTimeout(function () {
      if (!focusedEditor()) setKeyboardOpen(false);
    }, 220);
  });

  if (window.visualViewport) {
    var baselineHeight = Math.max(window.visualViewport.height || 0, window.innerHeight || 0);
    window.visualViewport.addEventListener('resize', function () {
      var viewportHeight = window.visualViewport.height || window.innerHeight || baselineHeight;
      baselineHeight = Math.max(baselineHeight, window.innerHeight || 0);
      var likelyKeyboard = !!focusedEditor() && viewportHeight < baselineHeight * 0.78;
      if (likelyKeyboard) setKeyboardOpen(true);
      else if (!focusedEditor()) setKeyboardOpen(false);
    }, { passive: true });
  }
}());
