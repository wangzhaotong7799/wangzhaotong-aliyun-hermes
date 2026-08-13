# 复诊列表显示停服患者 + 停服时间（2026-08-13 实施记录）

需求：① 复诊管理界面加「停服时间」列；② 导出数据补复诊时间（fu1/2/3 实际日期）。
项目：`/workspace/projects/drug-distribution-system/gaofang-v2/`（Flask + PostgreSQL，服务 `gaofang-v2-fusion`，gunicorn venv38，端口 8080）。

## 数据库

```sql
-- 备份先行（写库前必做）
su - postgres -c "pg_dump gaofang_v2" > backups/followup_stopped_at_$(date +%Y%m%d_%H%M%S).sql

ALTER TABLE follow_up_records ADD COLUMN stopped_at DATE;
-- 历史回填：自动停服理论日 = 服用结束 + 40 天（本次回填 2394 条）
UPDATE follow_up_records SET stopped_at = end_date + INTERVAL '40 days'
WHERE is_stopped = TRUE AND stopped_at IS NULL;
```

注意：`follow_up_records` 原先只有 `is_stopped` 布尔，没有时间字段——任何"停服时间"需求都必须先加字段。

## 后端（api/v1/follow_up_management.py + models/follow_up_record.py）

1. 模型加列 + `to_dict()` 输出 `'stopped_at': self.stopped_at.isoformat() if self.stopped_at else None`
2. 手动停服 `stop_follow_up`：**两个分支都要写** `rec.stopped_at = date.today()`
   （record_id 兜底分支 + 按姓名批量分支，只改一个会导致另一路径不写时间）
3. 自动停服 `_sync_records`：UPDATE SQL 改为
   `SET is_stopped = TRUE, stopped_at = end_date + INTERVAL '40 days'`
4. 列表 `get_follow_up_patients` 过滤联动（共 4 层，全部要松开才能显示停服患者）：
   - `include_stopped` 参数原来读了但从未拼进查询（死参数）→ 定义 `show_stopped = include_stopped or follow_up_status == '已停服'`
   - SQL 层：
     ```python
     if show_stopped:
         rec_query = rec_query.filter(or_(
             FollowUpRecord.is_stopped == True,          # 停服记录全部放行
             and_(FollowUpRecord.is_stopped == False,    # 在服记录保持窗口规则
                  FollowUpRecord.fu3_planned_end >= _month_start,
                  FollowUpRecord.fu1_planned_start <= _window_cutoff),
         ))
     else:
         rec_query = rec_query.filter(FollowUpRecord.is_stopped == False, ...窗口...)
     ```
   - 内存挑选层：`_pick_active_record(records, allow_stopped=False)` 加参数，全部停服时
     `return max([r for r in records if r.is_stopped], key=lambda r: r.month or date.min)`
     （否则返回 None，患者被丢弃）。调用处传 `allow_stopped=(include_stopped or follow_up_status == '已停服')`
   - **⚠️ 日期范围过滤层（第 2 轮用户反馈"停服时间列没有数据"的根因）**：列表接口后面还有按 fu 计划窗口的日期范围过滤（前端默认日期范围=今天~今天+3天），停服患者窗口全是过去日期 → 即使前 3 层都放行也被此层全灭。修复：
     ```python
     if start_date or end_date:
         for patient in result:
             if patient.get('is_stopped'):
                 filtered.append(patient)   # 停服患者豁免日期范围过滤
                 continue
             ...原有窗口交集判断...
     ```
     诊断法：同一请求带/不带 start_date&end_date 对比 total（本次 331 → 1671 定位）。
5. 数字自洽校验（验证正确性的关键）：默认 357（窗口内在服）+ 停服患者 1314 = 包含停服 1671；
   停服患者数 = 停服记录数按患者去重（2394 条 → 1314 人）。

## 在服患者也要显示停服时间（第 3 轮需求 + 主人口径纠正）

⚠️ 主人最终纠正（"停服时间 不是 = ？料*30天吗？"）：**停服时间 = 领取时间 + 料数×30 = end_date（药吃完那天）**。
曾实现为"已停服=stopped_at，在服=end_date+40"被主人纠正；40 天只用于**停药时间 = 停服时间 + 40天**（明细页字段）。

```python
# models/follow_up_record.py to_dict() — 最终正确实现（停服/在服统一）
'stop_time': self.end_date.isoformat() if self.end_date else None,
# 明细页另算 drug_stop_time = (end_date + timedelta(days=40)).isoformat()
```

前端「停服时间」列统一渲染 `patient.stop_time || '-'`（导出列同用 stop_time）——不要用 stopped_at，
否则在服患者全是空。验证：stop_time == 领取时间 + total_quantity×30（全量断言 PASS）。

## 导出必须带"待复诊时间"（第 5 轮需求，主人强调"很重要"）

