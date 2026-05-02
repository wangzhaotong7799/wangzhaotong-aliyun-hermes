# 并行独立委托模式

## 适用场景

多个子任务**写入不同文件**，彼此无共享状态，可以**完全并行**执行。

## 与串行 2-stage 的区别

| 维度 | 串行 2-stage（原技能） | 并行独立（本模式） |
|------|----------------------|-------------------|
| 任务关系 | 依赖/顺序执行 | 完全独立 |
| 文件冲突 | 可能改同一文件 | 写入不同文件 |
| 审核方式 | 每任务 spec + quality 双审 | 跑完一次性验证 |
| 速度 | 线性累加 | 并行 ≈ 最慢任务耗时 |
| 适用 | 数据模型、API 端点等共享组件 | 独立页面、独立配置、独立模块 |

## 决策条件

**先确认满足所有条件才用并行模式：**

- [ ] 每个任务写入不同的文件（无文件级冲突）
- [ ] 任务之间无执行顺序要求
- [ ] 每个任务的上下文可以完整独立描述
- [ ] 所有任务依赖同一套共享基础设施（API、CSS、工具函数）
- [ ] 失败一个任务不影响其他任务继续运行
- [ ] 无需跨任务的代码审查

## 实施方法

### 1. 先搭共享基础设施

在派发任务之前，先把所有**公共依赖**准备好：

```python
# 例：PWA 项目
# 先做共享层
write_file('static/mobile/index.html', ...)    # 入口 HTML
write_file('static/mobile/css/app.css', ...)    # 公共样式
write_file('static/mobile/js/api.js', ...)      # API 封装
write_file('static/mobile/js/router.js', ...)   # 路由
write_file('static/mobile/js/store.js', ...)    # 状态管理
write_file('static/mobile/js/page-login.js', ..) # 登录页
```

### 2. 派发并行任务

每个任务的 `context` 中必须包含完整的共享设施说明：

```
每个任务的 context 必须包含：
  ├── 项目背景（1-2 句话）
  ├── 可用的全局函数/变量（api 方法、store 方法、CSS 类名）
  ├── API 响应结构（字段名、示例值）
  ├── 写入文件路径（明确到绝对路径）
  ├── 风格说明（IIFE、var/let、引号等）
  └── 输出要求（写入后验证）
```

示例 context 结构（简化）：

```python
delegate_task(
    goal="为 XXX 系统编写「页面名」页面 JS",
    context="""
    ## 项目背景
    ...2句话描述...

    ## 可用的全局变量
    - Api.getXXX(params) — 返回 {data: [...]} 或 [...]
    - Store.getUser() — 返回 {username, full_name, roles}
    - Router.register(name, renderFn) — 注册路由
    - showToast(msg) — 显示 2 秒 toast

    ## CSS 可用类
    - .card, .card-row, .card-title — 卡片
    - .badge, .badge-xxx — 状态标签
    - .btn, .btn-primary — 按钮
    - .filter-tabs, .filter-tab — 筛选
    - .empty-state, .loading, .spinner — 空/加载

    ## API 响应结构
    { field1: "...", field2: "..." }

    ## 文件写入路径
    /absolute/path/to/output.js

    ## 风格
    - 使用 IIFE
    - 写入后读取文件验证
    - 不要请求确认，直接写入
    """,
    toolsets=['file', 'terminal']
)
```

### 3. 派发方式

一次性派发所有任务：

```python
delegate_task(
    tasks=[
        {"goal": "页面 A", "context": "...", "toolsets": [...]},
        {"goal": "页面 B", "context": "...", "toolsets": [...]},
        {"goal": "页面 C", "context": "...", "toolsets": [...]},
    ]
)
```

### 4. 汇合验证

所有任务完成后统一验证：

```python
# 检查所有文件是否存在
for f in ['page-a.js', 'page-b.js', 'page-c.js']:
    verify file exists and has content

# 重新启动服务
restart server

# 测试全链路
curl -s http://localhost:port/mobile/
login test
API call test
```

## 效率对比

以本会话（3 个独立 JS 页面）为例：

```
串行模式：每个页面估约 15 分钟 → 45 分钟 + 3 次审核 ≈ 1 小时
并行模式：3 个页面同时跑 → 约 1 分钟调度 + 1 分钟跑完 + 2 分钟验证 ≈ 4 分钟

节省约 93% 的耗时。
```

## 已知风险

1. **context 过期**：共享基础设施在派发后改变，子智能体的 context 变旧 → 解决方案：先固定基础设施再派发
2. **资源竞争**：两个任务写入同一文件 → 解决方案：派发前确认文件路径不冲突
3. **风格不一致**：不同子智能体写出的代码风格有差异 → 解决方案：在 context 中明确指定风格约定
4. **依赖陷阱**：某任务依赖另一任务输出的数据 → 解决方案：不是独立任务，改为串行

## 何时不要用

- 任务写入同一文件 → 串行
- 任务有依赖顺序 → 串行
- 需要跨任务代码审查 → 串行
- 任务数量少（1~2 个）→ 串行更快（省去 context 准备时间）
