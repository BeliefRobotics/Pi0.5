param([string]$Directory=$PSScriptRoot)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new()
$Directory=[IO.Path]::GetFullPath($Directory)
function File-Sha256([string]$Path) {
    $Stream=[IO.File]::OpenRead($Path); $Hasher=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($Hasher.ComputeHash($Stream))).Replace('-','').ToLowerInvariant() }
    finally { $Stream.Dispose(); $Hasher.Dispose() }
}
$Index=Get-Content -LiteralPath (Join-Path $Directory 'bundle-index.json') -Raw -Encoding UTF8 | ConvertFrom-Json
function Safe-Name([string]$Name) {
    if ([IO.Path]::GetFileName($Name) -ne $Name -or $Name -match '[\\/]' -or $Name -eq '.' -or $Name -eq '..') { throw 'Invalid archive filename.' }
    return (Join-Path $Directory $Name)
}
$Zip=Safe-Name $Index.archive_name
if (Test-Path -LiteralPath $Zip) {
    if ((File-Sha256 $Zip) -eq $Index.archive_sha256) { Write-Host "已存在并校验通过：$Zip"; exit 0 }
    throw "已有同名文件校验不匹配，请先保留或移走它：$Zip"
}
foreach ($Part in $Index.parts) {
    $Path=Safe-Name $Part.name
    if (-not (Test-Path -LiteralPath $Path)) { throw "缺少分卷：$($Part.name)" }
    if ((Get-Item -LiteralPath $Path).Length -ne $Part.bytes -or (File-Sha256 $Path) -ne $Part.sha256) { throw "分卷校验失败：$($Part.name)" }
}
$Temp=$Zip+'.assembling'
$Output=[IO.File]::Open($Temp,[IO.FileMode]::Create,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    foreach ($Part in $Index.parts) {
        $InputStream=[IO.File]::OpenRead((Safe-Name $Part.name))
        try { $InputStream.CopyTo($Output,4194304) } finally { $InputStream.Dispose() }
        Write-Host "已合并：$($Part.name)"
    }
} finally { $Output.Dispose() }
if ((File-Sha256 $Temp) -ne $Index.archive_sha256) { throw '整包 SHA-256 不匹配，未生成可用压缩包。' }
Move-Item -LiteralPath $Temp -Destination $Zip
Write-Host "整包还原并校验完成：$Zip"
Write-Host '请完整解压，再阅读 00_使用说明.md，按 01_install.cmd、02_start.cmd、03_test.cmd 顺序操作。'
