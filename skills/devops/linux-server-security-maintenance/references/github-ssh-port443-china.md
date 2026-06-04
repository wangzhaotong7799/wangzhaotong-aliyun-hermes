# GitHub SSH over Port 443（国内服务器网络优化）

## 背景

国内云服务器（阿里云、腾讯云、华为云等）对 GitHub SSH 的默认 port 22 数据通道有**不同程度的防火墙干扰**：

- SSH 认证握手（指纹验证、密钥交换）通常可以正常通过
- 但 `git push` / `git fetch` 的数据传输阶段会被**拦截或严重降速**，表现为 5 分钟以上的超时失败

GitHub 官方提供了 SSH over HTTPS（port 443）作为备用方案。

## 解决方案

### 配置 `~/.ssh/config`

```bash
cat > ~/.ssh/config << 'EOF'
Host github.com
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile ~/.ssh/id_rsa
    IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
```

> **关键细节**：`IdentityFile` 必须指向本地实际存在的私钥文件。常见的密钥文件名有 `id_rsa`、`id_ed25519`、`id_ecdsa` 等。先用 `ls ~/.ssh/` 确认实际文件名，再填入配置。

### 添加主机密钥

首次连接 `ssh.github.com:443` 需要添加 host key：

```bash
ssh-keyscan -p 443 ssh.github.com >> ~/.ssh/known_hosts
```

### 验证连接

```bash
ssh -T -p 443 git@ssh.github.com
```

预期输出：
```
Hi <username>! You've successfully authenticated, but GitHub does not provide shell access.
```

### 测试数据传输

```bash
cd /path/to/repo
git push origin main
```

预期：正常推送完成，无超时。

## 常见陷阱

| 陷阱 | 表现 | 解决 |
|------|------|------|
| `IdentityFile` 指向不存在的密钥 | `no such identity: ...` + `Permission denied` | 用 `ls ~/.ssh/` 确认实际密钥文件名 |
| 未添加 host key | `Host key verification failed.` | 运行 `ssh-keyscan -p 443 ssh.github.com >> ~/.ssh/known_hosts` |
| 配置后 `git push` 仍走 port 22 | `git push` 超时不走 443 | 确认 `~/.ssh/config` 中 `Host github.com` 正确，且 config 权限为 600 |
| 多人协作时身份混淆 | 推送被拒绝 | 可添加多个 `IdentityFile` 配合 `Match` 条件，或用 `GIT_SSH_COMMAND` 临时覆盖 |

## 验证配置生效

配置正确后，`git push` 的耗时应大幅下降（从 5+ 分钟超时降到 10-30 秒完成推送）。
