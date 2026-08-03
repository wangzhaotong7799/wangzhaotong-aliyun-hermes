---
name: gaofang-data-analysis
description: 膏方管理系统V2数据库查询与分析 — 连接PostgreSQL、按业务口径统计上传/发放/患者数、常见聚合查询模式
tags: [gaofang, database, postgresql, sql, analytics, business-intelligence]
category: software-development
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [gaofang, database, postgresql, analytics, sql]
    category: software-development
---

# 膏方数据库分析

膏方管理系统 V2（Flask + PostgreSQL）的业务数据库查询技能。覆盖月报统计、患者去重口径、状态分发等常见分析需求。

---

## 数据库连接

```bash
# 通过 postgres 系统用户直连
su - postgres -c "psql -d gaofang_v2 -c 'SQL 语句'"

# 或用完整连接参数（用户名 gaofang_app）
psql -h localhost -p 5432 -U gaofang_app -d gaofang_v2
```

**注意：** 数据库用户是 `gaofang_app`，不是 `gaofang_v2`。

---

## 核心表结构

### prescription_records（处方记录 —— 主要分析表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | integer | 主键 |
| `date` | date | 处方日期 |
| `prescription_id` | varchar(50) | 处方编号（唯一） |
| `patient_name` | varchar(50) | 患者姓名 |
| `gender` | varchar(10) | 性别 |
| `age` | integer | 年龄 |
| `prescription_type` | varchar(100) | 处方类型 |
| `quantity` | integer | **料数**（分析核心指标） |
| `doctor` | varchar(50) | 医生 |
| `assistant` | varchar(50) | 医助 |
| `status` | varchar(20) | 当前状态（见下） |
| `is_prescription_sent` | varchar(10) | 是否已传方（已传方/空） |
| `patient_phone` | varchar(20) | 手机号（允许空） |
| `decoction_material_type` | varchar(50) | 料型（全料） |
| `decoction_prescription_type` | varchar(50) | 方型（协定方/辩证方） |
| `decoction_weight` | varchar(10) | 料重 |
| `payment_status` | varchar(20) | 支付状态 |
| `shipping_time` | date | 邮寄时间 |
| `pickup_date` | date | 取药时间 |
| `follow_up_status` | varchar(20) | 复诊总体状态（默认'待回访'，超40天自动转'已停服'） |
| `follow_up_1_status` / `follow_up_1_date` | varchar(20) / date | 第1次复诊状态/日期 |
| `follow_up_2_status` / `follow_up_2_date` | varchar(20) / date | 第2次复诊状态/日期 |
| `follow_up_3_status` / `follow_up_3_date` | varchar(20) / date | 第3次复诊状态/日期 |
| `created_at` | timestamp | 创建时间 |
| `updated_at` | timestamp | 更新时间 |

### status_change_logs（状态变更日志）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | integer | 主键 |
| `patient_name` | varchar(50) | 患者姓名 |
| `prescription_id` | varchar(50) | 处方编号 |
| `old_status` | varchar(20) | 变更前状态 |
| `new_status` | varchar(20) | 变更后状态 |
| `change_reason` | varchar(255) | 变更原因 |
| `operator` | varchar(50) | 操作人 |
| `changed_at` | timestamp | 变更时间 |

### 索引

- `ix_prescription_records_date` — date 上有索引，按月统计时利用索引
- `ix_prescription_records_status` — status 上有索引，按状态过滤时利用
- `ix_prescription_records_prescription_id` — UNIQUE 索引，prescription_id 唯一

---

## 状态字典

| 状态值 | 含义 | 是否已发放 |
|:------:|:----:|:---------:|
| 已取 | 患者已到店取药 | ✅ 是 |
| 已邮寄 | 已快递寄出 | ✅ 是 |
| 未取 | 未到店取药 | ❌ 否 |
| 欠药 | 欠药状态（导入默认值） | ❌ 否 |
| 已退药 | 已退药 | ❌ 否 |

**导入默认状态：** 从外部系统导入时，默认为「欠药」，`is_prescription_sent` 默认为「已传方」，`assistant` 为空时用「-」占位。

---

## ⚠️ 铁律：患者去重口径

**这是用户明确纠正过的核心规则，必须严格遵守：**

> 统计「患者人数」时，必须按 `(patient_name + age + patient_phone)` 去重。
> 一个患者可能多次购买（多条记录对应一个人）。
> 不能直接 `COUNT(*)` — 83 条记录 ≠ 83 个患者。

### 标准去重 SQL 写法

```sql
-- 按月统计独立患者人数
SELECT 
  to_char(date, 'YYYY-MM') AS 月份,
  COUNT(DISTINCT (
    patient_name || '|' || age::text || '|' || COALESCE(patient_phone, '')
  )) AS 患者人数,
  SUM(quantity) AS 总料数,
  COUNT(*) AS 总条数
FROM prescription_records
WHERE date >= '2026-01-01' AND date < '2026-07-01'
GROUP BY 月份
ORDER BY 月份;
```

### 分类统计时的去重

统计"已取患者人数"：

```sql
SELECT 
  to_char(date, 'YYYY-MM') AS 月份,
  COUNT(DISTINCT (
    patient_name || '|' || age::text || '|' || COALESCE(patient_phone, '')
  )) AS 已取患者人数,
  SUM(quantity) AS 已取料数
FROM prescription_records
WHERE date >= '2026-01-01' AND date < '2026-07-01'
  AND status = '已取'
GROUP BY 月份
ORDER BY 月份;
```

### 处理空电话

