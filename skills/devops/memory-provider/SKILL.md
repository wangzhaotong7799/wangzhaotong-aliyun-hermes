---
name: memory-provider
description: "Set up and manage Hermes Agent external memory providers — OpenViking, Honcho, Mem0, etc. Installation, configuration, data migration, and troubleshooting."
version: 1.1.0
---

# Memory Provider — Hermes Agent External Memory Infrastructure

Configure Hermes Agent to use an external memory provider for persistent cross-session knowledge beyond built-in MEMORY.md / USER.md.

## Quick Start

```bash
# Interactive setup
hermes memory setup

# Manual config
hermes config set memory.provider openviking

# Check status
hermes memory status
```

## Supported Providers

| Provider | Type | Best For |
|----------|------|----------|
| OpenViking | Self-hosted (BYOD) | Structured filesystem hierarchy, tiered context |
| Honcho | Cloud API | Multi-agent systems, cross-session context |
| Mem0 | Cloud API | Hands-off memory management |
| Hindsight | Cloud/local | Graph-based recall |
| Holographic | Local SQLite | Zero dependencies |

## OpenViking Setup (Self-Hosted)

### Installation

```bash
pip install openviking
```

### Configuration

Config file: `~/.openviking/ov.conf`

```json
{
  "storage": { "workspace": "/path/to/workspace" },
  "embedding": {
    "dense": {
      "api_base": "https://api.siliconflow.cn/v1",
      "api_key": "${SILICONFLOW_API_KEY}",
      "provider": "openai",
      "dimension": 1024,
      "model": "BAAI/bge-m3"
    },
    "max_concurrent": 4
  },
  "vlm": {
    "api_base": "https://api.siliconflow.cn/v1",
    "api_key": "${SILICONFLOW_API_KEY}",
    "provider": "openai",
    "model": "Qwen/Qwen3-8B",
    "max_concurrent": 4
  }
}
```

Set env var: `export OPENVIKING_CONFIG_FILE=~/.openviking/ov.conf`

Validate: `openviking-server doctor`

### Systemd Service

```
[Unit]
Description=OpenViking Context Database Server
After=network.target

[Service]
Type=simple
ExecStart=/path/to/venv/bin/openviking-server
Environment=OPENVIKING_CONFIG_FILE=/root/.openviking/ov.conf
Restart=on-failure
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

### Hermes Integration

Env vars (in `~/.hermes/.env`):
```
OPENVIKING_ENDPOINT=http://127.0.0.1:1933
OPENVIKING_ACCOUNT=default
OPENVIKING_USER=<username>
OPENVIKING_AGENT=hermes
```

Config:
```yaml
memory:
  provider: openviking
```

## Data Migration

### From built-in memory_store.db to OpenViking

The `memory_store.db` is a SQLite database with facts stored under `facts` table (columns: content, category, tags, created_at).

**✅ RECOMMENDED — filesystem direct write** (avoids lock contention entirely).

This is the PRIMARY approach. The HTTP API approach is unreliable for more than 2-3 writes.

**Script:**
```python
import sqlite3, os, uuid

DB = "~/.hermes/memory_store.db"
BASE = "/workspace/openviking_workspace/viking/default/user/<name>/memories"
CATEGORY_MAP = {"general": "patterns", "user_pref": "preferences", "tool": "patterns"}

conn = sqlite3.connect(DB)
facts = conn.execute("SELECT content, category FROM facts ORDER BY fact_id").fetchall()
conn.close()

for content, cat in facts:
    subdir = CATEGORY_MAP.get(cat, "patterns")
    slug = uuid.uuid4().hex[:12]
    os.makedirs(f"{BASE}/{subdir}", exist_ok=True)
    with open(f"{BASE}/{subdir}/mem_{slug}.md", "w") as f:
        f.write(content)

# Restart to trigger auto-indexing
# systemctl restart openviking
```

After writing files, restart OpenViking to trigger auto-indexing:
```bash
systemctl restart openviking
```

**⚠️ Avoid HTTP API for bulk writes (2nd choice, slow):**
The `POST /api/v1/content/write` endpoint acquires a write lock on the parent directory. Concurrent writes to the same directory (e.g., `patterns/` or `preferences/`) fail with `"resource is busy"` and require 3-10s delay per write. 31 facts takes 3+ minutes. Only use this approach for single-memory writes (1-2 items).

### Category Mapping

| memory_store.db category | OpenViking subdir |
|--------------------------|-------------------|
| `general` | `patterns` |
| `user_pref` | `preferences` |
| `tool` | `patterns` |

## Pitfalls

1. **VLM model names must be exact** — SiliconFlow uses `Qwen/Qwen3-8B`, not `Qwen3-7B`. Check available models via `GET /v1/models?type=text` or the provider's model list. A wrong VLM model causes `commit_session()` to succeed but VLM extraction fails **silently** (`openai.BadRequestError: Model does not exist` logged server-side but never returned to the caller).

2. **Invalid `ov.conf` fields** — OpenViking 0.3.x does NOT accept `memory.auto_extract` or `memory.extraction_workers` fields. They cause startup failure: `Unknown config field 'auto_extract' (did you mean 'auto_generate_l1'?)`. The valid top-level sections are: `storage`, `log`, `embedding`, `vlm`, `server`.

3. **API key masking** — The terminal and file-write tools may mask API keys with `***` in output but write the actual value. Verify key length via `od -c` or Python `repr()`. If `write_file` wrote literal `***`, rebuild the config file via terminal with a heredoc or Python script.

4. **Directory lock contention** — OpenViking `content/write` acquires a write lock on the parent directory during indexing. Concurrent writes to the same subdirectory (e.g., `patterns/`) fail with `"resource is busy"`. For bulk imports (3+ items), write files directly to the workspace filesystem path, then verify with a search query. **No server restart required** — OpenViking auto-indexes filesystem writes within seconds.

5. **Retry strategy for HTTP API writes** — If you must use HTTP API for multiple writes: use `"mode": "overwrite"` instead of `"mode": "create"`, and back off 3-10s on `"busy"` errors. Still limit to 2-3 consecutive writes per directory.

6. **Filesystem write path** — The workspace path for direct file writes is: `/workspace/openviking_workspace/viking/default/user/<name>/memories/<subdir>/`. This bypasses all lock contention. After writing, OpenViking's indexer picks up new files automatically within 5-30 seconds.

7. **VLM extraction is async** — Session-based memory extraction (via `commit_session()`) runs asynchronously and depends on VLM availability. For immediate indexing, use `content/write` (single writes) or filesystem direct writes.

8. **Memory provider only one at a time** — Only one external provider can be active. Built-in memory (MEMORY.md + USER.md) always runs alongside.

9. **Gateway restart required** — After changing `memory.provider`, restart the gateway: `hermes gateway restart` or `systemctl --user restart hermes-gateway`. The change takes effect on the next new session (`/new` in chat).

## Verify

```bash
# OpenViking health
curl http://localhost:1933/health

# List memories in filesystem
curl "http://localhost:1933/api/v1/fs/ls?uri=viking://user/<name>/memories/"

# Semantic search (Python SDK)
python3 -c "
from openviking import SyncHTTPClient
c = SyncHTTPClient(url='http://127.0.0.1:1933')
c.initialize()
results = c.find('test', target_uri='viking://user/<name>/memories/')
for m in results.memories:
    print(f'{m.score:.2f} {m.uri}')
"

# Hermes recognizes the provider
hermes memory status
```
