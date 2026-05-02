---
name: multi-agent-team-enhancement
description: 系统化升级多智能体协作框架 — 添加共享状态管理、独立记忆、权限控制、并行执行和纪律铁律
version: 1.0.0
author: Multi-Agent Team Development Group
tags: [multi-agent, architecture, state-management, permissions, error-handling]
toolsets_required: ['terminal', 'file', 'execute_code']
category: multi-agent-team
metadata:
  complexity: high
  use_case: framework_upgrade
  estimated_time: "2-4 hours"
---

# 多智能体团队协作框架系统化升级指南

## 触发条件

使用此技能当需要:
- 为现有单智能体系统添加协作能力
- 增强多智能体团队的状态管理和容错能力
- 实施智能体间的权限控制和安全审计
- 构建企业级可靠的多智能体架构

---

## 核心问题识别 (v1.0 v2.0)

### v1.0 常见缺陷

| 维度 | 问题表现 | 风险等级 |
|------|---------|---------|
| 状态管理 | 无共享状态，手动传递信息 | 高 |
| 并行执行 | 串行调用，效率低下 | 中 |
| 错误恢复 | 直接失败，无重试机制 | 高 |
| 权限控制 | 统一权限，缺乏隔离 | 高 |
| 记忆持久化 | 会话内临时，丢失上下文 | 中 |
| 纪律约束 | 无强制规则，行为不可控 | 低 |

---

## 五步系统化升级法

### Step 1: 构建核心基础组件 (1-2 小时)

#### 1.1 创建共享状态管理器

```python
# 路径：~/.hermes/skills/multi-agent-team/core/shared_state_manager.py

关键功能实现要点:
1. 文件锁保护 (fcntl.flock) 防止并发写入冲突
2. 版本控制支持回滚到历史状态
3. 检查点机制用于故障恢复
4. 操作日志完整记录所有变更

核心 API 设计:
sm = SharedStateManager()
sm.create_task(task_id, description, agents, priority)
sm.update_task_stage(task_id, stage_name, agent_id, status, output)
sm.save_artifact(task_id, name, content, agent_id)
sm.get_artifact(task_id, name)
sm.create_checkpoint(task_id, name, data)
```

#### 1.2 创建独立记忆管理器

```python
# 路径：~/.hermes/skills/multi-agent-team/core/agent_memory_manager.py

记忆类型分类:
MemoryType.FACT        # 事实性知识
MemoryType.SKILL       # 技能和经验
MemoryType.LESSON      # 教训总结
MemoryType.PREFERENCE  # 用户偏好

关键设计决策:
- 按 agent_id 分文件存储，避免内存爆炸
- 支持标签搜索和重要性排序
- 定期清理低重要性旧记忆
```

#### 1.3 创建权限控制器

```python
# 路径：~/.hermes/skills/multi-agent-team/core/permission_controller.py

权限级别定义:
PermissionLevel.NONE        # 无权限
PermissionLevel.READ_ONLY   # 只读
PermissionLevel.RESTRICTED  # 受限 (白名单)
PermissionLevel.FULL        # 完全权限

安全检查清单:
1. 全局危险操作黑名单
2. 敏感文件访问限制
3. 每个智能体的定制规则
4. 完整审计日志记录所有请求
```

#### 1.4 创建错误处理器

```python
# 路径：~/.hermes/skills/multi-agent-team/core/error_handler.py

错误分类映射策略:
ErrorType.NETWORK: {max_retries: 5, base_delay: 1.0}
ErrorType.API_RATE_LIMIT: {max_retries: 3, base_delay: 30.0}
ErrorType.TIMEOUT: {max_retries: 3, base_delay: 2.0}
ErrorType.PERMISSION: {max_retries: 0}  # 不重试

三级容错机制:
Level 1: 自动重试 (指数退避，加随机抖动防雪崩)
Level 2: 降级模式 (切换简化方案或备用智能体)
Level 3: 人工介入 (发送告警请求主人决策)
```

---

### Step 2: 设计新型调度器架构 (30 分钟)

#### 2.1 拆分沟通协调员职责

原 v1.0 的 communication-coordinator 承担过多职责，v2.0 拆分为两个专门角色:

```yaml
task-dispatcher:          # 只负责任务分发
  responsibilities:
    - 分析任务特征
    - 计算智能体匹配度
    - 负载均衡决策
    - 启动任务执行

result-aggregator:        # 只负责结果聚合
  responsibilities:
    - 收集各智能体输出
    - 合并冲突信息
    - 生成综合报告
    - 向主人汇报
```

#### 2.2 实现优先级队列调度

```python
from dataclasses import dataclass
import heapq

@dataclass(order=True)
class PrioritizedTask:
    priority: int         # 0=emergency, 1=high, 2=normal, 3=low
    timestamp: str
    task_id: str
    description: str
    agents: List[str]

# 调度器维护最小堆，始终先处理最高优先级任务
orchestrator.task_queue = []
heapq.heappush(orchestrator.task_queue, task)
next_task = heapq.heappop(orchestrator.task_queue)
```

---

### Step 3: 引入并行执行机制 (45 分钟)

#### 3.1 识别可并行的任务

```python
SERIAL_AGENTS = [  # 必须串行执行
    "strategic-planner",   # 依赖上游规划结果
    "devops-engineer",     # 依赖代码完成
    "result-aggregator"    # 依赖所有结果
]

PARALLEL_AGENTS = [       # 可并行执行
    "code-architect",
    "implementation-engineer",
    "qa-specialist",
    "research-analyst",
    "documentation-specialist"
]
```

#### 3.2 实现异步并行执行

