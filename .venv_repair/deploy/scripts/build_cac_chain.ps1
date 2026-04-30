param(
    [string]$OutputPath = (Join-Path $PSScriptRoot '..\cac-chain.pem')
)

$ErrorActionPreference = 'Stop'

$storePaths = @(
    'Cert:\LocalMachine\Root',
    'Cert:\LocalMachine\AuthRoot',
    'Cert:\LocalMachine\CA',
    'Cert:\CurrentUser\Root',
    'Cert:\CurrentUser\AuthRoot',
    'Cert:\CurrentUser\CA'
)

$subjectPatterns = @(
    'Federal Common Policy',
    'Federal Bridge',
    'U.S. Government',
    'DoD',
    'DOD',
    'ECA'
)

$seen = @{}
$matchingCerts = foreach ($storePath in $storePaths) {
    if (-not (Test-Path $storePath)) {
        continue
    }

    Get-ChildItem $storePath | Where-Object {
        $subject = if ($null -ne $_.Subject) { $_.Subject } else { '' }
        $issuer = if ($null -ne $_.Issuer) { $_.Issuer } else { '' }
        foreach ($pattern in $subjectPatterns) {
            if ($subject -match $pattern -or $issuer -match $pattern) {
                return $true
            }
        }
        return $false
    }
}

$certs = @($matchingCerts | Where-Object {
    if ($seen.ContainsKey($_.Thumbprint)) {
        return $false
    }
    $seen[$_.Thumbprint] = $true
    return $true
})

if (-not $certs) {
    throw "No Federal/DoD CAC issuer certificates were found in the standard Windows certificate stores. Install the trust chain first, then rerun this script."
}

$pemBlocks = foreach ($cert in $certs) {
    $raw = [System.Convert]::ToBase64String($cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))
    $wrapped = ($raw -split '(.{1,64})' | Where-Object { $_ })
    @(
        '-----BEGIN CERTIFICATE-----'
        $wrapped
        '-----END CERTIFICATE-----'
        ''
    ) -join [Environment]::NewLine
}

[System.IO.File]::WriteAllText($OutputPath, ($pemBlocks -join [Environment]::NewLine))
Write-Host "Wrote $($certs.Count) certificate(s) to $OutputPath"
