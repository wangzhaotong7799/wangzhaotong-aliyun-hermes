#!/usr/bin/env python3
"""
Agent Memory Manager - 子智能体独立记忆管理器
===============================================

功能:
- 为每个智能体维护独立的长期记忆
- 支持记忆的分类存储和检索
- 实现记忆的生命周期管理
- 支持上下文感知的记忆激活
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib


class MemoryType(Enum):
    """记忆类型"""
    FACT = "fact"              # 事实性知识
    SKILL = "skill"            # 技能和经验
    PREFERENCE = "preference"  # 用户偏好
    PROJECT = "project"        # 项目信息
    LESSON = "lesson"          # 教训总结


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    agent_id: str
    memory_type: str
    title: str
    content: str
    tags: List[str]
    importance: int  # 1-5
    created_at: str
    updated_at: str
    access_count: int
    last_accessed_at: str
    metadata: Dict[str, Any]


class AgentMemoryManager:
    """智能体记忆管理器"""
    
    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = str(Path.home() / ".hermes/memory/agents")
        
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def get_agent_memory_path(self, agent_id: str) -> Path:
        """获取智能体的记忆文件路径"""
        agent_dir = self.base_path / agent_id
        agent_dir.mkdir(exist_ok=True)
        return agent_dir / "memory.json"
    
    def load_memories(self, agent_id: str) -> Dict[str, Any]:
        """加载智能体的所有记忆"""
        memory_file = self.get_agent_memory_path(agent_id)
        
        if not memory_file.exists():
            return {
                "agent_id": agent_id,
                "created_at": datetime.now().isoformat(),
                "memories": {},
                "statistics": {
                    "total_memories": 0,
                    "by_type": {},
                    "last_updated": None
                }
            }
        
        with open(memory_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_memories(self, agent_id: str, memory_data: Dict):
        """保存智能体的记忆"""
        memory_file = self.get_agent_memory_path(agent_id)
        
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)
    
    def create_memory(self, agent_id: str, memory_type: MemoryType, 
                     title: str, content: str, tags: List[str] = None,
                     importance: int = 3, metadata: Dict = None) -> str:
        """创建新的记忆条目"""
        memories = self.load_memories(agent_id)
        
        memory_id = self._generate_memory_id(agent_id, title, datetime.now())
        
        entry = MemoryEntry(
            id=memory_id,
            agent_id=agent_id,
            memory_type=memory_type.value,
            title=title,
            content=content,
            tags=tags or [],
            importance=importance,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            access_count=0,
            last_accessed_at=None,
            metadata=metadata or {}
        )
        
        memories["memories"][memory_id] = asdict(entry)
        
        # 更新统计
        memories["statistics"]["total_memories"] = len(memories["memories"])
        
        type_count = memories["statistics"]["by_type"].get(memory_type.value, 0)
        memories["statistics"]["by_type"][memory_type.value] = type_count + 1
        
        memories["statistics"]["last_updated"] = datetime.now().isoformat()
        
        self.save_memories(agent_id, memories)
        
        return memory_id
    
    def update_memory(self, agent_id: str, memory_id: str, 
                     content: str = None, tags: List[str] = None,
                     importance: int = None) -> bool:
        """更新记忆条目"""
        memories = self.load_memories(agent_id)
        
        if memory_id not in memories["memories"]:
            return False
        
        entry = memories["memories"][memory_id]
        
        if content is not None:
            entry["content"] = content
        if tags is not None:
            entry["tags"] = tags
        if importance is not None:
            entry["importance"] = importance
        
        entry["updated_at"] = datetime.now().isoformat()
        entry["access_count"] += 1
        entry["last_accessed_at"] = datetime.now().isoformat()
        
        self.save_memories(agent_id, memories)
        return True
    
    def get_memory(self, agent_id: str, memory_id: str) -> Optional[Dict]:
        """获取单个记忆"""
        memories = self.load_memories(agent_id)
        return memories["memories"].get(memory_id)
    
    def search_memories(self, agent_id: str, query: str = None,
                       memory_type: MemoryType = None,
                       tags: List[str] = None,
                       min_importance: int = None,
                       limit: int = 10) -> List[Dict]:
        """搜索记忆"""
        memories = self.load_memories(agent_id)
        results = []
        
        for memory_id, entry in memories["memories"].items():
            # 类型过滤
            if memory_type and entry["memory_type"] != memory_type.value:
                continue
            
            # 标签过滤
            if tags and not any(tag in entry["tags"] for tag in tags):
                continue
            
            # 重要性过滤
            if min_importance and entry["importance"] < min_importance:
                continue
            
            # 内容搜索
            if query:
                query_lower = query.lower()
                searchable = (
                    entry["title"].lower() + 
                    " " + entry["content"].lower() + 
                    " " + " ".join(entry["tags"]).lower()
                )
                if query_lower not in searchable:
                    continue
            
            results.append(entry)
        
        # 按重要性和访问时间排序
        results.sort(
            key=lambda x: (x["importance"], x["last_accessed_at"] or ""),
            reverse=True
        )
        
        return results[:limit]
    
    def delete_memory(self, agent_id: str, memory_id: str) -> bool:
        """删除记忆"""
        memories = self.load_memories(agent_id)
        
        if memory_id not in memories["memories"]:
            return False
        
        del memories["memories"][memory_id]
        memories["statistics"]["total_memories"] = len(memories["memories"])
        memories["statistics"]["last_updated"] = datetime.now().isoformat()
        
        self.save_memories(agent_id, memories)
        return True
    
    def activate_context_memories(self, agent_id: str, 
                                  context_keywords: List[str],
                                  max_count: int = 5) -> List[Dict]:
        """根据上下文激活相关记忆"""
        # 搜索与上下文关键词相关的记忆
        all_results = []
        for keyword in context_keywords:
            results = self.search_memories(
                agent_id=agent_id,
                query=keyword,
                limit=max_count
            )
            all_results.extend(results)
        
        # 去重并重新排序
        seen = set()
        unique_results = []
        for r in all_results:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique_results.append(r)
        
        return unique_results[:max_count]
    
    def _generate_memory_id(self, agent_id: str, title: str, timestamp) -> str:
        """生成记忆 ID"""
        unique_string = f"{agent_id}:{title}:{timestamp.isoformat()}"
        hash_value = hashlib.md5(unique_string.encode()).hexdigest()[:8]
        return f"{agent_id}_{timestamp.strftime('%Y%m%d%H%M%S')}_{hash_value}"
    
    def expire_old_memories(self, agent_id: str, 
                           days_threshold: int = 365,
                           min_importance_to_keep: int = 4) -> int:
        """清理过期记忆（低重要性且长时间未访问）"""
        memories = self.load_memories(agent_id)
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        deleted_count = 0
        to_delete = []
        
        for memory_id, entry in memories["memories"].items():
            last_accessed = entry.get("last_accessed_at")
            if not last_accessed:
                continue
            
            last_accessed_dt = datetime.fromisoformat(last_accessed)
            
            # 如果时间早于阈值且重要性低于保留标准
            if (last_accessed_dt < cutoff_date and 
                entry["importance"] < min_importance_to_keep):
                to_delete.append(memory_id)
        
        for memory_id in to_delete:
            del memories["memories"][memory_id]
            deleted_count += 1
        
        if deleted_count > 0:
            memories["statistics"]["total_memories"] = len(memories["memories"])
            memories["statistics"]["last_updated"] = datetime.now().isoformat()
            self.save_memories(agent_id, memories)
        
        return deleted_count
    
    def get_memory_statistics(self, agent_id: str) -> Dict:
        """获取记忆统计信息"""
        memories = self.load_memories(agent_id)
        return memories["statistics"]


# ==================== 使用示例 ====================

if __name__ == "__main__":
    mm = AgentMemoryManager()
    
    # 创建记忆
    memory_id = mm.create_memory(
        agent_id="strategic-planner",
        memory_type=MemoryType.LESSON,
        title="复杂项目规划经验",
        content="在处理涉及多个系统的数据迁移时，需要特别注意：1. 数据一致性验证 2. 回滚方案准备 3. 增量同步策略",
        tags=["数据迁移", "经验总结", "风险管控"],
        importance=5,
        metadata={"source_project": "customer-db-migration"}
    )
    print(f"Created memory: {memory_id}")
    
    # 搜索记忆
    results = mm.search_memories(
        agent_id="strategic-planner",
        query="数据迁移",
        min_importance=4
    )
    print(f"Found {len(results)} matching memories")
    
    # 激活上下文记忆
    context_memories = mm.activate_context_memories(
        agent_id="strategic-planner",
        context_keywords=["项目", "规划", "风险"]
    )
    print(f"Activated {len(context_memories)} context memories")
    
    # 查看统计
    stats = mm.get_memory_statistics("strategic-planner")
    print(f"Statistics: {json.dumps(stats, ensure_ascii=False, indent=2)}")
