---
name: profile-restoration
description: Hermes profile restoration from multiple backup sources — git repo, local tarball, and separate env/config snapshots. Merge strategy, duplicate cleanup, and verification.
tags:
  - hermes
  - profile
  - restoration
  - backup
  - migration
  - feishu
triggers:
  - "Restore Hermes profile"
  - "Recover from backup"
  - "Merge config from multiple sources"
  - "Restore settings from git repo"
  - "恢复设置"
---

# Hermes Profile Restoration

Restore a complete Hermes profile (~/.hermes/) from one or more backup sources. Covers the common scenario where the user has a **git repo** (for config + skills) and a **local tarball/systemd backup** (for runtime data, credentials, memories, cron state).

## When to Use

Use this when the user says things like:
- "恢复设置" (restore settings)
- "从 backup 恢复" (restore from backup)
- "迁移到新机器" (migrate to new machine)
- "找回之前的配置" (find previous config)

## Workflow Overview

```
1. DISCOVER → Find all backup sources
2. ASSESS → Determine age & contents of each source
3. RESTORE → Apply in correct order (git first, then overlay local)
4. MERGE → Resolve conflicts, deduplicate YAML
5. VERIFY → Validate config loads, check all keys present
```

---

## Step 1: Discover Backup Sources

Three common patterns:

| Source | Typical path | What it contains |
|--------|-------------|------------------|
| **Git repo** | `git@github.com:user/repo.git` | config.yaml, SOUL.md, skills/, static files |
| **Local tarball** | `/root/*-backup-*/hermes-profile.tar.gz` | Full `default/` profile with cron, memories, DB, .env.backup |
| **Systemd upgrade backup** | `/root/upgrade-backup-YYYYMMDD_HHMMSS/` | config.yaml.bak, env.bak, skills-backup/ |

Search commands:
```bash
# Find backup tarballs
find /root -name '*.tar.gz' -path '*backup*' 2>/dev/null | head -10

# Find backup directories
find /root -maxdepth 3 -type d -name '*backup*' 2>/dev/null

# Find env backups
find /root -name 'env.bak' -o -name '.env.backup' 2>/dev/null
```

## Step 2: Assess Each Source

Inspect contents without full extraction:

```bash
# Check tarball contents (top-level + key files)
tar -tzf backup.tar.gz | grep -v '\.git/objects/' | sort

# Examine env backup
cat /root/upgrade-backup-*/env.bak 2>/dev/null

# Check git repo structure
cd /tmp/restore-temp && find . -type f | sed 's|^\./||' | sort
```

**Key questions to answer:**
1. Which source has the **newest** config.yaml?
2. Which source has **runtime data** (cron outputs, memories, DB)?
3. Which source has **credentials** (.env / secrets)?
4. Which source has **skills** directory?

## Step 3: Apply in Correct Order

**Critical rule: git repo FIRST (broad config + skills), then overlay local backup (runtime state + credentials).**

The git repo contains the canonical config but excludes secrets. The local backup contains the real .env with API keys, cron state, and memory data.

```bash
# Phase A: Git repo — config, SOUL.md, skills
cp repo/config.yaml ~/.hermes/config.yaml
cp repo/SOUL.md ~/.hermes/SOUL.md
cp -a repo/skills ~/.hermes/skills

# Phase B: Local backup — overlay credentials, cron, memories, DB
cp backup/env.bak ~/.hermes/.env
chmod 600 ~/.hermes/.env
cp backup/config.yaml.bak ~/.hermes/config.yaml  # only if newer than git version
cp -a backup/default/cron ~/.hermes/cron/
cp -a backup/default/memories ~/.hermes/memories/
cp backup/default/memory_store.db ~/.hermes/memory_store.db
cp -a backup/default/memory ~/.hermes/memory/
cp backup/default/channel_directory.json ~/.hermes/
cp backup/default/feishu_seen_message_ids.json ~/.hermes/ 2>/dev/null
cp backup/skills-backup ~/.hermes/skills  # only if skills-backup is newer
```

## Step 4: Resolve Conflicts and Clean Up

### 4a: Config version mismatch

Old backups may have `_config_version: 23`. The running Hermes expects the current version. Update:

```python
import re
with open('/root/.hermes/config.yaml') as f:
    content = f.read()
content = re.sub(r'_config_version: \d+', '_config_version: 25', content)  # use actual current version
with open('/root/.hermes/config.yaml', 'w') as f:
    f.write(content)
```

**Always check the current config_version** in your running Hermes before changing:
```bash
grep '_config_version' /root/.hermes/config.yaml.bak  # old value from backup
# Compare with what the current hermes expects — update to match
```

### 4b: Duplicate YAML sections

Merging config from different sources can create duplicates. Common patterns:

**Duplicate feishu section** — old config had both `platforms.feishu.group_rules` (under `platforms:`) AND a top-level `feishu:` section:

```yaml
# DUPLICATE — two feishu sections with slightly different require_mention values
platforms:
  feishu:
    group_rules:
      oc_xxx:
        policy: open
        require_mention: true   # from git config
FEISHU_HOME_CHANNEL: oc_xxx
feishu:
  group_rules:
    oc_xxx:
      require_mention: false    # from local backup — different value
      policy: open
```

