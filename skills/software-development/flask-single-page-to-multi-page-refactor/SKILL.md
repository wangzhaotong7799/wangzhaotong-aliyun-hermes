---
name: flask-single-page-to-multi-page-refactor
description: "将单 HTML 文件（5000+行）的 Flask 应用重构为多页面架构 — 拆分 CSS/JS/HTML 到独立文件，实现标签页切换"
tags: [flask, refactoring, frontend, architecture, multi-page]
---

# Flask 单页面 → 多页面重构方法

## 适用场景

一个 5000+ 行的 `index.html` 包含了所有 HTML、CSS、JS（几十个函数 + 十几个 Modal），需要拆分为独立文件 + 标签页导航架构。

## 架构模式

```
project/
├── static/
│   ├── index.html           ← 主框架（导航栏 + 页面容器 + 登录/公用Modal）
│   ├── css/style.css        ← 从原 index.html 提取的自定义样式
│   └── js/
│       ├── common.js         ← 公共函数（fetchWithAuth、登录状态、切换页面）
│       └── page-{name}.js   ← 每个标签页的独立JS（按需注入）
├── templates/
│   └── {name}.html          ← 每个标签页的HTML片段（按需加载）
└── app.py                   ← 添加静态文件和子页面路由
```

## 加载策略（核心优化）

对于多标签页应用，采用 **预加载（Preload）+ 懒加载（Lazy Load）混合策略**：

| 页面类型 | 策略 | 实现方式 |
|---------|------|---------|
| **默认首页**（用户打开页面立刻看到的） | **预加载** | 模板HTML直接内联到 `index.html`，JS文件在 `<head>` 结束前加载，无需 AJAX |
| **其他标签页**（用户点击后才看） | **懒加载** | 切换时才动态注入 `<script>` 加载JS + `fetch` 获取模板HTML，并行加载 |

**收益**：
- 首页 **零额外网络请求**即可渲染（模板已内联）
- 非活跃页面的JS和HTML **不下发、不解析**，大幅减少首屏加载字节数和解析时间
- 模板HTML + JS文件 **一次加载后缓存**，重复切换零网络开销

### 懒加载实现模板（common.js）

```javascript
// ====== 页面加载器注册表 ======
window.pageLoaders = {};

// ====== 页面导航 ======
var currentPage = 'prescriptions';
var loadedPages = { 'prescriptions': 'loaded' };  // 预加载页标记

// 已注入的JS文件集合（防重复注入）
var injectedScripts = {};
// 已缓存的模板HTML（防重复请求）
var cachedTemplates = {};

function loadLazyPageContent(pageName) {
    var container = document.getElementById('page-' + pageName);
    if (!container) return;

    // 模板获取（缓存优先）
    var templatePromise = cachedTemplates[pageName]
        ? Promise.resolve(cachedTemplates[pageName])
        : fetch('/page/' + pageName)
            .then(function(r) { if (!r.ok) throw new Error('Page not found'); return r.text(); })
            .then(function(html) { cachedTemplates[pageName] = html; return html; });

    // JS注入（防重复）
    var jsPromise = injectedScripts[pageName]
        ? Promise.resolve()
        : new Promise(function(resolve, reject) {
            var script = document.createElement('script');
            script.src = '/static/js/page-' + pageName + '.js';
            script.onload = function() { injectedScripts[pageName] = true; resolve(); };
            script.onerror = function() { reject(new Error('加载JS失败')); };
            document.body.appendChild(script);
        });

    // 并行加载模板+JS，都就绪后渲染
    Promise.all([templatePromise, jsPromise])
        .then(function(results) {
            var html = results[0];
            if (!container.hasAttribute('data-rendered')) {
                container.innerHTML = html;
                container.setAttribute('data-rendered', 'true');
            }
            loadedPages[pageName] = 'loaded';
            if (window.pageLoaders && window.pageLoaders[pageName]) {
                window.pageLoaders[pageName]();
            }
        })
        .catch(function(err) {
            console.error('加载页面失败:', err);
            container.innerHTML = '<div class="alert alert-danger">加载失败: ' + err.message + '</div>';
        });
}

function switchPage(pageName) {
    // 隐藏所有页面容器，显示目标容器
    var pages = document.querySelectorAll('.page-content');
    for (var i = 0; i < pages.length; i++) pages[i].classList.remove('active');
    var targetPage = document.getElementById('page-' + pageName);
    if (targetPage) targetPage.classList.add('active');

    // 更新导航高亮
    var navLinks = document.querySelectorAll('.navbar-nav .nav-link[data-page]');
    for (var i = 0; i < navLinks.length; i++) navLinks[i].classList.remove('active');
    var activeLink = document.querySelector('.navbar-nav .nav-link[data-page="' + pageName + '"]');
    if (activeLink) activeLink.classList.add('active');

    currentPage = pageName;
    window.location.hash = pageName;

    // ⚡ 核心：预加载页直接渲染，其他按需懒加载
    if (pageName !== 'prescriptions') {
        loadLazyPageContent(pageName);
    } else {
        if (window.pageLoaders && window.pageLoaders['prescriptions']) {
            window.pageLoaders['prescriptions']();
        }
    }
}
```

