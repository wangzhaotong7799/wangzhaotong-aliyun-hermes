# Guest Login / 角色访问控制 — 实施细节

> 来自膏方管理系统 V2 移动端 PWA 的实战记录。
> 仓库: wangzhaotong7799/drug-distribution-system (本地)

## 需求

登录页新增「游客登录」按钮，点击后无需凭证即可查看「未取」膏方记录。
游客不能访问复诊、提醒模块，不能修改任何数据。

## 文件改动一览

| 文件 | 改动 |
|------|------|
| `api/v1/auth.py` | 新增 `POST /api/auth/guest-login` 端点 |
| `api/v1/prescriptions.py` | 新增 `_check_guest_role()`, get_prescriptions 中过滤 |
| `api/v1/followups.py` | 新增 `_check_guest_role()`, get_reminders/update 中拦截 |
| `api/v1/follow_up_management.py` | get_follow_up_patients/update 中添加角色检查 |
| `static/mobile/js/store.js` | 新增 `isGuest()` 方法 |
| `static/mobile/js/api.js` | 新增 `guestLogin()` 方法 |
| `static/mobile/js/page-login.js` | 新增游客按钮 + 事件处理器 |
| `static/mobile/js/router.js` | 游客路由拦截（仅允许 pickup） |
| `static/mobile/js/page-pickup.js` | 游客模式隐藏筛选标签 + 弹窗隐藏电话 |
| `static/mobile/index.html` | 底部导航隐藏复诊/提醒 tab（nav-guest-hidden 类） |
| `static/mobile/css/app.css` | 游客按钮样式（btn-guest） |

## 关键细节

### JWT Token 生成

```python
# auth.py 中的 generate_token 函数
payload = {
    'user_id': user_id,      # 游客设为 0
    'username': username,    # 游客设为 'guest'
    'roles': roles,          # 游客设为 ['guest']
    'exp': datetime.utcnow() + timedelta(hours=24)
}
```

注意：`_get_assistant_info` 函数中通过 `user_id` 查 User 表，游客 `user_id=0` 查不到用户，
但客端不需要医助过滤（游客只看未取，不按医助过滤）。

### 处方列表中的角色优先级

```python
# prescriptions.py get_prescriptions()
# 顺序很重要：
if _is_guest:
    query = query.filter(status == '未取')  # 1. 游客强制未取
elif start_date:
    query = query.filter(date >= start_date)  # 2. 非游客才加日期过滤
```

游客分支 **提前 return** 了 status 过滤，后面 status/doctor/assistant 参数在 `if _is_guest` 分支之后的 `elif`/`if` 链中不会再执行。但如果用户传了其他参数，需要在 `_is_guest` 分支后也做判断，避免遗漏。

### 前端 API 参数匹配陷阱

**问题：** `update_reminder_status` 后端接受 `patient_name` 查找记录，
但前端 `markVisited` 传了 `prescription_id`，导致 400 "缺少必要参数"。

**修复方案（推荐双兼容）：**

```python
# 后端优先用 prescription_id（唯一标识），其次用 patient_name
record = None
if prescription_id:
    record = query.filter_by(prescription_id=prescription_id).first()
if not record and patient_name:
    record = query.filter_by(patient_name=patient_name).first()
```

```javascript
// 前端同时传两个
Api.updateReminderStatus({
  prescription_id: prescriptionId,
  patient_name: patientName,
  status: '已回访'
});
```

### 游客模式下的数据量

- 总处方数：3,489 条（含所有状态）
- 游客可见（未取）：12 条
- 不限制时间范围（不需要 6 个月过滤）

## 测试清单

- [ ] `POST /api/auth/guest-login` 返回 valid JWT with `role=guest`
- [ ] `GET /api/prescriptions` with guest token → 仅返回 status=未取 的数据
- [ ] `GET /api/reminders` with guest token → 403
- [ ] `POST /api/reminders/update-status` with guest token → 403
- [ ] `GET /api/follow-up` with guest token → 403
- [ ] `POST /api/follow-up/update` with guest token → 403
- [ ] 正常用户 token 仍然可以访问所有接口
- [ ] 游客登录后底部导航只显示「膏方领取」
- [ ] 游客登录后筛选标签只显示「未取」
- [ ] 游客点击处方详情 → 「患者电话」不显示
- [ ] 游客点击复诊/提醒 tab → 重定向回膏方领取
