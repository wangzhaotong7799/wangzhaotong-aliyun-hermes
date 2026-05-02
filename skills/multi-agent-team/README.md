# 🎭 Hermes 多智能体团队协作系统

## 🌟 项目简介

这是一个专为 **Hermes Agent** 构建的专业化多智能体团队，包含 10 个角色各异的子智能体。通过协同工作，能够高效完成从项目规划到部署上线的全流程任务，以及日常生活管理。

---

## 📦 已交付内容

### ✅ 10 个专业子智能体

| # | 智能体名称 | 技能 ID | 状态 |
|---|---------|--------|------|
| 1 | 📋 战略规划师 | strategic-planner | ✅ 完成 |
| 2 | 🏗️ 代码架构师 | code-architect | ✅ 完成 |
| 3 | 💻 实现工程师 | implementation-engineer | ✅ 完成 |
| 4 | 🛡️ QA 专家 | qa-specialist | ✅ 完成 |
| 5 | 📊 研究分析师 | research-analyst | ✅ 完成 |
| 6 | 📝 文档专家 | documentation-specialist | ✅ 完成 |
| 7 | 🚀 运维师 | devops-engineer | ✅ 完成 |
| 8 | 🔌 MCP 专家 | mcp-specialist | ✅ 完成 |
| 9 | 🏠 生活助理 | life-assistant | ✅ 完成 |
| 10 | 🤝 沟通协调员 | communication-coordinator | ✅ 完成 |

### ✅ 配套工具

- ✅ TEAM-GUIDE.md - 完整使用指南
- ✅ multi-agent-orchestrator.py - Python 调度器脚本  
- ✅ README.md - 本文件

### ✅ 所有文件位置

```
~/.hermes/skills/multi-agent-team/
├── strategic-planner/SKILL.md
├── code-architect/SKILL.md
├── implementation-engineer/SKILL.md
├── qa-specialist/SKILL.md
├── research-analyst/SKILL.md
├── documentation-specialist/SKILL.md
├── devops-engineer/SKILL.md
├── mcp-specialist/SKILL.md
├── life-assistant/SKILL.md
├── communication-coordinator/SKILL.md
├── TEAM-GUIDE.md
├── multi-agent-orchestrator.py
└── README.md (本文件)
```

---

## 🚀 快速开始

### 方式一：直接在会话中使用

```bash
# 启动 Hermes 会话后，加载需要的智能体
/skill strategic-planner
/skill code-architect
/skill implementation-engineer

# 或者批量加载多个
/skill communication-coordinator,life-assistant,mcp-specialist
```

### 方式二：命令行启动

```bash
# 单个智能体
hermes -s strategic-planner "帮我规划一个电商项目的执行计划"

# 多个智能体
hermes -s code-architect,qa-specialist "设计并审查这个 API 接口"
```

### 方式三：使用调度器（高级）

```bash
# 运行调度器
python ~/.hermes/skills/multi-agent-team/multi-agent-orchestrator.py list

# 查看可用任务类型
python ~/.hermes/skills/multi-agent-team/multi-agent-orchestrator.py types

# 启动一个全栈项目
python ~/.hermes/skills/multi-agent-team/multi-agent-orchestrator.py \
    run full_stack_project "开发哈尔滨本地生活服务系统"
```

---

## 🎯 典型应用场景

### 场景 1: 从零开始一个完整项目

```
第 1 步：战略规划
/skill strategic-planner
→ 输入："我要开发一个在线教育系统"
→ 输出：详细的分阶段实施计划

第 2 步：系统设计  
/skill code-architect
→ 输入：[步骤 1 的计划]
→ 输出：技术架构图和选型建议

第 3 步：并行开发
/skill implementation-engineer,research-analyst
→ 工程师写代码，研究员调研竞品

第 4 步：质量保障
/skill qa-specialist
→ 测试代码、安全审计

第 5 步：文档编写
/skill documentation-specialist
→ API 文档、用户手册

第 6 步：部署上线
/skill devops-engineer
→ CI/CD 配置、生产环境部署

全程跟踪:
/skill communication-coordinator
→ 协调各方进度、向主人汇报
```

### 场景 2: 日常技术咨询

```
主人："这个函数怎么优化？"

自动匹配:
implementation-engineer → 代码优化建议
qa-specialist → 性能测试建议
communication-coordinator → 汇总回答
```

### 场景 3: 哈尔滨本地生活服务

```
主人："明天想去太阳岛，怎么安排？"

直接调用:
/skill life-assistant
→ 查询天气 + 交通建议 + 游玩提醒 + 餐饮推荐
```

---

## 💡 协作机制说明

### 智能体间的通信流程

```
主人提出需求
    ↓
沟通协调员接收 → 分析任务类型 → 分配给合适的智能体
    ↓
各专业智能体并行或串行执行
    ↓
沟通协调员收集结果 → 整合成统一答案 → 汇报给主人
```

### 何时需要多个智能体？

| 任务复杂度 | 建议配置 | 示例 |
|-----------|---------|------|
| ⭐ 简单 | 1 个智能体 | 查资料、改文件 |
| ⭐⭐ 中等 | 2-3 个智能体 | 小功能开发、数据报告 |
| ⭐⭐⭐ 复杂 | 4-6 个智能体 | 完整项目开发 |
| ⭐⭐⭐⭐ 超复杂 | 全部 10 个 | 大型产品从 0 到 1 |

---

## 🔍 验证安装

运行以下命令检查是否成功安装：

```bash
# 检查技能目录
ls ~/.hermes/skills/multi-agent-team/

# 应该看到这些文件：
# - 10 个子目录（每个智能体的 SKILL.md）
# - TEAM-GUIDE.md
# - multi-agent-orchestrator.py
# - README.md
```

---

## 📖 详细文档

请阅读 [TEAM-GUIDE.md](./TEAM-GUIDE.md) 获取：
- 完整的智能体介绍
- 详细的协作流程图
- 最佳实践指南
- 故障排查 FAQ

---

## 🎉 特色亮点

✅ **哈尔滨本地化**: 生活助理集成了哈尔滨特色服务和冬季防寒指南  
✅ **MCP 工具集成**: 专门的 MCP 专家负责工具生态建设  
✅ **全流程覆盖**: 从需求分析到上线部署的完整闭环  
✅ **灵活组合**: 可根据任务动态选择智能体组合  
✅ **专业分工**: 每个智能体都有明确的职责边界  

---

## 🤝 后续扩展

您可以根据需要添加更多专业智能体：

- AI 训练专家 - 模型微调和数据准备
- UI/UX设计师 - 界面设计和用户体验
- 产品经理 - 需求分析和功能优先级
- 法律合规顾问 - GDPR 和隐私政策
- 国际化专家 - 多语言和本地化支持

只需按照现有格式创建新的 `SKILL.md` 文件即可！

---

## 📊 版本信息

- **版本**: 1.0.0
- **创建日期**: 2026-04-22
- **所有者**: 主人（黑龙江哈尔滨）
- **维护者**: Multi-Agent Team Development Group

---

## 🎁 致谢

感谢主人的信任和授权，让我们有机会构建这套专业的多智能体系统！

**祝使用愉快！** 🎊
