---
name: feishu-integration-troubleshooting
description: Troubleshoot and set up Feishu (Lark) integration with Hermes Agent - pairing, gateway configuration, and authorization issues
tags:
  - feishu
  - lark
  - gateway
  - messaging
  - integration
  - troubleshooting
---

# Feishu Integration Troubleshooting

Complete guide to setting up and troubleshooting Feishu (Lark) integration with Hermes Agent. Covers pairing, gateway configuration, authorization issues, and common pitfalls.

## When to Use This Skill

Use this skill when:
- Setting up Feishu integration for the first time
- Encountering "Unauthorized user" errors in gateway logs
- Gateway fails to start after Feishu configuration
- Need to verify pairing status or troubleshoot connection issues

## Prerequisites

1. **Feishu Developer Account**: App ID and App Secret configured
2. **Environment Variables** already set:
   ```bash
   FEISHU_APP_ID=cli_xxxxxxxxxxxx
   FEISHU_APP_SECRET=xxxxxxxxxxxx
   ```

## Step-by-Step Setup

### 1. Verify Pairing Status

Check if pairing code has been successfully processed:

```bash
# Check pairing directory
ls -la ~/.hermes/pairing/

# View pending pairing file
cat ~/.hermes/pairing/feishu-pending.json
```

Expected output shows user details:
```json
{
  "PAIRING_CODE": {
    "user_id": "ou_xxxxxxxxxxxx",
    "user_name": "用户名",
    "created_at": 1776836007.4106693
  }
}
```

**Note**: The pairing code (e.g., `6JWF4ZWT`) becomes the key in the JSON file. If you see your code as a key with user details, pairing was successful.

**Troubleshooting pairing**:
- If file doesn't exist: Pairing hasn't completed or code was invalid
- If file exists but empty: Pairing process was interrupted
- If user_id is present: Pairing successful, proceed to gateway setup

### 2. Check Gateway Status

```bash
# Check if gateway is running
hermes gateway status

# View gateway logs (preferred — has full detail from current session)
tail -30 ~/.hermes/logs/gateway.log

# Also check systemd status for exit codes / signals
systemctl --user status hermes-gateway --no-pager | head -15
```

**Key distinction:** User systemd services (`systemctl --user`) may not write to the system journal (`journalctl`). If `journalctl -u hermes-gateway` returns "No entries", use `~/.hermes/logs/gateway.log` instead — it's always populated when the gateway runs.

### 3. Common Issues and Solutions

#### Issue 1: "Unauthorized user" warnings

**Symptoms**:
```
WARNING gateway.run: Unauthorized user: ou_xxxxxxxxxxxx (用户名) on feishu
WARNING gateway.run: No user allowlists configured. All unauthorized users will be denied.
```

**Understanding the issue**: Even with successful pairing, users need explicit authorization to interact with the gateway. This is a security feature.

**Solution**: Configure user authorization:

1. **Option A (Recommended)**: Add specific user to allowlist in `.env`:
   ```bash
   # Edit .env file and add:
   FEISHU_ALLOWED_USERS=ou_xxxxxxxxxxxx
   ```

2. **Option B**: Allow all users (use with caution for testing):
   ```bash
   # Edit .env file and add:
   GATEWAY_ALLOW_ALL_USERS=true
   ```

3. **Option C**: Platform-specific allow all (more secure than global):
   ```bash
   # Edit .env file and add:
   FEISHU_ALLOW_ALL_USERS=true
   ```

**Important**: After modifying `.env`, you must restart the gateway:
```bash
hermes gateway restart
# OR
systemctl --user restart hermes-gateway
```

**Verification**: Check gateway logs after restart:
```bash
journalctl -u hermes-gateway --since "1 minute ago" | grep -i "allow"
```
Should show gateway reading the new configuration.

#### Issue 2: Gateway fails to start (Python version)

**Symptoms**: Gateway exits with status 75 or Python compatibility errors like:
```
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

**Check Python version**:
```bash
python3 --version
```

**Solution**: Ensure Python 3.8+ is available:

```bash
# Check for newer Python versions
which python3.11 || which python3.10 || which python3.9 || which python3.8

# The gateway should use the virtual environment's Python
cd ~/.hermes/hermes-agent
./venv/bin/python --version

