# Credential Loss + SIGKILL Recovery Pattern

This reference documents a real recovery scenario from May 2, 2026.

## Symptom Pattern

The user reported "飞书连接不上了" (Feishu won't connect). Investigation revealed two independent failures:

### Layer 1: Gateway terminated by SIGKILL

```
systemctl --user status hermes-gateway
→ Active: failed (Result: signal)
→ Main PID: 258125 (code=killed, signal=KILL)
→ Killing process 273099 (bash) with signal SIGKILL.
→ Killing process 273120 (hermes) with signal SIGKILL.
→ ... (7 processes killed in cascade)
```

The gateway log showed:

```
08:55:46  Received SIGTERM/SIGINT — initiating shutdown
08:55:46  Shutdown diagnostic — other hermes processes running:
  hermes gateway stop
  systemctl --user stop hermes-gateway
  bash (hermes gateway start --replace)
08:56:21  Received SIGTERM/SIGINT — initiating shutdown (2nd attempt)
```

**Root cause**: A `hermes gateway stop` + `hermes gateway start --replace` race condition during an unrelated server health check killed the running gateway process and its children.

### Layer 2: `.env` credentials missing

After restarting the killed gateway:

```
~/.hermes/logs/gateway.log:
WARNING gateway.run: No messaging platforms enabled.
```

The `.env` file at `~/.hermes/.env` contained only `DEEPSEEK_API_KEY=***` — all Feishu credentials had been removed.

**Root cause**: Unknown (likely `.env` was overwritten by another operation). Credentials known to have existed from April 22 configuration:
- `FEISHU_APP_ID=cli_a93fdb2074789bc7`
- `FEISHU_APP_SECRET=***` (was set)
- `GATEWAY_ALLOW_ALL_USERS=true`

## Recovery Steps

1. Restart gateway to confirm the issue:
   ```bash
   systemctl --user restart hermes-gateway
   tail -10 ~/.hermes/logs/gateway.log
   # → "No messaging platforms enabled"
   ```

2. Check `.env`:
   ```bash
   cat ~/.hermes/.env
   # → Only DEEPSEEK_API_KEY present
   ```

3. Restore credentials (requires user to provide App ID and App Secret again).

## Key Diagnostic Points

- **gateway.log** path: `~/.hermes/logs/gateway.log` (NOT journalctl for user-systemd services)
- **stale state file**: `~/.hermes/gateway_state.json` showed `"state":"connected"` even though gateway was killed — the file is not updated on crash
- **collateral damage**: Running `hermes` CLI commands while gateway is active can trigger systemd stop/start cascades that kill the gateway
