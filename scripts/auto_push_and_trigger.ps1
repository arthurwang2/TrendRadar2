# 无人值守：重试 git push，成功后尝试触发 crawler workflow
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot
$LogFile = Join-Path $RepoRoot "output\meta\auto_push.log"
New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $LogFile -Value $line
    Write-Host $line
}

Write-Log "auto_push 启动，目标 origin master"

while ($true) {
    $out = git push origin master 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0) {
        Write-Log "git push 成功"
        Write-Log $out.Trim()
        Write-Output "AUTO_PUSH_OK"
        exit 0
    }
    Write-Log "git push 失败，300 秒后重试: $($out.Trim())"
    Start-Sleep -Seconds 300
}
