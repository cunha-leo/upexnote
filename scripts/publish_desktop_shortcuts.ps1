param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('personal','internal')]
    [string]$Edition
)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$folder=Join-Path $root ('releases\editions\'+$Edition)
$installerFile=Get-ChildItem -LiteralPath $folder -Filter '*setup.exe' -File |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if($null -eq $installerFile){throw ('No setup installer found: '+$folder)}
$installer=$installerFile.FullName
$portableFolder=Join-Path $folder 'portable'
$app=Join-Path $portableFolder 'upexnote.exe'
$worker=Join-Path $portableFolder 'worker\upexnote-worker.exe'
foreach($file in @($installer,$app,$worker)){
    if(-not(Test-Path -LiteralPath $file -PathType Leaf)){throw ('Required release file missing: '+$file)}
}
$desktop=[Environment]::GetFolderPath('Desktop')
if([string]::IsNullOrWhiteSpace($desktop) -or -not(Test-Path -LiteralPath $desktop -PathType Container)){
    throw 'The current Windows Desktop folder is not available'
}
$shell=New-Object -ComObject WScript.Shell

# Stable shortcuts: future builds UPDATE their target without creating dated duplicates.
$caption=if($Edition -eq 'personal'){'UpexNote Personal (Teste).lnk'}else{'UpexNote Internal (Teste).lnk'}
$appLinkPath=Join-Path $desktop $caption
$appLink=$shell.CreateShortcut($appLinkPath)
$appLink.TargetPath=$app
$appLink.WorkingDirectory=$portableFolder
$appLink.IconLocation=$app+',0'
$appLink.Description='Abrir UpexNote '+$Edition+' - release portatil validado (teste)'
$appLink.Save()

# Keep the existing installer shortcut as a separate convenience.
$title=if($Edition -eq 'personal'){'UpexNote Personal - Instalar R03.1.lnk'}else{'UpexNote Internal - Instalar R03.1.lnk'}
$installerLinkPath=Join-Path $desktop $title
$installerLink=$shell.CreateShortcut($installerLinkPath)
$installerLink.TargetPath=$installer
$installerLink.WorkingDirectory=$folder
$installerLink.Description='UpexNote R03.1 - instalador validado '+$Edition
$installerLink.IconLocation=$installer+',0'
$installerLink.Save()

# Resolve the actual .lnk again: saving a shortcut alone does not prove its target.
foreach($linkFile in @($appLinkPath,$installerLinkPath)){
    if(-not(Test-Path -LiteralPath $linkFile -PathType Leaf)){throw ('Shortcut missing after save: '+$linkFile)}
    $resolved=$shell.CreateShortcut($linkFile)
    if(-not(Test-Path -LiteralPath $resolved.TargetPath -PathType Leaf)){
        throw ('Shortcut points to a missing file: '+$linkFile)
    }
}
$hash=(Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash
Write-Output ('DESKTOP_APP_SHORTCUT_OK '+$appLinkPath)
Write-Output ('DESKTOP_INSTALLER_SHORTCUT_OK '+$installerLinkPath)
Write-Output ('SHA256 '+$hash)
