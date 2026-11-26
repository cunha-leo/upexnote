param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('personal','internal')]
    [string]$Edition
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$folder = Join-Path $root ('releases\editions\' + $Edition)
$portableFolder = Join-Path $folder 'portable'
$app = Join-Path $portableFolder 'upexnote.exe'
$worker = Join-Path $portableFolder 'worker\upexnote-worker.exe'

# Select the current version using Tauri config; never use an outdated installer.
. (Join-Path $PSScriptRoot 'resolve_release_installer.ps1')
$installerInfo = Get-UpexNoteInstaller -Root $root -Edition $Edition -Location release
$installer = $installerInfo.FullName
foreach ($file in @($installer, $app, $worker)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Arquivo do release ausente: $file"
    }
}

$desktop = [Environment]::GetFolderPath('Desktop')
if ([string]::IsNullOrWhiteSpace($desktop) -or
    -not (Test-Path -LiteralPath $desktop -PathType Container)) {
    throw 'Area de Trabalho do Windows indisponivel'
}

# These shortcuts are for portable builds. Native NSIS installation has its
# own optional desktop checkbox and handles UpexNote / UpexNote Internal.
$caption = if ($Edition -eq 'personal') { 'UpexNote Personal - Abrir.lnk' } else { 'UpexNote Internal - Abrir.lnk' }
$linkPath = Join-Path $desktop $caption
$shell = New-Object -ComObject WScript.Shell
$existing = Test-Path -LiteralPath $linkPath -PathType Leaf
if ($existing) {
    $oldTarget = $shell.CreateShortcut($linkPath).TargetPath
    $expectedPrefix = [IO.Path]::GetFullPath((Join-Path $root ('releases\editions\' + $Edition))).TrimEnd('\') + '\'
    if ($oldTarget -and
        -not [IO.Path]::GetFullPath($oldTarget).StartsWith($expectedPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Atalho com este nome pertence a outro destino; nao sobrescrever: $linkPath"
    }
}
$link = $shell.CreateShortcut($linkPath)
$link.TargetPath = $app
$link.WorkingDirectory = $portableFolder
$link.IconLocation = $app + ',0'
$link.Description = 'UpexNote ' + $Edition + ' - release portatil atual'
$link.Save()

# Remove only previous release-managed links that target this edition.
$oldNames = if ($Edition -eq 'personal') {
    @('UpexNote Personal (Teste).lnk',
      'UpexNote Personal - Multimodel.lnk',
      'UpexNote Personal - Instalar R03.1.lnk')
} else {
    @('UpexNote Internal (Teste).lnk',
      'UpexNote Internal - Multimodel.lnk',
      'UpexNote Internal - Instalar R03.1.lnk')
}
$allowedInstallerPrefix = [IO.Path]::GetFullPath($folder).TrimEnd('\') + '\'
foreach ($oldName in $oldNames) {
    $oldPath = Join-Path $desktop $oldName
    if (-not (Test-Path -LiteralPath $oldPath -PathType Leaf)) { continue }
    $target = $shell.CreateShortcut($oldPath).TargetPath
    if (-not $target) { continue }
    $fullTarget = [IO.Path]::GetFullPath($target)
    $isOurApp = [string]::Equals($fullTarget, [IO.Path]::GetFullPath($app), [StringComparison]::OrdinalIgnoreCase)
    $isOurInstaller = $fullTarget.StartsWith($allowedInstallerPrefix, [StringComparison]::OrdinalIgnoreCase) -and
                      $fullTarget.EndsWith('-setup.exe', [StringComparison]::OrdinalIgnoreCase)
    if ($isOurApp -or $isOurInstaller) {
        Remove-Item -LiteralPath $oldPath
        Write-Output ('OLD_RELEASE_SHORTCUT_REMOVED ' + $oldName)
    } else {
        Write-Output ('UNRELATED_SHORTCUT_PRESERVED ' + $oldName)
    }
}
if (-not (Test-Path -LiteralPath $linkPath -PathType Leaf)) { throw 'Atalho nao foi criado' }
$resolved = $shell.CreateShortcut($linkPath)
if (-not [string]::Equals($resolved.TargetPath, $app, [StringComparison]::OrdinalIgnoreCase)) {
    throw ('Destino do atalho incorreto: ' + $linkPath)
}
if (-not (Test-Path -LiteralPath $resolved.TargetPath -PathType Leaf)) {
    throw ('Atalho aponta para executavel ausente: ' + $linkPath)
}
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash
$verb = if ($existing) { 'UPDATED' } else { 'CREATED' }
Write-Output ('DESKTOP_RELEASE_SHORTCUT_' + $verb + ' ' + $linkPath)
Write-Output ('INSTALLER_VERIFIED_SHA256 ' + $hash)
