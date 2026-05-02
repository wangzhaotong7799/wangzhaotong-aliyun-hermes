#!/usr/bin/env python3
"""
Multi-Agent Orchestrator v2.0 - 多智能体协作调度器（增强版）
=============================================================

新增功能:
- 共享状态管理
- 并行执行支持
- 细粒度权限控制
- 错误重试与降级
- 任务优先级队列
"""

import os
import sys
import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import heapq

# 导入核心模块
sys.path.insert(0, str(Path(__file__).parent / "core"))
from shared_state_manager import SharedStateManager
from agent_memory_manager import AgentMemoryManager, MemoryType
from permission_controller import PermissionController
from error_handler import ErrorHandler, retry_on_error


@dataclass(order=True)
class PrioritizedTask:
    """带优先级的任务"""
    priority: int
    timestamp: str = None
    task_id: str = None
    description: str = None
    agents: List[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class MultiAgentOrchestratorV2:
    """第二代多智能体调度器"""
    
    # 智能体定义
    AGENTS = {
        "strategic-planner": {
            "name": "战略规划师",
            "role": "Planning",
            "keywords": ["计划", "规划", "策略"],
            "concurrency_limit": 1
        },
        "code-architect": {
            "name": "代码架构师", 
            "role": "Design",
            "keywords": ["架构", "设计", "技术选型"],
            "concurrency_limit": 1
        },
        "implementation-engineer": {
            "name": "实现工程师",
            "role": "Coding",
            "keywords": ["编码", "实现", "开发"],
            "concurrency_limit": 2  # 可以同时运行 2 个实例
        },
        "qa-specialist": {
            "name": "QA 专家",
            "role": "Testing",
            "keywords": ["测试", "审查", "审计"],
            "concurrency_limit": 2
        },
        "research-analyst": {
            "name": "研究分析师",
            "role": "Research",
            "keywords": ["调研", "分析", "研究"],
            "concurrency_limit": 3
        },
        "documentation-specialist": {
            "name": "文档专家",
            "role": "Documentation",
            "keywords": ["文档", "手册", "指南"],
            "concurrency_limit": 2
        },
        "devops-engineer": {
            "name": "运维师",
            "role": "DevOps",
            "keywords": ["部署", "监控", "运维"],
            "concurrency_limit": 1
        },
        "mcp-specialist": {
            "name": "MCP 专家",
            "role": "Tools",
            "keywords": ["工具", "集成", "API"],
            "concurrency_limit": 1
        },
        "life-assistant": {
            "name": "生活助理",
            "role": "Life",
            "keywords": ["日程", "安排", "提醒"],
            "concurrency_limit": 1
        },
        "task-dispatcher": {
            "name": "任务分发器",
            "role": "Dispatcher",
            "keywords": ["分配", "调度"],
            "concurrency_limit": 1
        },
        "result-aggregator": {
            "name": "结果聚合器",
            "role": "Aggregator",
            "keywords": ["汇总", "整合"],
            "concurrency_limit": 1
        }
    }
    
    # 任务类型映射
    TASK_TYPES = {
        "project_planning": ["strategic-planner", "task-dispatcher"],
        "system_design": ["code-architect", "research-analyst"],
        "feature_implementation": [
            "implementation-engineer", 
            "qa-specialist",
            "documentation-specialist"
        ],
        "full_stack_project": [
            "strategic-planner", "code-architect", 
            "implementation-engineer", "qa-specialist",
            "documentation-specialist", "devops-engineer",
            "result-aggregator"
        ],
        "market_research": ["research-analyst"],
        "life_management": ["life-assistant"]
    }
    
    def __init__(self):
        """初始化调度器"""
        print("🔄 Initializing Multi-Agent Orchestrator v2.0...")
        
        # 核心组件
        self.state_manager = SharedStateManager()
        self.memory_manager = AgentMemoryManager()
        self.permission_controller = PermissionController()
        self.error_handler = ErrorHandler(checkpoint_manager=self.state_manager)
        
        # 任务队列（最小堆，按优先级排序）
        self.task_queue = []
        self.task_counter = 0
        
        print("✅ Orchestrator initialized successfully!")
    
    def add_task(self, task_type: str, description: str, 
                 priority: int = 2) -> str:
        """添加任务到队列"""
        self.task_counter += 1
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.task_counter}"
        
        # 确定需要的智能体
        agents = self.TASK_TYPES.get(task_type, ["task-dispatcher"])
        
        # 创建状态记录
        self.state_manager.create_task(
            task_id=task_id,
            description=description,
            agents=agents,
            priority=priority
        )
        
        # 添加到优先级队列
        task = PrioritizedTask(
            priority=priority,
            timestamp=datetime.now().isoformat(),
            task_id=task_id,
            description=description,
            agents=agents
        )
        heapq.heappush(self.task_queue, task)
        
        print(f"📋 Task added: {task_id} (priority={priority})")
        return task_id
    
    async def execute_agent_async(self, agent_id: str, task_id: str, 
                                  context: Dict) -> Dict:
        """异步执行智能体任务"""
        # 检查权限
        perm_result = self.permission_controller.check_terminal_permission(
            agent_id=agent_id,
            command="ls -la"  # 基础检查
        )
        
        if not perm_result["allowed"]:
            raise PermissionError(perm_result["reason"])
        
        # 激活相关记忆
        activated_memories = self.memory_manager.activate_context_memories(
            agent_id=agent_id,
            context_keywords=list(context.get("keywords", []))
        )
        
        # 模拟执行（实际应该调用 Hermes Agent API）
        result = {
            "agent_id": agent_id,
            "task_id": task_id,
            "status": "completed",
            "output": {"message": f"{self.AGENTS[agent_id]['name']} completed the task"},
            "memory_references": [m["id"] for m in activated_memories[:3]],
            "timestamp": datetime.now().isoformat()
        }
        
        # 更新状态
        self.state_manager.update_task_stage(
            task_id=task_id,
            stage_name=agent_id,
            agent_id=agent_id,
            status="completed",
            output=result
        )
        
        return result
    
    @retry_on_error(max_attempts=3)
    def execute_agent_sync(self, agent_id: str, task_id: str,
                          context: Dict) -> Dict:
        """同步执行智能体任务（带重试）"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.execute_agent_async(agent_id, task_id, context)
            )
        finally:
            loop.close()
    
    async def execute_parallel_tasks(self, task_id: str, tasks: List[Dict]) -> List[Dict]:
        """并行执行多个独立任务"""
        # 使用信号量控制并发数
        results = []
        
        async def bounded_execute(task_info: Dict):
            agent_id = task_info["agent_id"]
            concurrency = self.AGENTS.get(agent_id, {}).get("concurrency_limit", 1)
            
            # 这里可以添加信号量来控制并发
            result = await self.execute_agent_async(
                agent_id=agent_id,
                task_id=task_id,
                context=task_info.get("context", {})
            )
            return result
        
        # 并行执行
        coroutines = [bounded_execute(t) for t in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        return list(results)
    
    def run_task_from_queue(self) -> Optional[Dict]:
        """从队列中运行下一个任务"""
        if not self.task_queue:
            print("⚠️  No pending tasks in queue")
            return None
        
        # 获取最高优先级任务
        task = heapq.heappop(self.task_queue)
        
        print(f"\n🚀 Executing task: {task.task_id}")
        print(f"   Description: {task.description}")
        print(f"   Agents: {', '.join([self.AGENTS[a]['name'] for a in task.agents])}")
        
        # 分离可并行的任务和必须串行的任务
        serial_agents = ["strategic-planner", "devops-engineer", "result-aggregator"]
        parallel_agents = [a for a in task.agents if a not in serial_agents]
        
        # 序列化执行第一步（规划）
        if "strategic-planner" in task.agents:
            plan_result = self.execute_agent_sync(
                agent_id="strategic-planner",
                task_id=task.task_id,
                context={"description": task.description}
            )
            print(f"✓ Planning complete: {plan_result['output']['message']}")
        
        # 并行执行中间步骤
        if parallel_agents:
            parallel_tasks = [
                {"agent_id": agent, "context": {"description": task.description}}
                for agent in parallel_agents
            ]
            
            print(f"⚡ Running {len(parallel_agents)} agents in parallel...")
            loop = asyncio.new_event_loop()
            try:
                parallel_results = loop.run_until_complete(
                    self.execute_parallel_tasks(task.task_id, parallel_tasks)
                )
                print(f"✓ Parallel execution complete: {len(parallel_results)} results")
            finally:
                loop.close()
        
        # 聚合结果
        if "result-aggregator" in task.agents or all(a in serial_agents for a in task.agents):
            aggregate_result = self.execute_agent_sync(
                agent_id="result-aggregator" if "result-aggregator" in task.agents else task.agents[-1],
                task_id=task.task_id,
                context={"description": task.description}
            )
            print(f"✓ Final aggregation complete")
        
        # 保存最终状态
        self.state_manager.create_checkpoint(
            task_id=task.task_id,
            checkpoint_name="final",
            data={"status": "completed", "agents_executed": task.agents}
        )
        
        print(f"✅ Task {task.task_id} completed!\n")
        return {"task_id": task.task_id, "status": "completed"}
    
    def get_status(self) -> Dict:
        """获取系统状态"""
        pending_tasks = len(self.task_queue)
        all_tasks = self.state_manager.list_tasks()
        
        return {
            "pending_in_queue": pending_tasks,
            "total_tasks": len(all_tasks),
            "tasks_by_status": {
                "pending": len([t for t in all_tasks if t["status"] == "pending"]),
                "in_progress": len([t for t in all_tasks if t["status"] == "in_progress"]),
                "completed": len([t for t in all_tasks if t["status"] == "completed"])
            },
            "active_agents": list(self.state_manager._load_state().get("agent_status", {}).keys())
        }
    
    def save_to_github(self, repo_path: str):
        """保存项目到 GitHub"""
        print(f"💾 Saving to GitHub repository: {repo_path}")
        # TODO: Implement git push logic


def main():
    """主入口"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     🎭 Multi-Agent Orchestrator v2.0                     ║
