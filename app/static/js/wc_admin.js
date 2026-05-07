(function () {
  'use strict';

  function output(value) {
    var el = document.getElementById('wc-admin-output');
    if (!el) return;
    el.textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  }

  function renderFiles(data) {
    var list = document.getElementById('wc-file-list');
    if (!list) return;
    var files = data && Array.isArray(data.files) ? data.files : [];
    if (!files.length) {
      list.innerHTML = '<p class="wc-empty">No files found.</p>';
      return;
    }
    list.innerHTML = files.map(function (file) {
      var relPath = encodeURI(file.rel_path || '');
      return [
        '<article class="wc-file-row">',
        '<div><strong>', escapeHtml(file.title || file.file_name || 'Officer file'), '</strong>',
        '<span>', escapeHtml([file.area, file.officer_id, file.uploaded_at].filter(Boolean).join(' / ')), '</span></div>',
        relPath ? '<a class="btn btn-outline" href="/api/admin/files/download/' + relPath + '">Download</a>' : '',
        '</article>',
      ].join('');
    }).join('');
  }

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, function (ch) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
    });
  }

  function formJson(form) {
    var payload = {};
    new FormData(form).forEach(function (value, key) {
      if (typeof value === 'string') payload[key] = value;
    });
    return payload;
  }

  function postJson(url, payload) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(function (response) { return response.json(); });
  }

  document.addEventListener('submit', function (event) {
    var form = event.target.closest('[data-wc-form]');
    if (!form) return;
    event.preventDefault();
    output('Working...');
    var type = form.getAttribute('data-wc-form');
    if (type === 'counseling') {
      postJson('/api/admin/counseling/generate', formJson(form)).then(function (data) { output(data.text || data); }).catch(function () { output('Counseling generation failed.'); });
      return;
    }
    if (type === 'award') {
      postJson('/api/admin/awards/generate', formJson(form)).then(function (data) { output(data.text || data); }).catch(function () { output('Award generation failed.'); });
      return;
    }
    if (type === 'learning') {
      postJson('/api/admin/learning/submit', formJson(form)).then(output).catch(function () { output('Learning submission failed.'); });
      return;
    }
    if (type === 'files') {
      fetch('/api/admin/files/upload', { method: 'POST', body: new FormData(form) }).then(function (response) { return response.json(); }).then(function (data) {
        output(data);
        renderFiles(data);
      }).catch(function () { output('File upload failed.'); });
    }
  });

  document.addEventListener('click', function (event) {
    if (event.target.closest('[data-wc-load-learning]')) {
      fetch('/api/admin/learning/pending').then(function (response) { return response.json(); }).then(output).catch(function () { output('Unable to load pending learning.'); });
    }
    if (event.target.closest('[data-wc-load-files]')) {
      fetch('/api/admin/files').then(function (response) { return response.json(); }).then(function (data) {
        output(data);
        renderFiles(data);
      }).catch(function () { output('Unable to load file index.'); });
    }
  });

  document.addEventListener('submit', function (event) {
    var form = event.target.closest('[data-wc-file-search]');
    if (!form) return;
    event.preventDefault();
    var params = new URLSearchParams(new FormData(form));
    fetch('/api/admin/files?' + params.toString()).then(function (response) { return response.json(); }).then(function (data) {
      output(data);
      renderFiles(data);
    }).catch(function () { output('Unable to search file index.'); });
  });
}());
