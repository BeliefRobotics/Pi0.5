param([ValidateSet('Install','Start','Test','Diagnose','Stop')][string]$Action='Diagnose')
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new()
try {
    if ($Action -eq 'Test') {
        & (Join-Path $PSScriptRoot 'send_task.ps1') -Task '抓取瓶子' -RequestFile (Join-Path $PSScriptRoot 'examples\recorded_request.json')
        exit 0
    }
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { throw '请先安装 WSL2：以管理员身份打开 PowerShell，运行 wsl --install -d Ubuntu-24.04，然后重启电脑。' }
    $DistroNames=@(& wsl.exe --list --quiet) | ForEach-Object { ($_ -replace "`0",'').Trim() } | Where-Object { $_ }
    if ($LASTEXITCODE -ne 0) { throw 'WSL 尚未就绪。请以管理员身份运行 wsl --install -d Ubuntu-24.04，然后重启并完成 Ubuntu 的首次用户设置。' }
    $Distro=$env:PI05_WSL_DISTRO
    if (-not $Distro) {
        if ($DistroNames -contains 'Ubuntu-24.04') { $Distro='Ubuntu-24.04' }
        elseif ($DistroNames -contains 'Ubuntu') { $Distro='Ubuntu' }
        else { throw '未找到 Ubuntu。请运行 wsl --install -d Ubuntu-24.04，完成首次用户设置后再安装模型。' }
    }
    if ($DistroNames -notcontains $Distro) { throw "未安装指定发行版：$Distro" }
    $Versions=(@(& wsl.exe --list --verbose) -join "`n") -replace "`0",''
    $NamePattern=[regex]::Escape($Distro)
    if ($Versions -notmatch "(?m)^\s*\*?\s*$NamePattern\s+.+\s+2\s*$") {
        throw "该发行版不是 WSL2。请运行：wsl --set-version $Distro 2"
    }
    $LinuxBundle=(& wsl.exe -d $Distro -- wslpath -a -u $PSScriptRoot).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $LinuxBundle.StartsWith('/')) { throw '无法转换整合包路径，请将整合包解压到本地磁盘，例如 D:\Pi05。' }
    Write-Host "使用 $Distro；整合包：$PSScriptRoot"
    switch ($Action) {
        'Install' { & wsl.exe -d $Distro -- bash "$LinuxBundle/install_linux.sh" }
        'Start' { & wsl.exe -d $Distro -- bash "$LinuxBundle/start_linux.sh" }
        'Stop' { & wsl.exe -d $Distro -- bash "$LinuxBundle/stop_linux.sh" }
        'Diagnose' { & wsl.exe -d $Distro -- bash "$LinuxBundle/diagnose_linux.sh" }
    }
    if ($LASTEXITCODE -ne 0) { throw "操作未完成（退出码 $LASTEXITCODE）。请保留窗口中的错误信息并查看使用说明。" }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
