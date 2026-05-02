# 详情弹窗内联编辑模式 — PWA 实施指南

> 来自膏方管理系统 V2 PWA page-pickup.js 的实战记录。

## 适用场景

在 PWA 的详情弹窗（modal）中，允许特定角色用户直接编辑某个字段，而不需要跳转到独立编辑页面。

## 模式结构

### 数据流

```
卡片点击 → showDetail(item, dataIdx)
  → 渲染弹窗（含编辑区域）
  → 用户点击「编辑」→ 显示输入框
  → 用户点击「保存」→ PUT /api/prescriptions/{id}
  → API 成功 → 更新本地 state.allData[dataIdx] → 重新渲染卡片列表
```

### 关键实现要素

#### 1. 角色检查

```javascript
var user = Store.getUser();
var canEditAssistant = user && user.username === 'yizhu001';
```

条件渲染整个编辑区域：

```javascript
overlay.innerHTML = ''
  + '<div class="modal-content">'
  +   detailHtml
  +   (canEditAssistant ? '<!-- 编辑区域 -->' : '')
  + '</div>';
```

#### 2. 编辑区域三态

| 状态 | 显示 | 操作 |
|------|------|------|
| 查看态 | 当前值 + [编辑医助] 按钮 | 点击→编辑态 |
| 编辑态 | 输入框 + [保存][取消] | 保存→API调用；取消→回到查看态 |
| 保存中 | 输入框 + [保存中...][取消]（按钮禁用） | 禁止重复提交 |

```html
<!-- 查看态 -->
<div class="card-row">
  <span class="card-label">医助</span>
  <span class="card-value" id="assistant-display">张医生</span>
</div>
<button class="btn btn-outline btn-sm" id="assistant-edit-btn">编辑医助</button>

<!-- 编辑态（默认隐藏） -->
<div id="assistant-edit-form" style="display:none">
  <input type="text" id="assistant-input" value="张医生" placeholder="输入医助姓名">
  <button class="btn btn-primary btn-sm" id="assistant-save-btn">保存</button>
  <button class="btn btn-outline btn-sm" id="assistant-cancel-btn">取消</button>
</div>
```

#### 3. 取消时的值恢复

```javascript
cancelBtn.addEventListener('click', function() {
  editForm.style.display = 'none';
  editBtn.style.display = 'inline-flex';
  // 从当前显示的文本（可能是上次保存后的值）恢复输入框
  input.value = display.textContent === '--' ? '' : display.textContent;
});
```

注意：不能用 `item.assistant` 恢复，因为 `item` 还是旧数据。要从 DOM 取最新的显示值。

#### 4. API 调用 + 本地状态同步

```javascript
saveBtn.addEventListener('click', function() {
  var newValue = input.value.trim();
  saveBtn.disabled = true;
  saveBtn.textContent = '保存中...';

  Api.updatePrescription(item.id, { assistant: newValue })
    .then(function() {
      showToast('医助已更新');
      // 1. 更新弹窗内的显示
      display.textContent = newValue || '--';
      editForm.style.display = 'none';
      editBtn.style.display = 'inline-flex';
      // 2. 同步更新卡片列表数据
      if (dataIdx !== undefined && dataIdx >= 0) {
        state.allData[dataIdx].assistant = newValue;
        renderList();  // 重新渲染所有卡片
      }
    })
    .catch(function(err) {
      showToast('更新失败：' + (err.message || '未知错误'));
    })
    .finally(function() {
      saveBtn.disabled = false;
      saveBtn.textContent = '保存';
    });
});
```

#### 5. dataIdx 参数传递链

**关键：** `dataIdx` 必须穿透到 `saveBtn` 的事件处理器中。

```javascript
// 卡片点击时传入 idx
card.addEventListener('click', function() {
  var idx = parseInt(card.getAttribute('data-index'), 10);
  var item = state.allData[idx];
  if (item) showDetail(item, idx);  // ← 传 idx
});

// showDetail 接受 idx
function showDetail(item, dataIdx) {  // ← 接收 idx
  // ... 在 saveBtn 回调中直接用 dataIdx
  saveBtn.addEventListener('click', function() {
    // ...
    state.allData[dataIdx].assistant = newValue;  // ← 使用
  });
}
```

