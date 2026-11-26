param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('personal','internal')]
    [string]$Edition
)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$folder=Join-Path $root ('releases\editions\'+$Edition)
$name=if($Edition -eq 'personal'){'UpexNote_0.45.0_x64-setup.exe'}else{'UpexNote Internal_0.45.0-internal_x64-setup.exe'}
$installer=Join-Path $folder $name
if(-not(Test-Path -LiteralPath $installer)){throw 'Installer not found'}
$desktop=[Environment]::GetFolderPath('Desktop')
$title=if($Edition -eq 'personal'){'UpexNote Personal - Instalar R03.1.lnk'}else{'UpexNote Internal - Instalar R03.1.lnk'}
$link=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop $title))
$link.TargetPath=$installer
$link.WorkingDirectory=$folder
$link.Description='UpexNote R03.1 - instalador validado ' + $Edition
$link.IconLocation=$installer+',0'
$link.Save()
$hash=(Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash
Write-Output ('DESKTOP_SHORTCUT_OK '+(Join-Path $desktop $title))
Write-Output ('SHA256 '+$hash)
