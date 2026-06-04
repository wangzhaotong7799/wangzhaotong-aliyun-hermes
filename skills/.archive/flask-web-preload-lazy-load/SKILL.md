---
name: flask-web-preload-lazy-load
description: Flask 单页面应用前端性能优化 — 默认页预加载（内联模板，零网络请求）+ 其他页面懒加载（按需注入 JS 和模板）
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [flask, performance, lazy-load, preload, frontend-optimization]
    related_skills: [flask-api-troubleshooting, write-file-truncation-prevention]
---

# Flask SPA 前端预加载 + 懒加载优化指南

## 当此技能匹配时，必须加载并遵循其步骤

## When to Use

**适用场景：**
- Flask 单页面应用（SPA）有多个标签页/视图，所有 JS 文件在首页一次性加载
- 用户反馈页面打开慢/卡顿（尤其第一次加载）
- 有 3 页以上的独立功能页面（每个页面的 JS 文件 200+ 行）
- 通过 AJAX 异步加载模板 HTML 导致切换页面时有可感知延迟

## Overview

将 Flask SPA 的页面加载分为两种策略：

| 页面类型 | 加载策略 | 用户感知 |
|---------|---------|---------|
| **默认页**（用户打开立刻看到的） | **预加载** — 模板 HTML 内联到 index.html，JS 随主页面加载 | 零网络请求，DOM 就绪立即渲染 |
| **其他 6+ 标签页** | **懒加载** — 模板 + JS 都按需注入，首次加载后缓存 | 切换时首次有轻微延迟，后续零延迟 |

## Implementation Steps

### Step 1: 分析当前加载方式

确认当前代码是用什么方式管理页面的：

```javascript
// 检查 common.js 中是否有类似 loadPageContent 的函数
// function loadPageContent(pageName) {
//     var container = document.getElementById('page-' + pageName);
//     if (loadedPages[pageName]) return;  // ← 有一个 loadedPages 缓存
//     ...
//     fetch('/page/' + pageName)  // ← 每个页面都通过 AJAX 获取
//         .then(r => r.text())
//         .then(html => {
//             container.innerHTML = html;
//             window.pageLoaders[pageName]();  // ← 每个页面有独立的 loader
//         });
// }
```

### Step 2: 分页策略

#### 默认页面（如膏方记录）→ 预加载

1. 将该页面的完整模板 HTML（包括所有 modal）直接复制到 `index.html` 的对应容器中
2. 只保留该页面的 JS 引用在 `<script>` 标签中
3. 移除其他页面的 JS 引用

```html
<!-- index.html — 只保留预加载页面的 JS -->
<script src="/static/js/common.js"></script>
<script src="/static/js/page-prescriptions.js"></script>
<!-- 其他 page-*.js 已移除 -->
```

```html
<!-- index.html 容器 — 预加载页面直接内联 -->
<div id="page-prescriptions" class="page-content active">
    <!-- 完整的 HTML，包括表格、筛选栏、弹窗 -->
    ...内联内容...
</div>

<!-- 其他页面容器为空，按需加载 -->
<div id="page-statistics" class="page-content"></div>
```

#### 其他页面 → 按需懒加载

在 `common.js` 中实现 `loadLazyPageContent` 函数：

```javascript
// ====== 页面加载器注册表 ======
window.pageLoaders = {};

// ====== 页面导航 ======
var currentPage = 'prescriptions';
var loadedPages = { 'prescriptions': 'loaded' };  // 预加载页面标记为已加载

// 已注入的JS文件集合
var injectedScripts = {};

// 已缓存的模板HTML
var cachedTemplates = {};

function loadLazyPageContent(pageName) {
    var container = document.getElementById('page-' + pageName);
    if (!container) return;

    // 并发获取模板和注入JS
    var templatePromise;
    if (cachedTemplates[pageName]) {
        templatePromise = Promise.resolve(cachedTemplates[pageName]);
    } else {
        templatePromise = fetch('/page/' + pageName)
            .then(function(r) {
                if (!r.ok) throw new Error('Page not found');
                return r.text();
            })
            .then(function(html) {
                cachedTemplates[pageName] = html;
                return html;
            });
    }

    var jsPromise;
    if (injectedScripts[pageName]) {
        jsPromise = Promise.resolve();
    } else {
        jsPromise = new Promise(function(resolve, reject) {
            var script = document.createElement('script');
            script.src = '/static/js/page-' + pageName + '.js';
            script.onload = function() {
                injectedScripts[pageName] = true;
                resolve();
            };
            script.onerror = function() {
                reject(new Error('加载JS失败: page-' + pageName + '.js'));
            };
            document.body.appendChild(script);
        });
    }

    // 模板 + JS 都就绪后触发渲染
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
            console.error('加载页面 ' + pageName + ' 失败:', err);
            container.innerHTML = '<div class="alert alert-danger">页面加载失败: ' + err.message + '</div>';
            loadedPages[pageName] = 'error';
        });
}
```

