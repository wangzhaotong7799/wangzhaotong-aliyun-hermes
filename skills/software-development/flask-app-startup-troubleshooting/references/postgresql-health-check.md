# PostgreSQL Connection Check for Flask Apps

## Quick Health Check

### Method 1: Via psycopg2 (direct connection)

```python
import psycopg2

conn = psycopg2.connect(
    host=os.environ.get('DB_HOST', 'localhost'),
    port=os.environ.get('DB_PORT', 5432),
    dbname=os.environ.get('DB_NAME', 'app_db'),
    user=os.environ.get('DB_USER', 'app_user'),
    password=os.environ.get('DB_PASSWORD', '')
)
cur = conn.cursor()
cur.execute("SELECT 1")
print("Database connection: OK")
cur.close()
conn.close()
```

### Method 2: Via Flask SQLAlchemy (app context)

```python
from app import create_app
from extensions import db

app = create_app()
with app.app_context():
    db.session.execute("SELECT 1")
    print("Database connection: OK (via SQLAlchemy)")
```

### Method 3: Via Flask app config (standalone script)

```python
import os, sys
sys.path.insert(0, '/path/to/project')

from config import Config
import psycopg2

conn = psycopg2.connect(
    host=Config.DB_HOST,
    port=Config.DB_PORT,
    dbname=Config.DB_NAME,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD
)
```

## Finding DB Credentials

Credentials may be stored in multiple places — try in this order:

1. **Environment variables** — `echo $DB_HOST`, `echo $DB_PASSWORD`
2. **`.env` file** — `cat .env`
3. **`config.py`** — Look for `Config` class with DB settings, including fallback defaults
4. **Systemd service file** — `Environment=` directives may contain DB passwords
5. **Shell startup scripts** — `.bashrc`, `.bash_profile`, `.zshrc`

## Handling Masked Passwords

Sometimes `.env` files show `DB_PASSWORD=***` (the actual value is literally the asterisks, or it's been redacted for display).

**Recovery approaches:**

1. Check `config.py` — the `Config` class may have a fallback:
   ```python
   DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'default_fallback_password'
   ```

2. Try with the fallback password first

3. If that fails, try running as the app user (check systemd `User=`)
   ```bash
   sudo -u app_user python3 -c "import psycopg2; ..."
   ```

## Common Connection Issues

| Symptom | Likely Cause |
|---------|-------------|
| `could not connect to server: Connection refused` | PostgreSQL not running, wrong host/port, or firewall blocking |
| `FATAL: password authentication failed` | Wrong password |
| `FATAL: database "X" does not exist` | DB not created yet |
| `FATAL: no pg_hba.conf entry` | Host auth not configured — check `pg_hba.conf` for `md5` vs `trust` |
| `could not translate host name` | `localhost` not resolving — try `127.0.0.1` |

## Quick PostgreSQL Service Check

```bash
# Check if PostgreSQL is running
systemctl is-active postgresql  || systemctl is-active postgresql-14  || pg_isready

# Check PostgreSQL port
ss -tlnp | grep 5432

# Check PostgreSQL version
psql --version
```
