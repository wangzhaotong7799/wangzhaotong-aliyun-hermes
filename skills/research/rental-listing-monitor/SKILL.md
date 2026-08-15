---
name: rental-listing-monitor
description: "租房/房源信息监测 — 定时抓取租房平台列表页，指纹去重后第一时间推飞书通知新房源"
version: 0.1.0
author: Hermes Agent
tags: [rental, scraper, monitoring, feishu, 租房, 监测]
toolsets_required: ['terminal', 'web', 'cron']
category: research
metadata:
  hermes:
    tags: [rental, monitor, scraper, 租房, 监测]
  applicability: rental-listing-monitoring
  priority: medium
---

# 租房信息监测（Rental Listing Monitor）

## 适用场景

主人要求**监测特定小区/区域的最新租房信息**，第一时间发现新房源并通知（如"监测哈尔滨格兰云天小区租房"）。2026-08-15 首次需求：来源 = 贝壳找房 + 安居客 + 品阁地产（微信小程序），目标 = 格兰云天小区。

## 架构（设计定稿，待实现）

```
定时任务（cron，建议 30 分钟）
  ├─ 抓取各源列表页（安居客可直接 HTTP；贝壳需无头浏览器）
  ├─ 提取房源指纹（平台房源 ID = 唯一键）
  ├─ 对比 SQLite 历史指纹库（~/.hermes/rental_monitor.db 之类）
  ├─ 发现新 ID → 立即推飞书私聊（标题+价格+面积+链接）
  └─ 无新增 → 静默
```

- **指纹去重**：用平台房源 ID（安居客 10+ 位数字 ID）做唯一键，只推新 ID，不重复打扰。
- **推送格式**：一房源一消息（小区/户型/价格/楼层/面积/链接），可点开看详情。
- **频率**：默认 30 分钟一轮；上架后通常 10 分钟内被收录，30 分钟足够"第一时间"。
- **合规**：仅读取公开列表页做个人租房监测，低频轮询（不碰登录、不撞库、不加参数爆破）。
- **通知渠道**：飞书私聊（oc_10d032f2e5b7b86d660945627d981888），与周报同机制。

## 数据源可行性（2026-08-15 实测，哈尔滨）

| 源 | 状态 | 详情 |
|----|------|------|
| **安居客** | ✅ 可直接爬 | `https://m.anjuke.com/hrb/community/477940/rent/`（格兰云天）HTTP 200。移动端 URL 带 `m.` 前缀；需 `-L` 跟随 302（`/heb/` → `/hrb/` 重定向）。能提取房源 ID（`/rent/<10+位数字>` 正则）、价格（`class="...price..."` 块）、房型（`N室N厅`）。 |
| **贝壳找房** | ⚠️ 反爬强 | `m.ke.com` 移动端返回 404 错误页（P2PBUY 壳）、PC `hrb.ke.com` 302 跳转。直连不可行，需无头浏览器（playwright）或逆向移动 API。服务器仅 1.8G 内存，无头浏览器方案吃紧——建议最后再攻。 |
| **微信小程序** | ❌ 服务器不可直连 | `#小程序://品阁地产/yoiLqyqXXiGOJLy` 是微信内部协议链接，服务器无法访问。替代：① 主人在手机装抓包 App（Stream/HttpCanary）逛小程序导出发我 → 拿到 API 地址和返回结构，若无需签名则服务器直调；② 找该中介在 58/安居客/房天下的店铺页（多平台同步发房）。 |
| **房天下** | ⚠️ 需登录 | `m.fang.com/zf/hrb_xm1910157983` 抓到的页面重定向到 passport 登录页，含房源数据少。 |
| **骄阳地产** | 🔶 可试 | `www.55555558.com`（哈尔滨本地中介平台）HTTP 200，有 `api.55555558.com` API 域名线索，品阁小区页面有 50 套房源。 |

## 关键信息速查

- **品阁地产 = 黑龙江省品阁房地产经纪有限公司**（58 有招聘页佐证），注意是"品阁"不是"品格"（主人第一次发的是"品格"，搜索无果，实际应为"品阁"）。
- 格兰云天：哈尔滨香坊区（哈慈区域），安居客 community ID = **477940**，贝壳小区 ID = 4220031685046012。
- 提取正则（安居客移动端实测）：
  - 房源 ID：`/(?:rent/)?(\d{10,})`
  - 价格：`class="[^"]*price[^"]*"[^>]*>([^<]+)`（取数字段）
  - 房型：`([\d]+室[\d]+厅[^<"]{0,50})`
- 反爬通用对策：`curl` 带移动端 UA（iPhone Safari）；`-L` 跟随重定向；验证用 `python urllib` 避免 rtk 输出截断误导（`curl -s | grep` 结果不可信，rtk 会把 stdout 截到 ~582B）。

## 下一步（主人确认后执行）

1. **安居客单源版先上线**（1 小时可交付）：cron 脚本抓 `m.anjuke.com/hrb/community/477940/rent/` → SQLite 指纹库 → 新房源推飞书。→ 实现后看 `references/` 里的验证数据。
2. **品阁**：等主人抓包配合，或找品阁在平台的店铺页。
3. **贝壳**：最后用 playwright 无头浏览器，评估 1.8G 内存可行性。

## 相关技能

- 定时任务与飞书推送 → `server-health-monitor`（cron 模式）、`webhook-subscriptions`
- 数据抓取（页面提取工具）→ `ecommerce-price-research`（价格验证思路类似，禁止从摘要推断）

## References

- `references/anjuke-harbin-probe.md` — 安居客格兰云天抓取探针（2026-08-15 实测）：目标 URL、curl 命令、已验证正则提取、各源反爬状态备忘。
