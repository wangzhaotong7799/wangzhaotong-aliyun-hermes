---
name: memory-infrastructure
title: Agent Memory Infrastructure
description: Setup, configuration, and maintenance of external memory providers for AI agents (OpenViking, etc.). Covers server deployment, Hermes integration, data migration, and troubleshooting.
domain: devops
trigger: user asks about memory provider, OpenViking, agent memory setup, migrating memories, or persistent memory configuration
---

# Agent Memory Infrastructure

Setting up external memory providers gives an AI agent persistent, cross-session knowledge beyond built-in MEMORY.md/USER.md. This skill documents the full lifecycle for OpenViking (ByteDance/Volcengine context database) as the primary provider, with patterns applicable to other providers.

## Architecture Overview

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Hermes     │────▶│  OpenViking     │────▶│  Embedding API   │
│  Agent      │     │  Server :1933   │     │  (SiliconFlow)   │
│             │◀────│  (context DB)   │◀────│  BAAI/bge-m3     │
└─────────────┘     └─────────────────┘     └──────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Workspace Storage │
                    │  (vector index +   │
                    │   fs hierarchy)    │
                    └────────────────────┘
```

## Installation

### 1. Install OpenViking

```bash
# Python package (into Hermes venv)
pip install openviking

# Verify
openviking-server --version
openviking-server doctor   # validate config
```

Prerequisites: Python ≥3.10, Rust (optional, for CLI), GCC/Clang.

### 2. Configure `~/.openviking/ov.conf`

The config file has three key sections: `storage`, `embedding`, and `vlm`.

**With SiliconFlow as embedding provider (OpenAI-compatible API):**

```json
{
  "storage": {
    "workspace": "/workspace/openviking_workspace"
  },
  "log": {
    "level": "INFO",
    "output": "stdout"
  },
  "embedding": {
    "dense": {
      "api_base": "https://api.siliconflow.cn/v1",
      "api_key": "<SILICONFLOW_API_KEY>",
      "provider": "openai",
      "dimension": 1024,
      "model": "BAAI/bge-m3"
    },
    "max_concurrent": 4,
    "text_source": "content_only",
    "max_input_tokens": 4096
  },
  "vlm": {
    "api_base": "https://api.siliconflow.cn/v1",
    "api_key": "<SILICONFLOW_API_KEY>",
    "provider": "openai",
    "model": "Qwen/Qwen3-8B",
    "max_concurrent": 4
  },
  "server": {
    "host": "127.0.0.1"
  }
}
```

**Key config notes:**
- `embedding.dense.provider: "openai"` — works with any OpenAI-compatible embedding API
- `BAAI/bge-m3` — multilingual, dimension 1024, max 8192 tokens
- VLM model names must EXACTLY match the provider's model list (SiliconFlow: `Qwen/Qwen3-8B`, NOT `Qwen/Qwen3-7B`)
- Server defaults to port **1933** (not configurable via `server.port` in the current version)
- Export `OPENVIKING_CONFIG_FILE=~/.openviking/ov.conf` before starting

### 3. Verify and Start

```bash
# Validate config
export OPENVIKING_CONFIG_FILE=~/.openviking/ov.conf
openviking-server doctor

# Start server
openviking-server

# Health check
curl http://127.0.0.1:1933/health
# → {"status":"ok","healthy":true,"version":"0.3.14","auth_mode":"dev"}
```

### 4. systemd Service (persist across reboots)

```bash
cat > /etc/systemd/system/openviking.service << 'EOF'
[Unit]
Description=OpenViking Context Database Server
After=network.target

[Service]
Type=simple
ExecStart=/path/to/hermes/venv/bin/openviking-server
Environment=OPENVIKING_CONFIG_FILE=/root/.openviking/ov.conf
Restart=on-failure
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable openviking
systemctl start openviking
systemctl status openviking
```

## Hermes Integration

### 1. Set Memory Provider

```bash
hermes config set memory.provider openviking
```

Verify: `grep -A3 "^memory:" ~/.hermes/config.yaml` should show `provider: openviking`.

### 2. Environment Variables

Add to `~/.hermes/.env`:

```
OPENVIKING_ENDPOINT=http://127.0.0.1:1933
OPENVIKING_ACCOUNT=default
OPENVIKING_USER=<your-username>
OPENVIKING_AGENT=hermes
```

Defaults: `OPENVIKING_ENDPOINT=http://127.0.0.1:1933`, `OPENVIKING_USER=default`, `OPENVIKING_AGENT=hermes`, `OPENVIKING_ACCOUNT=default`. The endpoint only needs explicit setting if running on a non-default port/host.

