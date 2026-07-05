---
name: gaofang-monthly-report
description: 膏方管理系统月度统计报告 — 按导入时间统计每月上传患者人数、总料数、发放患者数、发放料数
version: 1.0.0
author: wangzhaotong
tags: [gaofang, monthly-report, statistics, database]
---

# 膏方月度统计报告

每月1日自动运行，统计上一完整月份的膏方导入和发放数据。

## 数据口径

- **按导入时间（created_at）统计**，不是按处方日期（date）
- **上传** = 当月所有导入的处方记录（含跨月处方日期）
- **发放** = 当月导入记录中 status 为 `已取` 或 `已邮寄` 的
- **患者去重** = 按（姓名 + 年龄 + 电话）三字段联合去重
- **料数** = 数据库中 `quantity` 字段合计

## 查询SQL

```sql
WITH upload AS (
  SELECT 
    to_char(created_at::date, 'YYYY-MM') AS 月份,
    COUNT(DISTINCT patient_name || '|' || age::text || '|' || COALESCE(patient_phone, '')) AS 上传患者人数,
    SUM(quantity) AS 上传总料数
  FROM prescription_records
  WHERE created_at >= '上个月1号' AND created_at < '本月1号'
    AND created_at IS NOT NULL
  GROUP BY 月份
),
dispense AS (
  SELECT 
    to_char(created_at::date, 'YYYY-MM') AS 月份,
    COUNT(DISTINCT patient_name || '|' || age::text || '|' || COALESCE(patient_phone, '')) AS 发放患者数,
    SUM(quantity) AS 发放料数
  FROM prescription_records
  WHERE created_at >= '上个月1号' AND created_at < '本月1号'
    AND created_at IS NOT NULL
    AND status IN ('已取', '已邮寄')
  GROUP BY 月份
)
SELECT 
  COALESCE(u.月份, d.月份) AS 月份,
  COALESCE(u.上传患者人数, 0) AS 上传患者人数,
  COALESCE(u.上传总料数, 0) AS 上传总料数,
  COALESCE(d.发放患者数, 0) AS 发放患者数,
  COALESCE(d.发放料数, 0) AS 发放料数
FROM upload u
FULL OUTER JOIN dispense d ON u.月份 = d.月份
ORDER BY 月份;
```

## 执行方法

```bash
su - postgres -c "psql -d gaofang_v2 -c \"SQL语句\""
```

## 输出格式

| 月份 | 上传患者人数 | 上传总料数 | 发放患者数 | 发放料数 |

## 注意

- 如当月无导入记录，返回空结果
- 3月数据包含系统初始导入的历史全量数据
- 数据仅供内部管理参考