**为什么需要？** 因为编辑成功后要更新卡片列表中的对应数据行，而 `dataIdx` 是 `state.allData` 数组中的索引。没有它，编辑后卡片列表不会同步显示新值。

## 后端兼容性

### 后端需支持部分字段更新

```python
@prescriptions_bp.route('/prescriptions/<id>', methods=['PUT'])
def update_prescription(id):
    record = session.query(PrescriptionRecord).filter_by(id=id).first()
    # 医助角色允许编辑的字段
    if is_assistant:
        allowed_fields = ['assistant', 'patient_phone']
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
        data = filtered_data
    # 更新
    for key, val in data.items():
        setattr(record, key, val)
    session.commit()
```

### 后端 API 需返回 id 字段

```python
def to_dict(self):
    return {
        'id': self.id,           # ← 必须有！前端更新时靠这个传
        'patient_name': ...,
        'assistant': ...,
    }
```

## 与全局 toast 的集成

更新成功/失败后使用全局 `showToast()` 反馈：

```javascript
function showToast(msg) {
  // 已在 PWA 中定义的 toast 函数
  var el = document.getElementById('toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toast';
    el.className = 'toast';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(function() { el.classList.remove('show'); }, 2000);
}
```

## 典型陷阱

### 陷阱 1：`card` 变量在 showDetail 中不可用

`showDetail` 由不同上下文调用（卡片点击事件、可能的重渲染），内联编辑的保存回调中 **不要** 引用闭包外的 `card` 变量。用 `dataIdx` 替代：

```javascript
// ❌ 错误：card 在 showDetail 作用域中不存在
saveBtn.addEventListener('click', function() {
  var idx = card.getAttribute('data-index');  // ReferenceError
});

// ✅ 正确：用传递进来的 dataIdx
saveBtn.addEventListener('click', function() {
  if (dataIdx !== undefined) {
    state.allData[dataIdx].assistant = newValue;
  }
});
```

### 陷阱 2：API 调用后的 state 同步

API 成功后不要只更新弹窗内的显示，还要更新 `state.allData` 并调用 `renderList()`。否则关闭弹窗后卡片列表还是旧数据。

### 陷阱 3：转义用户输入

用户输入的医助姓名可能包含 HTML 特殊字符，插入 DOM 前必须转义：

```javascript
var input = '<script>alert(1)</script>';
display.textContent = input;  // ✅ 安全
display.innerHTML = input;     // ❌ XSS 漏洞
```

## 变体二：下拉框选择 + 新增

### 适用场景

可编辑字段的值来自数据库中的枚举集合（如医助名单、医生名单），需要：
- 从现有集合中选择一个值
- 也允许输入数据库中不存在的新值

### 三区域设计

| 区域 | DOM 元素 | 初始显示 |
|------|---------|---------|
| 查看态 | 当前值 + [编辑] 按钮 | ✅ 可见 |
| 选择态 | `<select>` 下拉 + [+新增] 按钮 + [保存][取消] | 点击[编辑]后显示 |
| 输入态 | `<input>` 输入框 + [添加并保存][返回] | 点击[+新增]后显示 |

### HTML 模板

```html
<!-- 选择态 -->
<div id="assistant-select-mode">
  <div style="display:flex;gap:6px">
    <select id="assistant-select" class="detail-input" style="flex:1">
      <option value="">— 请选择医助 —</option>
    </select>
    <button class="btn btn-outline btn-sm" id="assistant-add-new-btn">+ 新增</button>
  </div>
  <div style="display:flex;gap:6px;margin-top:8px">
    <button class="btn btn-primary btn-sm" id="assistant-save-select-btn">保存</button>
    <button class="btn btn-outline btn-sm" id="assistant-cancel-btn">取消</button>
  </div>
</div>

<!-- 输入态（初始隐藏） -->
<div id="assistant-input-mode" style="display:none">
  <input type="text" id="assistant-input" class="detail-input" placeholder="输入新医助姓名">
  <div style="display:flex;gap:6px;margin-top:8px">
    <button class="btn btn-primary btn-sm" id="assistant-save-input-btn">添加并保存</button>
    <button class="btn btn-outline btn-sm" id="assistant-back-btn">返回</button>
  </div>
</div>
```

