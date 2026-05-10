# PWA 拼音首字母搜索

## 背景

中文医疗管理系统的患者姓名搜索场景中，医助更习惯输入 **拼音首字母** 快速定位患者（如输入 `jsj` 找「姜树杰」），而非完整输入汉字。

## 实现方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| CDN 加载 `pinyin-pro` (50KB+) | 覆盖所有汉字 | 依赖外部网络，离线不可用 |
| **本地字典映射（本方案）** | 零依赖，离线可用 | 只覆盖常用汉字，生僻字需扩展 |
| 后端拼音搜索 | 准确性高 | 需要网络请求，有延迟 |

## 推荐做法：从数据库生成映射（🔥 最佳实践）

**不用手写字典**。直接从数据库患者姓名字段提取所有唯一汉字，用后端 `pypinyin` 库生成完整映射。

### 生成脚本

将以下脚本保存为 `scripts/gen-pinyin-map.py`：

```python
#!/path/to/venv/bin/python3
from pypinyin import lazy_pinyin, Style
import json

# 从数据库提取所有唯一中文姓名用字（按实际表结构调整）
# 示例：适用于 PostgreSQL
"""
SELECT DISTINCT unnest(regexp_split_to_array(patient_name, '')) AS ch
FROM prescription_records
WHERE patient_name ~ '[\\u4e00-\\u9fff]'
ORDER BY ch;
"""

# 将查到的所有字填入以下字符串
chars = "这里粘贴从数据库查到的所有唯一汉字"

# 生成拼音映射
result = {}
for c in chars:
    pinyin = lazy_pinyin(c, style=Style.FIRST_LETTER)[0].lower()
    result[c] = pinyin

# 按首字母分组
by_letter = {}
for ch, initial in result.items():
    by_letter.setdefault(initial, []).append(ch)

# 输出 JSON 格式的 PINYIN_MAP
output = {}
for letter in sorted(by_letter.keys()):
    chars_in_group = sorted(by_letter[letter])
    output[letter] = ''.join(chars_in_group)

print(json.dumps(output, ensure_ascii=False, indent=2))
```

### 生成的映射示例

从膏方系统 V2 数据库 3500+ 患者姓名中提取的完整映射（覆盖所有出现过的汉字），详见 `scripts/gen-pinyin-map.py` 运行结果。映射表包含约 1000+ 个汉字，覆盖 `a-z` 全部首字母。

> **注意**：不要手写字典！使用上面的 Python 脚本从数据库实际数据生成。每次数据库表中有新姓名用字出现时，重新运行一次脚本更新映射。

## 在搜索逻辑中集成

```javascript
// page-pickup.js
var filtered = state.allData.filter(function(item) {
  if (state.search) {
    var kw = state.search.toLowerCase();
    var name = (item.patient_name || '').toLowerCase();
    var id = (item.prescription_id || '').toLowerCase();
    var asst = (item.assistant || '').toLowerCase();
    if (name.indexOf(kw) !== -1 || id.indexOf(kw) !== -1 || asst.indexOf(kw) !== -1) {
      return true;
    }
    // 拼音首字母模糊查询（只在纯字母输入时触发）
    if (/^[a-z]+$/.test(kw)) {
      var nameInitials = PinyinUtil.getInitials(item.patient_name || '');
      if (nameInitials.indexOf(kw) !== -1) {
        return true;
      }
    }
    return false;
  }
  return true;
});
```

关键细节：
- **纯字母判断** `/^[a-z]+$/`：避免将汉字搜索路径与拼音路径混淆
- **`indexOf` 而非 `===`**：支持部分字母输入（`z` 匹配所有 z 开头的姓）
- **拼音只匹配姓名**：电话/代煎号/医助不走拼音

## HTML 中的引用顺序

```html
<script src="/mobile/js/router.js"></script>
<script src="/mobile/js/pinyin-util.js"></script>  <!-- ← 在页面模块之前加载 -->
<script src="/mobile/js/page-pickup.js"></script>
```

## 使用效果

| 输入 | 匹配姓名 | 说明 |
|------|---------|------|
| `z` | 张寿彭、周妍、张笑梅… | 单字母匹配所有姓/名含该首字母 |
| `jsj` | 姜树杰 | 全名首字母匹配 |
| `wsx` | 王双喜 | 三字姓名首字母 |
| `l` | 李薇、刘静华、刘彦… | 单一字母匹配 |

## 关键陷阱

### 1. 🔴 映射表不全导致漏人（真实教训）

**问题**：初始手写字典没有 "姜"、"树"、"杰" 等字，输入 `j` 搜不到"姜树杰"。

**原因**：常见字缩写表只覆盖了 1000+ 字，而患者姓名中的字不限于此集合。

