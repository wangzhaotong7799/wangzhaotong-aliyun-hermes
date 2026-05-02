#!/usr/bin/env python3
"""
Permission Controller - 智能体权限控制系统
=========================================

功能:
- 细粒度的工具访问控制
- 命令级别的安全过滤
- 操作审计日志
- 动态权限管理
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass


class PermissionLevel(Enum):
    """权限级别"""
    NONE = 0          # 无权限
    READ_ONLY = 1     # 只读
    RESTRICTED = 2    # 受限（需要白名单）
    FULL = 3          # 完全权限


@dataclass
class PermissionRule:
    """权限规则"""
    agent_id: str
    tool_name: str
    permission_level: PermissionLevel
    allowed_commands: Optional[Set[str]] = None  # 白名单命令
    denied_patterns: Optional[List[str]] = None  # 黑名单模式
    path_restrictions: Optional[Dict[str, List[str]]] = None  # 路径限制
    metadata: Optional[Dict] = None


class PermissionController:
    """权限控制器"""
    
    # 危险命令模式
    DANGEROUS_COMMANDS = [
        r'^rm\s+-rf\s+/',      # 删除根目录
        r'^rm\s+-rf\s+\*',     # 通配符删除
        r':\(\)\{\s*:\|\:&\s*\}',  # 分叉炸弹
        r'mkfs\s+',            # 格式化文件系统
        r'dd\s+if=/dev/zero',  # 数据覆盖
        r'sudo.*passwd',       # 修改密码
        r'chmod\s+777\s+/',    # 危险权限设置
    ]
    
    # 敏感文件模式
    SENSITIVE_FILES = [
        r'./\.ssh/',
        r'./id_rsa',
        r'./\.aws/credentials',
        r'/etc/shadow',
        r'/etc/passwd',
    ]
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = str(Path.home() / ".hermes/config/agent_permissions.json")
        
        self.config_path = Path(config_path)
        self.audit_log_path = Path.home() / ".hermes/logs/permission_audit.jsonl"
        
        # 确保目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载或初始化配置
        if not self.config_path.exists():
            self._initialize_default_config()
        
        self.rules = self._load_config()
    
    def _initialize_default_config(self):
        """初始化默认权限配置"""
        default_config = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "agents": {
                # 战略规划师 - 主要是分析和计划
                "strategic-planner": {
                    "terminal": {
                        "level": "read-only",
                        "allowed_commands": ["ls", "pwd", "cat", "grep", "find", "wc"],
                        "denied_patterns": ["^sudo", "^apt", "^yum", "^chmod", "^chown"]
                    },
                    "file": {
                        "level": "read",
                        "path_allow": ["/root", "/home", "/tmp"],
                        "path_deny": ["/etc", "/var/log", "/root/.ssh"]
                    },
                    "web": {
                        "level": "full"
                    }
                },
                
                # 代码架构师 - 设计和审查
                "code-architect": {
                    "terminal": {
                        "level": "restricted",
                        "allowed_commands": ["ls", "cat", "grep", "find", "tree", "diff"],
                        "denied_patterns": ["^rm\s+-rf", "^mv.*", "^cp.*"]
                    },
                    "file": {
                        "level": "read-write",
                        "path_allow": ["/root/projects", "/home/*/workspace"],
                        "path_deny": ["/etc", "/boot"]
                    }
                },
                
                # 实现工程师 - 开发和实现
                "implementation-engineer": {
                    "terminal": {
                        "level": "full",
                        "denied_patterns": ["rm\s+-rf\s+$", ":\\(\\)\\{\\s*:\\|&\\s:*\\}"]
                    },
                    "file": {
                        "level": "read-write",
                        "path_allow": ["/root", "/home"],
                        "path_deny": ["/etc/shadow", "/etc/sudoers"]
                    }
                },
                
                # QA 专家 - 测试和审查
                "qa-specialist": {
                    "terminal": {
                        "level": "restricted",
                        "allowed_commands": [
                            "python", "pytest", "npm test", "make test", 
                            "grep", "diff", "curl", "wget"
                        ],
                        "denied_patterns": ["^rm\\b", "^sudo\\b"]
                    },
                    "file": {
                        "level": "read",
                        "path_allow": ["/root", "/home", "/tmp"]
                    }
                },
                
                # 运维师 - 部署和监控
                "devops-engineer": {
                    "terminal": {
                        "level": "full",
                        "denied_patterns": [r':\\(\\)\\{\\s*:\\|&\\s:*\\}']  # 禁止分叉炸弹
                    },
                    "file": {
                        "level": "read-write",
                        "path_allow": ["/root", "/var", "/etc"],
                        "path_deny": ["/boot", "/proc"]
                    }
                },
                
                # MCP 专家 - 工具集成
                "mcp-specialist": {
                    "terminal": {
                        "level": "restricted",
                        "allowed_commands": ["curl", "wget", "jq", "cat", "echo"],
                        "path_allow": ["/tmp", "/home"]
                    },
                    "file": {
                        "level": "read-write",
                        "path_allow": ["/root/.hermes/config"]
                    }
                },
                
                # 生活助理 - 日常事务
                "life-assistant": {
                    "terminal": {
                        "level": "none"  # 不需要终端权限
                    },
                    "file": {
                        "level": "read",
                        "path_allow": ["/home"]
                    },
                    "web": {
                        "level": "full"
                    }
                },
                
                # 沟通协调员 - 管理和协调
                "communication-coordinator": {
                    "terminal": {
                        "level": "read-only",
                        "allowed_commands": ["ps", "top", "free", "df"]
                    },
                    "file": {
                        "level": "read",
                        "path_allow": ["/root/.hermes/state", "/root/.hermes/memory"]
                    }
                }
            },
            "global_rules": {
                "dangerous_commands_blocked": True,
                "sensitive_files_protected": True,
                "audit_all_operations": True
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
    
    def _load_config(self) -> Dict:
        """加载配置"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def check_terminal_permission(self, agent_id: str, command: str) -> Dict:
        """检查终端命令权限"""
        result = {
            "allowed": False,
            "reason": "",
            "agent_id": agent_id,
            "command": command,
            "timestamp": datetime.now().isoformat()
        }
        
        # 检查是否是全局危险命令
        if self.rules.get("global_rules", {}).get("dangerous_commands_blocked"):
            for pattern in self.DANGEROUS_COMMANDS:
                if re.match(pattern, command):
                    result["reason"] = f"Blocked by global dangerous command policy: {pattern}"
                    self._log_audit(result)
                    return result
        
        # 检查智能体特定规则
        agent_rules = self.rules.get("agents", {}).get(agent_id, {})
        terminal_rules = agent_rules.get("terminal", {})
        
        level_str = terminal_rules.get("level", "none")
        permission_level = PermissionLevel[level_str.upper()]
        
        if permission_level == PermissionLevel.NONE:
            result["reason"] = f"Agent '{agent_id}' has no terminal access"
            self._log_audit(result)
            return result
        
        # 检查黑名单
        denied_patterns = terminal_rules.get("denied_patterns", [])
        for pattern in denied_patterns:
            if re.match(pattern, command):
                result["reason"] = f"Command matches denied pattern: {pattern}"
                self._log_audit(result)
                return result
        
        # 如果是 restricted 级别，检查白名单
        if permission_level == PermissionLevel.RESTRICTED:
            allowed_commands = terminal_rules.get("allowed_commands", [])
            cmd_base = command.split()[0] if command.split() else ""
            
            if allowed_commands and cmd_base not in allowed_commands:
                result["reason"] = f"Command '{cmd_base}' not in whitelist"
                self._log_audit(result)
                return result
        
        # 通过检查
        result["allowed"] = True
        result["reason"] = "Permission granted"
        result["permission_level"] = level_str
        self._log_audit(result)
        return result
    
    def check_file_permission(self, agent_id: str, filepath: str, 
                             operation: str) -> Dict:
        """检查文件操作权限"""
        result = {
            "allowed": False,
            "reason": "",
            "agent_id": agent_id,
            "filepath": filepath,
            "operation": operation,
            "timestamp": datetime.now().isoformat()
        }
        
        # 检查敏感文件
        if self.rules.get("global_rules", {}).get("sensitive_files_protected"):
            for pattern in self.SENSITIVE_FILES:
                if re.match(pattern, filepath):
                    result["reason"] = f"Access to sensitive file blocked: {pattern}"
                    self._log_audit(result)
                    return result
        
        # 检查智能体特定规则
        agent_rules = self.rules.get("agents", {}).get(agent_id, {})
        file_rules = agent_rules.get("file", {})
        
        level_str = file_rules.get("level", "none")
        
        # 检查读写权限
        if operation in ["write", "delete", "modify"]:
            if level_str in ["none", "read"]:
                result["reason"] = f"Write operation not allowed (level: {level_str})"
                self._log_audit(result)
                return result
        
        # 检查路径限制
        path_allow = file_rules.get("path_allow", [])
        path_deny = file_rules.get("path_deny", [])
        
        # 先检查黑名单
        for pattern in path_deny:
            if re.match(pattern, filepath):
                result["reason"] = f"File path blocked by deny rule: {pattern}"
                self._log_audit(result)
                return result
        
        # 再检查白名单
        if path_allow:
            if not any(re.match(pattern, filepath) for pattern in path_allow):
                result["reason"] = f"File path not in allow list"
                self._log_audit(result)
                return result
        
        # 通过检查
        result["allowed"] = True
        result["reason"] = "Permission granted"
        result["permission_level"] = level_str
        self._log_audit(result)
        return result
    
    def get_agent_permissions_summary(self, agent_id: str) -> Dict:
        """获取智能体的权限摘要"""
        agent_rules = self.rules.get("agents", {}).get(agent_id, {})
        summary = {"agent_id": agent_id, "tools": {}}
        
        for tool_name, rules in agent_rules.items():
            summary["tools"][tool_name] = {
                "level": rules.get("level", "none"),
                "restrictions": {
                    k: v for k, v in rules.items() 
                    if k in ["allowed_commands", "denied_patterns", 
                            "path_allow", "path_deny"]
                }
            }
        
        return summary
    
    def _log_audit(self, audit_entry: Dict):
        """记录审计日志"""
        if not self.rules.get("global_rules", {}).get("audit_all_operations"):
            return
        
        with open(self.audit_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")


# ==================== 使用示例 ====================

if __name__ == "__main__":
    pc = PermissionController()
    
    # 测试终端命令权限
    result = pc.check_terminal_permission(
        agent_id="strategic-planner",
        command="ls -la /root"
    )
    print(f"Terminal permission check: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 测试文件操作权限
    result = pc.check_file_permission(
        agent_id="implementation-engineer",
        filepath="/root/project/app.py",
        operation="write"
    )
    print(f"File permission check: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 获取权限摘要
    summary = pc.get_agent_permissions_summary("qa-specialist")
    print(f"Permissions summary: {json.dumps(summary, ensure_ascii=False, indent=2)}")
