# Token 监控与压缩工具 — 金脉小队配套

wealth-analyst 是 Hermes Agent 上 Token 消耗最大的组件（三份周报每份 ~924K~1.62M 输入 Token），以下工具用于监控和优化 Token 开销。

---

## TokScale — 全局 Token 监控

**安装方式**: `npm install -g @tokscale/cli`（已全局安装）
**运行**: `tokscale`（交互式 TUI）或 `tokscale models`（模型用量报表）

自动读取 `~/.hermes/state.db`，支持：
- 按模型/日期/平台 查看 Token 消耗
- 实时定价估算（基于 LiteLLM）
- 导出 JSON 用于进一步分析

**使用场景**: 报告交付后扫一眼全局大盘，确认周报消耗是否正常。

---

## RTK — 终端命令 Token 压缩

**安装方式**: `cargo install --git https://github.com/rtk-ai/rtk`（已安装）
**二进制位置**: `~/.cargo/bin/rtk`
**工作原理**: 拦截 Shell 命令输出，去除噪声（注释、空白、重复行），平均压缩 80%+ 的 Token

**常用命令**:
```bash
rtk ls .                    # Token优化版目录树
rtk read file.py            # 智能文件读取
rtk git status              # 精简版 git status
rtk git diff                # 精简版 git diff
rtk grep "pattern" .        # 分组搜索结果
```

**与 Hermes Agent 集成**:
```bash
rtk init -g                 # 默认集成 Claude Code / Copilot
```

**关键限制**: RTK 只改写 Bash 工具调用的输出，内置工具（Read、Grep、Glob）不会经过 RTK。需要在这些场景显式使用 `rtk read`、`rtk grep` 等。

---

## Hermes Dashboard — 深度分析

**内置版**:
```bash
hermes dashboard            # 启动 Web UI（localhost:9119）
hermes dashboard --status   # 查看运行状态
```
内置看板包含：总Token、输入/输出拆分、缓存命中率、会话数、每日趋势图。

**Bichev 版（深度分析，未部署）**:
- [Bichev/hermes-dashboard](https://github.com/Bichev/hermes-dashboard)
- 按模型/平台/工具/会话深度 拆解 Token 去向
- 成本告警、错误追踪、Cron 作业监控
- 需要：**域名** + Caddy HTTPS 反代，部署后仪表板 IP/端口 + 密钥

---

## 推荐使用顺序

1. 报告跑完后 → `tokscale` 看一眼全局 Token 大盘
2. 如果某份报告消耗异常 → `hermes dashboard` 按组件看细节
3. 日常开发中 → 用 `rtk` 前缀压缩终端命令输出