**Fix:** Merge the values into ONE section under `platforms.feishu`, removing the top-level `feishu:` stanza. Prefer the **local backup's value** when in doubt (it reflects actual running state at backup time).

```python
# Python merge script
content = content.replace(
    """FEISHU_HOME_CHANNEL: oc_xxx
plugins:
feishu:
  group_rules:
    oc_xxx:""",
    "FEISHU_HOME_CHANNEL: oc_xxx\nplugins:"
)
```

### 4c: Missing platform_toolsets entries

Older configs may not have `feishu` in `platform_toolsets`:

```yaml
# Add missing entry
  qqbot:
  - hermes-qqbot
  feishu:        # ← add this
  - hermes-feishu
```

### 4d: Config-specific platform sections (not under gateway:)

Old configs may have top-level `platforms:` instead of `gateway.platforms:`. The top-level `platforms.feishu` is the correct location for feishu group_rules — do NOT move it under `gateway:`.

### 4e: API key expiry check

Restored `.env` keys may be **expired or invalid** — especially if the backup is old. This is a common pitfall: the user backs up, then rotates keys weeks later, and the backup carries old keys.

**After merging .env, verify all API keys are valid:**

```bash
# DeepSeek
curl -s https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer $(grep DEEPSEEK_API_KEY ~/.hermes/.env | cut -d= -f2)" \
  | head -3

# Should return: {"object":"list","data":[{"id":"deepseek-v4-flash",...}]}
# If 401: "Authentication Fails, Your api key: ****xxx is invalid" — key is expired
```

**When a key is invalid, the user must provide a replacement.** Update .env:
```bash
# Write the new key
python3 -c "
import re
with open('/root/.hermes/.env', 'r') as f:
    content = f.read()
content = re.sub(r'DEEPSEEK_API_KEY=.*', 'DEEPSEEK_API_KEY=<new-key>', content)
with open('/root/.hermes/.env', 'w') as f:
    f.write(content)
"
chmod 600 /root/.hermes/.env
```

### 4f: Stale gateway process blocking restart

After restoring credentials and restarting the gateway, an **old gateway process** (started manually via tmux/nohup before the backup) may still be running. This causes:

```
feishu: Another local Hermes gateway is already using this Feishu app_id (PID 755136).
Stop the other gateway before starting a second Feishu websocket client.
```

The old process won't be killed by `hermes gateway stop` (which targets the systemd service). Kill it explicitly:

```bash
# Find the old PID from the error message
kill <PID>
# Or force-kill if in D state (uninterruptible sleep):
kill -9 <PID>

# Then start cleanly
hermes gateway start
```

After starting, verify feishu connects in the journal:
```bash
journalctl --user -u hermes-gateway.service --since '30 sec ago' --no-pager | grep 'Lark.*connected'
# Expected: [Lark] [INFO] connected to wss://msg-frontier.feishu.cn/ws/v2?...
```

### 4g: Feishu require_mention conflict resolution

When merging duplicate `feishu.group_rules` sections (one under `platforms.feishu` and one standalone `feishu:`), the `require_mention` value may differ:

| Source | `require_mention` for group oc_xxx |
|--------|-----------------------------------|
| platforms.feishu (git config) | `true` |
| standalone feishu: (local backup) | `false` |

**Prefer the local backup's value** — it reflects the **actual running state** at backup time. A value of `false` means the group accepted messages without @-mention, which was the user's working setup.

Merge by keeping the `platforms.feishu.group_rules` section with the local backup's `require_mention` value, and delete the standalone `feishu:` stanza.

## Step 5: Verify Restoration

```python
import yaml
with open('/root/.hermes/config.yaml') as f:
    data = yaml.safe_load(f)

print(f"Model: {data.get('model',{}).get('default','?')}")
print(f"Provider: {data.get('model',{}).get('provider','?')}")
print(f"Config version: {data.get('_config_version','?')}")

feishu = data.get('platforms',{}).get('feishu',{})
print(f"Feishu configured: {'yes' if feishu else 'no'}")
print(f"Feishu group_rules: {len(feishu.get('group_rules',{}))}")
print(f'Home channel: {data.get('FEISHU_HOME_CHANNEL','not set')}')

pt = data.get('platform_toolsets',{})
print(f"Feishu in toolsets: {'yes' if 'feishu' in pt else 'no'}")

env_keys = set()
with open('/root/.hermes/.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            env_keys.add(line.split('=')[0].strip())
print(f"Env keys ({len(env_keys)}): {sorted(env_keys)}")
```