# If system Python is too old (3.6), the gateway service may fail
# Check the actual error in logs:
journalctl -u hermes-gateway --since "1 minute ago" | tail -20
```

**Additional Fix**: If gateway fails due to Python 3.6 compatibility:
1. Check if the service is using the correct Python
2. Manually start gateway with the venv Python for debugging:
   ```bash
   cd ~/.hermes/hermes-agent
   ./venv/bin/python -m hermes_cli.main gateway run --replace 2>&1 | head -50
   ```

#### Issue 3: No messaging targets found

**Symptoms**: `send_message` returns "No messaging platforms connected"

**Solution**: Verify gateway is connected to Feishu:

```bash
# Check gateway state file
cat ~/.hermes/gateway_state.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data.get('platforms', {}).get('feishu', {}), indent=2))"
```

Should show:
```json
{
  "state": "connected",
  "error_code": null,
  "error_message": null,
  "updated_at": "2026-04-22T05:29:24.970706+00:00"
}
```

**Important**: The gateway state file is stale once the gateway is killed/restarted. If `state` shows "connected" but the gateway is down, the file wasn't updated before exit. Always verify with systemd status first.

#### Issue 4: Gateway killed (SIGKILL) — service died unexpectedly

**Symptoms**:
```bash
systemctl --user status hermes-gateway --no-pager | head -10
```
Shows:
```
Active: failed (Result: signal) since ...
Main PID: 258125 (code=killed, signal=KILL)
... Failed with result 'signal'.
```

**Root causes**:
1. **OOM Killer** — If memory is exhausted, the kernel sends SIGKILL to the largest process. Check `dmesg | grep -i oom` for evidence.
2. **Collateral damage** — Another operation (e.g., a shell script, `hermes gateway restart` from a running CLI session) may kill child processes that include the gateway. Look for "Shutdown diagnostic — other hermes processes running" in `~/.hermes/logs/gateway.log` to see what was running alongside.
3. **Systemctl kill cascade** — When systemd receives a stop/restart command, it sends SIGTERM then SIGKILL to the main process and all child processes.

**Diagnostic steps**:
```bash
# 1. Check for OOM events
dmesg | grep -i "oom\|killed process" | tail -5

# 2. Read the gateway log around the crash time
grep -n "SIGTERM\|SIGINT\|Shutdown diagnostic\|signal=KILL" ~/.hermes/logs/gateway.log | tail -10

# 3. Check if .env credentials survived (see Issue 5)
```

**Resolution**:
```bash
# Simply restart — the gateway will recover
systemctl --user restart hermes-gateway

# Then verify it's running and check for platform connection
sleep 3 && systemctl --user status hermes-gateway --no-pager | head -5
tail -10 ~/.hermes/logs/gateway.log
```

#### Issue 5: Gateway starts but says "No messaging platforms enabled"

**Symptoms** in `~/.hermes/logs/gateway.log`:
```
WARNING gateway.run: No messaging platforms enabled.
```

The gateway runs but reports no platforms. Root cause: **Feishu credentials are missing from `~/.hermes/.env`**.

**When this happens**:
- `.env` gets overwritten during other operations (e.g., CLI setup wizards, config changes)
- `.env` gets truncated by `write_file` operations with incomplete content
- Manual editing accidentally removes the Feishu lines

**Required environment variables in `.env`**:
```bash
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxx
GATEWAY_ALLOW_ALL_USERS=true        # or FEISHU_ALLOWED_USERS=ou_xxxxxxxxxxxx
```

**Resolution**:
```bash
# 1. Check what's actually in .env
cat ~/.hermes/.env

# 2. If Feishu vars are missing, add them. Get credentials from:
#    - Feishu Developer Console: https://open.feishu.cn/app
#    - Backup at ~/.hermes/.env.bak or similar
#    - Or re-create the Feishu app if lost

# 3. Restart gateway after fixing
systemctl --user restart hermes-gateway
sleep 3 && tail -10 ~/.hermes/logs/gateway.log
```

**Expected success log**:
```
INFO gateway.run: Enabled platforms: feishu
[Lark] [INFO] connected to wss://msg-frontier.feishu.cn/ws/v2?
```

**Prevention**: Keep a backup of Feishu credentials in a dedicated config directory (e.g., `~/.hermes/hermes_config/.env.backup` or a git-tracked config repo) so they can be restored if `.env` is overwritten.

### 4. Manual Gateway Start (Debug Mode)

If automatic startup fails, run gateway manually for debugging:

```bash
# Stop systemd service
systemctl --user stop hermes-gateway

# Start manually with debug output
cd ~/.hermes/hermes-agent
./venv/bin/python -m hermes_cli.main gateway run --replace
```

Look for connection success message:
```
[Lark] [INFO] connected to wss://msg-frontier.feishu.cn/ws/v2?...
```

**Common manual start issues**:
1. **ModuleNotFoundError**: If you see `ModuleNotFoundError: No module named 'yaml'`, the virtual environment may not be activated or dependencies missing
2. **Python version errors**: If using system Python 3.6, switch to venv Python
3. **Permission errors**: Ensure you have read/write access to `~/.hermes/` directory

**Alternative manual start** (if venv Python has issues):
```bash
# Use absolute path to venv Python
/root/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main gateway run --replace
```

### 5. Testing the Connection

Once gateway is running:

1. **Check service status**:
   ```bash
   systemctl --user status hermes-gateway
   ```

2. **Monitor gateway logs**:
   ```bash
   # Follow logs for 10 seconds
   timeout 10 journalctl -u hermes-gateway -f
   ```

3. **Send test message from Feishu**:
   - Open Feishu app
   - Find Hermes Agent bot
   - Send message: "测试" or "hello"

### 6. Complete Verification

Run comprehensive check:

```bash
#!/bin/bash
echo "=== Feishu Integration Check ==="

