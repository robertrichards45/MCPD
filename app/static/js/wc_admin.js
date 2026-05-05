async function loadFiles() {
  const officer = document.getElementById('officerSearch').value;
  const area = document.getElementById('fileArea').value;
  const res = await fetch(`/api/admin/files?officer_id=${encodeURIComponent(officer)}&area=${area}`);
  const data = await res.json();
  const container = document.getElementById('fileResults');
  container.innerHTML = '';
  data.items.forEach(f => {
    const div = document.createElement('div');
    div.className = 'wc-file-row';
    div.innerHTML = `
      <strong>${f.title}</strong><br>
      ${f.category} | ${f.area}<br>
      <button onclick="downloadFile('${f.relativePath}')">Download</button>
      <button onclick="printFile('${f.relativePath}')">Print</button>
    `;
    container.appendChild(div);
  });
}

function downloadFile(path) {
  window.open(`/api/admin/files/download/${path}`, '_blank');
}

function printFile(path) {
  const win = window.open(`/api/admin/files/download/${path}`, '_blank');
  win.onload = () => win.print();
}

async function uploadAdminFiles() {
  const files = document.getElementById('uploadFiles').files;
  const officer = document.getElementById('uploadOfficerId').value;
  const area = document.getElementById('uploadArea').value;
  const desc = document.getElementById('uploadDescription').value;
  const form = new FormData();
  for (let f of files) form.append('files', f);
  form.append('officer_id', officer);
  form.append('area', area);
  form.append('description', desc);
  const res = await fetch('/api/admin/files/upload', { method: 'POST', body: form });
  const data = await res.json();
  document.getElementById('uploadStatus').innerText = 'Uploaded: ' + data.saved.length;
}

async function generateCounseling() {
  const res = await fetch('/api/admin/counseling/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      officer_name: document.getElementById('cOfficer').value,
      counseling_type: document.getElementById('cType').value,
      category: document.getElementById('cCategory').value,
      facts: document.getElementById('cFacts').value,
      corrective_action: document.getElementById('cCorrective').value
    })
  });
  const data = await res.json();
  document.getElementById('cOutput').value = data.text;
}

async function generateAward() {
  const res = await fetch('/api/admin/awards/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      officer_name: document.getElementById('aOfficer').value,
      award_type: document.getElementById('aType').value,
      actions: document.getElementById('aActions').value,
      impact: document.getElementById('aImpact').value
    })
  });
  const data = await res.json();
  document.getElementById('aOutput').value = data.text;
}

async function submitCurrentLearning(system) {
  const text = system === 'counseling' ? document.getElementById('cOutput').value : document.getElementById('aOutput').value;
  await fetch('/api/admin/learning/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ system: system, edited: text })
  });
  alert('Submitted for approval');
}

async function loadPendingLearning() {
  const res = await fetch('/api/admin/learning/pending');
  const data = await res.json();
  const container = document.getElementById('learningResults');
  container.innerHTML = '';
  data.items.forEach(item => {
    const div = document.createElement('div');
    div.innerHTML = `
      <pre>${item.edited}</pre>
      <button onclick="approveLearning('${item.id}')">Approve</button>
    `;
    container.appendChild(div);
  });
}

async function approveLearning(id) {
  await fetch('/api/admin/learning/approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id })
  });
  loadPendingLearning();
}
