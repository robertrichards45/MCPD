param(
    [string]$SourceDir = (Join-Path $PSScriptRoot '..\certs'),
    [string]$OutputPath = (Join-Path $PSScriptRoot '..\cac-chain.pem')
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $SourceDir)) {
    throw "Source directory not found: $SourceDir"
}

$files = Get-ChildItem (Join-Path $SourceDir '*') -File -Include *.cer,*.crt,*.pem,*.p7b -ErrorAction Stop
if (-not $files) {
    throw "No .cer, .crt, .pem, or .p7b files were found in $SourceDir"
}

$pemBlocks = New-Object System.Collections.Generic.List[string]

foreach ($file in $files) {
    if ($file.Extension -ieq '.pem') {
        $text = Get-Content $file.FullName -Raw
        if ($text -match '-----BEGIN CERTIFICATE-----') {
            $pemBlocks.Add($text.Trim())
            continue
        }
        throw "PEM file does not contain a certificate block: $($file.FullName)"
    }

    if ($file.Extension -ieq '.p7b') {
        $collection = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2Collection
        $collection.Import($file.FullName)
        foreach ($cert in $collection) {
            $raw = [System.Convert]::ToBase64String($cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))
            $wrapped = ($raw -split '(.{1,64})' | Where-Object { $_ })
            $pem = @(
                '-----BEGIN CERTIFICATE-----'
                $wrapped
                '-----END CERTIFICATE-----'
            ) -join [Environment]::NewLine
            $pemBlocks.Add($pem)
        }
        continue
    }

    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($file.FullName)
    $raw = [System.Convert]::ToBase64String($cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))
    $wrapped = ($raw -split '(.{1,64})' | Where-Object { $_ })
    $pem = @(
        '-----BEGIN CERTIFICATE-----'
        $wrapped
        '-----END CERTIFICATE-----'
    ) -join [Environment]::NewLine
    $pemBlocks.Add($pem)
}

[System.IO.File]::WriteAllText($OutputPath, (($pemBlocks | Select-Object -Unique) -join ([Environment]::NewLine + [Environment]::NewLine)))
Write-Host "Wrote $($pemBlocks.Count) certificate file(s) to $OutputPath"
