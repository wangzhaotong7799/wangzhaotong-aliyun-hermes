---
name: multi-agent-team-upgrade-framework
description: Complete methodology for systematically upgrading multi-agent team architecture - batch operations, iron rules implementation, shared state management
version: 1.0.0
author: Multi-Agent Team
tags: [upgrade, migration, architecture, best-practices]
category: multi-agent-team
metadata:
  skill_type: methodology
  complexity: high
  estimated_time: "4-8 hours"
  prerequisites: ["familiarity with existing agent structure"]
---

# Multi-Agent Team Upgrade Framework - 多智能体团队系统升级方法论

## 🎯 触发条件

使用此技能当您需要：
- 大规模升级现有智能体团队架构
- 为多个智能体统一添加新功能/规范
- 重构团队协作机制（状态共享、权限控制等）
- 批量实施纪律规则或质量标准

---

## 📋 核心步骤

### Step 1: 问题诊断与方案设计

**1.1 审计现有架构**
```bash
# 列出所有智能体和当前版本
find ~/.hermes/skills/multi-agent-team/*/SKILL.md -exec grep "^version:" {} \;

# 识别缺失能力
for agent in strategic-planner code-architect ...; do
    echo "=== $agent ===" 
    grep -c "memory_enabled\|permission_level\|iron_rules" ~/.hermes/skills/multi-agent-team/$agent/SKILL.md || echo "Missing!"
done
```

**1.2 制定升级矩阵**

| 维度 | 当前状态 | 目标状态 | 差距分析 |
|------|---------|---------|---------|
| 状态共享 | ❌ 无 | ✅ JSON 持久化 | 需要 Shared State Manager |
| 并行执行 | ❌ 串行 | ✅ 异步并发 | 需要 orchestrator-v2 |
| 错误恢复 | ⚠️ 仅记录 | ✅ 自动重试 | 需要 ErrorHandler |
| ... | ... | ... | ... |

**关键发现记录**:
- [ ] 哪些问题是结构性的（需要新组件）
- [ ] 哪些是增量改进（可以 patch）
- [ ] 优先级排序（P0/P1/P2）

---

### Step 2: 核心基础设施先行

**原则**: 先建地基再盖楼。不要直接在单个智能体里实现跨智能体功能。

**2.1 创建核心模块**

```python
# core/shared_state_manager.py - 必须包含的功能
class SharedStateManager:
    def create_task(self, ...)      # 任务生命周期
    def update_task_stage(self, ...) # 阶段更新
    def save_artifact(self, ...)     # 产物存储
    def get_artifact(self, ...)      # 跨智能体数据传递
    def create_checkpoint(self, ...) # 容错检查点
    
# core/agent_memory_manager.py - 记忆类型枚举
class MemoryType(Enum):
    FACT = "fact"              # 事实知识
    SKILL = "skill"            # 技能经验  
    LESSON = "lesson"          # 教训总结
    PREFERENCE = "preference"  # 用户偏好
    
# core/permission_controller.py - RBAC 实现
PermissionLevel = Enum(NONE, READ_ONLY, RESTRICTED, FULL)

# core/error_handler.py - 三级容错
class RecoveryStrategy(Enum):
    RETRY = "retry"                    # Level 1
    DEGRADATION = "degradation"        # Level 2
    MANUAL_INTERVENTION = "manual"     # Level 3
```

**2.2 验证核心组件**
```python
# 独立测试每个模块
from core.shared_state_manager import SharedStateManager
sm = SharedStateManager()
task = sm.create_task("test", "desc", ["agent1"], priority=1)
assert task["status"] == "pending"
print("✅ State Manager verified")
```

---

### Step 3: 设计统一的智能体模板

**3.1 YAML Header 标准化**
```yaml
name: <agent-id>
description: <一句话说明>
version: 2.0.0                    # 统一版本标记
toolsets_required: [...]
category: multi-agent-team
metadata:
  agent_type: <role_type>
  team_role: <中文角色名>
  priority: high|medium|low
  memory_enabled: true            # 新增字段
  permission_level: <level>       # 新增字段
  concurrency_limit: <int>        # 新增字段
```

**3.2 Markdown Body 固定结构**
```markdown
# <智能体中文名> v2.0

## 🎯 核心定位与使命
我是谁？我的核心价值？

## ⚖️ 铁律与纪律规则（必须严格遵守）
铁律一：XXXX 原则
❌ 禁止行为 vs ✅ 正确做法
...共 5 条

## 🧠 独立记忆模块
记忆结构示例代码（4 种类型）

## 🔧 核心职责
1-5 项具体职责 + 代码示例

## 📊 X 步工作流程
Step 1 → Step 6 流程图

## 🛠️ 推荐工具集
必备 + 辅助分类

## 📝 典型场景
3 个输入→输出示例

## 🔐 权限与安全
权限范围 + 检查清单

## 📞 调用方式
会话/命令行/API 三种方式

## 📈 版本历史
v2.0.0 变更列表

**核心理念**: <一句宣言>
```

---

### Step 4: 批量生成与个性化定制

**4.1 批量创建基础结构**
```bash
# 使用脚本或程序化方式快速生成
for agent in code-architect implementation-engineer qa-specialist; do
    cp templates/agent-skeleton.md ~/.hermes/skills/multi-agent-team/$agent/SKILL.md
done
```

