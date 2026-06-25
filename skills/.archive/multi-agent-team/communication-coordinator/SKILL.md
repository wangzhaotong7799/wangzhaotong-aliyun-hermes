---
name: communication-coordinator  
description: [已迁移] 原沟通协调员功能已拆分为 task-dispatcher(分发) + result-aggregator(聚合),保留此技能用于兼容旧代码
version: 1.5.0 (deprecated)
author: Multi-Agent Team  
tags: [coordination, legacy, compatibility]
toolsets_required: ['file', 'terminal']
category: multi-agent-team
metadata:
  agent_type: legacy_coordinator
  team_role: 沟通协调 (legacy)
  priority: low
  memory_enabled: true
  permission_level: read-only
  deprecated_since: "2.0.0"
  migration_path: "task-dispatcher + result-aggregator"
---

# 🤝 沟通协调员 (Communication Coordinator) - Legacy Version

## ⚠️ 弃用通知

**重要**: 从 v2.0.0 开始，本角色已被拆分为两个专用角色:

| 原功能 | 新角色 | 说明 |
|-------|--------|------|
| 任务分配和调度 | `task-dispatcher` | 更智能的路由和负载均衡 |
| 结果整合汇报 | `result-aggregator` | 专业的文档合成能力 |

**建议**: 新任务请使用上述两个角色，本技能仅保留用于兼容历史项目。

---

## 📋 原始职责 (供参考)

### 1. 任务分配 - 现由 Task Dispatcher 负责
- 分析主人需求
- 匹配合适智能体
- 创建任务队列

### 2. 进度追踪 - 现由 Shared State Manager 支持
- 监控各阶段状态
- 记录执行日志
- 生成进度报告

### 3. 结果汇总 - 现由 Result Aggregator 负责
- 收集多方产出
- 整合成完整报告
- 向主人汇报

---

## 🔄 迁移指南

### 原有调用方式 → 新方式

```bash
# ❌ 旧方式
/skill communication-coordinator
"帮我规划并开发一个电商系统"

# ✅ 新方式
# 步骤 1: 自动路由和分发
python multi-agent-orchestrator-v2.py add full_stack_project \
    "开发电商系统" 1

# 步骤 2: 执行任务链
python multi-agent-orchestrator-v2.py queue

# 步骤 3: 自动生成报告
# (result-aggregator 会在最后自动触发)
```

---

## 📈 版本历史

- **v1.5.0** (2026-04-23): 标记为 deprecated，添加迁移指引
- **v1.0.0** (2026-04-22): 初始版本
