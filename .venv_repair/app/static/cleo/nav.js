(function () {
  const sel = document.getElementById('cleoNav');
  const navLabel = document.querySelector('label[for="cleoNav"]');
  if (sel) {
    const current = window.location.pathname.split('/').pop();
    for (const opt of sel.options) {
      if (opt.value === current) opt.selected = true;
    }
  }
  if (navLabel) {
    navLabel.textContent = 'Mock Report Pages:';
  }
})();
