# 新增 PC 独立页面完整配方（膏方管理系统 V2 实战）

来源：2026-08-13 会话新增「在服患者明细」「停药患者明细」两页 + 复诊页多列改造。
全部步骤经接口实测验证（服务 `gaofang-v2-fusion`，gunicorn venv38，端口 8080）。
配套：SKILL.md pitfall 16（common.js 菜单门控 5 处清单）。

## 页面机制（common.js 懒加载）

- `/page/<page_name>` 路由 → `send_from_directory('templates', f'{page_name}.html')`
  **文件名必须与 pageName 完全一致**（连字符风格，如 `active-patients`），无 Jinja 渲染
- JS：`static/js/page-<page_name>.js`，末尾注册 `window.pageLoaders['<page_name>'] = fn`
  （common.js 自动注入 script 并调用 loader）
- JS 注入带 `?v=Date.now()` 时间戳 → **改 JS 无需升版本号**
- ⚠️ index.html 本体被 Nginx `expires 7d` 缓存 → 改导航/容器后必须提醒主人 **Ctrl+F5 强刷**

## 新增页面 6 步

1. `templates/<page-name>.html` — 骨架：标题 + 导出按钮 + 筛选区（`row g-2 align-items-center` +
   `col-auto` + `form-control-sm`，紧凑一行）+ loading + 表格 + 分页控件
   （`pagination-container` + `page-btn`，控件 ID 加页面前缀防冲突如 `ap-`/`sp-`）
2. `static/js/page-<page-name>.js` — IIFE + 分页状态 + load/render/updatePagination/export +
   `window.pageLoaders['<page-name>']`
3. index.html 导航：`<li class="nav-item" id="<name>-nav" style="display:none;">`
   `<a class="nav-link" data-page="<page-name>" href="#<page-name>">菜单名</a></li>`
4. index.html 容器：`<div id="page-<page-name>" class="page-content"></div>`
5. common.js 菜单门控 **5 处**（见 SKILL.md pitfall 16：元素获取 / canManage / hasLeader /
   canSeeFollowup / 未登录隐藏）
6. 权限列：剂型列 `prescription_type:view`、医生列 `doctor:view`（前端显隐 + 后端
   `_mask_sensitive_fields` 双保险）；colCount = `9 + (canSeeSensitive?1:0) + (canSeeDoctor?1:0)`

## 导出列顺序 = 界面列顺序

`XLSX.utils.json_to_sheet` 的列顺序 = 对象键插入顺序。权限列插在中间时用有序重建：

```javascript
var headers = ['患者姓名', '性别', '年龄', '电话'];
if (canSeeSensitive) headers.push('处方类型');
headers.push('数量');
if (canSeeDoctor) headers.push('医生');
headers = headers.concat(['医助', '领取时间', '停服时间', '停药时间']);
var rows = data.map(function(p) { /* 与 headers 同步 push */ });
var ws = XLSX.utils.aoa_to_sheet([headers].concat(rows));
```

权限变化时导出列要跟着变。`aoa_to_sheet` 比 `json_to_sheet` 更可控（列顺序显式声明）。

## 复诊时间导出（待复诊计划窗口，主人强调"很重要"）

导出不能只有已复诊日期，待复诊必须给计划窗口 `start~end`：

```javascript
function fuExportTime(num) {
    var date = patient['follow_up_' + num + '_date'];
    if (date) return date;                          // 已复诊 → 实际日期
    var start = patient['follow_up_' + num + '_start'];
    var end = patient['follow_up_' + num + '_end'];
    if (start && end) return start + '~' + end;     // 待复诊 → 计划窗口
    return '';
}
```

## 无密码验证接口法（本项目通用，可复用）

不知道任何账号密码时，用 app 上下文直接生成 token + Flask test_client 验证 auth-required 接口：

```python
import sys; sys.path.insert(0, '/workspace/projects/drug-distribution-system/gaofang-v2')
from app import app
from database import db
from auth import generate_token   # 注意不是 create_token（该名不存在）
from models import User

with app.app_context():
    u = db.session.query(User).filter_by(username='yaoju001').first()
    token = generate_token(u.id, u.username, [r.name for r in u.roles])
    client = app.test_client()
    r = client.get('/api/follow-up/patients?type=active&page=1&page_size=5',
                   headers={'Authorization': f'Bearer {token}'})
```

用 `./venv38/bin/python` 跑。写接口验证：INSERT 临时记录（如 `patient_name='__test_stop__'`）→
调用写接口 → 断言 → DELETE 清理；严禁拿真实患者数据调写接口。

## 搜索区医生/医助下拉

医生下拉不要从分页记录提取（只有当前页医生）。专用接口：
- `/api/follow-up/doctors`：`_apply_scope_filter` 后对 `doctor` 列 DISTINCT 返回，医生角色自然只剩自己
- 医助 `/api/assistants`（已有，无需认证版在 auth.py、需认证版在 prescriptions.py）
- 下拉 change 触发自动搜索（`currentPage = 1; loadPatients();`），姓名输入框 Enter 同效

## 页面上方合计统计卡（主人两次纠正对齐）

需求"页面上方显示患者合计数量 + 卡片增加底色"。最终布局（踩过两次位置坑）：

- **标题行只放**：标题 + 导出按钮（`d-flex justify-content-between align-items-center`）
- **卡片位置**：与「搜索」按钮**同一行、右对齐、底边平齐**——外层 `d-flex justify-content-between align-items-center` 包「搜索区 row + 卡片」，卡片 `d-inline-block` 自适应宽度
- ❌ 不要放导出按钮正下方/垂直居中对齐——第一次放导出按钮下被否（"和导出的底边平齐了"），
  主人要求**与搜索按钮底边平齐**
- **底色**：`background:#e7f1ff`（在服浅蓝）+ `border-left:4px solid #0d6efd` + 数字 `text-primary`；
  `background:#fdecea`（停药浅红）+ `border-left:4px solid #dc3545` + 数字 `text-danger`，`fs-4 fw-bold`
- 数量实时更新：分页接口返回 `total`，`document.getElementById('<前缀>-total-count').textContent = total`

## 陷阱

- **colCount 5+ 处同步**：页面加列时 JS 里所有空态 colspan 三元（未登录/加载中/错误/空/正常）
  必须全部同步 +1，漏一处表格占不满整行（本次累计 12→13→14→15）。
- 筛选区压缩成一行：`col-md-3` 换 `col-auto` + `form-control-sm` + `g-2 align-items-center`，
  复选框加 `white-space:nowrap`，`margin-bottom:0`。
- 新接口若受"本月窗口"限制会查不到历史数据——明细页用独立查询（不复用列表接口的窗口过滤），
  按患者去重取 `max(end_date)` 最近疗程；排序在服按 stop_time 升序、停药按 drug_stop_time 降序。
