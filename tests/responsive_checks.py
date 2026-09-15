"""Browser geometry checks shared by the mobile audit and CI (synthetic data only)."""

PAGE_PATHS = [
    '/', '/login', '/register',
    '/dashboard', '/sentinel/search', '/sentinel/report-inspector',
    '/sentinel/fto-center', '/sentinel/fto-center/programs',
    '/sentinel/fto-center/scenario-alerts', '/sentinel/fto-instructor',
    '/sentinel/fto-center/scenario-lab/', '/sentinel/fto-center/scenario-lab/shift/',
    '/sentinel/fto-center/scenario-notebook/',
    '/sentinel/fto-center/scenario-paperwork/',
    '/sentinel/fto-center/scenario-paperwork/training-forms',
    '/reports', '/reports/new', '/reports/accidents',
    '/reports/accident-reconstruction', '/reports/accident-reconstruction/new',
    '/tools/narrative', '/tools/5w',
    '/forms', '/forms/manage', '/forms/call-types', '/forms/maintenance',
    '/forms/saved', '/forms/upload', '/forms/pdf-renders',
    '/training/menu', '/training', '/training/search', '/training/upload',
    '/training/tracker', '/training/tracker/readiness', '/training/tracker/log',
    '/training/tracker/categories', '/training/tracker/categories/new',
    '/legal', '/legal/search', '/orders/reference', '/orders',
    '/reference', '/officer-handbook', '/officer-handbook/admin',
    '/admin/users', '/profile', '/officers', '/admin/system-status',
    '/admin/legal-corpus', '/admin/legal-analytics', '/admin/site-builder',
    '/bolo/', '/bolo/new', '/announcements', '/notifications/inbox',
    '/performance/my-stats', '/performance/submit', '/performance/my-history',
    '/performance/pending', '/performance/team', '/performance/elements',
    '/private/credit-simulator/',
    '/mobile/home', '/mobile/more', '/mobile/stats', '/mobile/contact',
    '/mobile/supervisor/dashboard', '/mobile/supervisor/officers',
    '/mobile/fast-capture', '/mobile/critical-incident',
    '/mobile/incident/start', '/mobile/incident/basics', '/mobile/incident/persons',
    '/mobile/incident/persons/edit', '/mobile/incident/statute',
    '/mobile/incident/checklist', '/mobile/incident/facts',
    '/mobile/incident/statements', '/mobile/incident/domestic-supplemental',
    '/mobile/incident/narrative-review', '/mobile/incident/recommended-forms',
    '/mobile/incident/packet-review', '/mobile/incident/send-packet',
]

# Check descendants too: document.scrollWidth alone passes when overflow:hidden
# clips an entire field/card. Horizontal table/diagram scrollers are intentional.
GEOMETRY = r"""() => {
  const width = document.documentElement.clientWidth;
  const visible = e => { const s=getComputedStyle(e); const r=e.getBoundingClientRect();
    return r.width>0 && r.height>0 && s.visibility!=='hidden' && s.display!=='none'
      && !e.closest('[hidden],[aria-hidden="true"],.ai-panel-hidden'); };
  const describe = e => e.tagName.toLowerCase() + (e.id ? '#'+e.id : '') +
    '.' + String(e.className).trim().replace(/\s+/g,'.').slice(0,100);
  const scrolled = e => {
    for(let p=e.parentElement;p && p!==document.body;p=p.parentElement) {
      const s=getComputedStyle(p);
      if (['auto','scroll'].includes(s.overflowX) && p.scrollWidth>p.clientWidth+2) return true;
    } return false;
  };
  const outside=[], cramped=[], textZoom=[], clipped=[], oversized=[];
  for(const e of document.querySelectorAll('main *, .page-wrap *, .mobile-main *, .mcpd-command-header *, .login-panel *')) {
    if(!visible(e) || e.closest('svg,.leaflet-pane')) continue;
    const r=e.getBoundingClientRect(),s=getComputedStyle(e);
    if((r.right>width+2 || r.left < -2) && !scrolled(e)) outside.push(describe(e));
    if(e.matches('button,a,input,textarea,select,h1,h2,h3,h4,p') && !scrolled(e)) {
      for(let a=e.parentElement;a && a!==document.body;a=a.parentElement) {
        const as=getComputedStyle(a),ar=a.getBoundingClientRect();
        if(['hidden','clip'].includes(as.overflowX) && (r.right>ar.right+2 || r.left<ar.left-2)) {
          clipped.push(describe(e)+' in '+describe(a)); break;
        }
      }
    }
    if(e.matches('input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=range]),select,textarea') && parseFloat(s.fontSize)<16) textZoom.push(describe(e));
    if(e.matches('button,.btn') && (r.height<43 || r.width<43)) cramped.push(describe(e));
    if(e.matches('button') && r.height>200) oversized.push(describe(e));
  }
  const main=document.querySelector('main,.page-wrap,.mcpd-command-main');
  return {width, scrollWidth:document.documentElement.scrollWidth,
    mainWidth:main ? main.getBoundingClientRect().width:null,
    outside:[...new Set(outside)].slice(0,20), cramped:[...new Set(cramped)].slice(0,20),
    textZoom:[...new Set(textZoom)].slice(0,20), clipped:[...new Set(clipped)].slice(0,20), oversized:[...new Set(oversized)].slice(0,20)};
}"""
