# Multi-Agent Team Upgrade Framework — 模板定制与运维指南

> 吸收自 `multi-agent-team-upgrade-framework`（2026-05 合并）
> 本节覆盖 upgrade-methodology 未详细展开的智能体模板定制指南、成功指标和持续维护。

## 智能体内容定制指南

为每个智能体填充专业内容时回答以下问题：

**A. 角色身份定义**
- 这个角色的比喻是什么？（如：总建筑师、质量守门员）
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

## 调度器配置示例

```python
AGENTS_CONFIG = {
    "strategic-planner": {
        "concurrency_limit": 1,
        "keywords": ["计划", "规划"],
        "dependencies": []
    },
    "implementation-engineer": {
        "concurrency_limit": 2,
        "keywords": ["编码", "实现"],
        "dependencies": ["code-architect"]
    },
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

## 成功指标

升级完成后应达到：
- **覆盖率**: 100% 智能体升级到新版本
- **一致性**: 所有智能体遵循相同模板结构
- **功能性**: 核心组件全部通过测试
- **可用性**: 能成功运行至少一个端到端任务
- **可靠性**: 错误恢复机制正常触发
- **安全性**: 权限限制按预期生效

## 持续维护

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
