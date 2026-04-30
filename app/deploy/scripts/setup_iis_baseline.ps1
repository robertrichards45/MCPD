$ErrorActionPreference = 'Stop'

$repoRoot = 'C:\Users\rober\Desktop\mcpd-portal'
$siteName = 'Default Web Site'
$hostName = 'mclbpd.com'
$logPath = Join-Path $repoRoot 'deploy\setup_iis_baseline.log'
$webConfigSource = Join-Path $repoRoot 'deploy\web.config.example'
$webConfigTarget = 'C:\inetpub\wwwroot\web.config'

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -Path $logPath -Value "$timestamp $Message"
}

Set-Content -Path $logPath -Value ''
Write-Log 'Starting IIS baseline setup'

Import-Module WebAdministration

$cert = Get-ChildItem Cert:\LocalMachine\My |
    Where-Object { $_.Subject -eq "CN=$hostName" } |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1

if (-not $cert) {
    Write-Log "Creating self-signed certificate for $hostName"
    $cert = New-SelfSignedCertificate -DnsName $hostName -CertStoreLocation 'Cert:\LocalMachine\My' -FriendlyName 'MCPD Portal Local Test'
} else {
    Write-Log "Reusing existing certificate $($cert.Thumbprint)"
}

$proxyFilter = 'system.webServer/proxy'
$proxyPath = 'MACHINE/WEBROOT/APPHOST'
$proxyEnabled = (Get-WebConfigurationProperty -PSPath $proxyPath -Filter $proxyFilter -Name enabled).Value
if (-not $proxyEnabled) {
    Set-WebConfigurationProperty -PSPath $proxyPath -Filter $proxyFilter -Name enabled -Value True
    Write-Log 'Enabled ARR proxy'
} else {
    Write-Log 'ARR proxy already enabled'
}

if (-not (Test-Path "IIS:\Sites\$siteName")) {
    throw "IIS site '$siteName' does not exist"
}

$binding = Get-WebBinding -Name $siteName -Protocol https -HostHeader $hostName -ErrorAction SilentlyContinue
if (-not $binding) {
    New-WebBinding -Name $siteName -Protocol https -Port 443 -HostHeader $hostName
    Write-Log "Created HTTPS binding for $hostName"
} else {
    Write-Log "HTTPS binding for $hostName already exists"
}

$sslBindingPath = "IIS:\SslBindings\!443!$hostName"
if (Test-Path $sslBindingPath) {
    Remove-Item $sslBindingPath -Force
    Write-Log "Removed existing SSL binding for $hostName"
}
New-Item $sslBindingPath -Thumbprint $cert.Thumbprint -SSLFlags 1 | Out-Null
Write-Log "Bound certificate $($cert.Thumbprint) to $hostName:443"

Copy-Item $webConfigSource $webConfigTarget -Force
Write-Log 'Copied reverse proxy web.config to C:\inetpub\wwwroot'

$accessFilter = "system.applicationHost/sites/site[@name='$siteName']/application[@path='/']/virtualDirectory[@path='/']"
$currentAccessPolicy = (Get-WebConfigurationProperty -PSPath $proxyPath -Filter $accessFilter -Name sslFlags -ErrorAction SilentlyContinue).Value
Set-WebConfigurationProperty -PSPath $proxyPath -Filter $accessFilter -Name sslFlags -Value 'Ssl,SslNegotiateCert'
Write-Log "Set SSL flags to Ssl,SslNegotiateCert (previous: $currentAccessPolicy)"

iisreset | Out-Null
Write-Log 'Ran iisreset'
Write-Log "Completed IIS baseline setup with certificate $($cert.Thumbprint)"
