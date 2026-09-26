<#
  MCPD Sentinel government-PC bootstrap.
  This script never accepts or stores passwords, tokens, or API keys.
  Run it from a government workstation after the user authenticates with pac.
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$EnvironmentUrl,
    [string]$SolutionName = "MCPDSentinel",
    [string]$PublisherName = "MCPD",
    [string]$PublisherPrefix = "mcpd",
    [string]$Version = "1.0.0.0",
    [string]$OutputFolder = ".\government-build"
)

$ErrorActionPreference = "Stop"
if ($EnvironmentUrl -notmatch '^https://') { throw "EnvironmentUrl must be an HTTPS URL." }
if (-not (Get-Command pac -ErrorAction SilentlyContinue)) {
    throw "Power Platform CLI (pac) is required. Install it through the approved government software channel."
}

New-Item -ItemType Directory -Force -Path $OutputFolder | Out-Null
$evidence = Join-Path $OutputFolder "bootstrap-evidence.txt"
"MCPD Sentinel bootstrap" | Set-Content $evidence
"UTC: $([DateTime]::UtcNow.ToString('o'))" | Add-Content $evidence
"Environment: $EnvironmentUrl" | Add-Content $evidence
"Solution: $SolutionName $Version" | Add-Content $evidence

Write-Host "Checking authenticated Power Platform profile..."
pac auth list | Tee-Object -FilePath $evidence -Append
Write-Host "Checking target environment..."
pac org who --environment $EnvironmentUrl | Tee-Object -FilePath $evidence -Append

$solutionFolder = Join-Path $OutputFolder $SolutionName
if (-not (Test-Path $solutionFolder)) {
    Write-Host "Creating solution source shell..."
    pac solution init --publisher-name $PublisherName --publisher-prefix $PublisherPrefix --outputDirectory $solutionFolder | Tee-Object -FilePath $evidence -Append
} else {
    Write-Host "Solution source shell already exists: $solutionFolder"
}

Write-Host ""
Write-Host "Bootstrap complete. Evidence: $evidence"
Write-Host "Next: add the Dataverse schema, environment variables, connection references, app, flows, and security roles; run Solution Checker; export only after approval."
