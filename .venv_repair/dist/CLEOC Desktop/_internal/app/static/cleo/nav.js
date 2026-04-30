(function(){
  const sel = document.getElementById('cleoNav');
  if (sel) {
    const current = window.location.pathname.split('/').pop();
    for (const opt of sel.options) {
      if (opt.value === current) opt.selected = true;
    }
  }
})();
