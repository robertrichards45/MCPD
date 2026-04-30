$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell

$items = @(
    @{
        Name = 'CLEOC Desktop (This PC).lnk'
        Target = (Join-Path $PSScriptRoot 'launch_cleoc_desktop.cmd')
        Description = 'Launch the local CLEOC desktop app on this PC.'
    },
    @{
        Name = 'CLEOC Shared Host.lnk'
        Target = (Join-Path $PSScriptRoot 'launch_cleoc_shared_host.cmd')
        Description = 'Run CLEOC on this PC for other officers on the same network.'
    },
    @{
        Name = 'CLEOC Officer Client.lnk'
        Target = (Join-Path $PSScriptRoot 'open_cleoc_officer_client.cmd')
        Description = 'Open the shared CLEOC host from this officer workstation.'
    }
)

foreach ($item in $items) {
    $shortcutPath = Join-Path $desktop $item.Name
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $item.Target
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Description = $item.Description
    $shortcut.Save()
}

Write-Host "CLEOC desktop shortcuts created on $desktop"
