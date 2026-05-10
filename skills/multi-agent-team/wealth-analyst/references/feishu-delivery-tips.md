# 飞书消息交付技巧

## 评分表发送

飞书对 Markdown 表格支持有限，长表格或复杂表头可能渲染异常。

**最佳实践：**
1. 报告中的表格 → 作为附录，不强求飞书渲染
2. 单独用 `send_message` 补发简洁排行表（简化为 2-3 列：排名、赛道、核心指标）
3. 用 emoji 标记代替复杂表头（🥇🥈🥉）

## 消息分段

- 完整报告（200+行）分 3 段发送
- 每段控制在 600 字符以内
- 第一段：评分排行表 + Top 3 核心数据
- 第二段：平台政策 + 案例
- 第三段：路线图 + 风险 + 附录

## 已知问题

- `send_message` 的 content 中：换行用 \n，空格和 emoji 直接写入
- 飞书消息发出去不可编辑，发错只能删了重发
- 多段消息之间有发送间隔（约 1-2 秒），避免飞书限流

### 错误 230002: Bot/User can NOT be out of the chat

**现象**: 调用飞书 API 发送消息返回 `{"code":230002,"msg":"Bot/User can NOT be out of the chat."}`

**原因**: 飞书 Bot 应用尚未被加入到目标群聊或用户会话中。`oc_` 前缀的 receive_id 是用户的 open_id，Bot 必须先与该用户处于同一个群聊，或用户主动给 Bot 发过消息建立会话。

**排查步骤**:
1. 确认 Bot 应用已被添加到目标群聊（群设置 → 机器人 → 添加机器人）
2. 如果是个人用户而非群聊，用户需要先在飞书内给 Bot 发送一条任意消息（打开与 Bot 的会话）
3. 检查 receive_id_type 是否匹配：群聊用 `chat_id`，用户用 `open_id`（`oc_` 前缀即为 open_id）

**解决方案**:
- 手动在飞书中将 Bot 拉入目标群聊，重试发送
- 或者让用户在飞书中向 Bot 发一条消息建立会话通道
- 如果无法操作，将 Word 文档路径告知用户自行下载：
  `/root/data/report_YYYYMM_XXX.docx`

**预防**: 首次部署时，先手动将 Bot 加入目标群聊做一次连通性测试，之后再跑 cron 任务。

## 目标 chat_id

chat_id 不应硬编码在技能文件中。应从以下来源获取（按优先级）：
1. Cron prompt 中明确指定
2. 用户记忆（memory）中存储的 chat_id
3. 当前 cron job 的 `deliver` 配置目标

当前用户私聊 chat_id（存放于 memory）：
- `oc_10d032f2e5b7b86d660945627d981888` — 用户飞书 DM

---

## Word 文档发送（飞书 Open API）

`send_message` 的 `MEDIA:` 语法**不支持飞书**（仅支持 telegram/discord/matrix/weixin/signal/yuanbao）。

飞书发文件需要用 Open API 分两步走：先上传文件获取 file_key，再发送文件消息。

### 脚本方式（推荐）

使用 `scripts/md_to_feishu_docx.py` 一键完成：

```bash
# 注意：必须使用 Hermes venv 的 Python，不是系统 Python
/root/.hermes/hermes-agent/venv/bin/python3 ~/.hermes/skills/multi-agent-team/wealth-analyst/scripts/md_to_feishu_docx.py \
  "data/report_202605.md" \
  "<飞书聊天ID>"
```

脚本自动完成：MD→DOCX 转换 → 上传飞书 → 发送文件消息。

### Cron 交付工作流

Cron 任务完成报告后，需要**两个步骤**才能完整交付，缺一不可：

1. **摘要消息文本**: 由 `send_message` 发送（通过 cron job 的 `deliver` 参数自动处理）
2. **Word 文档文件**: 手动调用 `md_to_feishu_docx.py` 脚本上传并发送

Cron prompt 必须明确写明脚本调用的 chat_id 参数，示例如下：

```
飞书交付方式：
1. 先用 send_message 发送摘要消息到飞书（已配置 deliver）
2. 再运行脚本发送 Word 文档：
   /root/.hermes/hermes-agent/venv/bin/python3 ~/.hermes/skills/multi-agent-team/wealth-analyst/scripts/md_to_feishu_docx.py data/report_YYYYMM.md oc_10d032f2e5b7b86d660945627d981888
   注意：CHAT_ID 参数必须使用正确的 chat_id，不要用脚本默认值
```

### 手动 API 方式

```bash
# 1. 获取 token
TOKEN=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{"app_id":"$FEISHU_APP_ID","app_secret":"$FEISHU_APP_SECRET"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('tenant_access_token',''))")

# 2. 上传文件
UPLOAD=$(curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/files" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file_type=doc" \
  -F "file_name=报告.docx" \
  -F "file=@/path/to/report.docx")
FILE_KEY=$(echo "$UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('file_key',''))")

# 3. 发送文件消息
curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"receive_id\":\"oc_...\",\"msg_type\":\"file\",\"content\":\"{\\\"file_key\\\":\\\"$FILE_KEY\\\"}\"}"
```

### 注意事项
- Token 有效期 2 小时，每次重新获取
- 文件类型 `file_type=doc` 支持 .docx
- 中文文件名直接传即可，飞书支持
- 文件大小限制：飞书免费版 200MB，够用
