# PWA 医助下拉编辑模式（dropdown + 新增）

## 适用场景

在 PWA 详情弹窗中编辑数据库已有选项（如医助姓名），且允许用户从现有列表中选择或添加全新值。适用于：医助分配、医生指派、科室选择等「有限枚举 + 可扩展」字段。

## 核心模式

### 两态切换

```
初始态（显示模式）
  ┌──────────────────┐
  │ 医助   李庆荣     │
  │  [编辑医助]        │
  └──────────────────┘
        ↓ 点击「编辑」

状态 A（下拉选择模式）
  ┌──────────────────┐
  │ 医助   [请选择▼]  │
  │  ┌──────────┐ [新增]│   ← 下拉框 + 新增按钮并行
  │  │ 李庆荣    │      │
  │  │ 张春梅    │      │
  │  │ 刘凯东    │      │
  │  └──────────┘      │
  │  [  保存  ] [取消]  │
  └──────────────────┘
        ↓ 点击「+ 新增」

状态 B（输入模式）
  ┌──────────────────┐
  │ 医助              │
  │ [输入新医助姓名___]│   ← 自由输入
  │ [添加并保存] [返回] │
  └──────────────────┘
        ↓ 点击「返回」
        ↑ 回到状态 A
```

### 数据流

```
编辑开始
  ├─ Api.getAssistants() → 获取下拉选项列表
  ├─ 当前值自动选中
  │
  ├─ 选择模式：用户选一个 → 保存
  │   └─ PUT /api/prescriptions/{id} → { assistant: "新值" }
  │
  ├─ 新增模式：用户输入新名字 → 添加并保存
  │   └─ PUT /api/prescriptions/{id} → { assistant: "新名字" }
  │
  └─ 保存成功
      ├─ 更新弹窗显示值（display.textContent）
      ├─ 同步 state.allData[dataIdx].assistant
      ├─ 重新渲染卡片列表（renderList()）
      └─ 切回初始态
```

## 实现结构

### HTML 模板

```javascript
// 选择模式：下拉框 + 新增按钮
'<div id="assistant-select-mode">'
+   '<select id="assistant-select">'
+     '<option value="">— 请选择 —</option>'
+   '</select>'
+   '<button id="assistant-add-new-btn">+ 新增</button>'
+   '<button id="assistant-save-select-btn">保存</button>'
+   '<button id="assistant-cancel-btn">取消</button>'
+ '</div>'

// 输入模式：文本输入 + 返回按钮
'<div id="assistant-input-mode" style="display:none">'
+   '<input id="assistant-input" placeholder="输入新医助姓名">'
+   '<button id="assistant-save-input-btn">添加并保存</button>'
+   '<button id="assistant-back-btn">返回</button>'
+ '</div>'

// 入口按钮
'<button id="assistant-edit-btn">编辑医助</button>'
```

### 下拉列表加载

```javascript
function loadAssistantList() {
  var currentVal = display.textContent === '--' ? '' : display.textContent;

  Api.getAssistants().then(function(list) {
    var html = '<option value="">— 请选择 —</option>';
    var found = false;
    (list || []).forEach(function(name) {
      var selected = (name === currentVal) ? ' selected' : '';
      if (name === currentVal) found = true;
      html += '<option value="' + escapeHtml(name) + '"' + selected + '>' + escapeHtml(name) + '</option>';
    });
    // 当前值不在列表中时，也保留为选中项
    if (currentVal && !found) {
      html += '<option value="' + escapeHtml(currentVal) + '" selected>' + escapeHtml(currentVal) + '（当前）</option>';
    }
    selectEl.innerHTML = html;
  }).catch(function() {
    // 加载失败：保留默认选项
  });
}
```

### 保存逻辑（共享函数）

```javascript
function saveAssistant(newValue) {
  // 判断当前是哪种模式，取对应的按钮
  var btn = selectMode.style.display !== 'none'
    ? document.getElementById('assistant-save-select-btn')
    : document.getElementById('assistant-save-input-btn');

  btn.disabled = true;
  btn.textContent = '保存中...';

  Api.updatePrescription(item.id, { assistant: newValue })
    .then(function() {
      showToast('医助已更新');
      display.textContent = newValue || '--';
      selectMode.style.display = 'none';
      inputMode.style.display = 'none';
      editBtn.style.display = 'inline-flex';

      // 关键：同步本地数据
      if (dataIdx !== undefined && dataIdx >= 0) {
        state.allData[dataIdx].assistant = newValue;
        renderList();  // 重绘卡片列表
      }
    })
    .catch(function(err) {
      showToast('更新失败：' + (err.message || '未知错误'));
    })
    .finally(function() {
      btn.disabled = false;
      btn.textContent = '保存';
    });
}
```

## 关键要点

### 1. 权限控制

只在特定用户登录时显示编辑入口：

```javascript
var user = Store.getUser();
var canEditAssistant = user && user.username === 'yizhu001';
```

### 2. dataIdx 穿透传递

从卡片点击 → `showDetail(item, dataIdx)` → save 回调，必须保持 dataIdx 在作用域链中：

```javascript
// 卡片点击
card.addEventListener('click', function() {
  var idx = parseInt(card.getAttribute('data-index'), 10);
  var item = state.allData[idx];
  if (item) showDetail(item, idx);  // ← 索引穿透
});

// 函数定义
function showDetail(item, dataIdx) {
  // ... 在 saveAssistant 内使用 dataIdx 更新 state.allData
}
```

### 3. 同步本地状态

保存成功后必须同步 3 个地方：
- 弹窗显示值（`display.textContent`）
- 数据数组（`state.allData[dataIdx]`）
- 卡片列表（`renderList()`）

### 4. 取消/返回时的恢复

- 取消：只隐藏编辑区，回到初始态
- 返回（从输入模式回选择模式）：重新加载下拉列表（确保新增的选项出现）

## 必装的后端 API

需要存在两个后端接口：

```python
# 1. 获取选项列表
GET /api/assistants
Response: ["李庆荣", "张春梅", "刘凯东", ...]

# 2. 更新字段
PUT /api/prescriptions/<id>
Body: { "assistant": "新值" }
Response: { "message": "更新成功" }
```

## 与 inline-edit-pattern.md 的区别

| 维度 | inline-edit-pattern（已有） | assistant-edit-pattern（本文） |
|------|---------------------------|-------------------------------|
| 编辑方式 | 状态按钮点击（三态切换） | 下拉框选择 + 新增输入 |
| 数据来源 | 本地状态值 | 后端 API 动态加载 |
| 选项集合 | 固定枚举（待回访/已回访） | 动态列表（数据库去重） |
| 用户输入 | 不允许自由输入 | 支持新增（切换输入模式） |
| 适用字段 | 状态类（有限枚举） | 姓名/名称类（可扩展枚举） |
