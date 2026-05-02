# ⚡ 闪电 (Sparky) — 工作记忆

## 👤 主人信息
- **项目根目录**：`/root/projects/drug-distribution-system/gaofang-v2/`
- **运行环境**：venv38 + gunicorn 23.0.0 + systemd
- **代码风格**：以实用为主，不过度抽象

## 📋 已知功能模块
- PWA 移动端：pickup / followup / reminders 三个页面
- API 端：prescriptions、follow-ups、reminders、assistants
- 前后端分离：JS fetch + Flask REST

## 🧠 开发经验
- PWA 是独立目录，不影响桌面端 SPA
- 状态筛选在 client 端做（filter + render），API 只做按需加载
- 编辑医助走 PUT /api/prescriptions/<id>，已有权限控制
- gunicorn 的 --reuse-port 是上线前一天加的

## ⏳ 待跟进
- [ ] 搜索功能是否支持拼音匹配
- [ ] 了解主人对代码注释风格的要求