# 1. Check pairing
echo "1. Pairing status:"
if [ -f ~/.hermes/pairing/feishu-pending.json ]; then
    echo "   ✓ Pairing file exists"
    cat ~/.hermes/pairing/feishu-pending.json | python3 -c "import sys, json; data=json.load(sys.stdin); print('   Users:', list(data.keys()))"
else
    echo "   ✗ No pairing file"
fi

# 2. Check gateway
echo "2. Gateway status:"
if systemctl --user is-active hermes-gateway >/dev/null 2>&1; then
    echo "   ✓ Gateway is running"
else
    echo "   ✗ Gateway is not running"
fi

# 3. Check connection
echo "3. Feishu connection:"
if [ -f ~/.hermes/gateway_state.json ]; then
    CONNECTION=$(cat ~/.hermes/gateway_state.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('platforms', {}).get('feishu', {}).get('state', 'unknown'))" 2>/dev/null)
    echo "   Connection state: $CONNECTION"
fi

echo "=== Check Complete ==="
```

### 7. Sending Messages: open_id vs chat_id

**Key distinction when using `send_message(target="feishu:...")`:**
- `feishu:ou_<open_id>` → ❌ Error `[230001] invalid receive_id`
- `feishu:oc_<chat_id>` → ✅ Works

The user's pairing info stores their **open_id** (`ou_` prefix), but `send_message` requires a **chat_id** (`oc_` prefix) — even for DMs.

**How to find the correct chat_id:**
```bash
cat ~/.hermes/channel_directory.json
# Look under platforms.feishu — the first entry is your DM chat:
# {
#   "id": "oc_xxxxxxxxxxxx",
#   "type": "dm"
# }
```

**Test before sending important messages:**
Send a short test message first with the chat_id before sending long reports or file links. This avoids losing work when the target format is wrong.

**Note:** For group chats (delivery targets like `oc_99961a56e530e89f7e369cd6ecb50218` in cron jobs), the Bot must be added to the group first, or you'll get error `[230002] Bot/User can NOT be out of the chat.`

## Common Pitfalls

1. **Python Version**: Hermes Agent requires Python 3.8+. System Python 3.6 will fail.
2. **Virtual Environment**: Gateway should use the venv Python, not system Python.
3. **User Authorization**: New users need to be added to allowlist via `FEISHU_ALLOWED_USERS`.
4. **Service Permissions**: User systemd services may need linger enabled.
5. **Network Connectivity**: Ensure outbound connections to Feishu servers are allowed.
6. **`.env` file integrity**: Feishu credentials in `.env` can be silently lost when:
   - Another tool/command overwrites `.env` with a template or incomplete content
   - The `write_file` tool truncates the file before writing new content
   - A setup wizard regenerates `.env` without preserving existing entries
   **Mitigation**: Keep credentials in a version-controlled backup config directory.
7. **Gateway.log vs journalctl**: For user-systemd services, `journalctl --user` may return "No entries". Always use `~/.hermes/logs/gateway.log` as the primary log source.
8. **Stale gateway_state.json**: The state file is not updated on crash/kill. If it shows "connected" but the gateway is down, the data is stale. Trust `systemctl --user status` over the state file.

## Troubleshooting Flowchart

```
Start → Check pairing file → Exists? → No → Need new pairing code
                    ↓ Yes
            Check gateway status → 
                Running? → No → Check systemd result → 
                    signal=KILL (SIGKILL) → Check OOM / collateral damage → Restart
                    exit code 75 → Python version issue → Use venv
                    Stopped → Start gateway → Verify credentials in .env
                ↓ Yes
            Check log for platform → 
                "No messaging platforms enabled" → Feishu credentials missing from .env → Add them → Restart
                "Enabled platforms: feishu" → Check connection state
                ↓
            Check connection state → 
                "connected to wss://msg-frontier.feishu.cn" → ✓
                "Unauthorized user" → Configure allowlist → Restart
                Anything else → Check logs for specific error
                    ↓
            Test with Feishu message → Works? → No → Check authorization
                    ↓ Yes
            Integration Complete
```

## Reference Files

- `references/credential-loss-sigkill-recovery.md` — Full diagnostic walkthrough of a real incident where the gateway was killed by SIGKILL and Feishu credentials were lost from `.env`. Useful as a concrete pattern to follow when investigating "Feishu not working".

## Related Skills

- `github-auth` - Similar OAuth/API key configuration patterns
- `send_message` - General messaging platform integration