# 🏗️ 小筑 (Buildy) — 工作记忆

## 👤 主人信息
- **技术栈偏好**：Python Flask、SQLite/PostgreSQL、jQuery-free 前端
- **项目路径**：`/root/projects/drug-distribution-system/gaofang-v2/`
- **架构纪律**：宝塔面板不动原则、铁律第 7 条

## 📋 系统架构知识
- 膏方系统 V2：Flask + gunicorn + venv38，运行在 8080 端口
- PWA 移动端：`static/mobile/` 独立目录，vanilla JS + CSS3
- 数据库模型：PrescriptionRecord 含 follow_up_status 多阶段字段

## 🧠 架构决策记录
- 移动端 PWA 零后端改动原则（独立 /mobile/ 目录）
- 单页面预加载 + 其他页面懒加载策略
- gunicorn 23.0.0 + --reuse-port 防止端口占用崩溃

## ⏳ 待跟进
- [ ] 了解主人对 API 版本管理的偏好
- [ ] 记录数据库表结构变更历史
