# PWA 客户端过滤 vs 服务端过滤 — 诊断记录

## 场景

膏方系统 V2 PWA，膏方领取页筛选标签（全部/欠药/未取/已取/已邮寄）。

## 症状

| 问题 | 预期 | 实际 |
|------|------|------|
| 未取数量 | 12 条 | 仅显示 3 条（第一页中的） |
| 已取数据 | 3176 条 | 显示「暂无处方记录」 |
| 总计 | 3489 | — |

## 根因

PWA 默认调用：`Api.getPrescriptions({ page: 1, per_page: 50, start_date: sixMonthsAgo })`

不传 `status` 参数 → 服务端返回第 1 页 50 条（全部状态）→ 客户端 `state.allData.filter()` 过滤。

但第 1 页（按 id DESC 排序的最新记录）分布：

| 状态 | 数量 |
|------|------|
| 欠药 | 47 |
| 未取 | 3 |
| 已取 | 0 |

所以「已取」客户端过滤永远返回 0 条。

## 复现步骤

```bash
# 1. 查数据库真实数据
PGPASSWORD=gaofang_password psql -h localhost -U gaofang_app -d gaofang_v2 \
  -c "SELECT status, COUNT(*) FROM prescription_records GROUP BY status ORDER BY status;"

# 2. 模拟 PWA 调用（不传 status）
curl -s "http://localhost:8080/api/prescriptions?page=1&per_page=50" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
s = {}
for i in data.get('data', []):
    st = i.get('status', '?')
    s[st] = s.get(st, 0) + 1
import pprint; pprint.pprint(s)
"

# 3. 验证服务端过滤（传 status=已取）
curl -s "http://localhost:8080/api/prescriptions?status=%E5%B7%B2%E5%8F%96&page=1&per_page=1" \
  | python3 -c "import json,sys; data=json.load(sys.stdin); print(f'total={data[\"total\"]}')"
# 输出: total=3176 ✅ 服务端过滤正常工作
```

## 修复

在 `page-pickup.js` 的 `fetchPage()` 中，将当前筛选标签的 `status` 值作为参数传给 API：

```javascript
function fetchPage(page) {
  var params = { page: page, per_page: 50 };
  
  // 如果有关键 start_date 参数（6个月范围），带上
  var sixMonthsAgo = new Date();
  sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
  params.start_date = sixMonthsAgo.toISOString().split('T')[0];
  
  // ★ 关键：把当前 status 传给服务端
  if (state.filter && state.filter !== '全部') {
    params.status = state.filter;
  }
  
  Api.getPrescriptions(params).then(function(resp) {
    state.allData = state.allData.concat(resp.data);
    state.hasMore = state.page < (resp.total_pages || 1);
    state.page = page;
    renderList();   // 此时 renderList 不需要再 filter 了
  });
}
```

切换筛选标签时重置并重新加载：

```javascript
// 筛选标签切换
filterTabs.addEventListener('click', function(e) {
  var tab = e.target.closest('.filter-tab');
  if (!tab) return;
  
  state.filter = tab.getAttribute('data-filter');
  state.allData = [];   // 清空
  state.page = 1;
  
  // 更新 active 样式
  document.querySelectorAll('.filter-tab').forEach(function(t) {
    t.classList.remove('active');
  });
  tab.classList.add('active');
  
  fetchPage(1);  // 重新加载
});
```

## 相关文件

- `static/mobile/js/page-pickup.js` — `fetchPage()` 和 `renderList()` 函数
- `api/v1/prescriptions.py` — 服务端 `get_prescriptions()` 函数（已支持 `status` 参数）

## 已学习教训

1. **分页 + 客户端过滤 = 反模式** — 当数据跨多页时，当前页不包含所有可能的状态
2. **服务端已有能力就用服务端** — 先查 API 是否支持 `status` 等参数，不支持再加
3. **每个筛选标签都问**：这个过滤是客户端做还是服务端做？分页场景默认服务端
