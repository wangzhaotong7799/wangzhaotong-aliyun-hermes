# Gunicorn 日志解读：HUP reload vs max-requests SIGTERM 轮换（2026-08-14 自检实录）

## 问题场景

健康检查/自检时看 gunicorn-error.log，发现大量 `[ERROR] Worker (pid:X) was sent SIGTERM!`，
容易误判为 worker 反复崩溃或异常重启。2026-08-14 自检时 8/13 当天出现 ~15 条 SIGTERM
（10:11~16:55 多个时间簇），初判"reload 异常频繁"。

## 关键区分（两类信号长得像、含义完全不同）

### 1. max-requests 正常轮换（良性，最常见）
- gunicorn 配置 `--max-requests 1000 --max-requests-jitter 200`
- worker 处理 800-1200 请求后自动退出，日志表现为**密集 SIGTERM 簇**：
  ```
  [ERROR] Worker (pid:2998881) was sent SIGTERM!
  [INFO]  Worker exiting (pid: 2998882)
  ```
- 多个 worker 几乎同时轮换（同秒或几秒内），**健康的日子天天如此**
- **不是 reload、不是崩溃**

### 2. 真 reload（运维/调度驱动）
- 标志性日志：`[INFO] Handling signal: hup` + `[INFO] Hang up: Master` + `Booting worker with pid`
- 来源：定时 cron（膏方 V2 有每日 06:00 `gaofang-gunicorn-daily-reload`）或手动 `kill -HUP` / systemctl reload
- reload 后旧 worker 清理也会打 SIGTERM——**是 reload 的正常收尾，不是崩溃**

## 判定方法

1. **数 reload 次数只数 `Handling signal: hup`**，不要数 SIGTERM：
   ```bash
   grep -c "Handling signal: hup" gunicorn-error.log
   ```
2. 对照 cron 计划（`hermes cron list` / crontab）看是否有**计划外**的 hup：
   - 膏方 V2 基线 = 每日 06:00 一次
   - 2026-08-13 发现计划外 hup：13:10、16:23、16:55（3 次）
3. 计划外 hup 的排查顺序：
   - 有没有对应 cron？→ 无
   - 当天有无 SSH 登录？→ `last` 无
   - 两者都没有 → **大概率主人手动操作**（宝塔面板重启/调试）
4. **上报前先确认，不要当成异常/恶意脚本**。若用户确认非手动操作，才深挖重复部署脚本。

## 本次自检的良性佐证

- 8/13 13:12 出现 1 条 `[CRITICAL] WORKER TIMEOUT (pid:2999913)`——位于 13:10 HUP reload 边界，
  是旧 worker 清理超时（技能 Pitfall 12 已定性为良性），非 OOM、非持续问题。
- 8/14 06:00 例行热重启正常完成，新 workers 全部就绪。

## 报告写法

- 报告时区分：`N 次 HUP reload（其中 M 次计划外）` + `worker 轮换正常`
- 不要把 SIGTERM 簇写成"reload 15 次"——那是轮换不是 reload，会夸大问题
- 计划外 hup 用 ⚠️ 观察项而非 🚨 错误标记，附上"建议确认是否主人手动操作"
