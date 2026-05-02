#!/usr/bin/env python3
"""
多智能体团队协作调度器
========================

这个脚本提供了多种方式来触发和协调多智能体团队工作。
使用方法：python multi-agent-orchestrator.py <command> [arguments]

命令:
  run <task_type> [description]   - 运行特定类型的任务
  status                          - 查看当前任务状态  
  list                            - 列出所有可用智能体
  help                            - 显示帮助信息

示例:
  python multi-agent-orchestrator.py run project_planning "开发一个电商网站"
  python multi-agent-orchestrator.py run feature_impl "添加用户登录功能"
  python multi-agent-orchestrator.py run research "调研 AI Agent 市场"
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import subprocess


# ============== 配置 ==============

# 智能体技能路径
SKILLS_DIR = Path.home() / ".hermes/skills/multi-agent-team"

# 智能体定义
AGENTS = {
    "strategic-planner": {
        "name": "战略规划师",
        "role": "Planning",
        "skills_required": ["todo", "terminal"],
        "trigger_keywords": ["计划", "规划", "策略", "roadmap", "timeline"]
    },
    "code-architect": {
        "name": "代码架构师", 
        "role": "Design",
        "skills_required": ["terminal", "file"],
        "trigger_keywords": ["架构", "设计", "技术选型", "design", "architecture"]
    },
    "implementation-engineer": {
        "name": "实现工程师",
        "role": "Coding",
        "skills_required": ["terminal", "file"],
        "trigger_keywords": ["编码", "实现", "写代码", "develop", "implement"]
    },
    "qa-specialist": {
        "name": "QA 专家",
        "role": "Testing",
        "skills_required": ["terminal", "file"],
        "trigger_keywords": ["测试", "审查", "审计", "test", "review"]
    },
    "research-analyst": {
        "name": "研究分析师",
        "role": "Research",
        "skills_required": ["web", "file"],
        "trigger_keywords": ["调研", "分析", "研究", "research", "analyze"]
    },
    "documentation-specialist": {
        "name": "文档专家",
        "role": "Documentation",
        "skills_required": ["file", "terminal"],
        "trigger_keywords": ["文档", "手册", "指南", "document", "manual"]
    },
    "devops-engineer": {
        "name": "运维师",
        "role": "DevOps",
        "skills_required": ["terminal", "file"],
        "trigger_keywords": ["部署", "监控", "运维", "deploy", "monitor"]
    },
    "mcp-specialist": {
        "name": "MCP 专家",
        "role": "Tools",
        "skills_required": ["terminal", "file"],
        "trigger_keywords": ["工具", "集成", "API", "tool", "integration"]
    },
    "life-assistant": {
        "name": "生活助理",
        "role": "Life",
        "skills_required": ["web", "file"],
        "trigger_keywords": ["日程", "安排", "提醒", "schedule", "daily"]
    },
    "communication-coordinator": {
        "name": "沟通协调员",
        "role": "Coordination",
        "skills_required": ["file", "terminal"],
        "trigger_keywords": ["协调", "跟踪", "汇报", "coordinate", "report"]
    }
}

# 任务类型映射
TASK_TYPES = {
    "project_planning": ["strategic-planner", "communication-coordinator"],
    "system_design": ["code-architect", "research-analyst", "communication-coordinator"],
    "feature_implementation": ["implementation-engineer", "qa-specialist", "documentation-specialist"],
    "full_stack_project": [
        "strategic-planner", "code-architect", "implementation-engineer",
        "qa-specialist", "documentation-specialist", "devops-engineer",
        "communication-coordinator"
    ],
    "code_review": ["qa-specialist", "code-architect"],
    "deployment": ["devops-engineer", "mcp-specialist"],
    "market_research": ["research-analyst"],
    "life_management": ["life-assistant"],
    "tool_integration": ["mcp-specialist", "implementation-engineer", "qa-specialist"]
}


# ============== 核心功能 ==============

def print_banner():
    """打印横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        🎭 Hermes Multi-Agent Team Orchestrator           ║
║              多智能体团队协作调度器                       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def list_agents():
    """列出所有可用的智能体"""
    print("\n📋 可用智能体列表:\n")
    print("=" * 70)
    
    for agent_id, info in AGENTS.items():
        print(f"\n🤖 {info['name']} ({agent_id})")
        print(f"   角色：{info['role']}")
        print(f"   触发词：{', '.join(info['trigger_keywords'][:5])}")
        print(f"   需要工具：{', '.join(info['skills_required'])}")
    
    print("\n" + "=" * 70)
    print(f"\n总计：{len(AGENTS)} 个智能体\n")


def show_task_types():
    """展示可用的任务类型"""
    print("\n📊 预定义任务类型:\n")
    print("=" * 70)
    
    for task_type, agents in TASK_TYPES.items():
        agent_names = ", ".join([AGENTS[a]["name"] for a in agents if a in AGENTS])
        print(f"\n💼 {task_type.replace('_', ' ').title()}")
        print(f"   参与智能体：{agent_names}")
    
    print("\n" + "=" * 70 + "\n")


def detect_needed_agents(description: str) -> List[str]:
    """根据描述自动检测需要的智能体"""
    matched = {}
    
    description_lower = description.lower()
    
    for agent_id, info in AGENTS.items():
        score = sum(1 for kw in info["trigger_keywords"] if kw in description_lower)
        if score > 0:
            matched[agent_id] = score
    
    # 始终包含沟通协调员用于复杂任务
    if len(matched) > 1:
        matched["communication-coordinator"] = matched.get("communication-coordinator", 1)
    
    # 按匹配度排序返回
    sorted_agents = sorted(matched.keys(), key=lambda x: matched[x], reverse=True)
    
    return sorted_agents


