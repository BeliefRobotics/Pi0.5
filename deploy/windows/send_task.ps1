param(
    [string]$Task='抓取瓶子',
    [string]$RequestFile='',
    [string]$ObservationFile='',
    [string]$Url='http://127.0.0.1:8796',
    [string]$OutputFile=''
)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new()
try {
    if ($RequestFile -and $ObservationFile) { throw 'RequestFile 和 ObservationFile 只能选择一个。' }
    if ($ObservationFile) {
        $Observation=Get-Content -LiteralPath $ObservationFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $Body=[pscustomobject]@{ task=$Task; observation=$Observation }
    } else {
        if (-not $RequestFile) { $RequestFile=Join-Path $PSScriptRoot 'examples\recorded_request.json' }
        $Body=Get-Content -LiteralPath $RequestFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $Body.task=$Task
    }
    $Body | Add-Member -NotePropertyName request_id -NotePropertyValue ([guid]::NewGuid().ToString()) -Force
    $Json=$Body | ConvertTo-Json -Depth 20 -Compress
    $Timer=[Diagnostics.Stopwatch]::StartNew()
    $Result=Invoke-RestMethod -Uri ($Url.TrimEnd('/')+'/v1/infer') -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($Json)) -TimeoutSec 180
    $Timer.Stop()
    $Result | Add-Member -NotePropertyName client_roundtrip_ms -NotePropertyValue $Timer.Elapsed.TotalMilliseconds -Force
    if (-not $OutputFile) {
        $ResultsDir=Join-Path $PSScriptRoot 'results'
        New-Item -ItemType Directory -Force -Path $ResultsDir | Out-Null
        $OutputFile=Join-Path $ResultsDir ((Get-Date -Format 'yyyyMMdd_HHmmss_fff')+'.json')
    }
    $Result | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutputFile -Encoding UTF8
    Write-Host "模型步骤：$($Result.checkpoint_step)"
    Write-Host "生成子任务：$($Result.generated_subtask)"
    Write-Host "动作维度：$($Result.action_shape -join ' x ')；调用耗时：$([math]::Round($Timer.Elapsed.TotalMilliseconds,1)) ms"
    Write-Host "结果：$OutputFile"
    Write-Host '只生成预测，没有让机器人运动。默认测试使用固定录制样本，修改任务文字不会改变图像和关节状态。'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host '请先运行 02_start.cmd，并等到 READY；若接口返回 422，请检查观测字段。'
    exit 1
}
