# Scrapling 实地测试：番茄小说

> 测试日期：2026-05-26
> Scrapling v0.4.8 | Alibaba Cloud Linux 3

## 结论总览

| 采集层 | 可用性 | 阻礙因素 |
|--------|:------:|---------|
| 首页/推荐榜 | ✅ 通 | 无防爬 `/api/rank/recommend/list` |
| 最近更新 | ✅ 通 | `/api/rank/recent/update/list` |
| 小说详情 | ✅ 通 | `/api/book/info` |
| 章节目录 | ✅ 通 | `/api/reader/directory/detail` |
| **章节正文** | **❌ 被盾** | **百度Turing验证码** |

## 关键发现

### 1. 番茄小说的防护体系

番茄小说使用**三层防护**：

- **第一层**：TLS指纹检测（curl_cffi 轻松过）
- **第二层**：SPA架构 + Token（简单，API加Referer/Origin就过）
- **第三层（章节正文专属）**：**百度Turing验证码（滑块验证）**
  - 触发条件：调用 `/api/reader/full` 获取章节正文时
  - 响应特征：HTTP 200，Content-Length: 0，Header 带 `bdturing-verify`
  - 所有其他API（info/directory/list等）均**不触发**此验证

### 2. Scrapling StealthyFetcher 浏览器适配

**Alibaba Cloud Linux 3** 缺少Playwright必需的动态库：

```bash
# 缺失的库（按序补齐）
yum install -y atk at-spi2-atk libX11 libxcb libXcomposite \
  libXcursor libXdamage libXext libXi libXrandr libXrender \
  libXtst pango cairo gdk-pixbuf2 cups-libs
yum install -y mesa-libgbm libwayland-server
```

浏览器下载（不走apt-get的情况下）：
```bash
# --with-deps 不能用，因为没有 apt-get
/root/.hermes/hermes-agent/venv/bin/python -m playwright install --force chromium
# 约170MB，下载耗时依赖网络，国内需2-5分钟
```

### 3. Scrapling 当前的反爬能力边界

| 反爬类型 | Scrapling 自解 | 备注 |
|---------|:-------------:|------|
| Cloudflare Turnstile | ✅ 自动 | `solve_cloudflare=True` |
| Cloudflare Interstitial | ✅ 自动 | 同上 |
| TLS指纹检测 | ✅ 自动 | curl_cffi + 浏览器 |
| 浏览器自动化检测 | ✅ StealthyFetcher | PatchRight注入 |
| **百度Turing验证码** | **❌ 不支持** | 需要第三方打码服务 |
| 极验/geetest | ❌ 不支持 | 同上 |
| 登录态验证 | ❌ 需Cookie | 手动传入 |

### 4. 番茄小说的正确采集策略

```
搜索/发现 → 目录/详情 → 章节正文
   ✅可用         ✅可用         ❌被盾
```

章节正文的正确解法：
1. **带Cookie登录** — 用真实浏览器登录后导出Cookie，通过 `StealthySession` 传入
2. **第三方打码服务** — 对接2Captcha/AnyCaptcha等过百度Turing
3. **引导用户去App看** — 番茄小说本身就是免费阅读平台，正文内容对用户可免费获取

## API端点清单（已验证可用）

| 端点 | 方法 | 参数 | 用途 |
|------|------|------|------|
| `/api/rank/recommend/list` | GET | `type`, `limit`, `offset` | 推荐列表 |
| `/api/rank/recent/update/list` | GET | `limit`, `offset` | 最近更新 |
| `/api/banner/list` | GET | `location` | 首页Banner |
| `/api/book/info` | GET | `bookId` | 书籍详情 |
| `/api/reader/directory/detail` | GET | `bookId` | 完整目录+章节ID |
| `/api/reader/directory/list` | POST | `itemIds[]` | 批量章节信息 |
| `/api/reader/full` | GET | `itemId` | **章节正文（被盾）** |
