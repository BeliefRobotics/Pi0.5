param([string]$Directory=(Join-Path $PSScriptRoot 'release-download'))
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new()
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
function File-Sha256([string]$Path) {
    $Stream=[IO.File]::OpenRead($Path); $Hasher=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($Hasher.ComputeHash($Stream))).Replace('-','').ToLowerInvariant() }
    finally { $Stream.Dispose(); $Hasher.Dispose() }
}
$Api='https://api.github.com/repos/BeliefRobotics/Pi0.5/releases/tags/pi05-3000-windows-20261027'
$Release=Invoke-RestMethod -Uri $Api -Headers @{'User-Agent'='BeliefRobotics-Pi05-Installer'}
New-Item -ItemType Directory -Force -Path $Directory | Out-Null
$Directory=[IO.Path]::GetFullPath($Directory)
$IndexAsset=@($Release.assets | Where-Object name -eq 'bundle-index.json')
if ($IndexAsset.Count -ne 1) { throw 'Release 不完整，未找到 bundle-index.json。请稍后再试。' }
Invoke-WebRequest -UseBasicParsing -Uri $IndexAsset[0].browser_download_url -OutFile (Join-Path $Directory 'bundle-index.json')
$Index=Get-Content -LiteralPath (Join-Path $Directory 'bundle-index.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($Part in $Index.parts) {
    if ([IO.Path]::GetFileName($Part.name) -ne $Part.name -or $Part.name -match '[\\/]') { throw 'Invalid release filename.' }
    $Path=Join-Path $Directory $Part.name
    if ((Test-Path -LiteralPath $Path) -and (Get-Item -LiteralPath $Path).Length -eq $Part.bytes -and (File-Sha256 $Path) -eq $Part.sha256) { Write-Host "已有完整分卷：$($Part.name)"; continue }
    $Asset=@($Release.assets | Where-Object name -eq $Part.name)
    if ($Asset.Count -ne 1) { throw "Release 缺少分卷：$($Part.name)" }
    Write-Host "正在下载 $($Part.name)..."
    Invoke-WebRequest -UseBasicParsing -Uri $Asset[0].browser_download_url -OutFile ($Path+'.downloading')
    if ((Get-Item -LiteralPath ($Path+'.downloading')).Length -ne $Part.bytes -or (File-Sha256 ($Path+'.downloading')) -ne $Part.sha256) { throw "下载校验失败：$($Part.name)；可重新运行重试。" }
    Move-Item -LiteralPath ($Path+'.downloading') -Destination $Path -Force
}
& (Join-Path $PSScriptRoot 'restore_bundle.ps1') -Directory $Directory