### init() 中的 hash 恢复逻辑

```javascript
function init() {
    // ... 绑定导航、登录表单 ...

    var hash = window.location.hash.replace('#', '');
    if (hash && document.getElementById('page-' + hash)) {
        switchPage(hash);  // hash 页可能是懒加载页，走 switchPage 完整逻辑
    } else {
        // 默认页：预加载，直接调用 pageLoader 跳过 switchPage 的完整流程
        currentPage = 'prescriptions';
        if (window.pageLoaders && window.pageLoaders['prescriptions']) {
            window.pageLoaders['prescriptions']();
        }
    }
}
```

### ❗ 关键陷阱：window.app 导出旧函数名

重命名函数后（例如 `loadPageContent` → `loadLazyPageContent`），**必须同步更新 `window.app` 导出**，否则调用方会报 `ReferenceError`：

```javascript
// ✅ 必须一致
window.app = {
    ...
    loadLazyPageContent: loadLazyPageContent,  // ✅ 更新后的名字
    ...
};
```

## 实施步骤

### 1. 摸底（必须）

```bash
# 统计原始文件
wc -l index.html
# 找出所有顶级区块
grep -n 'id="[a-z][a-z-]*"' index.html | grep -v 'modal\|form\|btn\|header'
# 找出所有Modal
grep -n 'class="modal fade"' index.html
# 列出所有JS函数
grep -n 'function ' index.html
# 找出所有CSS块
grep -n '^\s*[.#@]' index.html | grep -v 'bootstrap\|@import'
# 找出导航结构
grep -n 'nav-item\|nav-link' index.html
```

### 2. 后端路由支持（app.py 改动）

```python
# 静态资源服务
@app.route('/static/<path:filename>')
def serve_static_file(filename):
    return send_from_directory('static', filename)

# 子页面模板（动态加载用）
@app.route('/page/<page_name>')
def serve_page_template(page_name):
    return send_from_directory('templates', f'{page_name}.html')

# 主页面指向 static/index.html
@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')
```

### 3. 创建 static/index.html（主框架）

- 导航栏（含版本标识）
- 页面容器 `<div id="page-{name}" class="page-content"></div>` 每个标签页一个
- 共用 Modal（登录、修改密码等）
- CDN 引用（Bootstrap, Chart.js, xlsx）
- 登录表单处理
- 页面加载逻辑 `loadPageContent(pageName)`：
  1. `fetch('/page/' + pageName)` 获取 HTML
  2. 插入到对应的 `#page-{name}` 容器
  3. 用 `<script src="/static/js/page-{name}.js">` 加载 JS
- 权限控制导航项显示

### 4. 创建 static/js/common.js

```javascript
(function() {
    'use strict';
    // 工具函数：formatDate, formatDaysFromPrescriptionToShipping
    // 认证：getToken, isLoggedIn, getUserRoles, hasRole, hasAnyRole
    // 网络：fetchWithAuth(url, options) — 自动带token、处理401过期
    // 导航：switchPage(pageName) — 显示/隐藏 + hash更新 + 触发pageLoaders
    // 初始化：updateLoginStatus, init
    
    window.app = { ... };  // 暴露全局
})();
```

### 5. 创建各子页面

**HTML 模板（templates/{name}.html）：**
- 只包含内容区域，不含导航/登录框架
- 用 `<div class="{name}-page">` 包裹
- 保持原有 Bootstrap 类名和结构

**JS 文件（static/js/page-{name}.js）：**
```javascript
(function() {
    'use strict';
    // 页面专属函数
    // 使用 window.app.fetchWithAuth、window.app.hasRole 等公共函数
    
    window.pageLoaders['{name}'] = function() {
        // 页面加载逻辑
    };
})();
```

### 6. 后端分页支持（如果原 API 不分页）

