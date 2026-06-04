# Hermes Agent Cron `script` 字段

Hermes Agent cron 作业支持 `script` 字段，用于执行独立的 Python 脚本而不是由 Agent 推理任务。

## 工作原理

在 `~/.hermes/cron/jobs.json` 中：

```json
{
  "id": "5495db19311f",
  "name": "gaofang-gunicorn-daily-reload",
  "prompt": "执行脚本内容即为任务。",
  "script": "gunicorn-daily-reload.py",
  "schedule": { "kind": "cron", "expr": "0 6 * * *", "display": "0 6 * * *" },
  "enabled": true,
  "deliver": "local"
}
```

当 `"script": "<name>"` 被设置且非 null 时，Agent 会：
1. 将 `prompt` + 脚本内容作为任务提示词
2. 查找 `/root/.hermes/scripts/<name>` 作为脚本文件
3. 执行脚本内容（Agent 读取文件并运行 `python3 <path>`）

## 注意事项

- 脚本文件路径固定为 `/root/.hermes/scripts/<name>`
- 脚本被删除后 cron 作业会报错 — **scripts 目录不会自动备份恢复**
- 脚本应包含完整的错误处理和 syslog 日志（cron 无交互式用户，只能靠日志排查）
- `deliver: "local"` 表示输出仅保留本地，不投递到外部平台

## 与 Hermes Cron 的对照

| 特性 | `script` 模式 | `skill` 模式 |
|:-|:-|:-|
| 执行方式 | 运行独立脚本 | Agent 推理 + 调用工具 |
| 适合场景 | 机械重复操作（重启、清理、检查） | 需要分析/决策的复杂任务 |
| 输出投递 | 仅 local | 可投递到飞书/邮箱等 |
| 失败可观测性 | syslog + job status | Agent response + job status |
