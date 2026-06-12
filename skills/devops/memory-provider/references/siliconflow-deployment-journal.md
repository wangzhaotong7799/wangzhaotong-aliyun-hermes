# OpenViking + SiliconFlow 完整部署记录

## 环境
- OS: Alibaba Linux 8 (5.10.134-19.6.al8.x86_64)
- Python: 3.11.15 (Hermes venv)
- Hermes: v0.15.1 (2026.5.29) → v0.16.0 待升级
- OpenViking: v0.3.14

## 已安装组件
- Rust/Cargo: 1.75.0
- GCC: 10.2.1
- pip: openviking==0.3.14

## 配置路径

| 项目 | 路径 |
|------|------|
| OpenViking 配置 | `~/.openviking/ov.conf` |
| OpenViking 工作区 | `/workspace/openviking_workspace` |
| Hermes 内存配置 | `~/.hermes/config.yaml` → `memory.provider: openviking` |
| Hermes 环境变量 | `~/.hermes/.env` → `OPENVIKING_*` |
| Systemd 服务 | `/etc/systemd/system/openviking.service` |
| 迁移脚本 | `/workspace/scripts/migrate_memory_to_openviking.py` |

## 硅基流动模型

| 用途 | 模型 | 维度 |
|------|------|------|
| Embedding | `BAAI/bge-m3` | 1024 |
| VLM (记忆提取) | `Qwen/Qwen3-8B` | — |

API Base: `https://api.siliconflow.cn/v1`

## 已知问题

1. **`content/write` 目录锁** — 批量写入同一子目录时，OpenViking 会对父目录加锁。批量导入应直接写文件系统然后重启服务。
2. **VLM 模型名** — 硅基流动上的模型名与 HuggingFace 不一致，需用 `Qwen/Qwen3-8B` 而非 `Qwen3-7B`。
3. **API Key 输出遮蔽** — Terminal 输出中 API key 会被 `***` 替换，但实际文件内容正确。用 `od -c` 或 `repr()` 验证。

## 验证命令

```bash
# 健康检查
curl http://127.0.0.1:1933/health
# → {"status":"ok","healthy":true,"version":"0.3.14","auth_mode":"dev"}

# 搜索记忆 (Python SDK)
python3 -c "
from openviking import SyncHTTPClient
c = SyncHTTPClient(url='http://127.0.0.1:1933')
c.initialize()
for m in c.find('搜索关键词', target_uri='viking://user/wangzhaotong/memories/').memories:
    print(m.uri, m.score)
"

# 查看文件系统
curl http://127.0.0.1:1933/api/v1/fs/ls?uri=viking://user/wangzhaotong/memories/

# 服务状态
systemctl status openviking
```

## 迁移结果

| 项目 | 值 |
|------|-----|
| 原始数据 | `memory_store.db` facts 表 |
| 事实数量 | 31 条 |
| 迁移方法 | 直接写入 workspace 文件系统 |
| 文件路径 | `/workspace/openviking_workspace/viking/default/user/wangzhaotong/memories/` |
| 写入文件数 | 42 个 .md（31 条事实 + 11 个自动生成的 overview/abstract） |
| 搜索引擎可检索 | ✅ 写入后自动索引，无需重启 |
| VLM 提取 | ✅ Qwen3-8B 自动生成了中文摘要 |
| 耗时 | < 5 秒（文件系统写入） |

## 文件系统写入方案（推荐）

避免 HTTP API 目录锁争用的最佳方案：

```bash
# 路径格式
/workspace/openviking_workspace/viking/default/user/{USER}/memories/{subdir}/mem_{slug}.md

# 子目录映射
# patterns ← general, tool
# preferences ← user_pref

# 写入后 5-30 秒内自动索引
# 无需重启服务
```