```python
import asyncio

async def execute_parallel_tasks(self, task_id: str, tasks: List[Dict]):
    """并行执行多个独立任务"""
    
    async def bounded_execute(task_info):
        agent_id = task_info["agent_id"]
        result = await self.execute_agent_async(
            agent_id=agent_id,
            task_id=task_id,
            context=task_info.get("context", {})
        )
        return result
    
    coroutines = [bounded_execute(t) for t in tasks]
    results = await asyncio.gather(*coroutines, return_exceptions=True)
    return list(results)

性能提升估算:
- 串行：A(10s) + B(8s) + C(12s) = 30s
- 并行：max(A, B, C) = 12s (2.5x 加速)
```

---

### Step 4: 为每个智能体添加铁律和记忆 (1-2 小时)

#### 4.1 五大铁律模板 (每个智能体必须包含)

```markdown
## 铁律与纪律规则 (必须严格遵守)

### 铁律一：架构流程优先原则
禁止行为:
- 为了快速给出答案而跳过需求分析步骤
- 在信息不足时擅自假设或脑补细节
- 绕开既定的工作流程直接跳到解决方案

正确做法:
1. 先确认任务的完整背景和目标
2. 按照标准流程逐步推进
3. 遇到不明确之处主动询问澄清

### 铁律二：诚信执行原则
禁止行为:
- 编造不存在的技术方案或数据
- 夸大能力承诺无法完成的时间表
- 隐瞒风险和问题报喜不报忧

正确做法:
- 基于事实和已知信息进行判断
- 保守估计时间并预留缓冲空间
- 及时暴露风险和不确定性

### 铁律三：透明可追溯原则
禁止行为:
- 不做记录就修改计划
- 跳过验证步骤直接输出结果
- 决策过程不写理由

正确做法:
- 每一步操作都记录到共享状态中
- 关键决策附带理由和依据
- 保持完整的执行日志链

### 铁律四：质量优先原则
禁止行为:
- 为了赶工降低交付标准
- 忽略风险评估环节
- 接受有缺陷的输入数据

正确做法:
- 宁可延迟完成也不降低质量标准
- 严格执行检查清单
- 对上游输入进行有效性验证

### 铁律五：绝不妥协原则
当发现以下情况时，必须停止并向主人报告:
- 项目目标存在根本性矛盾
- 所需资源远超可用范围
- 技术方案违反安全或合规要求
- 时间表不合理可能导致质量严重下降
```

#### 4.2 记忆模块集成模板

在每个智能体的 SKILL.md 中添加:

```python
from core.agent_memory_manager import AgentMemoryManager, MemoryType

self.memory = AgentMemoryManager()

# 创建记忆条目
memory.create_memory(
    agent_id="{agent_id}",
    memory_type=MemoryType.LESSON,
    title="具体经验名称",
    content="详细的经验内容...",
    tags=["领域关键词"],
    importance=5  # 1-5 评级
)

# 激活上下文相关记忆
activated = memory.activate_context_memories(
    agent_id="{agent_id}",
    context_keywords=["关键词 1", "关键词 2"],
    max_count=5
)
```

---

## 常见陷阱与经验教训

### 陷阱 1: 过早优化并行执行
错误做法：一开始就上复杂的分布式执行框架
正确做法：先用简单的同步调用保证正确性，再用 ThreadPoolExecutor

### 陷阱 2: 状态文件格式不统一
错误做法：各个智能体随意写自己的 JSON 结构
正确做法：定义统一的 StateEntry 数据类，强制版本号管理 schema

### 陷阱 3: 权限配置过度宽松
错误做法：默认给所有智能体 FULL 权限
正确做法：默认 NONE，按需申请，READ-ONLY 是大多数合理起点

### 陷阱 4: 错误重试导致雪崩
错误做法：所有错误都无差别重试 5 次
正确做法：差异化策略，网络错误重试 5 次，权限错误不重试

### 陷阱 5: 忘记添加铁律章节
错误做法：只添加功能，忽略行为约束
正确做法：五大铁律必须在每个智能体的 SKILL.md 首页之后立即出现

---

## 验收检查清单

### 基础设施 (必须全部通过)
- [ ] SharedStateManager 可以正常创建和读取任务
- [ ] AgentMemoryManager 可以为每个智能体独立存储记忆
- [ ] PermissionController 可以阻止非法操作
- [ ] ErrorHandler 可以正确处理并重试网络错误

### 调度器 (必须全部通过)
- [ ] Orchestrator v2.0 可以初始化成功
- [ ] 优先级队列按正确顺序处理任务
- [ ] 并行执行不会造成竞态条件
- [ ] 权限检查在任务执行前生效

### 智能体升级 (每个都必须通过)
- [ ] SKILL.md 已升级到 v2.0.x 版本号
- [ ] 五大铁律章节已添加
- [ ] 记忆模块配置已完成
- [ ] 权限级别已明确定义
- [ ] YAML 头部元数据已更新

---

## 部署步骤

### 1. 备份现有配置
```bash
cp -r ~/.hermes/skills/multi-agent-team \
      ~/.hermes/skills/multi-agent-team.backup_v1_$(date +%Y%m%d)
```

### 2. 增量式替换
```bash
cp core/*.py ~/.hermes/skills/multi-agent-team/core/
cp multi-agent-orchestrator-v2.py ~/.hermes/skills/multi-agent-team/
```

### 3. 验证部署
```bash
cd ~/.hermes/skills/multi-agent-team/
python multi-agent-orchestrator-v2.py status
python multi-agent-orchestrator-v2.py add project_planning "测试任务" 2
python multi-agent-orchestrator-v2.py run
```

---

*版本*: 1.0.0  
*最后更新*: 2026-04-23  
*适用范围*: Hermes Agent 多智能体团队架构升级
