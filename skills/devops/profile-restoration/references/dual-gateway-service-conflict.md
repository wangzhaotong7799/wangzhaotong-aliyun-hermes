# Dual Gateway Service Conflict — Diagnosis & Resolution

## Symptoms

After restoring a Hermes profile from backup, the gateway enters a restart loop:

```
⚠️ Gateway shutting down — Your current task will be interrupted.
(Repeated every few seconds)
```

`hermes gateway status` shows:

```
● hermes-gateway.service
   Active: activating (auto-restart)
  Process: ... (code=exited, status=0/SUCCESS)
⚠ Both user and system gateway services are installed (user + system).
```

The gateway log (`~/.hermes/logs/gateway.log`) shows feishu connecting successfully, then immediately receiving SIGTERM.

## Root Cause

Two systemd services are installed for the same gateway:

| Type | Service file | Management command |
|------|-------------|-------------------|
| **User** | `~/.config/systemd/user/hermes-gateway.service` | `hermes gateway ...` |
| **System** | `/etc/systemd/system/hermes-gateway.service` | `sudo systemctl ... hermes-gateway` |

Only one can hold the feishu WebSocket connection. The two services fight — one connects, the other SIGTERMs it, systemd auto-restarts it, and the cycle repeats.

## Diagnosis

```bash
# Check user-level
hermes gateway status | head -5

# Check system-level
sudo systemctl status hermes-gateway | head -5

# Look for the "Both user and system" warning
hermes gateway status 2>&1 | grep "Both user and system"
```

## Resolution

### Option A: Remove user service, keep system (recommended for this environment)

```bash
# 1. Remove the user service
hermes gateway uninstall

# 2. Kill any stuck gateway processes (may be in D/Ssl state and unkillable by SIGTERM)
pkill -f 'hermes.*gateway run' 2>/dev/null
# Check for survivors
ps aux | grep 'hermes.*gateway' | grep -v grep
# Force-kill any stuck ones
kill -9 <STUCK_PID>

# 3. Reset systemd state and restart
sudo systemctl reset-failed hermes-gateway 2>/dev/null
sudo systemctl start hermes-gateway

# 4. Verify
sleep 10
sudo systemctl status hermes-gateway | head -10
# Expected: Active: active (running) since ...
```

### Option B: Remove system service, keep user

```bash
sudo hermes gateway uninstall --system
hermes gateway restart
```

## Stuck "deactivating" State

Sometimes after killing processes, systemd shows:

```
Active: deactivating (stop-sigterm) since ...; 41s ago
Main PID: <PID> (hermes)
```

Despite the process already being killed, systemd is waiting for it to acknowledge the stop signal. Fix:

```bash
sudo systemctl reset-failed hermes-gateway
sudo systemctl start hermes-gateway
```

## Prevention

Check for this condition immediately after restoring a profile. The `hermes gateway status` command always warns about dual services — don't ignore this warning.