在 API 列表接口中，检测 `page` 和 `page_size` 参数：
```python
total = query.count()
if page and page_size:
    query = query.offset((page - 1) * page_size).limit(page_size)

records = query.all()
# ... 处理逻辑

if page and page_size:
    total_pages = max(1, (total + page_size - 1) // page_size)
    return jsonify({
        "data": result_list,
        "total": total,
        "page": page,
        "per_page": page_size,
        "total_pages": total_pages
    })
return jsonify(result_list)  # 兼容无分页调用
```

### 7. 前端分页控件

HTML 结构：
```html
<div class="pagination-container">
    <div class="pagination-info" id="pagination-info">共0条 第0/0页</div>
    <div class="pagination-controls">
        <button class="page-btn" id="page-first">首页</button>
        <button class="page-btn" id="page-prev">上页</button>
        <span id="page-numbers"></span>
        <button class="page-btn" id="page-next">下页</button>
        <button class="page-btn" id="page-last">末页</button>
        <select class="page-size-select" id="page-size-select">
            <option value="50">50条/页</option>
            <option value="100">100条/页</option>
            <option value="200">200条/页</option>
        </select>
    </div>
</div>
```

JS 渲染分页：
```javascript
function renderPagination(currentPage, total, pageSize) {
    var totalPages = Math.ceil(total / pageSize) || 1;
    // 更新 info
    document.getElementById('pagination-info').textContent = 
        '共' + total + '条 第' + currentPage + '/' + totalPages + '页';
    // 生成页码按钮（最多5个）
    // 绑定首页/上页/下页/末页事件
}
```

### 8. 关键修复：JS 加载时序问题的解决方案

本次实践中遇到了两个关键坑：

#### ❌ 陷阱1：动态创建 `<script>` 标签加载 JS 导致时序不可控

```javascript
// ❌ 错误做法
container.innerHTML = html;
var script = document.createElement('script');
script.src = '/static/js/page-prescriptions.js';
document.body.appendChild(script);
// 此时 window.pageLoaders['prescriptions'] 还是 undefined！
// 因为 script 是异步加载，即使设置 script.async = false 也不可靠
```

**原因**：通过 `createElement` 创建并 `appendChild` 的 `<script>` 标签在浏览器中是异步加载和执行的。`appendChild` 之后不会阻塞等待脚本执行完成。

**解决方案**：**不要动态加载 JS。一次性在 HTML 中加载所有 page-*.js 文件。**

```html
<!-- ✅ 正确做法：一次性加载所有JS -->
<script src="/static/js/common.js"></script>
<script src="/static/js/page-prescriptions.js"></script>
<script src="/static/js/page-statistics.js"></script>
<script src="/static/js/page-followup.js"></script>
<!-- ... 所有页面JS ... -->
```

#### ❌ 陷阱2：`common.js` 的执行顺序导致 `pageLoaders` 未注册

`common.js` 在 `<script>` 顺序中排在所有 page-*.js **之前**。如果 `init()` 在 `DOMContentLoaded` 时立即触发，此时 page-*.js 还未执行，`window.pageLoaders` 还是空对象。

```javascript
// ❌ 错误做法
document.addEventListener('DOMContentLoaded', init);
// 此时 page-loaders 还没注册！

// ✅ 正确做法：延迟到事件队列末尾
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(init, 0);  // setTimeout(0) 让 init 排在所有同步脚本之后
});
```

**原理**：浏览器执行 `<script>` 是同步的（默认），`common.js` 执行完后才到 `page-prescriptions.js`。`DOMContentLoaded` 在**所有同步脚本执行完后触发**，但由于 `common.js` 中的事件监听绑定先于 page-*.js 注册，`init()` 仍然会先执行。`setTimeout(init, 0)` 把 `init()` 推到**事件队列尾部**，确保所有脚本都已完成。

#### ✅ 整体加载流程（正确）

```
1. HTML 解析到 <script src="common.js">  → 下载并执行 common.js
   → 注册 DOMContentLoaded 监听器（内部用 setTimeout(0) 包装 init）
2. HTML 解析到 <script src="page-prescriptions.js"> → 执行 IIFE
   → 注册 window.pageLoaders['prescriptions'] = function() {...}
3. HTML 解析到 <script src="page-statistics.js"> → 执行 IIFE
   → 注册 window.pageLoaders['statistics'] = function() {...}
4. ...
5. DOMContentLoaded 事件触发
   → common.js 的 setTimeout(init, 0) 入队
6. 当前事件循环完成，setTimeout 回调执行
   → init() 运行，此时 window.pageLoaders 已包含所有页面
   → switchPage('prescriptions') 正常工作
```

## 关键注意事项