### 3. Restart Gateway

```bash
hermes gateway restart
```

After restart, Hermes automatically:
- Injects provider context into system prompt
- Prefetches relevant memories before each turn
- Syncs conversation turns after each response
- Extracts memories on session end
- Mirrors built-in memory writes (MEMORY.md/USER.md writes) to OpenViking

## Memory Data Migration

### From `memory_store.db` (SQLite built-in) to OpenViking

The built-in `~/.hermes/memory_store.db` may contain 20-30 facts from previous sessions. OpenViking stores memories under `viking://user/{user}/memories/{subdir}/` using a filesystem hierarchy.

**Category mapping:**

| memory_store.db category | OpenViking subdir |
|---|---|
| `general` | `patterns` |
| `user_pref` | `preferences` |
| `tool` | `patterns` |

**Migration approach:**
1. Read facts from `memory_store.db` SQLite
2. For each fact, POST to OpenViking `/api/v1/content/write`
3. URI format: `viking://user/{user}/memories/{subdir}/mem_{slug}.md`

**Critical: Sequential writes with delay.** OpenViking's path-locking mechanism prevents concurrent writes to the same directory. Each write must be followed by a 3-second delay to allow vector indexing to complete. Without this delay, the server returns `"resource is busy and cannot be written now"`.

### Migration Script Template

```python
import json, uuid, sqlite3, urllib.request, time

OPENVIKING_URL = "http://127.0.0.1:1933"
USER = "your-username"
CATEGORY_MAP = {"general": "patterns", "user_pref": "preferences", "tool": "patterns"}

conn = sqlite3.connect("~/.hermes/memory_store.db")
cur = conn.cursor()
cur.execute("SELECT content, category FROM facts ORDER BY fact_id")
for content, category in cur.fetchall():
    subdir = CATEGORY_MAP.get(category, "patterns")
    uri = f"viking://user/{USER}/memories/{subdir}/mem_{uuid.uuid4().hex[:12]}.md"
    data = json.dumps({"uri": uri, "content": content, "mode": "create"}).encode()
    req = urllib.request.Request(
        f"{OPENVIKING_URL}/api/v1/content/write", data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=30)
    time.sleep(3)  # ⚠️ MUST wait for indexing
conn.close()
```

## Pitfalls & Troubleshooting

### 1. VLM Model Name Mismatch

OpenViking uses the VLM model for automatic memory extraction at session end. If the model name doesn't exist on the provider:

```
openai.BadRequestError: Error code: 400 - {'code': 20012, 'message': 'Model does not exist.'}
```

**Fix:** Query the provider's model list to find exact model IDs, then update `ov.conf` and restart the server.

### 2. Path Lock Contention ("resource is busy")

Multiple concurrent writes to the same `viking://user/{user}/memories/{subdir}/` directory cause:

```
resource is busy and cannot be written now
```

**Fix:** Write sequentially with at least 3s delay between writes. Do NOT parallelize. Retry with backoff if busy.

### 3. API Key Masked by write_file Tool

The Hermes `write_file` tool masks known API key patterns with `***`. When writing API keys to config files, use Python heredoc through the terminal tool instead:

```bash
python3 << 'PYEOF'
import json
key = "sk-xxxxx"
conf = json.load(open('/path/to/config'))
conf['embedding']['dense']['api_key'] = key
json.dump(conf, open('/path/to/config', 'w'), indent=2)
PYEOF
```

### 4. Hermes Gateway must be restarted

After changing `memory.provider`, Hermes needs a full gateway restart (`hermes gateway restart`) or new CLI session. `hermes config set` alone does NOT reload the provider mid-session.

### 5. `openviking-server doctor` validates config before starting

Run `openviking-server doctor` before trying to start the server. It catches:
- Config file validity
- Python version
- Native engine compatibility
- Embedding/VLM API connectivity
- Disk space in workspace

### 6. Silently failed VLM extraction

If `vlm.model` is wrong, the server starts fine but memory extraction at session end silently fails. Check server logs for model errors.

## Verification

After setup is complete:

```bash
# 1. Server health
curl http://127.0.0.1:1933/health

# 2. Hermes recognizes the provider
hermes memory status

# 3. Memory store has data
curl -s "http://127.0.0.1:1933/api/v1/fs/ls?uri=viking://user/{user}/memories/"

# 4. Semantic search works
curl -X POST http://127.0.0.1:1933/api/v1/search/find \
  -H "Content-Type: application/json" \
  -d '{"query":"test","target_uri":"viking://user/{user}/memories/","limit":5}'
```
