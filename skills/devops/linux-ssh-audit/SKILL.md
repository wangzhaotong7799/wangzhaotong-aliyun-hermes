---
name: linux-ssh-audit
description: Complete guide to SSH login auditing across different Linux distributions, with troubleshooting for common log location issues and security best practices.
tags: [security, audit, logging, ssh]
---
# Linux SSH 审计与日志查看

## 概述

本技能介绍如何在不同 Linux 发行版上查看 SSH 登录历史和审计日志。关键点是**不同发行版的日志位置不同**。

## 快速诊断流程

### 1. 确认系统类型和日志位置

```bash
# 查看可用的日志文件
ls -lh /var/log/ | grep -E "log|messages|auth|secure"

# 系统类型判断
cat /etc/os-release | grep PRETTY_NAME
# - CentOS/RHEL/Fedora → /var/log/secure
# - Ubuntu/Debian → /var/log/auth.log
# - Alpine/SUSE → /var/log/messages
```

### 2. 查看 SSH 成功登录记录

```bash
# RHEL/CentOS (使用 secure)
sudo grep "Accepted" /var/log/secure | tail -50

# Ubuntu/Debian (使用 auth.log)
sudo grep "Accepted" /var/log/auth.log | tail -50

# 通用方式：检查所有可能位置
for logfile in /var/log/secure /var/log/auth.log /var/log/messages; do
    if [ -f "$logfile" ]; then
        echo "=== $logfile ===" && grep "Accepted" "$logfile" | tail -10
    fi
done
```

### 3. 查看失败的登录尝试

```bash
# 检测暴力破解尝试
sudo grep "Failed password\|Invalid user" /var/log/secure | tail -50

# 统计最频繁的攻击 IP
sudo grep "Failed password" /var/log/secure | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -20
```

### 4. 当前活跃会话

```bash
# 查看所有活动终端
who

# 显示详细登录信息（IP、时间）
w

# 查看最近登录记录
last -x 50
```

## 常见问题排查

### wtmp 为空或 last 命令无结果

```bash
# wtmp 可能被日志轮转清空，尝试从 secure/auth.log 直接提取
grep "Accepted" /var/log/secure | awk '{print $1, $2, $3}' | sort > recent_logins.txt
```

### 找不到认证日志

```bash
# 确认 rsyslog/journald 是否在运行
systemctl status rsyslog
systemctl status systemd-journald

# 使用 journalctl 查询（如果启用 systemd 日志）
journalctl _SYSTEMD_UNIT=sshd.service --since today | grep -i "accepted"
```

## 安全建议

### 识别可疑模式

| 异常迹象 | 说明 |
|----------|------|
| HTTP 请求到 SSH 端口 | 端口扫描攻击 |
| 大量 Failed password | 暴力破解 |
| 无效用户名尝试 | 用户枚举攻击 |
| 同一内网 IP 多账号登录 | 可能的内部威胁 |

### 推荐的防护措施

1. **Fail2Ban** - 自动封禁恶意 IP
2. **禁用 root SSH 登录** - 改用普通用户 + sudo
3. **使用密钥认证** - 禁止密码登录
4. **修改默认端口** - 减少自动化扫描

## 参考命令清单

```bash
# 完整的 SSH 审计快照
echo "=== Active Sessions ===" && who
echo "=== Recent Accepted Logins ===" && sudo grep "Accepted" /var/log/secure 2>/dev/null || sudo grep "Accepted" /var/log/auth.log 2>/dev/null || echo "No log found"
echo "=== Recent Failures ===" && sudo grep "Failed password" /var/log/secure 2>/dev/null || sudo grep "Failed password" /var/log/auth.log 2>/dev/null || echo "No log found"
echo "=== Last Commands by Root ===" && history 2>/dev/null | tail -20
```

## 注意事项

⚠️ 不要依赖单一日志源 —— `wtmp` 可能为空，某些云服务器会清理本地日志  
⚠️ 阿里云等云平台的内网 IP 可能与公网 IP 不同（如 100.104.x.x vs 112.103.x.x）  
⚠️ 日志轮转可能导致旧记录被压缩为 `.gz` 文件，需使用 `zgrep` 查看
