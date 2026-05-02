# 金脉小队 — Cron 定时任务注册表

定时任务可能因系统重启或 Hermes 内部状态重置而丢失。
此文件作为**备份源**——丢失后按以下配置重新创建。

创建命令：`cronjob(action='create', name='任务名', schedule='cron表达式', prompt='...', skills=['wealth-analyst'], enabled_toolsets=[...], deliver='feishu:oc_...')`

---

## 🛒 电商周报 (电商 weekly report)

- 名称: `电商周报`
- 调度: `0 5 * * 1` (每周一 05:00 CST)
- 技能: `wealth-analyst`
- 工具集: `[delegation, web, terminal, file, skills]`
- 交付: `feishu:oc_99961a56e530e89f7e369cd6ecb50218`
- 预计消耗: ~1.62M 输入 Token / ~6.5min
- 赛道数: 10

完整 Prompt:

```
CRON_MODE

域：电商
赛道：国内电商平台(淘宝/天猫/京东)、拼多多白牌、快手电商、视频号电商、
      直播电商(抖音)、社交电商(小红书/微信私域)、TikTok Shop、
      TEMU全托管、东南亚电商、即时零售
数据平台：综合
报告深度：完整版

按照猎财SOP，跳过域适配确认，直接按域配置执行全流程。
完成后将报告通过飞书发送给用户（摘要消息+Word文档附件）。
```

---

## 📱 自媒体周报 (自媒体 weekly report)

- 名称: `自媒体周报`
- 调度: `30 5 * * 1` (每周一 05:30 CST)
- 技能: `wealth-analyst`
- 工具集: `[delegation, web, terminal, file, skills]`
- 交付: `feishu:oc_99961a56e530e89f7e369cd6ecb50218`
- 预计消耗: ~924K 输入 Token / ~5min
- 赛道数: 8

完整 Prompt:

```
CRON_MODE

域：自媒体
赛道：短剧、本地生活、教育知识、美妆、美食、母婴、数码、健身
数据平台：抖音、小红书、B站、视频号、快手、TikTok
报告深度：完整版

按照猎财SOP，跳过域适配确认，直接按域配置执行全流程。
完成后将报告通过飞书发送给用户（摘要消息+Word文档附件）。
```

---

## 恢复流程

如果 `cronjob(action='list')` 返回 0 个任务：

1. 从本文件找到丢失的任务配置
2. 逐条执行 `cronjob(action='create', ...)` 重建
3. 用 `cronjob(action='list')` 验证恢复成功
4. 注意：两个任务的调度时间不重叠（05:00 vs 05:30），不冲突
