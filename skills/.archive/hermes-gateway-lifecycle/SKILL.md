---
name: hermes-gateway-lifecycle
description: Self-hosted Hermes Gateway systemd service lifecycle — setup, notification scripts, `hermes send` CLI usage, readiness verification, and common failure debugging.
version: 1.0.0
author: Hermes Agent (learned from production ops)
tags: [hermes, gateway, systemd, service, notification, send, lifecycle, dogfood]
---

# Hermes Gateway Lifecycle

Manage a self-hosted Hermes Gateway as a systemd service: startup, notifications,
service health, and scripting.

---

## Systemd Service Setup

### Basic gateway service file (`/etc/systemd/system/hermes-gateway.service`)

```ini
[Unit]
Description=Hermes Agent Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/root/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main gateway run --replace
User=root
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

The `--replace` flag kills any existing gateway process before starting the new one.

### Enable at boot

```bash
systemctl daemon-reload
systemctl enable hermes-gateway
systemctl start hermes-gateway
```

---

## Online Notification Service

Fire a message to the user after the gateway connects to messaging platforms.

### Service file (`/etc/systemd/system/hermes-online-notify.service`)

```ini
[Unit]
Description=Hermes Online Notification
After=hermes-gateway.service
Wants=hermes-gateway.service

[Service]
Type=oneshot
ExecStart=/root/.hermes/scripts/hermes-online-notify.sh
User=root
RemainAfterExit=no

[Install]
WantedBy=multi-user.target
```

### Notification script pattern

```bash
#!/bin/bash
# Wait for gateway startup (typical: ~12s for feishu)
sleep 40

HERMES_BIN="/root/.hermes/hermes-agent/venv/bin/hermes"

# Poll for feishu connection in gateway logs
for i in $(seq 1 30); do
    if pgrep -f "gateway run" >/dev/null && \
       tail -5 /root/.hermes/logs/gateway.log 2>/dev/null | grep -q "feishu connected"; then
        break
    fi
    sleep 3
done

# Send notification
"$HERMES_BIN" send --to feishu:oc_10d032f2e5b7b86d660945627d981888 "message text" 2>/dev/null
```

**Key points:**
- Use absolute paths for venv and binary — systemd strips PATH
- Gateway does NOT have an HTTP server — check readiness via gateway.log, not curl
- The `hermes send` command works independently of the gateway (uses same .env credentials)

---

## `hermes send` CLI Syntax

Important: the syntax is **NOT** `hermes send TARGET message` (this was a common bug).

| Correct | Wrong |
|---------|-------|
| `hermes send --to feishu:target "hello"` | `hermes send feishu:target "hello"` |
| `hermes send -t telegram:-100123 "hello"` | `hermes send telegram:-100123 "hello"` |
| `echo "body" \| hermes send --to slack:#chan` | `hermes send slack:#chan "body"` |

Full syntax:
```bash
hermes send [--to TARGET] [--file PATH] [--subject LINE] [--quiet] [--json] [message]
```

The `--to` flag was introduced in Hermes v0.15.x. Older syntax without the flag no longer works.

### Common uses in scripts

```bash
# Simple notification
hermes send --to feishu:chat_id "Deploy complete ✅"

# Read from file
hermes send --to telegram:-1001234567890 --file /tmp/report.md

# With subject line
hermes send --to discord:#ops --subject "[CI] Build finished" "Tests passed"
```

---

## Gateway Readiness Verification

**DO NOT** use HTTP health checks — the gateway has no HTTP server. It connects to platforms via WebSocket.

### Method 1: Check gateway logs (recommended)

```bash
# Wait for connection confirmation
tail -5 /root/.hermes/logs/gateway.log | grep -q "feishu connected"

# Or look for "Gateway running"
tail -5 /root/.hermes/logs/gateway.log | grep -q "Gateway running with"
```

### Method 2: Check process exists

```bash
pgrep -f "gateway run" >/dev/null && echo "gateway running"
```

### Method 3: Check journal for recent activity

```bash
journalctl -u hermes-gateway --no-pager -n 10
```

---

## Common Failure Modes

### 1. Script exits 127 — Command not found

**Cause:** systemd strips PATH. The script uses a relative path or bare command
name.

**Fix:** Use absolute paths for all binaries, venv, and script paths.

### 2. Script exits 2 — Bad syntax

**Cause:** Wrong `hermes send` arguments (missing `--to` flag).

**Fix:** Use `hermes send --to TARGET "message"`.

### 3. Notification never fires

**Cause:** `sleep` too short (gateway not ready yet), or readiness check uses
curl on a non-existent HTTP port.

**Fix:** Sleep 40s minimum, use log-based readiness check.

### 4. Service starts before gateway

**Cause:** `After=hermes-gateway.service` is set but the gateway's health check
is weak (systemd only checks process start, not platform connection).

**Fix:** Add `Wants=hermes-gateway.service` (not just `After=`), and implement
the log-based polling inside the notification script.

---

## References

- `hermes-agent` skill — full CLI reference, gateway installation, config
- `systematic-debugging/references/debugging-systemd-services.md` — detailed debugging guide with reproduction transcript
- `references/dual-gateway-service-conflict.md` — two systemd services fighting over feishu WebSocket, diagnosis and resolution
