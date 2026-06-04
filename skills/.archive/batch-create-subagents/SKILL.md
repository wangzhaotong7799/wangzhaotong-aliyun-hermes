---
name: batch-create-subagents
description: 批量构建多专业子智能体团队的标准化工作流程 - 自动化生成、统一配置、质量验证
version: 2.0.0
author: Multi-Agent Team  
tags: [automation, batch-creation, team-building]
toolsets_required: ['file', 'terminal']
category: multi-agent-team
metadata:
  agent_type: batch_creator
  team_role: 团队构建工具
  priority: low
  memory_enabled: true
  permission_level: read-write
---

# 🔨 批量创建子智能体工具 (Batch Create Subagents) v2.0

## 🎯 核心定位与使命

### 我是什么？
我不是一个独立的智能体，而是一个**自动化工具集**,用于快速批量创建标准化的子智能体配置文件。我就像工厂的模具生产线，一次性产出规格统一的智能体基础结构。

### 我的核心价值
- **标准化**: 确保每个智能体遵循相同的质量标准
- **高效率**: 几分钟内完成原本需要数小时的工作
- **一致性**: 避免手工操作的遗漏和不一致
- **可扩展性**: 轻松复制新的智能体类型

---

## ⚠️ 使用注意事项

```
重要提示:
1. 本工具生成的只是基础模板，需要后续人工补充详细内容
2. 批量创建后必须逐一验证每个智能体的完整性
3. 建议先用单个智能体测试流程再批量执行
4. 保留原始备份以便回滚
```

---

## 🔧 使用方法

### 方式一：命令行批量创建
```bash
cd ~/.hermes/skills/multi-agent-team/

# 运行批量创建脚本
python batch_create_tool.py --template advanced --count 5 --prefix custom_

# 输出:
# ✅ Created custom-specialist-1/SKILL.md
# ✅ Created custom-specialist-2/SKILL.md
# ...
```

### 方式二：交互式创建
```bash
python interactive_agent_wizard.py

# 引导式问答:
# 请输入智能体名称：> data-analyst
# 请选择角色类型：> researcher
# 输入核心职责描述：> ...
# 选择权限级别：> read-only
# 
# ✅ SKILL.md generated successfully!
```

---

## 📝 模板变量说明

```yaml
{{agent_name}}        # 智能体 ID(kebab-case)
{{agent_title}}       # 显示名称 (中文 + 英文)
{{core_role}}         # 核心角色定位
{{domain_keywords}}   # 领域关键词列表
{{permission_level}}  # 权限等级
{{concurrency_limit}} # 并发限制数量
{{created_date}}      # 创建日期
{{team_version}}      # 团队版本号
```

---

## 📈 版本历史

- **v2.0.0** (2026-04-23): 配合团队 v2.0 升级，支持新模板格式
- **v1.0.0** (2026-04-22): 初始版本
