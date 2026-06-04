# Multi-Agent Team Enhancement — 部署步骤与定制补充

> 吸收自 `multi-agent-team-enhancement`（2026-05 合并）
> 本节覆盖 upgrade-methodology 未详细展开的部署执行步骤和常见陷阱细化。

## 部署步骤

### 备份现有配置
```bash
cp -r ~/.hermes/skills/multi-agent-team \
      ~/.hermes/skills/multi-agent-team.backup_v1_$(date +%Y%m%d)
```

### 增量式替换
```bash
cp core/*.py ~/.hermes/skills/multi-agent-team/core/
```

### 验证部署
```bash
cd ~/.hermes/skills/multi-agent-team/
python multi-agent-orchestrator-v2.py status
```

## 常见陷阱（补充）

### 过早优化并行执行
先用简单的同步调用保证正确性，再用 ThreadPoolExecutor。

### 状态文件格式不统一
定义统一的 StateEntry 数据类，强制版本号管理 schema。

### 权限配置过度宽松
默认 NONE，按需申请，READ-ONLY 是大多数合理起点。

### 错误重试导致雪崩
差异化策略：网络错误重试 5 次，权限错误不重试。

### 忘记添加铁律章节
五大铁律必须在每个智能体的 SKILL.md 首页之后立即出现。

## 验收检查清单

### 基础设施
- [ ] SharedStateManager 可以正常创建和读取任务
- [ ] AgentMemoryManager 可以为每个智能体独立存储记忆
- [ ] PermissionController 可以阻止非法操作
- [ ] ErrorHandler 可以正确处理并重试网络错误

### 调度器
- [ ] Orchestrator v2.0 可以初始化成功
- [ ] 优先级队列按正确顺序处理任务
- [ ] 并行执行不会造成竞态条件
- [ ] 权限检查在任务执行前生效

### 每个智能体
- [ ] SKILL.md 已升级到 v2.0.x 版本号
- [ ] 五大铁律章节已添加
- [ ] 记忆模块配置已完成
- [ ] 权限级别已明确定义