### 下拉数据加载

```javascript
function loadAssistantList() {
  var currentVal = display.textContent === '--' ? '' : display.textContent;

  Api.getAssistants().then(function(list) {
    var html = '<option value="">— 请选择医助 —</option>';
    var found = false;
    (list || []).forEach(function(name) {
      var selected = (name === currentVal) ? ' selected' : '';
      if (name === currentVal) found = true;
      html += '<option value="' + escapeHtml(name) + '"' + selected + '>' + escapeHtml(name) + '</option>';
    });
    // 如果当前值不在下拉列表中，追加一个选项
    if (currentVal && !found) {
      html += '<option value="' + escapeHtml(currentVal) + '" selected>' + escapeHtml(currentVal) + '（当前）</option>';
    }
    selectEl.innerHTML = html;
  });
}
```

**关键细节：** 当前值可能不在数据库返回的列表中（比如是新录入的值、已被删除的旧值），要额外追加一个 `（当前）` 选项确保选中态。

### 模式切换逻辑

```javascript
// 选择态 → 输入态
document.getElementById('assistant-add-new-btn').addEventListener('click', function() {
  selectMode.style.display = 'none';
  inputMode.style.display = 'block';
  inputEl.value = display.textContent === '--' ? '' : display.textContent;
  inputEl.focus();
});

// 输入态 → 选择态（返回）
document.getElementById('assistant-back-btn').addEventListener('click', function() {
  inputMode.style.display = 'none';
  selectMode.style.display = 'block';
  loadAssistantList();  // 重新加载确保列表是最新数据
});
```

### 存方法（两模式共用）

```javascript
function saveAssistant(newValue) {
  var btn = (selectMode.style.display !== 'none')
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
      // 同步更新卡片列表
      if (dataIdx !== undefined && dataIdx >= 0) {
        state.allData[dataIdx].assistant = newValue;
        renderList();
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

### 陷阱

**陷阱 1：`editBtn.style.display` 在取消时的值** — 按钮默认 `display` 是 `inline-block`（`<button>` 的默认值），但 Bootstrap `/btn` 类设置的是 `inline-flex`。恢复显示时要用 `display = 'inline-flex'` 而非 `''`，否则按钮宽度会变化。

**陷阱 2：下拉框的值与当前显示不一致** — 用户已经成功保存过一次新值后再次编辑，下拉框应该自动选中这个新值。`loadAssistantList()` 中从 `display.textContent` 读取当前值确保匹配。

**陷阱 3：新增模式下按回车提交** — 用户习惯在输入框中按 Enter 提交，需要绑定 keydown 事件：
```javascript
inputEl.addEventListener('keydown', function(e) {
  if (e.key === 'Enter') document.getElementById('assistant-save-input-btn').click();
});
```

### 后端 API 要求

```python
# GET /api/assistants — 返回医助名称列表
@prescriptions_bp.route('/assistants', methods=['GET'])
def get_assistants():
    query = session.query(distinct(PrescriptionRecord.assistant)).filter(
        PrescriptionRecord.assistant.isnot(None),
        PrescriptionRecord.assistant != '',
        PrescriptionRecord.assistant != '-'
    )
    query = query.order_by(PrescriptionRecord.assistant)
    return jsonify([row[0] for row in query.all()])
```

新值通过 `PUT /api/prescriptions/<id>` 保存，通过前端直接写入数据库。下次再查 `GET /api/assistants` 时自动包含新值。

## 扩展思路

- **多字段编辑**：编辑区域可包含多个字段（医助 + 患者电话），每个字段独立编辑或统一保存
- **拖拽排序**：如果要编辑字段顺序，可用 `drag` API 替代弹窗编辑
- **验证逻辑**：保存前检查输入合法性（如非空、长度限制）