**4.2 逐个填充专业内容**

对于每个智能体，回答以下问题以定制内容：

**A. 角色身份定义**
- 这个角色的比喻是什么？(如：总建筑师、质量守门员)
- 核心价值用哪 4 个点概括？

**B. 铁律设计**
- 该角色最容易犯什么错误？→ 转化为禁止行为
- 正确的最佳实践是什么？→ 转化为推荐做法

**C. 记忆类型举例**
- FACT: 该领域的事实性知识有哪些？
- SKILL: 什么专业技能值得沉淀？
- LESSON: 历史上学到了什么教训？
- PREFERENCE: 用户可能有什么偏好？

**D. 工具集选择**
- 必备工具（必须有）vs 辅助工具（锦上添花）
- 根据职责匹配合适的工具集

**E. 权限级别设定**
```python
READ_ONLY:    strategic-planner, research-analyst, qa-specialist
RESTRICTED:   code-architect, mcp-specialist, task-dispatcher
FULL:         implementation-engineer, devops-engineer
NONE:         life-assistant
```

---

### Step 5: 调度器集成

**5.1 更新 Orchestrator 配置**
```python
AGENTS_CONFIG = {
    "strategic-planner": {
        "concurrency_limit": 1,
        "keywords": ["计划", "规划"],
        "dependencies": []
    },
    "implementation-engineer": {
        "concurrency_limit": 2,  # 可并行
        "keywords": ["编码", "实现"],
        "dependencies": ["code-architect"]  # 依赖关系
    },
    # ...
}

TASK_TYPES = {
    "full_stack_project": [
        "strategic-planner", 
        "code-architect",
        ["implementation-engineer", "research-analyst"],  # 可并行组
        "qa-specialist",
        "result-aggregator"
    ]
}
```

**5.2 实现并行执行逻辑**
```python
async def execute_parallel_tasks(tasks: List[Dict]):
    """区分串行任务和可并行的独立任务"""
    serial_agents = ["strategic-planner", "devops-engineer"]
    parallel_tasks = [t for t in tasks if t["agent"] not in serial_agents]
    
    # 执行串行部分
    for task in serial_tasks:
        await run_agent(task)
        
    # 并行执行独立任务
    results = await asyncio.gather(*[run_agent(t) for t in parallel_tasks])
```

---

### Step 6: 全面验证

**6.1 单元测试**
```bash
# 测试每个核心模块
pytest tests/test_shared_state.py
pytest tests/test_memory_manager.py
pytest tests/test_permissions.py
pytest tests/test_error_handler.py
```

**6.2 集成测试**
```bash
# 端到端流程
python multi-agent-orchestrator-v2.py add project_planning "测试任务" 2
python multi-agent-orchestrator-v2.py run
python multi-agent-orchestrator-v2.py status
```

**6.3 验收检查清单**
- [ ] 所有智能体都能正确加载
- [ ] 状态管理器读写正常
- [ ] 权限控制在生效
- [ ] 错误重试机制工作
- [ ] 并行执行没有死锁
- [ ] 日志审计记录完整

---

## ⚠️ 常见陷阱与解决方案

### 陷阱 1: 过早优化
**现象**: 在第一轮就引入 Redis/Kafka 等复杂组件  
**解决**: 先用本地 JSON 验证流程，确认真实需求后再升级

### 陷阱 2: 铁律过于笼统
**现象**: "要写得高质量"这类无法验证的规则  
**解决**: 每条铁律必须有具体的禁止行为和检查标准

### 陷阱 3: 记忆模块滥用
**现象**: 把所有临时数据都存入长期记忆  
**解决**: 明确区分短期上下文和真正值得持久的经验

### 陷阱 4: 权限一刀切
**现象**: 所有智能体都给完全权限或完全没有权限  
**解决**: 基于最小特权原则，逐个评估实际需求

### 陷阱 5: 忘记向后兼容
**现象**: 直接删除旧 API 导致历史项目崩溃  
**解决**: 保留 deprecated 标记，提供迁移路径

---

## 📊 成功指标

升级完成后应达到：
- **覆盖率**: 100% 智能体升级到新版本
- **一致性**: 所有智能体遵循相同模板结构
- **功能性**: 核心组件全部通过测试
- **可用性**: 能成功运行至少一个端到端任务
- **可靠性**: 错误恢复机制正常触发
- **安全性**: 权限限制按预期生效

---

## 🔄 持续维护

### 定期任务
```python
# 每周
- 审查错误日志中的新模式
- 清理过期的记忆条目 (>365 天未访问)
- 更新第三方依赖

# 每月
- 收集用户反馈优化铁律
- 调整并发限制参数
- 审查权限分配的合理性

# 每季度
- 大规模回归测试
- 性能基准测试
- 架构技术债务清理
```

---

## 💡 关键洞察

1. **模块化思维**: 把共享能力提取成独立模块，避免重复造轮子
2. **渐进式迭代**: 先 MVP 验证可行性，再逐步增加复杂度
3. **文档驱动**: 每个智能体的铁律本身就是使用手册
4. **自动化优先**: 批量操作必须用脚本，手动容易出错
5. **防御性设计**: 假设任何环节都会失败，提前准备降级方案

**记住**: 升级不是目的，提升团队协作效能才是根本。每一步改动都要问"这真的让系统更好了吗？"
