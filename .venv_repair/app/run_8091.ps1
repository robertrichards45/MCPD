Set-Location "C:\Users\rober\Desktop\mcpd-portal"
$env:PORT = "8091"
$env:FLASK_DEBUG = "0"
& "C:\Users\rober\Desktop\mcpd-portal\.venv\Scripts\python.exe" "C:\Users\rober\Desktop\mcpd-portal\app.py"
