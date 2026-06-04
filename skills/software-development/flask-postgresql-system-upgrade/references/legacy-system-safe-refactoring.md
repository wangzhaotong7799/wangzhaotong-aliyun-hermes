# 系统安全重构方法论 — 遗留系统升级流程

> 吸收自 `legacy-system-safe-refactoring`（2026-05 合并）
> 本节补充 flask-postgresql-system-upgrade 主文档未详细展开的安全重构方法论。

## 阶段 0: 完整功能清单梳理（最关键）

### API 接口枚举
```bash
grep -n "@app.route\|@router\." app.py | sort
```

### 前端功能逆向
```bash
grep -oE 'function\s+[a-zA-Z_]+|async function\s+[a-zA-Z_]+' index.html | sort -u
```

### 数据库结构分析
```python
import sqlite3
conn = sqlite3.connect('your.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
for table in cursor.fetchall():
    cursor.execute(f"PRAGMA table_info({table[0]})")
    print(cursor.fetchall())
```

## 并行部署与灰度切流

```bash
# 双端口运行
# V1 (port 5000), V2 (port 80)
# 完全验证后切换

# 一键回滚
systemctl stop gaofang-v2
pkill -f "gunicorn.*wsgi"
```

## 中断恢复机制

使用检查点文件恢复中断的重构任务：

```bash
# .upgrade_checkpoint
STATUS=READY_TO_START_NEXT_PHASE
LAST_COMPLETED_TASK=T2-05
NEXT_TASK=T2-06
```

## 关键经验教训

1. **阶段 0（功能清单）需占总工期 20-30%**
2. **不要过度优化** — 先追求完全兼容，再考虑更优雅
3. **自动化测试是必须的**
