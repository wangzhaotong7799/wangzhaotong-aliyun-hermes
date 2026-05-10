# PWA 列表页数据合计数量栏

## 适用场景

移动端 PWA 的列表页面（膏方领取、复诊等），在筛选标签下方显示当前状态/搜索条件下的数据条数。

## 实现模式

### 1. HTML 容器

在筛选标签和列表之间插入 summary 容器：

```javascript
// render() 函数中
container.innerHTML = ''
  + '<div class="search-bar">...</div>'
  + '<div class="filter-tabs" id="pickup-filters">...</div>'
  + '<div id="pickup-summary" class="summary-bar"></div>'  // ← 新增
  + '<div id="pickup-list" class="loading"><div class="spinner"></div></div>';
```

### 2. CSS 样式

```css
.summary-bar {
  font-size: 13px;
  color: var(--gray-600);
  padding: 6px 2px 10px;
  text-align: left;
}
```

### 3. 状态变量

在 `state` 对象中新增 `totalCount`：

```javascript
var state = {
  allData: [],
  filter: '未取',
  search: '',
  totalCount: 0   // ← 服务端返回的总数
};
```

### 4. 更新函数

```javascript
function updateSummary(count) {
  var summaryEl = document.getElementById('pickup-summary');
  if (!summaryEl) return;
  var label = state.filter === '全部' ? '全部' : state.filter;
  // 有搜索词时用本地过滤数，无搜索时用服务端总数（更准确）
  var displayCount = state.search ? count : (state.totalCount || count);
  summaryEl.textContent = label + '：共 ' + displayCount + ' 条';
}
```

### 5. 调用时机

**在 renderList() 中**（每次渲染列表时更新）：

```javascript
function renderList() {
  var filtered = state.allData.filter(function(item) {
    // ... 搜索过滤逻辑 ...
  });

  // 更新合计数量
  updateSummary(filtered.length);

  // ... 渲染列表 ...
}
```

**在 fetchPage() 中**（每次加载数据时保存服务端总数）：

```javascript
Api.getPrescriptions(params).then(function(resp) {
  state.allData = state.allData.concat(newItems);
  state.page = page;
  // 保存服务端总数
  if (resp && resp.total !== undefined) {
    state.totalCount = resp.total;
  }
  renderList();
});
```

## 计数逻辑说明

| 场景 | 显示的计数 | 为什么 |
|------|-----------|--------|
| 无搜索词，加载第一页 | 服务端 total（如 `153 条`） | 服务端知道完整总数 |
| 无搜索词，加载更多后 | 仍保持服务端 total | 未刷新筛选，总数不变 |
| 有搜索词 | 本地过滤后的条数 | 搜索在客户端执行，服务端不知道 |
| 切换筛选标签 | 重新从第 1 页加载 → 服务端返回新 total | 筛选走服务端接口 |

## 已有实现

- `page-pickup.js`：膏方领取页
- 复诊页和提醒页可复用相同模式
