param(
    [Parameter(Mandatory=$true)]
    [string]$EnvironmentUrl,

    [string]$SolutionName = "MCPDSentinel",

    [string]$OutputFolder = ".\dist"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command pac -ErrorAction SilentlyContinue)) {
    throw "Power Platform CLI (pac) is required before this script can run."
}

New-Item -ItemType Directory -Force -Path $OutputFolder | Out-Null

Write-Host "Authenticating to development environment..."
pac auth create --url $EnvironmentUrl

$unmanaged = Join-Path $OutputFolder "$SolutionName-unmanaged.zip"
$managed = Join-Path $OutputFolder "$SolutionName-managed.zip"

Write-Host "Exporting unmanaged backup..."
pac solution export --name $SolutionName --path $unmanaged --managed false --overwrite

Write-Host "Exporting managed production package..."
pac solution export --name $SolutionName --path $managed --managed true --overwrite

Write-Host ""
Write-Host "Export complete."
Write-Host "Unmanaged: $unmanaged"
Write-Host "Managed:   $managed"
Write-Host ""
Write-Host "Before government transfer, verify no personal-tenant production data or personal connection values are embedded."