║         Enhanced with State Management & Parallelism      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)
    
    orchestrator = MultiAgentOrchestratorV2()
    
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "add":
        if len(sys.argv) < 4:
            print("Usage: python multi-agent-orchestrator.py add <task_type> <description>")
            return
        
        task_type = sys.argv[2]
        description = " ".join(sys.argv[3:])
        priority = int(sys.argv[4]) if len(sys.argv) > 4 else 2
        
        task_id = orchestrator.add_task(task_type, description, priority)
        print(f"Task added: {task_id}")
    
    elif command == "run":
        print("Running next task from queue...")
        orchestrator.run_task_from_queue()
    
    elif command == "queue":
        print("Processing entire queue...")
        while orchestrator.task_queue:
            orchestrator.run_task_from_queue()
    
    elif command == "status":
        status = orchestrator.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    
    elif command == "list":
        print("Available task types:")
        for task_type in orchestrator.TASK_TYPES.keys():
            agents = orchestrator.TASK_TYPES[task_type]
            agent_names = ", ".join([orchestrator.AGENTS[a]["name"] for a in agents])
            print(f"  • {task_type}: {agent_names}")
    
    elif command == "help" or command == "--help":
        show_help()
    
    else:
        print(f"Unknown command: {command}")
        show_help()


def show_help():
    """显示帮助"""
    help_text = """
📘 Multi-Agent Orchestrator v2.0 - Usage

Commands:
  add <type> <desc> [priority]  Add new task to queue
  run                           Execute next task from queue
  queue                         Process all queued tasks
  status                        Show system status
  list                          List available task types
  help                          Show this help

Task Types:
  project_planning              Project planning workflow
  system_design                 System design and architecture
  feature_implementation        Feature development pipeline
  full_stack_project            Complete full-stack project
  market_research               Market analysis and research
  life_management               Personal life management

Priority Levels:
  0 - Emergency (immediate attention)
  1 - High (urgent deadline)
  2 - Normal (default)
  3 - Low (background task)

Examples:
  # Add a high-priority project planning task
  python multi-agent-orchestrator.py add project_planning \\
    "Develop Harbin local services app" 1

  # Run next task
  python multi-agent-orchestrator.py run

  # Check system status
  python multi-agent-orchestrator.py status

New Features in v2.0:
  ✅ Shared state management across agents
  ✅ Parallel execution for independent tasks
  ✅ Error handling with automatic retry
  ✅ Fine-grained permission control
  ✅ Agent memory persistence
  ✅ Priority-based task scheduling
    """
    print(help_text)


if __name__ == "__main__":
    main()
