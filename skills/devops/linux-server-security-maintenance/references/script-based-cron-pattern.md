# Script-Based Cron Job 模式

## 应用场景

当定时任务不需要 LLM 推理（仅需执行脚本并输出结果）时，使用 `no_agent=true` 模式：

- 自动备份脚本
- 健康检查脚本
- 数据采集脚本
- 日志清理脚本
- 任何"执行 X 然后输出结果"的纯脚本任务

## 步骤

### 1. 将脚本放入 `~/.hermes/scripts/`

```bash
cp <你的脚本> ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/<脚本名>
```

> 必须是 `.sh`（bash）或 `.py`（Python）后缀。cronjob 工具要求脚本路径**仅文件名**，且必须在 `~/.hermes/scripts/` 下。

### 2. 创建 cron job

```bash
# 通过 cronjob 工具
cronjob action=create
  schedule="0 23 * * *"    # cron 表达式
  name="每日自动备份"
  script="daily-backup.sh"  # 仅文件名，在 ~/.hermes/scripts/ 下
  no_agent=true             # 关键！跳过 LLM，直接执行脚本
```

### 3. 脚本要求

- 脚本的 stdout 会被直接投递到 `deliver` 目标
- 脚本的 stderr 会在出错时作为错误消息
- 脚本退出码非 0 时，标记为执行失败
- 脚本不需要交互输入

## 与 LLM-driven cron 的区别

| 特性 | LLM-driven（默认） | Script-based（no_agent=true） |
|------|-------------------|-------------------------------|
| 消耗 Token | 每次运行消耗 Token | 不消耗 Token |
| 灵活度 | 可推理、可调用工具 | 只能执行预设脚本 |
| 适用场景 | 需要分析/判断的任务 | 固定的自动化任务 |
| 脚本路径 | 不适用 | 必须在 `~/.hermes/scripts/` |
| 运行频率 | 建议低频（每日/每周） | 适合高频（每小时/每 30 分钟） |
