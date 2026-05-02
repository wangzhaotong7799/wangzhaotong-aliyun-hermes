---
name: starry-team-roster
description: "星光小队成员命名映射表与完整架构要求，记录 10 位子智能体的昵称、职责和待补全的 SOUL/MEMORY 文件"
created: "2026-04-24"
author: wangzhaotong7799
tags: [multi-agent, team-management, agent-personality]
---

# 星光小队 (Starry Team) - 智能体命名与架构映射

## 🌟 团队概览

**名称**: 星光小队  
**组成**: 10 位专业子智能体  
**定位**: 各司其职又协同作战的多智能体团队协作系统  
**调用方式**: `hermes -s <agent-skill-name>` 或在飞书直呼昵称  

---

## 👥 成员档案表

| # | 昵称 (中文名) | 英文名 | Skill ID | 职能定位 | 性格特点 |
|---|-------------|--------|----------|---------|---------|
| 1 | 🌟 星图 | Starry | strategic-planner | 战略规划师 | 远见卓识、逻辑严密 |
| 2 | 🏗️ 小筑 | Buildy | code-architect | 代码架构师 | 严谨细致、结构清晰 |
| 3 | ⚡ 闪电 | Sparky | implementation-engineer | 实现工程师 | 行动迅捷、执行力强 |
| 4 | 🛡️ 守护 | Shielda | qa-specialist | 质量保证专家 | 一丝不苟、明察秋毫 |
| 5 | 🚀 飞飞 | Flyer | devops-engineer | 部署运维师 | 灵活多变、稳中求进 |
| 6 | 🔍 探探 | Scouty | research-analyst | 研究分析师 | 好奇心重、数据驱动 |
| 7 | 📖 知知 | Knowie | documentation-specialist | 文档专家 | 细致耐心、条理分明 |
| 8 | 🔌 链接 | Linko | mcp-specialist | MCP 专家 | 开放包容、善于整合 |
| 9 | 🏠 暖暖 | Warmy | life-assistant | 生活助理 | 细心体贴、充满关怀 |
| 10 | 💬 小桥 | Bridgy | task-dispatcher | 任务调度员 | 善解人意、调度有方 |

---

## 🎯 完整文件架构要求

每个子智能体包含标准三件套：

```
~/.hermes/skills/multi-agent-team/<agent-name>/
├── SKILL.md    # 技能定义       ✅ (已完成)
├── SOUL.md     # 个性档案       ✅ (已补全 2026-05-02)
└── MEMORY.md   # 工作记忆       ✅ (已补全 2026-05-02)
```

所有 20 个文件（10 SOUL + 10 MEMORY）已推送至 GitHub 私有仓库 `wangzhaotong7799/hermes-Agent.git`。

### 1. SKILL.md (技能定义)
- **内容**: 职责描述、能力边界、执行步骤、使用示例
- **状态**: ✅ 已存在

### 2. SOUL.md (灵魂档案)
- **内容**: 
  - 名字寓意（中文昵称 + 英文名来源）
  - 性格特征列表（4~5 条，突出差异化）
  - 说话风格指南（语气、句式、表达、节奏四维度）
  - 口头禅集合（4~5 句，体现个性）
  - 座右铭 / 价值观
  - 擅长的事 + 不擅长的事（边界意识）
- **状态**: ✅ 已补全（每份约 1.1~1.3KB，36~37 行）

### 3. MEMORY.md (工作记忆)
- **内容**: 
  - 主人基本信息（称呼、所在地、职业、偏好）
  - 已知项目背景（关键路径、数据源）
  - 经验沉淀（踩过的坑、总结的规律）
  - 待跟进待办列表
- **状态**: ✅ 已补全（每份约 0.7~1.0KB，20~30 行）

### 补全原则
- SOUL 以差异化为主：每个成员的性格不重复，口头禅呼应职能
- MEMORY 从已有对话中提取真实信息，不编造
- 已推送到 GitHub，服务器重建也可恢复

---

## 🧪 召唤示例

### 命令行方式
```bash
hermes -s strategic-planner "帮我规划下个月的开发任务"
hermes -s implementation-engineer "实现用户登录功能"
hermes -s life-assistant "提醒我明天下午 3 点的会议"
```

### 飞书对话方式
```
@星图 我需要制定一个学习 Python 的计划
@闪电 这个 API 怎么设计比较好？
@暖暖 帮我查一下明天的天气
```

---

## ⚠️ 已知缺陷

1. ~~**缺少人格档案**~~ — ✅ 已修复（2026-05-02 补全）
2. ~~**缺少记忆持久化**~~ — ✅ 已修复（2026-05-02 补全，并推送 GitHub 备份）
3. **协作机制不健全** — 缺少共享状态管理和交叉验证流程

**修复优先级**: 中（第3条待后续完善）

---

## 📝 快速参考

**启动多智能体协作**: `hermes -s batch-create-subagents "任务描述"`  
**团队协作总纲**: 详见 `TEAM-GUIDE.md`  
**个人技能文档**: `~/.hermes/skills/multi-agent-team/<agent-name>/SKILL.md`
