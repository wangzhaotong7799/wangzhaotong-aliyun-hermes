# 权限改造端到端测试方法（Flask RBAC/组织架构）

适用：`get_visible_scope()` / `can_view_field()` / 字段脱敏 / 领导层只读改造完成后的功能验证。
核心原则：**必须 API 层验证，直调函数通过 ≠ 接口生效**。

## 1. 定位技巧：直调 vs API 层对比

同一逻辑两条路走一遍，结果不一致就是认证注入问题：

| 层 | 做法 | 结果含义 |
|----|------|---------|
| 直调 | `app_context` 内 `get_visible_scope(user_id)`（显式传 uid） | 验证 scope 逻辑本身（角色/小组解析）是否正确 |
| API 层 | `test_client` 带 token 请求路由 | 验证 `g.user_id` 是否注入、过滤是否真的作用于查询 |

**判读**：直调各角色结果正确，但 API 层所有用户返回全量同数 → 路由缺 `@auth_required`，`g.user_id` 从未设置 → `get_visible_scope()` 返回 None（不过滤）、`can_view_field()` 返回 False（全员脱敏，连 admin 也被脱敏）。
**反向验证**：找带 `@auth_required` 的模块（如 stats.py 的统计接口）对比 admin vs 医助返回量，正常则证明 scope 逻辑本身无误、问题在缺装饰器的路由。

## 2. SQL 期望值口径（自验证，不靠肉眼）

期望条数按 scope 语义从 DB 现算，测试内断言 `API 返回 == SQL 期望`：

```python
def scope_sql_count(names):  # names=None 全量；[] 只空值；[姓名...] 集合
    if names is None: return TOTAL
    q = db.session.query(PrescriptionRecord)
    if not names:
        return q.filter(or_(assistant.is_(None), assistant=='', assistant=='-')).count()
    return q.filter(assistant.in_(names) | assistant.is_(None) |
                    assistant=='' | assistant=='-').count()
```

注意：空 assistant 记录（NULL/''/'-'）对**每个受限用户都可见**，期望值必须加上这一部分，否则算出来偏小误报 FAIL。

## 3. 字段脱敏断言

- admin/药局：响应里 prescription_type/doctor **存在非 null 值**（应可见）
- 其他角色：全部为 null
- 若 admin 也为 null → 同根因（g.user_id 未注入，can_view_field 恒 False）

## 4. 写操作测试卫生（不污染生产库）

- **总监范围 PUT**：先快照 `director_group_scope` 原行 → 改 → 验证 `get_visible_scope` 变化 → **删掉重建原行**还原 → 再验证还原后 scope 与原始一致
- **匿名写测试**：临时记录用唯一前缀（如 `PERMTEST<hex>` / `DELTEST<hex>`），测完删除；结束时 `SELECT COUNT(*) WHERE prescription_id LIKE '%TEST%'` 必须 = 0
- **SQLAlchemy 删除坑**：`query.filter(...like...).delete()` 抛 `UnevaluatableError: Cannot evaluate BinaryExpression`（ORM 无法 Python 端求值 LIKE）→ 用原生 SQL `db.session.execute("DELETE FROM ... WHERE ... LIKE ...")` 或加 `synchronize_session=False`

## 5. 领导层只读验证

领导层拦截通常靠路由内 `_get_token_user_info()` 重新解析 token（与 scope 机制是两套代码路径）——即使 scope 失效，POST/PUT/DELETE 的 403 也可能"碰巧"通过。逐条测：POST 新建（空 body 即可，拦截在字段校验前）、PUT 改状态、DELETE。

## 6. 密码/账号获取（无文档时）

- 项目 `ARCHITECTURE.md` 的测试账号表（明文）优先
- 历史会话搜索（session_search）确认过的密码：admin/admin123、yaoju001/yaoju001123、GJD-A/gjd123456、yizhu003/yizhu003123、zj002/Zj002@123456
- 命名规律 `username+123` 可作候选（实测通过）：zj001 沿用原 yizhu001 的密码 `yizhu001123`（改名不换密码）、yizhu002123、cw001123
- 候选全失败 → 该用户改用直调 `get_visible_scope(uid)` 验证（不需要密码）

## 7. 膏方V2 实测发现（2026-08-06，基线 4385 条处方）

**致命回归**：`api/v1/prescriptions.py` 全部 7 个路由（GET 列表/statistics/详情、POST、PUT、DELETE、import）与 `api/v1/follow_up_management.py` 全部 5 个路由**均无 `@auth_required`**：
- 所有用户（含医助）API 返回全量 4385 条（期望：zj001=3833、yizhu003=963、yizhu002=390、zj002=361）
- admin/yaoju001 也看不到剂型/医生（全 null）
- 匿名 POST 201 真实入库、匿名 GET 详情 200、匿名 DELETE 200 成功
- 复诊模块 `/api/follow-up` admin 与医助均 408 条（scope 未生效）
- **正常对照**：stats.py（6 路由全有 @auth_required）admin=4385 vs yizhu003=963 生效；excel/export GJD-A 403

**修复**：给上述路由补 `@auth_required`（一次修复 scope+脱敏+匿名漏洞）；或让 scope/mask 函数在 g.user_id 缺失时回退手动解析 token（不推荐，双轨易漏）。改后清 `__pycache__` + 重启 Gunicorn，用 §1-3 用例回归。

**数据一致性观察**：处方表 assistant='张春梅' 100 条 与 用户表 yizhu009='张冬梅' 不符 → 总监/组长范围看不到这 100 条。属数据问题非代码问题，但影响行级过滤覆盖面，需提示主人。