导出曾只有已复诊的实际日期（fuX_date），待复诊的计划窗口漏掉。模式：

```javascript
function fuExportTime(num) {
    var date = patient['follow_up_' + num + '_date'];
    if (date) return date;                          // 已复诊 → 实际日期
    var start = patient['follow_up_' + num + '_start'];
    var end = patient['follow_up_' + num + '_end'];
    if (start && end) return start + '~' + end;     // 待复诊 → 计划窗口
    return '';
}
// 列: '第一次复诊': 状态, '第一次复诊时间': fuExportTime(1), ...
```

导出列顺序 = 界面列顺序：XLSX `json_to_sheet` 按对象键插入顺序出列，有权限列插在中间时
用 `orderedHeaders` 数组重建对象（基础列 + 权限列按权限 push 进对应位置 + concat 尾部列）。

## 同会话续作（第 4~7 轮）：电话列 + 两个明细页

- `follow_up_records` 无电话字段 → `ALTER TABLE ADD COLUMN patient_phone VARCHAR(20)`；
  回填用 `UPDATE ... FROM (SELECT DISTINCT ON (patient_name,gender,age) ... patient_phone
  FROM prescription_records WHERE patient_phone <> '' ORDER BY ..., id DESC)`（本次 3694/3988 条）。
  ⚠️ 加字段必须同步 4 处：ALTER+回填 / model+to_dict / `_sync_records` UPSERT（INSERT 列、VALUES、
  DO UPDATE SET、params 字典）/ `_group_patients`。
- 新接口 `GET /api/follow-up/patients?type=active|stopped`：按患者去重取最近疗程（`max(recs,
  key=lambda r: r.end_date or date.min)`），返回 `stop_time`(=end_date)、`drug_stop_time`(=end_date+40)，
  `_mask_sensitive_fields` 掩码，分页 {data,total}。明细页不受"本月窗口"限制（独立查询，不复用列表接口的窗口过滤）。
- 新增页面完整 recipe（模板命名 / pageLoaders / 导航 / common.js 5 处门控）见
  本技能 `references/add-pc-page.md` 与 SKILL.md pitfall 16。

## 前端

- `templates/followup.html`：表头加 `<th>停服时间</th>`、`<th>领取时间</th>`（pickup_date，第 4 轮需求）；状态下拉加 `<option value="已停服">`；加「包含停服患者」复选框 `#follow-up-include-stopped`
- `static/js/page-followup.js`：
  - **colCount 硬编码 `? 12 : 10` 全部同步改（共 5 处）**——空态 colspan 用，漏改占不满整行；两轮累计加 2 列后最终为 `? 14 : 12`
  - 列表请求 + 导出请求都要 `if (el && el.checked) params.append('include_stopped', '1')`
  - 渲染行加 `'<td>' + (patient.pickup_date || '-') + '</td>'`（领取时间）和 `'<td>' + (patient.stop_time || '-') + '</td>'`（停服时间）
  - 导出 row 加：`'领取时间'`、`'停服时间': patient.stop_time`、`'第一次复诊时间': patient.follow_up_1_date`、`'第二次复诊时间'`、`'第三次复诊时间'`
  - 自动搜索监听数组加 `'follow-up-include-stopped'`
- 本页 JS 由 common.js 动态注入（`?v=Date.now()`），无需升 index.html 版本号；模板 followup.html 刷新页面即更新

## 验证：无需用户密码的接口测试（可复用技术）

用户密码未知时，用应用上下文内 `generate_token` + Flask test client 直接测 auth-required 接口：

```python
import sys; sys.path.insert(0, '/workspace/projects/drug-distribution-system/gaofang-v2')
from app import app
from database import db
from auth import generate_token   # 注意不是 create_token（该名不存在）
from models import User

with app.app_context():
    user = db.session.query(User).filter_by(username='yaoju001').first()
    token = generate_token(user.id, user.username, [r.name for r in user.roles])
    client = app.test_client()
    r = client.get('/api/follow-up?include_stopped=1', headers={'Authorization': f'Bearer {token}'})
```

写接口安全测试：INSERT 临时记录（如 patient_name='__test_stop__'）→ 调用写接口 → 断言结果 → DELETE 清理。
严禁直接拿真实患者数据调写接口验证。

## 运行环境备忘

- 服务：`systemctl status gaofang-v2-fusion`；热重启 `kill -HUP $(systemctl show gaofang-v2-fusion -p MainPID --value)`
- 清 `__pycache__`（find -name __pycache__ -type d | xargs rm -rf）
- 语法检查：`node --check static/js/page-followup.js` + `./venv38/bin/python -m py_compile <py文件>`
- HUP 日志里的 `Worker was sent SIGHUP/SIGTERM` 是正常信号，不是错误
