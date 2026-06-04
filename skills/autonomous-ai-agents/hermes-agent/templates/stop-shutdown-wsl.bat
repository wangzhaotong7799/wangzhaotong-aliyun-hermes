@echo off
chcp 65001 >nul
title ⛔ 阻断自动关机 V2 - 直接停掉肇事进程
color 0C

echo ════════════════════════════════════════════
echo      🛑 自动关机阻断工具 V2
echo        ——直接停掉触发源
echo ════════════════════════════════════════════
echo.
echo [!] 适用于：WSL 中 Hermes Agent cron 触发 shutdown /s /t 0
echo    开机后1-2分钟直接显示"正在关机"，无倒计时
echo.

:: ─────────────────────────────────────────────
:: 第一步：进 WSL 杀掉 Hermes Agent 进程
:: ─────────────────────────────────────────────
echo [1/4] 进 WSL 截停 Hermes Agent...

wsl -e bash -c "pkill -f 'hermes' 2>/dev/null"
if %errorlevel% equ 0 (
    echo   ✅ 已杀掉 WSL 中 Hermes Agent 进程
) else (
    echo   ℹ️ WSL 中未发现 Hermes Agent 进程
)

:: 补刀：防止有 crontab 进程正在跑关机
wsl -e bash -c "pkill -f 'shutdown' 2>/dev/null"
wsl -e bash -c "pkill -f 'poweroff' 2>/dev/null"
echo   ✅ WSL 进程清理完毕
echo.

:: ─────────────────────────────────────────────
:: 第二步：清除 Windows 计划任务中的关机触发器
:: ─────────────────────────────────────────────
echo [2/4] 扫描并清除计划任务...

for /f "tokens=2 delims=:" %%a in (
    'schtasks /query /fo list /v 2^>nul ^| findstr /i "TaskName" ^| findstr /i "shutdown halt poweroff"'
) do (
    echo   🔍 发现: %%a
    schtasks /end /tn "%%a" >nul 2>&1
    schtasks /delete /tn "%%a" /f >nul 2>&1
    echo   ✅ 已删除: %%a
)
echo   计划任务扫描完成
echo.

:: ─────────────────────────────────────────────
:: 第三步：清 WSL crontab 中的关机任务
:: ─────────────────────────────────────────────
echo [3/4] 清除 WSL crontab...

wsl -e bash -c "crontab -l 2>/dev/null | grep -viE 'shutdown|poweroff|halt|reboot|systemctl|init\s+0' | crontab -"
echo   ✅ WSL crontab 已清理
echo.

:: ─────────────────────────────────────────────
:: 第四步：阻止 WSL 下次开机自动启动
:: ─────────────────────────────────────────────
echo [4/4] 暂停 WSL 开机自启...

wsl -l -v > "%TEMP%\wsl_status_before.txt" 2>nul

powershell -Command "Get-Service 'LxssManager' | Stop-Service" >nul 2>&1
powershell -Command "Set-Service 'LxssManager' -StartupType Disabled" >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✅ WSL 服务已停止并禁用开机自启
    echo   ⚠️ 注意：删完 cron 任务后记得恢复：
    echo      powershell Set-Service LxssManager -StartupType Automatic
    echo      powershell Start-Service LxssManager
) else (
    echo   ℹ️ WSL 服务操作可能需要管理员权限
)
echo.

echo ════════════════════════════════════════════
echo  ✅ 阻断执行完毕！
echo.
echo  📌 接下来请进 WSL 删掉那个 cron 任务：
echo     wsl
echo     hermes cron list
echo     hermes cron remove ^<job_id^>
echo.
echo  📌 删完后，恢复 WSL 开机自启：
echo     powershell Set-Service LxssManager -StartupType Automatic
echo     powershell Start-Service LxssManager
echo.
echo  🚀 按任意键退出...
echo ════════════════════════════════════════════
pause >nul
exit /b 0