### Step 3: 修改 `switchPage` 逻辑

```javascript
function switchPage(pageName) {
    // ... 隐藏/显示页面逻辑不变 ...

    // 预加载页面 vs 懒加载页面的分支
    if (pageName !== 'prescriptions') {
        loadLazyPageContent(pageName);
    } else {
        // 预加载页面 — DOM已存在，直接触发渲染
        if (window.pageLoaders && window.pageLoaders['prescriptions']) {
            window.pageLoaders['prescriptions']();
        }
    }
}
```

### Step 4: 修改 `init()` — 默认页直接渲染

```javascript
function init() {
    // ... 事件绑定 ...

    // 从 hash 恢复页面
    var hash = window.location.hash.replace('#', '');
    if (hash && document.getElementById('page-' + hash)) {
        switchPage(hash);
    } else {
        // 默认预加载页面 — 零网络请求，直接触发渲染
        currentPage = 'prescriptions';
        if (window.pageLoaders && window.pageLoaders['prescriptions']) {
            window.pageLoaders['prescriptions']();
        }
    }
}
```

### Step 5: 关键命名一致性检查

```javascript
// 暴露给全局 API 的名字也要更新
window.app = {
    // ...
    loadLazyPageContent: loadLazyPageContent,  // ← 不是 loadPageContent!
    init: init
};
```

## Special Cases

### 1. 用户通过 URL hash 进入非默认页（如 `#statistics`）

当 hash 为 `#statistics` 时，`init()` 调用 `switchPage('statistics')` → 走懒加载分支 → `loadLazyPageContent('statistics')` → 模板 + JS 按需加载。无需额外处理。

### 2. 用户点击导航切换到非默认页

导航点击直接调用 `switchPage()`，判断当前页不是预加载页就走懒加载。

### 3. 登录后在预加载页显示/隐藏元素

`pageLoaders['prescriptions']` 函数中已有的 `updateLoginStatus()` 调用仍然有效，因为 `switchPage` 会重新触发 pageLoader。

## Verification

```bash
# 1. 验证首页 HTML 包含内联模板
curl -s http://localhost:8080/ | grep -c "page-prescriptions"

# 2. 验证只有预加载页的 JS 被引用
curl -s http://localhost:8080/ | grep -o "page-[a-z-]*\.js"

# 3. 验证 API 正常
curl -s http://localhost:8080/api/prescriptions?page=1\&per_page=10 | head -c 100

# 4. 验证切换页面路由
for page in statistics reminders admin-users; do
    curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8080/page/$page"
done
```

## Pitfalls

1. **`window.app.loadPageContent` vs `loadLazyPageContent`** — 如果函数改名了，`window.app` 的导出也要同步更新，否则报 `ReferenceError`
2. **`write_file` 截断风险** — 重写 `index.html` 时（内联模板），确保把完整的模板 HTML 写入；推荐先用 `read_file` 读完整内容
3. **内联模板的大小** — 大模板（如包含多个 modal 的膏方记录页，约 300+ 行）内联后会增加 index.html 体积，但对性能无负面影响（相比之下省去了 AJAX 请求）
4. **`document.querySelector('.page-content')`** — 预加载页已内联，查询类选择器时要注意它也在 `.page-content` 集合中
5. **缓存问题** — 修改 JS 文件后，用户需要 Ctrl+F5 强制刷新才能获取新版本
6. **`data-rendered` 属性** — 用这个属性防止懒加载页面被重复设置 innerHTML（否则每次切换都会重复插入 DOM）

## Performance Comparison

| 指标 | 优化前（全量加载） | 优化后（预加载+懒加载） |
|------|-------------------|----------------------|
| 首页 JS 加载数量 | 8 个脚本 (~4000 行) | 2 个脚本 |
| 首页 HTTP 请求 | 2 次 (index.html + 模板 AJAX) | **1 次** |
| 其他页面 JS | 全部预先下载 | **按需下载** (仅一次) |
| 第二次切换页面 | 重新 AJAX 获取模板 | **零网络请求** (缓存命中) |
