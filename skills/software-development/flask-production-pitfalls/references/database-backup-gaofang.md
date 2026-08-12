# 膏方 V2 数据库备份架构与 2026-08 静默失败实录

## 服务器备份全景（2026-08 现状）

| 对象 | 机制 | 路径 / 保留 | 状态 |
|------|------|------------|------|
| **数据库**（gaofang_v2, PostgreSQL） | crontab `0 3 * * *` → `/workspace/scripts/backup_gaofang_db.sh` | `/workspace/backups/db/gaofang_v2_YYYYMMDD.sql`，保留 15 天自动清理 | 每日自动 |
| **网站代码** | git 仓库 + GitHub 远程（`wangzhaotong7799/drug-distribution-system`） | 手动 commit + `git push origin master` | 手动 |
| 改代码前快照 | 手动 `backup_db.py` / cp 目录 | `gaofang-v2/backups/` | 手动 |
| Hermes 配置 | crontab `0 2 * * *` → `/root/.hermes/scripts/hermes-backup.sh` | `/root/hermes-backup/`，保留 14 份 | 每日自动 |
| Hermes 配置 → GitHub | cron job 每日 23:00 → `daily-backup.sh` | `wangzhaotong-aliyun-hermes` 仓库 | 每日自动 |

> ⚠️ **网站代码仓库本地分支是 `master`（不是 main）**：`git push origin main` 会报 `src refspec main does not match any`，必须 `git push origin master`。push 前先 `git branch` 确认。
> ⚠️ `.gitignore` 已含 `*.bak` / `*.bak-*` 规则，改代码生成的 `.bak` 备份文件不会被误提交。

## 备份脚本关键逻辑（backup_gaofang_db.sh）

```bash
PGPASSWORD=... pg_dump -h localhost -U gaofang_app gaofang_v2 > "$FILEPATH" 2>> backup.log
# 成功判定：$? -eq 0 且文件非空；失败则 rm -f 空文件并 exit 1
# 清理：find ... -mtime +15 -delete
```

**判断要点**：
- 失败时**空文件会被删除** → 备份目录看起来只是"停在旧日期"，没有报错痕迹 → 必须看 `backup.log` 尾部。
- 校验脚本健康：`tail -n 20 /workspace/backups/db/backup.log`，最后一条应是 `✅ 备份成功`；再 `ls -lah /workspace/backups/db/ | tail` 确认日期连续。

## 2026-08-07~12 静默失败实录

- **症状**：8/06 最后一次成功（2.5M），8/07 起每天 `backup.log` 追加：
  ```
  pg_dump: error: query failed: ERROR:  permission denied for sequence doctor_user_doctors_id_seq
  pg_dump: error: query was: SELECT last_value, is_called FROM public.doctor_user_doctors_id_seq
  ```
- **根因**：8/06 RBAC 权限架构重构时用 `su - postgres` 新建了 `groups`、`doctor_user_doctors` 表，sequence owner = postgres；应用用户 `gaofang_app` 无 `USAGE/SELECT` → pg_dump 读 sequence 报错中断，连续 6 天失败。
- **修复**（主人确认后执行）：
  ```bash
  su - postgres -c "psql -d gaofang_v2 -c \"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gaofang_app;\""
  ```
- **验证**：手动 `bash /workspace/scripts/backup_gaofang_db.sh` → 生成 2.6M 文件；`grep "^COPY" ... | grep prescription_records|users` 确认 11 张表全在。
- **预防（未执行，已建议）**：`ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES/SEQUENCES TO gaofang_app;`

## 教训

1. **任何用 postgres 超级用户建表/迁移后，必须验证数据库备份仍正常**——否则备份静默中断多天不被发现。
2. 检查备份健康时看**日志尾部**而非目录文件列表（失败文件被删了）。
3. 同源问题见 SKILL.md Pattern 1 警告："用 postgres 建的表默认无权限"。

## 附：宝塔面板解绑后的 crontab 残留清理（2026-08-12）

宝塔面板已解绑/删除后，root 的 crontab 里仍残留宝塔计划任务条目（脚本路径 `/www/server/cron/<hash>`，无扩展名）。`/www/server/cron/` 目录不存在后，该条目**每晚空跑失败且无日志**（重定向日志也进不存在的目录）。清理方式：

```bash
crontab -l > /root/crontab_backup_$(date +%Y%m%d).txt   # 先备份
crontab -l | grep -v '<宝塔任务hash>' | crontab -       # 删掉失效条目
crontab -l                                              # 确认
```

⚠️ crontab 里的 `LANG=...` / `LC_ALL=...` 是环境变量行不是任务，别误删。本次清理后保留：3:00 数据库备份、周一 6:30 周清理、2:00 Hermes 备份。
