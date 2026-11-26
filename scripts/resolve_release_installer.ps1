# Resolve installer according to the actual Tauri edition configuration,
# rather than assuming today's version number or selecting the other edition.
function Get-UpexNoteInstaller {
    param(
        [Parameter(Mandatory=$true)][string]$Root,
        [Parameter(Mandatory=$true)][ValidateSet('personal','internal')][string]$Edition,
        [Parameter(Mandatory=$true)][ValidateSet('bundle','release')][string]$Location
    )
    $configFolder=Join-Path $Root 'apps\desktop\src-tauri'
    $base=Get-Content -LiteralPath (Join-Path $configFolder 'tauri.conf.json') -Raw | ConvertFrom-Json
    $editionConfig=Get-Content -LiteralPath (Join-Path $configFolder ("tauri."+ $Edition + ".conf.json")) -Raw | ConvertFrom-Json
    $product=if($editionConfig.productName){$editionConfig.productName}else{$base.productName}
    $version=if($editionConfig.version){$editionConfig.version}else{$base.version}
    if(-not $product -or -not $version){throw 'Missing product name or version in Tauri config'}
    $prefix=$product + '_' + $version + '_'
    $folder=if($Location -eq 'bundle'){
        Join-Path $configFolder 'target\release\bundle\nsis'
    }else{
        Join-Path $Root ('releases\editions\' + $Edition)
    }
    if(-not(Test-Path -LiteralPath $folder -PathType Container)){
        throw "Installer folder not found: $folder"
    }
    $matches=@(Get-ChildItem -LiteralPath $folder -Filter '*-setup.exe' -File |
        Where-Object { $_.Name.StartsWith($prefix,[System.StringComparison]::OrdinalIgnoreCase) } |
        Sort-Object LastWriteTime -Descending)
    if($matches.Count -lt 1){throw "Installer not found for $Edition ($product $version)"}
    return $matches[0]
}
