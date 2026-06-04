# 导出弹窗内嵌筛选模式 (Export Modal Built-in Filter Pattern)

## 问题

导出弹窗打开时，常依赖主页筛选条件来过滤数据。但用户可能在导出场景下需要**独立调整筛选条件**（如只导出某个医生的数据），此时：

1. 用户必须返回主页调整筛选再重新打开导出 → 流程断裂
2. 用户不知道导出会继承主页筛选 → 导出全部数据，不符合预期
3. 主页筛选与导出意图混在一起 → 容易误操作

## 用户纠正信号

> 第一次实现只给导出表格加了两列（医生/医助），用户反馈：
> "导出的功能应该增加那个医生和医助的筛选，现在只能导出状态，日期什么的，针对医生，我想就是呃，导出一个医生的，他现在把所有的医生都给我导出来"

这说明：**给导出加列 ≠ 给导出加筛选**。两者是独立需求，用户需要的是筛选能力，不是显示能力。

## 解决方案模式

在导出弹窗（Modal）内部添加专属于导出功能的筛选控件，而非依赖主页筛选。

### 架构

```
┌─────────────────────────────────────┐
│  导出弹窗                            │
│  ┌─ 筛选栏 ──────────────────────┐  │
│  │ [医生▼]  [医助▼]  [🔄 刷新]   │  │
│  └────────────────────────────────┘  │
│  ┌─ 结果预览 ────────────────────┐  │
│  │ ☑ 日期  代煎号  姓名  ... 医生 医助│  │
│  │ ☑ ...                         │  │
│  └────────────────────────────────┘  │
│  [取消]                    [确认导出] │
└─────────────────────────────────────┘
```

### 关键实现

#### 1. HTML：弹窗内加筛选行

```html
<div class="modal-body">
  <div class="row mb-3">
    <div class="col-md-4">
      <select class="form-select" id="export-filter-doctor">
        <option value="">所有医生</option>
      </select>
    </div>
    <div class="col-md-4">
      <select class="form-select" id="export-filter-assistant">
        <option value="">所有医助</option>
      </select>
    </div>
    <div class="col-md-4">
      <button type="button" class="btn btn-outline-primary" id="export-refresh-btn">
        🔄 刷新
      </button>
    </div>
  </div>
  <!-- 按钮行 + 表格 -->
</div>
```

#### 2. JS：从弹窗内筛选控件读取值

```javascript
// ❌ 错误：从主页筛选读（用户不知道、不直观）
var doctor = document.getElementById('filter-doctor');

// ✅ 正确：从弹窗内筛选读（显式可控）
var doctor = document.getElementById('export-filter-doctor');
```

#### 3. JS：数据加载后动态填充筛选下拉

```javascript
function populateExportFilterDropdowns(records) {
  // 保留当前选中的值
  var selected = docSelect.value;
  
  // 从记录中提取唯一值
  var doctors = [...new Set(records.map(r => r.doctor).filter(Boolean))];
  
  // 重建下拉
  docSelect.innerHTML = '<option value="">所有医生</option>';
  doctors.forEach(function(d) {
    var opt = document.createElement('option');
    opt.value = d;
    opt.textContent = d;
    docSelect.appendChild(opt);
  });
  
  // 恢复选中值（如果在列表中）
  if (selected && doctors.indexOf(selected) !== -1) docSelect.value = selected;
}
```

#### 4. JS：绑定刷新按钮

```javascript
document.getElementById('export-refresh-btn').addEventListener('click', function() {
    loadExportRecords(); // 重新读取弹窗内筛选值，发起API请求
});
```

### 注意事项

- **不要依赖主页筛选作为导出数据源** — 用户可能调整了主页筛选但不记得，或者根本没调整
- **每次打开弹窗时自动加载一次数据** — 默认显示最新200条，但不自动继承主页的任何筛选
- **筛选下拉从已加载的记录中填充** — 保证下拉选项与实际数据一致
- **刷新按钮保留选中的值** — 用户切换筛选后点击刷新，下拉应记住当前选中项（如果还在新数据中）
- **导出的 Excel 内容也应包含筛选相关的列** — 如果用户能按医生筛选，导出的 Excel 中也要有医生列

### 相关信号

| 用户表述 | 对应问题 |
|---------|---------|
| "只能导出状态，日期什么的" | 导出功能缺少筛选维度 |
| "想导出一个医生的，他把所有医生都导出来" | 导出时未应用医生筛选 |
| "给我把所有的医生都导出来了" | 导出没有按医生维度过滤 |

## 来源

- 项目：gaofang-v2 (膏方管理系统)
- 文件：static/js/common.js, static/index.html
- 修改日期：2026-05-25
