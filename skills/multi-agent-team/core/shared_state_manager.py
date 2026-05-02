#!/usr/bin/env python3
"""
Shared State Manager - 多智能体共享状态管理器
============================================

功能：
- 提供统一的中间状态存储
- 支持版本控制和回滚
- 实现任务上下文持久化
- 支持并发读写锁保护
"""

import json
import os
import uuid
import fcntl
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class StateOperation(Enum):
    """状态操作类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"


@dataclass
class StateEntry:
    """状态条目"""
    key: str
    value: Any
    version: int
    created_at: str
    updated_at: str
    agent_id: str  # 哪个智能体创建/修改
    operation: str
    metadata: Dict[str, Any]


class SharedStateManager:
    """共享状态管理器"""
    
    def __init__(self, base_path: str = None):
        """初始化状态管理器"""
        if base_path is None:
            base_path = str(Path.home() / ".hermes/state/multi-agent")
        
        self.base_path = Path(base_path)
        self.state_file = self.base_path / "state.json"
        self.history_file = self.base_path / "history.jsonl"
        self.lock_file = self.base_path / ".lock"
        
        # 创建目录
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化状态文件
        if not self.state_file.exists():
            self._init_state_file()
    
    def _init_state_file(self):
        """初始化状态文件"""
        initial_state = {
            "version": 1,
            "last_updated": datetime.now().isoformat(),
            "tasks": {},           # 任务上下文
            "shared_data": {},     # 全局共享数据
            "agent_status": {},    # 各智能体状态
            "checkpoints": {}      # 检查点
        }
        self._save_state(initial_state)
    
    def _save_state(self, state: Dict):
        """保存状态（带锁）"""
        with open(self.lock_file, 'w') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    
    def _load_state(self) -> Dict:
        """加载状态（带锁）"""
        with open(self.lock_file, 'w') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_SH)
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    
    def create_task(self, task_id: str, description: str, agents: List[str], 
                    priority: int = 2) -> Dict[str, Any]:
        """创建新任务"""
        state = self._load_state()
        
        task_entry = {
            "task_id": task_id,
            "description": description,
            "agents_assigned": agents,
            "priority": priority,  # 0=emergency, 1=high, 2=normal, 3=low
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "stages": [],
            "artifacts": {},
            "metadata": {}
        }
        
        state["tasks"][task_id] = task_entry
        state["last_updated"] = datetime.now().isoformat()
        self._save_state(state)
        
        self._log_operation(
            operation="create_task",
            details={"task_id": task_id, "agents": agents}
        )
        
        return task_entry
    
    def update_task_stage(self, task_id: str, stage_name: str, 
                         agent_id: str, status: str, 
                         output: Dict[str, Any] = None) -> bool:
        """更新任务阶段"""
        state = self._load_state()
        
        if task_id not in state["tasks"]:
            return False
        
        task = state["tasks"][task_id]
        
        # 查找或创建阶段
        stage_found = False
        for stage in task["stages"]:
            if stage["name"] == stage_name:
                stage["status"] = status
                stage["agent_id"] = agent_id
                stage["completed_at"] = datetime.now().isoformat()
                stage["output"] = output or {}
                stage_found = True
                break
        
        if not stage_found:
            task["stages"].append({
                "name": stage_name,
                "status": status,
                "agent_id": agent_id,
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "output": output or {}
            })
        
        task["updated_at"] = datetime.now().isoformat()
        
        # 更新任务状态
        if all(s["status"] == "completed" for s in task["stages"]):
            task["status"] = "completed"
        
        self._save_state(state)
        
        self._log_operation(
            operation="update_task_stage",
            details={
                "task_id": task_id,
                "stage": stage_name,
                "agent": agent_id,
                "status": status
            }
        )
        
        return True
    
    def save_artifact(self, task_id: str, artifact_name: str, 
                     content: Any, agent_id: str) -> bool:
        """保存任务产物"""
        state = self._load_state()
        
        if task_id not in state["tasks"]:
            return False
        
        state["tasks"][task_id]["artifacts"][artifact_name] = {
            "content": content,
            "created_by": agent_id,
            "created_at": datetime.now().isoformat()
        }
        
        state["tasks"][task_id]["updated_at"] = datetime.now().isoformat()
        self._save_state(state)
        
        return True
    
    def get_artifact(self, task_id: str, artifact_name: str) -> Optional[Any]:
        """获取任务产物"""
        state = self._load_state()
        
        if task_id not in state["tasks"]:
            return None
        
        artifacts = state["tasks"][task_id].get("artifacts", {})
        if artifact_name not in artifacts:
            return None
        
        return artifacts[artifact_name]["content"]
    
    def set_shared_data(self, key: str, value: Any, agent_id: str):
        """设置全局共享数据"""
        state = self._load_state()
        state["shared_data"][key] = {
            "value": value,
            "set_by": agent_id,
            "timestamp": datetime.now().isoformat()
        }
        state["last_updated"] = datetime.now().isoformat()
        self._save_state(state)
    
    def get_shared_data(self, key: str) -> Optional[Any]:
        """获取全局共享数据"""
        state = self._load_state()
        if key not in state["shared_data"]:
            return None
        return state["shared_data"][key]["value"]
    
    def update_agent_status(self, agent_id: str, status: str, 
                           current_task: str = None) -> None:
        """更新智能体状态"""
        state = self._load_state()
        state["agent_status"][agent_id] = {
            "status": status,  # idle, busy, error
            "current_task": current_task,
            "last_activity": datetime.now().isoformat()
        }
        state["last_updated"] = datetime.now().isoformat()
        self._save_state(state)
    
    def create_checkpoint(self, task_id: str, checkpoint_name: str,
                         data: Dict[str, Any]) -> None:
        """创建检查点（用于恢复）"""
        state = self._load_state()
        
        if "checkpoints" not in state:
            state["checkpoints"] = {}
        
        checkpoint_key = f"{task_id}:{checkpoint_name}"
        state["checkpoints"][checkpoint_key] = {
            "data": data,
            "created_at": datetime.now().isoformat()
        }
        
        self._save_state(state)
    
    def restore_from_checkpoint(self, task_id: str, checkpoint_name: str) -> Dict:
        """从检查点恢复"""
        state = self._load_state()
        checkpoint_key = f"{task_id}:{checkpoint_name}"
        
        if checkpoint_key not in state.get("checkpoints", {}):
            raise ValueError(f"Checkpoint not found: {checkpoint_key}")
        
        return state["checkpoints"][checkpoint_key]["data"]
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务详情"""
        state = self._load_state()
        return state["tasks"].get(task_id)
    
    def list_tasks(self, status: str = None) -> List[Dict]:
        """列出所有任务"""
        state = self._load_state()
        tasks = list(state["tasks"].values())
        
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        
        return sorted(tasks, key=lambda x: (x["priority"], x["created_at"]))
    
    def _log_operation(self, operation: str, details: Dict):
        """记录操作日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "details": details
        }
        
        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 测试代码
    sm = SharedStateManager()
    
    # 创建任务
    task = sm.create_task(
        task_id="demo-task-001",
        description="测试多智能体协作",
        agents=["strategic-planner", "code-architect"],
        priority=1
    )
    print(f"Created task: {json.dumps(task, ensure_ascii=False, indent=2)}")
    
    # 模拟智能体工作
    sm.update_task_stage(
        task_id="demo-task-001",
        stage_name="planning",
        agent_id="strategic-planner",
        status="completed",
        output={"plan": "分三步执行..."}
    )
    
    # 保存产物
    sm.save_artifact(
        task_id="demo-task-001",
        artifact_name="project_plan",
        content={"steps": ["分析", "设计", "实施"]},
        agent_id="strategic-planner"
    )
    
    # 读取产物（供下一个智能体使用）
    plan = sm.get_artifact("demo-task-001", "project_plan")
    print(f"Retrieved artifact: {plan}")
    
    # 获取任务状态
    task_status = sm.get_task("demo-task-001")
    print(f"Task status: {json.dumps(task_status, ensure_ascii=False, indent=2)}")