`patient_phone` 允许为空（`NULL` 或空字符串）。用 `COALESCE(patient_phone, '')` 统一处理，防止 NULL 破坏字符串拼接。

---

## 常见分析模式

### 1. 月报统计（上传+发放+未发放）

```sql
WITH monthly AS (
  SELECT 
    to_char(date, 'YYYY-MM') AS 月份,
    patient_name,
    age,
    COALESCE(patient_phone, '') AS phone,
    quantity,
    status,
    CASE WHEN status IN ('已取', '已邮寄') THEN 1 ELSE 0 END AS 已发放标记
  FROM prescription_records
  WHERE date >= '2026-01-01' AND date < '2026-07-01'
)
SELECT 
  月份,
  COUNT(DISTINCT (patient_name || '|' || age::text || '|' || phone)) AS 上传患者数,
  COUNT(*) AS 上传条数,
  SUM(quantity) AS 上传料数,
  COUNT(DISTINCT CASE WHEN 已发放标记=1 THEN (patient_name || '|' || age::text || '|' || phone) END) AS 发放患者数,
  SUM(CASE WHEN 已发放标记=1 THEN quantity ELSE 0 END) AS 发放料数
FROM monthly
GROUP BY 月份
ORDER BY 月份;
```

### 2. 按状态分布

```sql
SELECT 
  to_char(date, 'YYYY-MM') AS 月份,
  status,
  COUNT(*) AS 数量,
  SUM(quantity) AS 料数
FROM prescription_records
WHERE date >= '2026-01-01' AND date < '2026-07-01'
GROUP BY 月份, status
ORDER BY 月份, status;
```

### 3. 多次购买/复购分析

多次购买 = 同一患者在同一个月中出现多条记录（按 name+age+phone 去重后 count > 1）。

```sql
WITH patient_monthly AS (
  SELECT 
    to_char(date, 'YYYY-MM') AS 月份,
    patient_name,
    age,
    COALESCE(patient_phone, '') AS phone,
    SUM(quantity) AS 个人总料数,
    COUNT(*) AS 个人总条数
  FROM prescription_records
  WHERE date >= '2026-01-01' AND date < '2026-07-01'
  GROUP BY 月份, patient_name, age, phone
)
SELECT 
  月份,
  COUNT(*) AS 总患者数,
  COUNT(*) FILTER (WHERE 个人总条数 > 1) AS 多次购买人数,
  ROUND(AVG(个人总料数)::numeric, 2) AS 人均料数,
  MAX(个人总料数) AS 单人最高料数
FROM patient_monthly
GROUP BY 月份
ORDER BY 月份;
```

### 4. 医生/医助维度的业务量统计

```sql
SELECT 
  doctor,
  COUNT(DISTINCT (patient_name || '|' || age::text || '|' || COALESCE(patient_phone, ''))) AS 患者数,
  COUNT(*) AS 处方数,
  SUM(quantity) AS 总料数
FROM prescription_records
WHERE date >= '2026-01-01' AND date < '2026-07-01'
GROUP BY doctor
ORDER BY 总料数 DESC;
```

---

## 复诊/回访模块

复诊列表（GET /api/follow-up）、服用提醒（GET /api/reminders）、更新复诊（POST /api/follow-up/update）、停服（POST /api/follow-up/stop）、复诊统计（/api/follow-up/statistics + /stats/follow-up-stats）的**实施后基线**（2026-08-03 已上线：新表 follow_up_records 方案B、每月3次复诊 10~19/20~29/30~39 循环+顺延规则、权限统计、PWA/PC 改版、PC 保存 bug 已修、PWA 统计 Tab 改版、PWA 搜索栏+首拼搜索（后端返回 pinyin/pinyin_initial）、停服/已停药自动状态灯（前端按 end_date / end_date+40 计算颜色，不再手动编辑）、admin 用户管理 ID 不匹配 bug 已修），以及实施陷阱（PostgreSQL GRANT 权限、测试 token 用真实 user_id、schedule 边界缓冲、JS 中文引号、**并发唯一键冲突→"Unexpected token '<'"→UPSERT+节流锁+单事务提交 146s→0.06s**、**Nginx expires 7d immutable 静态缓存→cache-busting（?v= 版本号/时间戳）**、处方类型/医生快照字段、**统计必须基于全量数据不能基于筛选后子集**、**getElementById ID 与 HTML 不匹配→"Cannot set properties of null"→ID 交叉核对脚本**、**前端日期比较用 new Date(y,m-1,d) 本地构造避免时区偏移**），全部见 `references/followup-module.md`。

⚠️ **生产代码改动工作流（主人操作习惯）**：
1. 先读逻辑 → 2. **先备份当前逻辑**（`backups/followup_logic_backup_YYYYMMDD_HHMMSS/`，按 backend/ pc/ mobile/ 分目录避免 PC/PWA 同名 JS 互相覆盖；cp 后 md5 校验）→ 3. 列方案让主人确认 → 4. 才动手改 → 5. 改后重启 Gunicorn 验证。
- 备份注意：`static/js/` 与 `static/mobile/js/` 下存在**同名文件**（如 page-followup.js），cp 到同一目录会互相覆盖，必须分目录。
- 项目是 git 仓库（master），备份前先 `git status` 确认改动基线。

---

- 应用路径：`/workspace/projects/drug-distribution-system/gaofang-v2/`
- 日志路径：`/workspace/projects/drug-distribution-system/gaofang-v2/logs/`
- Gunicorn service：`gaofang-v2-fusion.service`
- 每日06:00 Gunicorn HUP热重启（cronjob）
- 每日03:00数据库备份脚本：`/workspace/scripts/backup_gaofang_db.sh`
