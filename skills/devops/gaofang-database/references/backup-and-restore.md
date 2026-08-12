# 膏方 V2 数据库备份与恢复 — 实操手册

> 记录于 2026-08-12（连续 6 天备份失败排查修复后沉淀）。服务器：阿里云 39.107.78.58，同机运行 Flask+Gunicorn+Nginx+PostgreSQL+Hermes。

## 1. 备份机制全貌

| 层 | 任务 | 触发 | 脚本 | 产物 | 保留 |
|---|---|---|---|---|---|
| 数据库 | 每日全量备份 | crontab `0 3 * * *` | `/workspace/scripts/backup_gaofang_db.sh` | `/workspace/backups/db/gaofang_v2_YYYYMMDD.sql`（pg_dump 纯 SQL，COPY 格式） | 15 天 |
| 数据库 | 手动按需 | 无定时 | `gaofang-v2/backup_db.py` | `gaofang-v2/backups/gaofang_v2_*.sql.gz`（gzip） | 手动 |
| 数据库 | 改代码前快照 | 手动 | cp/脚本 | `gaofang-v2/backups/`（followup_*/gaofang_code_*.tar.gz 等） | 手动 |
| Hermes | 配置全量 | crontab `0 2 * * *` | `/root/.hermes/scripts/hermes-backup.sh` | `/root/hermes-backup/hermes-backup-*.tar.gz` | 14 天 |
| Hermes | 配置→GitHub | crontab `0 23 * * *` | `~/.hermes/scripts/daily-backup.sh` | wangzhaotong-hermes 仓库（config/skills/memories/SOUL） | 归档 7 天 |
| 网站代码 | git | 手动 | git commit+push | GitHub drug-distribution-system（**分支是 master 不是 main**） | 永久 |

当前系统 crontab（2026-08-12 清理宝塔残留后）：
```
LANG=en_US.UTF-8
LC_ALL=en_US.UTF-8
0 3 * * * /workspace/scripts/backup_gaofang_db.sh
30 6 * * 1 /workspace/scripts/weekly_cleanup.sh
0 2 * * * /root/.hermes/scripts/hermes-backup.sh > /root/hermes-backup/backup-cron.log 2>&1
```

## 2. 备份失败排查（关键案例）

### 症状与根因
- 2026-08-07 起连续 6 天 `gaofang_v2_YYYYMMDD.sql` 缺失
- `backup.log` 尾部：`pg_dump: error: query failed: ERROR: permission denied for sequence doctor_user_doctors_id_seq`
- 根因：8-06 RBAC 重构用 **postgres 超级用户**新建了 `groups`、`doctor_user_doctors` 表，其序列 owner=postgres，备份用的 `gaofang_app` 无 USAGE/SELECT → pg_dump 中断
- 脚本 `if [ $? -eq 0 ] && [ -s "$FILEPATH" ]` 失败后 `rm -f` 删文件 → 目录里看不出痕迹，**只在 backup.log 有记录，无告警**

### 诊断步骤
1. `ls -lah /workspace/backups/db/` — 找缺失的日期文件
2. `tail -20 /workspace/backups/db/backup.log` — **这是关键**，失败原因都在这
3. 查序列 owner：`su - postgres -c "psql -d gaofang_v2 -c \"SELECT c.relname, pg_get_userbyid(c.relowner) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='S' AND c.relname LIKE '%_id_seq' AND pg_get_userbyid(c.relowner)='postgres';\""`
   — 列出的就是缺权限的序列

### 修复
```bash
# 序列授权（本次根因）
su - postgres -c "psql -d gaofang_v2 -c \"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gaofang_app;\""
# 表授权（新表场景同样需要）
su - postgres -c "psql -d gaofang_v2 -c \"GRANT ALL ON ALL TABLES IN SCHEMA public TO gaofang_app;\""
```

### 预防（已配置，防复发）
```sql
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO gaofang_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO gaofang_app;
```
验证：`SELECT defaclobjtype, array_to_string(defaclacl, ',') FROM pg_default_acl;`
期望：`r` → `gaofang_app=arwdDxt/postgres`，`S` → `gaofang_app=rwU/postgres`

### 修复后验证
```bash
bash /workspace/scripts/backup_gaofang_db.sh
grep -c "^COPY" /workspace/backups/db/gaofang_v2_$(date +%Y%m%d).sql   # 应 >10（11 张表）
grep "^COPY" /workspace/backups/db/gaofang_v2_$(date +%Y%m%d).sql | grep -E "prescription_records|users|groups|doctor_user_doctors"
```
注意：pg_dump 默认 COPY 格式，`grep "INSERT INTO"` 为 0 是**正常**的，不要误判。

## 3. 恢复流程

### 方式 A：backup_db.py 恢复（gzip 备份，自动识别格式）
```bash
cd /workspace/projects/drug-distribution-system && python3 -c "
from backup_db import restore_database
restore_database('gaofang_v2_YYYYMMDD_HHMMSS.sql.gz')
"
```
脚本自动判断：含 `CREATE TABLE` → 先 DROP 再恢复（pg_dump 格式）；否则 TRUNCATE+INSERT（老格式）。

### 方式 B：手动 psql 恢复（每日 .sql 备份）
```bash
# 如需清空旧数据（pg_dump 格式本身带 DROP TABLE IF EXISTS，可跳过）
PGPASSWORD=gaofang_password psql -h localhost -U gaofang_app -d gaofang_v2 < /workspace/backups/db/gaofang_v2_YYYYMMDD.sql
```

## 4. 教训
- **备份失败不告警**：backup_gaofang_db.sh 只写日志不通知。巡检备份健康度必须 `tail backup.log`。
- **postgres 超级用户建表 = 应用用户失权**：任何 DBA 操作（建表/加序列）后立即授权，或依赖已配置的 ALTER DEFAULT PRIVILEGES。
- **crontab 变更先备份**：`crontab -l > /root/crontab_backup_<date>.txt`。
