# 广积德医助 PWA — 上下文记录

## 系统环境
- 公网地址: http://39.107.78.58 (HTTP/80 → gunicorn 8080)
- PWA 入口: http://39.107.78.58/mobile/
- 项目位置: ~/projects/drug-distribution-system/gaofang-v2/
- Python: 3.8.17 (venv38), gunicorn 23.0.0
- 数据库: PostgreSQL 13.23, gaofang_v2, 用户 gaofang_app
- 桌面端 SPA: http://39.107.78.58/ (不受影响)

## 测试账号
- yizhu003 / yizhu003123 — 医助
- admin / admin123 — 管理员

## PWA 目录结构
```
static/mobile/
├── index.html        # SPA 入口 + PWA manifest/sw 引用
├── manifest.json     # PWA 安装配置
├── sw.js             # Service Worker
├── css/app.css       # 移动端样式（12px 卡片、底部导航、弹窗）
└── js/
    ├── store.js      # Token/用户持久化（localStorage）
    ├── api.js        # API 封装（JWT 自动注入、get/post/put）
    ├── router.js     # Hash 路由（login/pickup/followup/reminders）
    ├── page-login.js # 登录页（登录后自动跳转膏方领取页）
    ├── page-pickup.js# 膏方领取（搜索+筛选+卡片+弹窗详情）
    ├── page-followup.js # 复诊（待复诊/已完成 tab + 5 状态按钮）
    └── page-reminders.js # 提醒（超期高亮 + 标记回访）
```

## 3 个核心页面细节

### 膏方领取 (page-pickup.js)
- IIFE 模式，Router.register('pickup', render)
- 搜索栏 + 5 个筛选标签 [全部/欠药/未取/已取/已邮寄]
- 默认选中「未取」标签
- 所有筛选条件下只查最近 6 个月数据（`start_date: 六个月前`）
- 分页加载：每次 50 条，底部「加载更多」
- **卡片列表字段顺序：** 患者名+状态badge → 日期 → 代煎号 → **医助** → 数量（医生和剂型已隐藏）
- 点击弹出底部详情弹窗（全部字段，空值不显示）
- 弹窗已将「医生」和「剂型」移除，保留「医助」
- **不要**传 `assistant` 参数，后端 JWT 自动过滤
- API 兼容两种返回格式: `{data: [...]}` 和 `[...]`

### 复诊 (page-followup.js)
- IIFE 模式，Router.register('followup', render)
- 2 个 tab: [待复诊] [已完成] — **注意用后端识别的值 '待复诊'/'已复诊'**
- **卡片字段顺序：** 患者姓名 → 代煎号 → **医助** → 复诊状态 → 最近取药日期 → 回访次数
- 卡片含 `data-pid`(代煎号) 和 `data-id`(数据库ID) 属性
- 更新时传 `patient_id`(数据库ID), `status`, `follow_up_number`
- 5 个状态按钮: 已打通/拒接/空号/已复诊/已停药
- follow_up_number 由已完成的回访次数+1 自动计算

### 提醒 (page-reminders.js)
- IIFE 模式，Router.register('reminders', render)
- **使用 `\n\` 反斜杠续行模式拼 HTML**（容易出 bug 的写法，改字段需谨慎）
- 3 个筛选标签: [全部] [未回访] [已回访]
- **卡片字段顺序：** 患者名 → **医助** → 服用结束日期 → 到期天数 → 服用天数/料数 → 最近取药日期 → 状态
- 状态标签读取 **`item.follow_up_status`**（后端返回字段），不要读 `item.reminder_status`（后端不存在该字段）
- 超期高亮: days_until_end > 0 用红色, <= 0 用绿色
- 标记回访调用: Api.updateReminderStatus({prescription_id, status: "已回访"})
- 筛选参数 `?status=待回访` / `?status=已回访` 由后端 `request.args.get('status')` 过滤，而非前端过滤

## 用户字段偏好（2026-05-01 确认）
- 三个页面（领取/复诊/提醒）均显示「医助」行
- 膏方领取页面隐藏「医生」和「剂型」（卡片列表 + 弹窗详情都隐藏）
