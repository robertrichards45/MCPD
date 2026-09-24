param(
    [Parameter(Mandatory=$true)]
    [string]$EnvironmentUrl,

    [Parameter(Mandatory=$true)]
    [string]$ManagedSolutionZip
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command pac -ErrorAction SilentlyContinue)) {
    throw "Power Platform CLI (pac) is required before this script can run."
}

if (-not (Test-Path $ManagedSolutionZip)) {
    throw "Managed solution ZIP not found: $ManagedSolutionZip"
}

Write-Host "Authenticating to target government environment..."
pac auth create --url $EnvironmentUrl

Write-Host "Importing MCPD Sentinel managed solution..."
pac solution import --path $ManagedSolutionZip --publish-changes

Write-Host ""
Write-Host "Solution import completed."
Write-Host "Next:"
Write-Host "  1. Set government environment-variable values."
Write-Host "  2. Rebind connection references."
Write-Host "  3. Assign Dataverse security roles/teams."
Write-Host "  4. Share the app with the approved department group."
Write-Host "  5. Validate Power BI access/RLS."
Write-Host "  6. Run the government validation checklist."
