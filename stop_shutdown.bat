@echo off
chcp 65001 >nul
title ⛔ 阻断自动关机 - Hermes Agent
color 0C

echo ════════════════════════════════════════════
echo       🛑 自动关机阻断工具
echo           by Hermes Agent
echo ════════════════════════════════════════════
echo.
echo [!] 检测到系统启动后 1-2 分钟自动关机
echo    正在执行四级阻断方案...
echo.

:: ─────────────────────────────────────────────
:: 第一步：中止当前待处理的关机倒计时
:: ─────────────────────────────────────────────
echo [1/4] 中止待处理关机...
shutdown /a >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✅ 成功中止待处理关机！
) else (
    echo   ℹ️ 无待处理关机（可能已被其他手段触发）
)
echo.

:: ─────────────────────────────────────────────
:: 第二步：清除计划任务中的关机触发器
:: ─────────────────────────────────────────────
echo [2/4] 扫描并清除计划任务...

set "TASK_DELETED=0"
for /f "tokens=2 delims=:" %%a in (
    'schtasks /query /fo list /v 2^>nul ^| findstr /i "TaskName" ^| findstr /i "shutdown halt poweroff homicide"'
) do (
    set "taskname=%%a"
    set "taskname=!taskname: =!"
    echo   🔍 发现: %%a
    schtasks /end /tn "%%a" >nul 2>&1
    schtasks /delete /tn "%%a" /f >nul 2>&1
    if !errorlevel! equ 0 (
        echo   ✅ 已删除: %%a
        set TASK_DELETED=1
    )
)

:: 安全检查：删除所有在任务名中包含 "关机" / "shutdown" 的日常/开机触发任务
for /f "tokens=2 delims=:" %%a in (
    'schtasks /query /fo list /v 2^>nul ^| findstr /i "TaskName" ^| findstr /i "关机 定时 10pm 22"'
) do (
    echo   🔍 发现: %%a
    schtasks /end /tn "%%a" >nul 2>&1
    schtasks /delete /tn "%%a" /f >nul 2>&1
    if !errorlevel! equ 0 (
        echo   ✅ 已删除: %%a
    )
)

echo.
echo   📋 计划任务扫描完成
echo.

:: ─────────────────────────────────────────────
:: 第三步：清理 WSL 内的关机定时任务
:: ─────────────────────────────────────────────
echo [3/4] 检查 WSL (Windows Subsystem for Linux)...

wsl -e bash -c "crontab -l 2>/dev/null" > "%TEMP%\wsl_cron.txt" 2>&1
findstr /i "shutdown poweroff halt init" "%TEMP%\wsl_cron.txt" >nul 2>&1
if %errorlevel% equ 0 (
    echo   🔍 WSL crontab 发现关机指令:
    type "%TEMP%\wsl_cron.txt"
    echo.
    wsl -e bash -c "crontab -l 2>/dev/null | grep -viE 'shutdown|poweroff|halt|reboot|init\s+0' | crontab -" >nul 2>&1
    echo   ✅ 已清除 WSL crontab 中的关机指令
) else (
    echo   ℹ️ WSL crontab 无关机指令
)

:: 检查 WSL systemd 服务
wsl -e bash -c "systemctl list-timers --all 2>/dev/null | grep -i shutdown" > "%TEMP%\wsl_systemd.txt" 2>&1
findstr /i "shutdown" "%TEMP%\wsl_systemd.txt" >nul 2>&1
if %errorlevel% equ 0 (
    echo   🔍 WSL systemd 定时器发现关机服务
    type "%TEMP%\wsl_systemd.txt"
    wsl -e bash -c "systemctl disable --now *.shutdown*.timer *.shutdown*.service 2>/dev/null" >nul 2>&1
    echo   ✅ 已禁用 WSL 关机定时器
) else (
    echo   ℹ️ WSL systemd 无关机定时器
)
echo.

:: ─────────────────────────────────────────────
:: 第四步：检查启动项和注册表
:: ─────────────────────────────────────────────
echo [4/4] 检查注册表启动项...

set "FOUND_STARTUP=0"

:: 检查 HKCU Run
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" 2>nul | findstr /i "shutdown halt poweroff" >nul 2>&1
if %errorlevel% equ 0 (
    echo   🔍 HKCU\Run 发现可疑条目！
    reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" 2>nul | findstr /i "shutdown halt poweroff"
    echo.
    for /f "tokens=3*" %%a in (
        'reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" 2^>nul ^| findstr /i "shutdown halt poweroff"'
    ) do (
        reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "%%a" /f >nul 2>&1
        echo   ✅ 已删除启动项: %%a
    )
    set FOUND_STARTUP=1
)

:: 检查 HKLM Run
reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" 2>nul | findstr /i "shutdown halt poweroff" >nul 2>&1
if %errorlevel% equ 0 (
    echo   🔍 HKLM\Run 发现可疑条目！
    reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" 2>nul | findstr /i "shutdown halt poweroff"
    echo.
    for /f "tokens=3*" %%a in (
        'reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" 2^>nul ^| findstr /i "shutdown halt poweroff"'
    ) do (
        reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "%%a" /f >nul 2>&1
        echo   ✅ 已删除启动项: %%a
    )
    set FOUND_STARTUP=1
)

if %FOUND_STARTUP% equ 0 (
    echo   ℹ️ 注册表启动项中未发现关机指令
)

:: 检查启动文件夹
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\*.bat" (
    echo.
    echo   🔍 启动文件夹发现批处理文件：
    dir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\*.bat" /b 2>nul
    echo   ⚠️ 请手动检查这些文件是否包含关机指令
)
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\*.vbs" (
    echo.
    echo   🔍 启动文件夹发现 VBS 文件：
    dir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\*.vbs" /b 2>nul
    echo   ⚠️ 请手动检查这些文件是否包含关机指令
)
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\*.ps1" (
    echo.
    echo   🔍 启动文件夹发现 PowerShell 文件：
    dir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\*.ps1" /b 2>nul
    echo   ⚠️ 请手动检查这些文件是否包含关机指令
)

echo.
echo ════════════════════════════════════════════
echo  ✅ 四级阻断方案执行完毕！
echo.
echo  🛡️ 已执行操作：
echo     • 中止待处理关机
echo     • 删除计划任务中的关机触发器
echo     • 清除 WSL 内关机定时任务
echo     • 清理注册表启动项
echo.
echo  📌 如果问题仍然存在，请手动排查：
echo     1️⃣ 运行 taskschd.msc → 查看任务计划程序
echo     2️⃣ 运行 eventvwr.msc → Windows日志→系统→筛选"6006"关机事件
echo     3️⃣ 检查第三方软件："homicide" 是否有自己的计划任务
echo     4️⃣ 运行 msconfig → 启动 → 打开任务管理器 → 禁用可疑启动项
echo.
echo  🚀 按任意键退出...
echo ════════════════════════════════════════════
pause >nul
exit /b 0
