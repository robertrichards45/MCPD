$files = Get-ChildItem app\static\cleo\*.html | Where-Object { $_.Name -ne 'index.html' }
$inject = '<div class="cleo-headerbar"><div id="reportBadge">Report</div><div><button class="save-btn" onclick="cleoSave()">Save</button> <button class="save-btn" onclick="cleoNewReport()">New Report</button> <button class="save-btn" onclick="cleoReports()">Reports</button> <button class="save-btn" onclick="cleoSummary()">Summary</button></div></div>'
foreach ($f in $files) {
  $name = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
  $c = Get-Content $f.FullName -Raw
  if ($c -notmatch 'data-page-key') {
    $c = $c.Replace('<body>', '<body data-page-key="' + $name + '">')
  }
  if ($c -notmatch 'reportBadge') {
    $c = $c.Replace('<div class="nav">', $inject + "`n    <div class=""nav"">")
  }
  if ($c -notmatch 'cleo_report.js') {
    $c = $c.Replace('</body>', "  <script src=""./cleo_report.js""></script>`n</body>")
  }
  Set-Content -Path $f.FullName -Value $c
}