**根治方案**：从数据库提取所有唯一汉字，用 `pypinyin` 生成完整映射。详见上方「推荐做法」章节。

### 2. 生僻字静默跳过

不在映射表中的汉字会被静默忽略，不影响其他字的匹配。

### 3. 数据库更新后映射过时

如果新导入的患者姓名包含映射表中没有的字，需要重新运行生成脚本更新 `pinyin-util.js`。

### 4. 🔴 Service Worker 缓存导致更新不生效（真实教训）

**问题**：更新了 `pinyin-util.js`（从数据库生成了完整映射），但用户刷新页面后输入 `j` 仍然搜不到"姜树杰"。

**根因**：PWA 的 Service Worker 使用 cache-first 策略，浏览器第一次加载 `pinyin-util.js` 后将其缓存。后续服务端文件已更新，但浏览器始终从缓存读取旧版本，永远不会发请求去服务器获取新文件。

```javascript
// sw.js 中的缓存策略
event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
    // ↑ cache-first: 有缓存就用缓存，不去网络
);
```

**修复方案（三步）：**

**① 更新 sw.js 缓存版本号**

```javascript
// 改之前
const CACHE_NAME = 'gaofang-mobile-v1';

// 改之后
const CACHE_NAME = 'gaofang-mobile-v2';
```

activate 事件中已有的清理逻辑会自动删除旧 cache：
```javascript
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
            );
        })
    );
    self.clients.claim();
});
```

**② sw.js 自身禁止 HTTP 缓存**

在 Flask 路由中设置 `sw.js` 不缓存：
```python
@app.route('/mobile/<path:path>')
def serve_mobile(path='index.html'):
    resp = send_from_directory('static/mobile', path)
    if path.endswith('sw.js'):
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
    return resp
```

**③ 告知用户操作**

| 设备 | 操作 |
|------|------|
| **iPhone Safari** | 设置 → Safari → 高级 → 网站数据 → 找到域名 → 删除 |
| **安卓 Chrome** | 地址栏锁图标 → 网站设置 → 清除数据 |
| **Chrome 桌面** | F12 → Application → Service Workers → Unregister |
| **所有浏览器** | 完全关闭 PWA 的所有标签页，重新打开 |

**为什么是 Service Worker 的问题不是浏览器普通缓存的问题？**
- 普通缓存（`Cache-Control` 头）只要文件内容变了下次请求就会取新文件
- Service Worker 的 `cache-first` 策略让浏览器**根本不发送网络请求**，直接从本地缓存服务
- 即使服务端文件已经更新，Service Worker 依然返回旧的缓存副本
- 这也是为什么更新 `pinyin-util.js`（或其他 JS/CSS 文件）后必须改 SW 版本号

**防御措施：**
- 所有静态文件（JS/CSS/HTML）的更新，都要先想 Service Worker 缓存在不在
- 养成习惯：前端文件改动后，顺手 `grep -n CACHE_NAME sw.js` 检查版本号，+1 递增
- 给 `sw.js` 加 HTTP 禁止缓存头（如上），确保浏览器下次访问时能检测到 SW 文件本身已更新

## 诊断方法

### 快速诊断：映射表是否损坏

看到 pinyin-util.js 后第一件事：**数一下 `"b"` 条目的字符数**。

#### 正常情况
```
"b": "丙伯佰冰博卜宝帮彪彬斌本柏毕波滨炳白鲍"  → 约 10~30 个汉字
```

#### 损坏情况（真实案例）
```
"b": "白柏鲍彪滨彬斌波柏本毕博炳冰伯卜宝...（共 2515 个字符）"
→ 所有汉字都被错误映射到了 'b' 桶！
```

**Python 一句话诊断：**
```bash
python3 -c "
import re
with open('pinyin-util.js') as f:
    m = re.search(r'\"b\":\s*\"([^\"]*)\"', f.read())
    print(f'b 桶: {len(m.group(1))} 字' if m else '未找到')
"
# 如果输出 > 200 → 映射表坏了，重新生成
```

#### 根因
生成脚本曾有一个 bug，写入 PINYIN_MAP 时所有字符都被分配到了同一个字母（通常是 'b'）。`gen-pinyin-map.py` 当前版本已修复此问题，但如果之前生成的旧版本被误部署，就会出现这个症状。**重新运行生成脚本即可恢复。**

### 浏览器控制台测试

```javascript
PinyinUtil.getInitials('姜树杰');
// 应返回 'jsj'
```

**文件更新后检查清单：**
1. ✅ `pinyin-util.js` 已更新（含所有新字）
2. ✅ `sw.js` 缓存版本号 +1
3. ✅ `sw.js` HTTP 缓存头已设置为 no-cache
4. ✅ 服务已重启
5. ✅ 用户已关闭 PWA 重新打开
