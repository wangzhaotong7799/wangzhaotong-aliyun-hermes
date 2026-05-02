# 🚀 飞飞 (Flyer) — 工作记忆

## 👤 主人信息
- **服务器**：阿里云 ECS，CentOS，公网 39.107.78.58
- **服务管理**：systemd + gunicorn + nginx
- **Python 环境**：venv38（Python 3.8 + gunicorn 23.0.0）

## 📋 已知服务器信息
- 内存 1.8G，Swap 6G（上次 OOM 后扩容的）
- Nginx 反向代理到 8080
- 日志路径：`gaofang-v2/logs/`
- systemd unit: `gaofang-v2-fusion.service`

## 🧠 运维经验
- RESTART 风暴预防：已加 --reuse-port
- OOM 防护：OOMScoreAdjust=-800
- 重启策略：Restart=always, RestartSec=10
- 日志轮转需关注磁盘空间

## ⏳ 待跟进
- [ ] 定期检查磁盘使用率
- [ ] 关注 OOM 是否复发
- [ ] 确认是否需要做日志轮转配置
