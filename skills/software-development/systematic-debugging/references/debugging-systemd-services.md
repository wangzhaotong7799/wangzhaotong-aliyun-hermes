# Debugging Systemd Services for Hermes Gateway

## Problem Pattern

Systemd-invoked shell scripts run in a stripped-down environment (no interactive PATH, no shell profiles), but the same commands work fine in a terminal. The script exits with a non-zero code, but `2>/dev/null` masks the actual error.

## Diagnostic Workflow

### Step 1: Identify the exit code

```bash
systemctl status <service-name> --no-pager
```

| Exit Code | Meaning | Common Cause |
|-----------|---------|-------------|
| 127 | Command not found | PATH issue — binary doesn't exist or not on PATH |
| 2 | Syntax/argument error | Wrong CLI syntax |
| 1 | Generic error | Script ran but failed internally |

### Step 2: Test each command manually

Extract each command from the script and run it in the terminal with the same absolute paths the script uses. Don't trust `2>/dev/null` — temporarily remove it during debugging.

```bash
# Wrong (script's guess)
hermes send feishu:target "message"

# Right (actual syntax)  
/root/.hermes/hermes-agent/venv/bin/hermes send --to feishu:target "message"
```

### Step 3: Check the journal for hidden output

```bash
journalctl -u <service-name> --no-pager -n 50
```

# Reproduction Transcript (this session)

Two failures of `hermes-online-notify.service`:

1. **Status 127** — `source venv/bin/activate` resolved to wrong path:
   - Script used: `cd /root/.hermes && source venv/bin/activate`
   - Actual venv: `/root/.hermes/hermes-agent/venv/`
   - Fix: absolute path `/root/.hermes/hermes-agent/venv/bin/activate`

2. **Status 2** — Wrong `hermes send` syntax:
   - Script used: `hermes send feishu:target "message"`  
   - Actual syntax: `hermes send --to feishu:target "message"` (v0.15.1+)

## Hermes Gateway Specifics

- **No HTTP server** — The gateway connects to messaging platforms via WebSocket. It does NOT expose an HTTP health check endpoint. Don't use `curl localhost:9090/health`.
- **Readiness check** — Instead of HTTP, grep the gateway log:
  ```bash
  tail -5 /root/.hermes/logs/gateway.log | grep -q "feishu connected"
  ```
- **`hermes send`** — This command does NOT require a running gateway for bot-token platforms (Telegram, Discord, Feishu, etc.). It uses the same `.env` credentials.
- **Service dependency** — `hermes-online-notify` depends on gateway being active. Use `After=hermes-gateway.service` and `Wants=hermes-gateway.service` in the `.service` file.
