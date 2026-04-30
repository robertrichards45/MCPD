$files = Get-ChildItem app\static\cleo\*.html | Where-Object { $_.Name -ne 'index.html' }
foreach ($f in $files) {
  $c = Get-Content $f.FullName -Raw
  if ($c -notmatch 'cleo_report\.js') {
    $c = $c.Replace('</body>', "  <script src=""/static/cleo/cleo_report.js""></script>`n</body>")
  }
  Set-Content -Path $f.FullName -Value $c
}
