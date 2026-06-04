# CentOS/AlmaLinux 8 Python 3.6 环境部署指南

> **吸收自 `centos-python36-deployment`** (2026-05-22 consolidated into `flask-app-startup-troubleshooting`)
>
> Content that overlaps with the parent umbrella (bcrypt compat, JWT bytes, nginx proxy, firewall, Gunicorn/systemd) has been removed. This file preserves CentOS-specific content only.

## Dependency Compatibility Matrix for Python 3.6

Python 3.6 went EOL at end of 2021. On CentOS/AlmaLinux 8 (Python 3.6.8), lock these packages:

| Package | Python 3.6 Version | Python 3.8+ Version | Reason |
|---------|-------------------|-------------------|--------|
| bcrypt | 3.2.2 | 4.x+ | 4.x requires Python 3.8+ and Rust |
| Flask | 2.0.3 | 2.3.x+ | |
| SQLAlchemy | 1.4.46 | 2.0+ | 1.4.x is last supporting 3.6 |
| psycopg2-binary | 2.9.3 | latest | |
| PyJWT | 2.4.0 | 2.x | |
| Werkzeug | 2.0.3 | latest | |
| openpyxl | 3.0.10+ | latest | |

**bcrypt failure pattern on Python 3.6:**
```
Link requires a different Python (3.6.8 not in: '>=3.8')
This package requires Rust >=1.56.0.
```
Fix: `pip3 install 'bcrypt==3.2.2'`

## Python 3.6 → 3.8 Upgrade Guide (EL8 Systems)

### Installation

```bash
# EL8 systems (CentOS 8 / AlmaLinux 8 / Alibaba Cloud Linux 3 / OpenAnolis)
yum install -y python38 python38-devel

# Verify
python3.8 --version   # → Python 3.8.17
python3.8 -m pip install --upgrade pip setuptools wheel
```

### Creating venv

```bash
cd ~/projects/your-app
python3.8 -m venv venv38
source venv38/bin/activate
pip install -r requirements.txt

# Flask version jump note:
# Python 3.6 → pip installs Flask 2.0.3
# Python 3.8 → pip installs Flask 2.3.3 (latest compatible)
# Lock if concerned: Flask==2.0.3
```

### Verification

```bash
# Syntax check (pass = no 3.6→3.8 compatibility issues)
find . -name "*.py" -exec python3.8 -m py_compile {} \; 2>&1 | grep -v "Errors:" | head -5

# Import test
python3.8 -c "
import sys; sys.path.insert(0, '.')
from app import app
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    print(rule.rule, '->', rule.endpoint)
print(f'Total: {len(list(app.url_map.iter_rules()))} routes')
"

# API test
python3.8 app.py &
sleep 2
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080/
```

### Known Upgrade Pitfalls

| Issue | Description | Fix |
|-------|-------------|-----|
| Flask version jump | `>=2.0.0` pulls 2.3.3 | Lock `Flask==2.0.3` or test upgrade |
| venv migration | Old venv interpreter can't point to 3.8 | Must recreate: `python3.8 -m venv venv38` |
| System Python confusion | `python3` may still point to 3.6 | Use full path `python3.8` or activate venv |
| BT panel env | Panel uses independent pyenv (3.7+) | Installing python38 has no conflict |
| psycopg2 | Old version on 3.6 | `psycopg2-binary>=2.9.10` works on 3.8 |

### Alibaba Cloud Linux 3 (OpenAnolis) Notes

EL8-compatible:
- Package manager: `yum` (not `dnf`)
- Repos: `alinux3-module` / `alinux3-updates` / `epel`
- Python 3.8 package: `python38` (in alinux3-module)
- Verified: Python 3.8.17 + Flask 2.3.3 + PostgreSQL 13 + psycopg2 2.9.10

### Production Switch (zero-downtime)

```bash
# Step 1: Test on temp port
python3.8 -m venv venv38 && source venv38/bin/activate && pip install -r requirements.txt
python3.8 app.py --port 8081 &
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/

# Step 2: Kill old, start new
kill $(pgrep -f "python3.6 app.py")
nohup python3.8 app.py > app.log 2>&1 &

# Step 3: Verify
sleep 2 && curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080/
```

### .gitignore for venv directories

```gitignore
# Virtual environments
venv/
venv*/
.venv/
```

Use `venv*/` (not just `venv/`) to catch multiple test envs like `venv38/`, `venv39/`, etc.
