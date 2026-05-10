# Finding the Actual Project Path

## When the Stated Path Doesn't Exist

A common situation in server operations: the task description says the project is at path `A`, but `A` doesn't exist or is wrong. Here's how to find the real path systematically.

### Method 1: Check Systemd Service Files (Fastest)

If the project runs as a systemd service, the service file contains the `WorkingDirectory`:

```bash
# List all matching service files
ls /etc/systemd/system/*.service

# Read the relevant one
cat /etc/systemd/system/<service-name>.service
# Look for: WorkingDirectory=/actual/path
```

This is the **most reliable** method because systemd MUST have the correct path to start the service.

### Method 2: Check Nginx Config

If the app is behind Nginx (common in production), the Nginx site config reveals the project root and upstream port:

```bash
# Find Nginx configs
ls /etc/nginx/sites-enabled/
ls /etc/nginx/conf.d/

# Look for root directive and proxy_pass
cat /etc/nginx/sites-enabled/<config>
```

### Method 3: Check Running Processes

```bash
# Find the gunicorn/uwsgi process and its working directory
ps aux | grep gunicorn
# Look at the cwd or command-line args for paths

# More detailed
cat /proc/<PID>/cwd 2>/dev/null || readlink -f /proc/<PID>/cwd
```

### Method 4: Search Common Project Locations

```bash
# Search for the project by name
find / -maxdepth 5 -name "<project-name>" -type d 2>/dev/null

# Search for specific files (e.g., app.py, manage.py)
find / -maxdepth 5 -name "app.py" -path "*<project-name>*" 2>/dev/null
```

### Method 5: Check Cron Jobs or Script References

If the task runs as a cron job, check the crontab for path hints:

```bash
crontab -l
# Look for WORKING_DIR, cd commands, or script paths
```

## Common Root Paths on Linux Servers

| Context | Typical Base Path |
|---------|-------------------|
| User projects | `/home/<user>/` or `/root/` |
| Workspace projects | `/workspace/` or `/workspace/projects/` |
| Standard web | `/var/www/` |
| Custom deployment | `/opt/` or `/srv/` |

## Example: Path Not Found Resolution

```
Question: Project is at ~/wangzhaotong-hermes/drug-distribution-system/gaofang-v2/
Reality:  Path doesn't exist

Resolution:
1. cat /etc/systemd/system/gaofang-v2*.service → WorkingDirectory=/workspace/projects/...
2. Actual path is /workspace/projects/drug-distribution-system/gaofang-v2/
```

## Pitfall: Relative Paths with ~ Expansion

`~` in task descriptions does **not** automatically expand correctly in all contexts:
- In `find` commands: `find ~/...` works (shell expands)
- In `systemd` service files: `~` is NOT expanded; use absolute paths
- When passed to `execute_code`/`terminal` tools: depends on how the tool handles it

**Always resolve `~` to the absolute path early** when the path matters for `read_file`, `search_files`, or other tools that don't go through a shell.
