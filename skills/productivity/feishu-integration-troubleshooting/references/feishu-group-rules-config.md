# 按群配置权限：group_rules

## 场景

不想逐个添加用户 OpenID 到 `FEISHU_ALLOWED_USERS`，希望某个群里所有人都能 @机器人。

## 方案：config.yaml 中的 group_rules

在 `~/.hermes/config.yaml` 中为指定群聊设置 `group_rules`：

```yaml
platforms:
  feishu:
    group_rules:
      oc_1f9226e5dfa154dc80f30c94911f704d:
        policy: open           # open | disabled | admin_only | allowlist | blacklist
        require_mention: true  # 是否需要 @机器人 才触发
        # allowlist: []        # policy=allowlist 时生效，用户 OpenID 列表
        # blacklist: []        # policy=blacklist 时生效
      oc_7404e0fa8470ca3e7f04d614b806fdaf:
        policy: open
        require_mention: true
```

## 策略选项

| policy | 效果 |
|--------|------|
| `open` | 群聊中任何人（符合 `require_mention` 时需 @Bot）都能和 Bot 聊天 |
| `disabled` | 该群完全禁用 Bot |
| `admin_only` | 仅管理员（`admins` 列表中的用户）可用 |
| `allowlist` | 仅白名单用户可用（需配 `allowlist: [ou_xxx, ou_yyy]`） |
| `blacklist` | 黑名单用户不可用（其他人都可以） |

## 和 `FEISHU_ALLOWED_USERS` 的关系

- `FEISHU_ALLOWED_USERS`（全局环境变量）只对没有 `group_rules` 条目或 policy 设为 `allowlist`/`blacklist` 的群生效
- 设置了 `group_rules: { oc_xxx: { policy: open } }` 的群，允许谁用完全由该规则决定

## 修改后

修改完 config.yaml 后重启网关：

```bash
hermes gateway restart
```

## 适用范围

`group_rules` 支持按群 ID（`oc_xxx`）精准配置，适合：
- 内部测试群：`policy: open`，谁都能 @ 机器人
- 客户群：`policy: disabled`，机器人不参与
- 核心团队群：`policy: allowlist`，仅核心成员可用
