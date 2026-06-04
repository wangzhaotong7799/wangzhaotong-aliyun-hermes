# Alibaba Cloud Linux 3 安全加固实测记录

**日期**: 2026-06-01
**系统**: Alibaba Cloud Linux 3.2104 U13 (OpenAnolis Edition)
**内核**: 5.10.134-19.3.al8 → 5.10.134-19.6.al8（已安装待重启）
**内存**: 1.8GiB + 6GB swap（3 个 swap 文件）

## 安全更新概况

- 共 28 个安全通告：1 Critical + 22 Important + 5 Moderate
- 涉及包：openssh / sudo / kernel / nginx / vim / rsync / python3

## 已安装的安全更新

| 包 | 旧版本 | 新版本 |
|---|---|---|
| openssh-server | 8.0p1-28 | 8.0p1-29.0.1.1 |
| sudo | 旧版 | 1.9.5p2-1.0.2.al8.5 |
| nginx | 旧版 | 1.24.0-3.0.1.al8.1 |
| kernel | 5.10.134-19.3 | 5.10.134-19.6（待重启） |
| vim-enhanced | 旧版 | 8.0.1763-22.0.1.al8.3 |
| rsync | 旧版 | 3.1.3-25.0.1.al8 |

## SSH 加固前后对比

| 项目 | 改前 | 改后 |
|---|---|---|
| PermitRootLogin | yes（密码可登录） | prohibit-password（仅密钥） |
| PasswordAuthentication | yes | no |
| authorized_keys | 空文件（0字节） | 已注册本机 rsa 公钥 |

## 已知爆破尝试

```
May 31 07:17:45 Failed password for root from 154.8.177.123
Jun  1 08:33:33 Failed password for invalid user admin2 from 47.239.123.96
Jun  1 08:33:45 Failed password for invalid user adminuser from 47.239.123.96
```

## dmesg OOM 历史记录（旧日志，不影响当前）

| 启动后秒数 | 时间（约） | 被杀进程 |
|---|---|---|
| 3251s (~54min) | ~4月22日 | BT-Panel（已卸载） |
| 124243s (~1.4天) | ~4月24日 | hermes |
| 171492s (~2天) | ~4月24日 | hermes |
| 198366s (~2.3天) | ~4月24日 | hermes |

注：主机已配 6GB swap（/www/swap 1G + /www/swap2 2G + /swapfile 3G），OOM 问题已解决。

## swap 配置

```
NAME       TYPE SIZE   USED PRIO
/www/swap  file   1G 201.3M   -2
/www/swap2 file   2G     0B   -3
/swapfile  file   3G     0B   -4
```

## 关键命令备忘

```bash
# 安全更新相关
yum check-update --security          # 列出待处理安全更新
yum upgrade-minimal --security -y    # 只装安全更新，不升级功能版本
yum updateinfo list security all     # 查看所有安全通告详情

# 内核版本确认
uname -r                             # 当前运行的内核
rpm -q kernel                        # 所有已安装的内核版本

# SSH 加固
sshd -t                              # 配置语法检查
systemctl restart sshd               # 重启 SSH 服务
grep "Accepted" /var/log/secure      # 查看成功登录记录
grep "Failed password" /var/log/secure  # 查看爆破记录
```