**Checklist:**
- [ ] config.yaml loads without YAML parse errors
- [ ] `.env` has all required API keys (check for masked/truncated values)
- [ ] SOUL.md present
- [ ] Skills directory populated
- [ ] Cron jobs present
- [ ] Memories restored (MEMORY.md, USER.md)
- [ ] memory_store.db present
- [ ] channel_directory.json present (with expected platform entries)
- [ ] gateway_state.json (may be stale — indicates what was connected)
- [ ] feishu_seen_message_ids.json present (dedup state)
- [ ] config_version matches running Hermes version
- [ ] No duplicate YAML keys (validate: `python3 -c "import yaml; yaml.safe_load(open('/root/.hermes/config.yaml')); print('OK')"`)
- [ ] API keys are valid (test with `curl` against each provider)
- [ ] Gateway starts and feishu WebSocket connects without conflict errors
- [ ] No old gateway PID blocking feishu

## Feishu Configuration Details

When restoring a profile that had feishu connected, these files must all be present:

| File | Purpose |
|------|---------|
| `.env` with `FEISHU_APP_ID`, `FEISHU_APP_SECRET` | API credentials |
| `.env` with `FEISHU_ALLOWED_USERS` or `GATEWAY_ALLOW_ALL_USERS` | Access control |
| `config.yaml` with `platforms.feishu` section | Group rules and home channel |
| `config.yaml` with `FEISHU_HOME_CHANNEL` | Default delivery target |
| `channel_directory.json` | Channel ID mappings |
| `feishu_seen_message_ids.json` | Dedup state (avoids re-processing old messages) |

**Missing credentials troubleshooting:** If `.env` comes from a backup but FEISHU_APP_SECRET appears masked (shown as `***`), the actual raw value can be extracted with:
```python
import os
env_path = os.path.expanduser("~/.hermes/.env")
with open(env_path, 'rb') as f:
    raw = f.read()
for line in raw.split(b'\n'):
    if b'FEISHU_APP_SECRET' in line:
        secret = line.decode('utf-8').split('=', 1)[1]  # fully readable
        break
```

## Pitfalls

1. **Backup order matters.** Apply git repo FIRST (config/skills), then overlay local backup (credentials/runtime). Reversing this loses the git config.
2. **Secrets are never in git repos.** The `.env` with API keys only comes from local backups. Always check the local backup for credentials.
3. **Gateway state files are stale.** `gateway_state.json` shows what was connected at backup time — not current state. Check `systemctl --user status hermes-gateway` for live status.
4. **Config version drift.** Backups can be weeks old with a lower `_config_version`. The user's running Hermes may reject old format. Always update to the current version.
5. **Feishu dedup state reset.** Without `feishu_seen_message_ids.json`, the gateway will re-process old messages. Restore this file if available.
6. **Skills directory can come from either source.** The git repo has the canonical skills; the skills-backup may have additional or newer skills. Prefer git for canonical, overlay backup for additions.
7. **Dual env.bak files.** When both a `env.bak` and `tar.gz/default/.env.backup` exist, compare them — the env.bak may have more recent keys (like `ALIYUN_BAILIAN_API_KEY`).
8. **rtk-rewrite plugin.** The config may list `plugins.enabled: [rtk-rewrite]` but the plugin binary may not be installed. This is not a restoration issue — the config entry is correct, the binary needs separate installation via `pip install rtk-hermes`.
9. **Dual gateway services (user + system) causing restart loops.** After restoring a profile from backup, both user and system gateway services may be installed simultaneously. This causes a conflict: the services fight over feishu's WebSocket connection, resulting in repeated SIGTERM/shutdown loops. **hermes gateway status** shows the warning: `Both user and system gateway services are installed (user + system).`

   **Step-by-step resolution:**
   ```bash
   # 1. Check which is running
   hermes gateway status  # user-level
   sudo systemctl status hermes-gateway  # system-level
   
   # 2. Uninstall the one you don't want (usually the user service)
   hermes gateway uninstall
   
   # 3. Kill any stuck gateway processes (may be in D/Ssl state)
   pkill -f 'hermes.*gateway run' 2>/dev/null
   # If a specific PID won't die:
   kill -9 <PID>
   
   # 4. Reset systemd state and restart
   sudo systemctl reset-failed hermes-gateway 2>/dev/null
   sudo systemctl start hermes-gateway
   
   # 5. Verify no more crash loops
   sleep 10 && sudo systemctl status hermes-gateway | head -10
   # Expected: Active: active (running)
   # Check feishu connected:
   journalctl -u hermes-gateway --since '30 sec ago' --no-pager | grep 'Lark.*connected'
   ```
   
   **Diagnosing stuck "deactivating (stop-sigterm)" state:** If `systemctl status` shows `Active: deactivating (stop-sigterm)` but the PID is still alive (Ssl state), systemd sent SIGTERM but the process didn't exit. The process is stuck — SIGKILL is the only way out. After kill, run `systemctl reset-failed hermes-gateway` before starting again.

10. **Restored API keys may be expired.** `.env` files from backups often carry stale API keys that were rotated after the backup was made. Always test them immediately after restoration. Common pattern:
    ```python
    import requests
    # Test DeepSeek
    r = requests.get('https://api.deepseek.com/v1/models',
                     headers={'Authorization': f'Bearer {key}'})
    if r.status_code == 401:
        print("Key expired — user must provide a replacement")
    ```