1. **括号匹配检查**：拆分后 JS 文件可能因模板字符串或正则含多层嵌套，需检查 `{}` `()` `[]` 匹配
2. **global chart 变量**：Chart.js 实例需要 `window.chartXxx = new Chart(...)` 避免重复创建
3. **页面加载时序**：用 `window.pageLoaders` 注册表，common.js 的 `switchPage()` 统一触发
4. **URL hash**：每个标签页对应一个 hash（如 `#prescriptions`），刷新后自动恢复
5. **权限导航**：登录后显示需要登录的标签页，管理员额外显示管理标签页
6. **按需注入JS**：懒加载页面用 `createElement('script')` 动态注入，`script.onload` 通知完成后才触发 pageLoader
7. **模板防重复渲染**：用 `container.setAttribute('data-rendered', 'true')` 标记已渲染容器
8. **init() 不能直接调 switchPage(默认页)**：会触发 switchPage 中的懒加载逻辑。对预加载页面，直接调用 `pageLoaders[name]()` 即可，避免不必要的条件判断
9. **旧 URL 兼容**：老系统的 `/api/backups` / `/api/restore` 等路径保持不变
10. **分页与筛选联动**：改变筛选条件时重置到第1页
8. **分页与筛选联动**：改变筛选条件时重置到第1页

## 已知陷阱

### 🪤 patch 工具修改 JS 文件的风险

`patch` 工具对 JS/HTML 文件做替换时，如果 `old_string` 匹配不精确或有多处匹配，可能导致：
- **语法残片残留**：新旧代码混插，文件被截断或多余的代码块残留
- **大括号不匹配**：替换区域的开闭 `{}` 不对应，导致语法错误
- **解决方法**：替换整个 `function()` 区块时，确认 `old_string` 从 `function funcName()` 开始到匹配的 `}` 结束。替换后立即用 `python3 -c "compile(open(fn).read(), fn, 'exec')"` 验证语法。
- **安全做法**：复杂 JS 文件的重构直接用 `write_file` 全量重写，避免 `patch` 的局部替换风险

### 🪤 `window.app` 导出与内部函数名不一致

重命名内部函数后（如 `loadPageContent` → `loadLazyPageContent`），必须同步更新 `window.app` 导出：
```javascript
// ❌ 引发 ReferenceError: loadPageContent is not defined
window.app = { loadPageContent: loadPageContent };

// ✅
window.app = { loadLazyPageContent: loadLazyPageContent };
```
**排查方法**：搜索 `window.app = {` 的每一行，逐个核对函数名是否与 `function` 定义一致。ES5 对象字面量不会报语法错，只在调用时报 ReferenceError。

### 🪤 导航栏功能按钮丢失

从单页面拆分为多页面时，原导航栏中的**功能按钮**（如导入、导出、打印、备份）很容易丢失，因为重构时只关注了标签页切换。**必须清点原导航栏所有 `<li class="nav-item">`**，逐个确定归入哪个页面。

功能按钮的事件绑定不能放进子页面的 `pageLoaders`（因为它们不属于特定标签页），应该放在 `common.js` 的 `init()` 函数中统一注册。

- **Python 3.6 兼容**：不能用 f-string 中的复杂表达式，JS 模板字符串中的 `${}` 不影响
- **原有路由冲突**：app.py 中可能有多个同路径路由，旧路由定义和函数名不能冲突
- **Modal 内容过大**：编辑弹窗（如 editFollowUpModal）可能有 2000+ 行，拆分时注意完整提取
- **V2 标识**：导航栏品牌名 + favicon + footer 都要加上版本号

*最后更新：2026-05-01 — 新增预加载/懒加载混合策略、window.app 导出陷阱、patch 工具风险、验证清单补充*

## 验证清单

- [ ] 主页 200 响应
- [ ] 所有 `/static/` 文件 200
- [ ] 所有 `/page/{name}` 模板 200
- [ ] 所有 `page-{name}.js` 200
- [ ] 所有 API 端点正常（含带分页参数和不带参数两种）
- [ ] 登录/登出流程
- [ ] 标签页切换 + URL hash 恢复
- [ ] 权限控制（未登录/登录/管理员不同的导航项）
- [ ] 分页控件可用（页码、每页条数）
- [ ] 合计行正确
- [ ] 全部19个Modal功能正常（编辑、更新状态、导入、导出、打印等）
- [ ] **预加载页面**首屏零网络请求（打开 DevTools Network tab 验证）
- [ ] **懒加载页面**切换时只增加 1 个模板请求 + 1 个 JS 请求（而非全量下载）
- [ ] **`window.app` 导出函数名**与内部实现一致（重命名后易遗漏）
- [ ] **Ctrl+F5 强制刷新**后所有功能正常（验证完全冷启动）
