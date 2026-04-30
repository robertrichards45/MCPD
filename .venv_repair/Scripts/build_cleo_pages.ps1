$nav = @'
  <div class="nav">
    <label for="cleoNav">CLEO Pages:</label>
    <select id="cleoNav" onchange="if(this.value) window.location.href=this.value;">
      <option value="">Select?</option>
      <option value="index.html">Home</option>
      <option value="incident-admin.html">Incident Admin</option>
      <option value="ta-main.html">TA Main</option>
      <option value="ta-person.html">TA Person</option>
      <option value="persons.html">Involved Persons</option>
      <option value="property.html">Involved Property</option>
      <option value="organization.html">Involved Organization</option>
      <option value="vehicle.html">Vehicle Info</option>
      <option value="offenses.html">Offenses</option>
      <option value="narcotics.html">Narcotics</option>
      <option value="narrative.html">Narrative</option>
      <option value="violation-1408.html">1408 Violation</option>
      <option value="dd-1408.html">DD Form 1408</option>
      <option value="enclosure.html">Enclosure</option>
    </select>
  </div>
'@

$generic = @'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{TITLE}</title>
  <link rel="stylesheet" href="./cleo.css" />
</head>
<body>
  <div class="wrap">
{NAV}
    <div class="cleo-action-bar">
      <button class="save-btn" type="button" onclick="addPage(this)">Add Page</button>
    </div>
    <div class="cleo-form">
      <div class="cleo-title">{HEADER}</div>
      <div class="cleo-section">
        <div class="cleo-section-header">Administrative</div>
        <div class="cleo-grid">
          <div class="cleo-field" style="grid-column: span 2;">
            <label>Incident Type</label>
            <select class="cleo-select"><option></option></select>
          </div>
          <div class="cleo-field" style="grid-column: span 2;">
            <label>Date Received (YYYYMMDD)</label>
            <input class="cleo-input" />
          </div>
          <div class="cleo-field" style="grid-column: span 2;">
            <label>Time Received (24 Hour)</label>
            <input class="cleo-input" />
          </div>
        </div>
      </div>
      <div class="cleo-section">
        <div class="cleo-section-header">Details</div>
        <div class="cleo-grid">
          <div class="cleo-field" style="grid-column: span 3;">
            <label>Subject</label>
            <input class="cleo-input" />
          </div>
          <div class="cleo-field" style="grid-column: span 3;">
            <label>Location</label>
            <input class="cleo-input" />
          </div>
          <div class="cleo-field" style="grid-column: span 6;">
            <label>Notes</label>
            <textarea class="cleo-textarea"></textarea>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div class="save-bar">
    <button class="save-btn green">Save</button>
    <button class="save-btn">Load</button>
    <button class="save-btn">Clear</button>
  </div>
  <script src="./nav.js"></script>
  <script>
    function addPage(btn) {
      const form = btn.closest('.wrap').querySelector('.cleo-form');
      const clone = form.cloneNode(true);
      form.parentElement.appendChild(clone);
    }
  </script>
</body>
</html>
'@

$pages = @(
  @{file='index.html'; title='Home'; header='CLEO Home'},
  @{file='incident-admin.html'; title='Incident Admin'; header='Incident Administrative Section'},
  @{file='ta-main.html'; title='TA Main'; header='Traffic Accident Incident Reporting'},
  @{file='ta-person.html'; title='TA Person'; header='Person for Traffic Incident'},
  @{file='persons.html'; title='Involved Persons'; header='Involved Persons'},
  @{file='property.html'; title='Involved Property'; header='Involved Property'},
  @{file='organization.html'; title='Involved Organization'; header='Involved Organization'},
  @{file='vehicle.html'; title='Vehicle Info'; header='Vehicle Information'},
  @{file='offenses.html'; title='Offenses'; header='Offenses'},
  @{file='narcotics.html'; title='Narcotics'; header='Narcotics'},
  @{file='violation-1408.html'; title='1408 Violation'; header='1408 Violation Notice'},
  @{file='dd-1408.html'; title='DD Form 1408'; header='DD Form 1408'},
  @{file='enclosure.html'; title='Enclosure'; header='Enclosure Checklist'}
)

foreach ($p in $pages) {
  $html = $generic.Replace('{TITLE}', $p.title).Replace('{HEADER}', $p.header).Replace('{NAV}', $nav)
  Set-Content -Path (Join-Path 'app\static\cleo' $p.file) -Value $html
}