def build_hermes_command(agent_ids: List[str], prompt: str) -> str:
    """构建 Hermes 命令行"""
    skills_param = ",".join([f"-s {aid}" for aid in agent_ids])
    return f"hermes chat {skills_param} -q \"{prompt}\""


def run_task(task_type: str, description: str, interactive: bool = True):
    """执行任务"""
    print(f"\n🚀 启动任务：{task_type}")
    print(f"💬 任务描述：{description}\n")
    
    # 获取需要的智能体
    if task_type in TASK_TYPES:
        agent_ids = TASK_TYPES[task_type]
        print(f"📦 使用预设配置：{task_type}")
    else:
        agent_ids = detect_needed_agents(description)
        if not agent_ids:
            agent_ids = ["communication-coordinator"]
            print("⚠️  未识别到特定模式，使用沟通协调员作为入口")
        else:
            print("🔍 自动检测到的智能体:")
    
    # 显示将使用的智能体
    print("\n🤖 将调用的智能体:")
    for agent_id in agent_ids:
        if agent_id in AGENTS:
            print(f"   • {AGENTS[agent_id]['name']} ({agent_id})")
    
    # 构建命令
    command = build_hermes_command(agent_ids, description)
    print(f"\n📝 将执行的命令:")
    print(f"   {command}\n")
    
    if interactive:
        confirm = input("是否继续执行？(y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 已取消")
            return
    
    # 执行命令
    try:
        print("\n⏳ 正在启动 Hermes Agent...\n")
        subprocess.run(command, shell=True, check=True)
        print("\n✅ 任务执行完成!")
        
        # 保存记录
        log_execution(task_type, description, agent_ids, "success")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 执行出错：{e}")
        log_execution(task_type, description, agent_ids, "failed", str(e))
    except KeyboardInterrupt:
        print("\n\n⚠️  被用户中断")
        log_execution(task_type, description, agent_ids, "interrupted")


def log_execution(task_type: str, description: str, agents: List[str], 
                  status: str, error: str = None):
    """记录执行日志"""
    log_dir = Path.home() / ".hermes/logs/multi-agent"
    log_dir.mkdir(exist_ok=True)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "task_type": task_type,
        "description": description,
        "agents_used": agents,
        "status": status,
        "error": error
    }
    
    log_file = log_dir / f"executions_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def show_status():
    """显示状态"""
    log_dir = Path.home() / ".hermes/logs/multi-agent"
    
    if not log_dir.exists():
        print("\n📊 暂无执行记录\n")
        return
    
    today_log = log_dir / f"executions_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    if not today_log.exists():
        print("\n📊 今日暂无执行记录\n")
        return
    
    print("\n📈 今日执行记录:\n")
    print("=" * 70)
    
    count = 0
    with open(today_log, "r", encoding="utf-8") as f:
        for line in reversed(list(f)[:10]):  # 最近 10 条
            entry = json.loads(line.strip())
            status_icon = {"success": "✅", "failed": "❌", "interrupted": "⚠️"}.get(entry["status"], "?")
            
            print(f"\n{status_icon} [{entry['timestamp'][:16]}]")
            print(f"   类型：{entry['task_type']}")
            print(f"   描述：{entry['description'][:50]}...")
            print(f"   智能体：{', '.join(entry['agents_used'][:3])}")
            
            count += 1
            if count >= 10:
                break
    
    print("\n" + "=" * 70 + "\n")


# ============== 主程序 ==============

def main():
    """主入口函数"""
    print_banner()
    
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_agents()
        
    elif command == "types":
        show_task_types()
        
    elif command == "status":
        show_status()
        
    elif command == "run":
        if len(sys.argv) < 3:
            print("❌ 错误：请指定任务类型")
            print("用法：python multi-agent-orchestrator.py run <task_type> [description]")
            return
        
        task_type = sys.argv[2]
        description = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        
        if not description:
            description = input("请输入任务描述：").strip()
        
        run_task(task_type, description)
        
    elif command in ["help", "--help", "-h"]:
        show_help()
        
    else:
        print(f"❌ 未知命令：{command}")
        print("使用 'hermes-multi-agent help' 查看帮助")


def show_help():
    """显示帮助信息"""
    help_text = """
📘 多智能体团队协作调度器 - 使用说明

基本命令:
  list                    列出所有可用智能体
  types                   显示预定义的任务类型
  status                  查看最近的执行记录
  run <type> [desc]       运行任务
  help                    显示此帮助信息

任务类型示例:
  project_planning        项目规划
  system_design           系统设计
  feature_implementation  功能实现
  full_stack_project      全栈项目开发
  code_review             代码审查
  deployment              部署上线
  market_research         市场调研
  life_management         生活管理
  tool_integration        工具集成

快捷示例:
  # 启动一个新项目的规划
  hermes-multi-agent run project_planning "开发哈尔滨本地生活服务 APP"

  # 实现某个功能
  hermes-multi-agent run feature_impl "添加用户注册功能"

  # 直接让沟通协调员处理（自动识别需要的智能体）
  hermes-multi-agent run custom "帮我分析一下竞争对手的定价策略"

配置文件位置:
  技能目录：~/.hermes/skills/multi-agent-team/
  日志文件：~/.hermes/logs/multi-agent/

需要帮助？
  查看 TEAM-GUIDE.md 获取详细的使用指南
"""
    print(help_text)


if __name__ == "__main__":
    main()
