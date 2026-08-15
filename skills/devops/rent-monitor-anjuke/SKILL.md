---
name: rent-monitor-anjuke
description: "格兰云天租房监控 — 安居客房源抓取、SQLite指纹去重、飞书新房源推送"
version: 1.0.0
author: Hermes Agent
tags: [rent, anjuke, monitor, feishu, crawler]
toolsets_required: ['terminal', 'file']
category: devops
metadata:
  hermes:
    tags: [租房, 监控, 安居客]
  applicability: rent-monitoring
  priority: medium
---

# 格兰云天租房监控（安居客源）

## 适用场景

主人要求监测哈尔滨格兰云天小区最新租房信息，第一时间推送飞书。当前已上线安居客源（2026-08-15），待接入品阁地产小程序（需抓包）和贝壳（反爬）。

## 核心文件

- **脚本**：`/root/.hermes/scripts/monitor_gelan_rent.py`
- **指纹库**：`~/.hermes/rent_monitor/gelan_yuntian.db`（SQLite，表 houses，主键 house_id）
- **日志**：`~/.hermes/rent_monitor/monitor.log`
- **cron**：`*/30 * * * *`（每30分钟，系统 python3）

## 运行模式

```bash
python3 monitor_gelan_rent.py            # run：抓3页→去重→新房源推送飞书；无新增静默
python3 monitor_gelan_rent.py --init     # 初始化指纹库（抓取入库，不推送）
python3 monitor_gelan_rent.py --test     # 测试：打印当前房源，不写库不推送
```

## 双层去重（2026-08-15 修复重复通知 bug）

**问题**：安居客经纪人常用多个 ID 重复发布同一套房源（标题/价格/户型几乎相同），纯 ID 去重会把每套重复发布的都推一遍，主人看到"重复通知"。

**修复**：`houses` 表加 `fingerprint` 列（内容指纹 = price|room|标题核心）。run 模式判定新房源必须 **ID 不在库 且 指纹不在库** 双重条件：

- `make_fingerprint()`：去空白、去营销词（格兰云天/电梯房/精装修/家电齐全/拎包入住/急租/随时看/南北通透等）、去数字、去"卫"差异（"2室1厅1卫"与"2室1厅"同质），取核心前10字
- 实测 59 套中识别出 5 组重复（20 条同质房源），如 `1600|2室1厅|室厅` 组 6 条
- 验证：同指纹房源即使换新 ID 重新上架也不推送（下架→重抓→0新房源静默）

## 安居客页面结构要点（2026-08 实测）

- 列表 URL：`https://m.anjuke.com/hrb/community/477940/rent/`（格兰云天小区 ID=477940）
- 分页：`p2/` `p3/` 路径式（`?p=2` 无效！ID 会重复）
- 移动端 SSR 渲染房源块：`<li class="house-item-wrap">` 内 `href="https://heb.zu.anjuke.com/fangyuan/<ID>"` + `info-title` 标题 + `info-addr` 地址 + `info-room` 房型 + `price-num` 价格
- **默认智能排序，无"最新"排序参数**（p1o3/o2/sort=time 均无效）→ 靠指纹去重发现新房源，无需排序
- 抓3页约59套覆盖活跃在租；房源 ID 前13位是 Unix 毫秒时间戳（可用于判断上架时间）
- 反爬：UA 用 iPhone Safari 即可，无需登录/cookie；页间 sleep 1s 温和抓取

## 飞书推送（复用 li_chunfeng_clinic_reminder.py 模式）

- 从 `~/.hermes/.env` **raw bytes** 读 FEISHU_APP_ID/SECRET（read_file 会打码）
- tenant_access_token → `POST /open-apis/im/v1/messages?receive_id_type=chat_id` → chat_id=`oc_10d032f2e5b7b86d660945627d981888`（主人私聊）
- 推送格式：`🏠 格兰云天新房源 N 套` + 价格/房型/标题/链接，按价格升序，最多10条

## 扩展计划（待接入）

1. **品阁地产小程序**：`#小程序://品阁地产/yoiLqyqXXiGOJLy` 微信内部协议服务器无法访问 → 主人手机装 Stream 抓包 → 提取 API → 服务器直调轮询（若需签名 token 则定期更新）
2. **贝壳找房**：`m.ke.com` 移动端返回 404 反爬、PC 302 → 需无头浏览器（playwright，吃内存）或逆向 API，放最后

## 坑

- rtk 输出截断到 582B 会误导 curl/grep 验证 → 用 python urllib 验证线上内容
- cron 环境无 PATH，脚本内用绝对路径 + 系统 python3
