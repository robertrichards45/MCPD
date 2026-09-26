param(
    [Parameter(Mandatory=$true)]
    [string]$EnvironmentUrl,
    [string]$SolutionName = "MCPDSentinel"
)

$ErrorActionPreference = "Stop"

if ($EnvironmentUrl -notmatch '^https://') {
    throw "EnvironmentUrl must be an HTTPS Power Platform environment URL."
}
if (-not (Get-Command pac -ErrorAction SilentlyContinue)) {
    throw "Power Platform CLI (pac) is required. Install it through the approved Microsoft tooling channel."
}

Write-Host "Checking Power Platform CLI..."
pac --version
Write-Host "Checking authenticated profile..."
pac auth list
Write-Host "Checking target environment access..."
pac org who --environment $EnvironmentUrl
Write-Host "Checking solution existence: $SolutionName"
pac solution list --environment $EnvironmentUrl | Select-String $SolutionName
Write-Host ""
Write-Host "Preflight complete. Continue with export-development.ps1 only after synthetic-data and solution-checker gates pass."
