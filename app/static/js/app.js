// existing code above unchanged

function loadIncidentAssistantPatch() {
  if (document.querySelector('script[data-assistant-incident]')) return;
  const script = document.createElement('script');
  script.src = '/static/js/assistant-incident.js?v=2026-05-05-incident';
  script.defer = true;
  script.setAttribute('data-assistant-incident', 'true');
  document.body.appendChild(script);
}

// existing window load
window.addEventListener('load', () => {
  // existing calls preserved
  loadIncidentAssistantPatch();
});
