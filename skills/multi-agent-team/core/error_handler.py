#!/usr/bin/env python3
"""
Error Handler - 智能体错误处理与重试机制
==========================================

功能:
- 智能重试（指数退避）
- 多级降级策略
- 检查点恢复
- 错误分类和告警
"""

import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from enum import Enum
from functools import wraps
import logging


class ErrorType(Enum):
    """错误类型"""
    NETWORK = "network"        # 网络错误
    API_RATE_LIMIT = "api_rate_limit"  # API 限流
    TIMEOUT = "timeout"        # 超时
    PERMISSION = "permission"  # 权限错误
    VALIDATION = "validation"  # 验证失败
    UNKNOWN = "unknown"        # 未知错误


class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"           # 重试
    DEGRADATION = "degradation"  # 降级
    CHECKPOINT_RESTORE = "checkpoint_restore"  # 从检查点恢复
    MANUAL_INTERVENTION = "manual"   # 需要人工介入
    ABORT = "abort"           # 放弃任务


@dataclass
class ErrorContext:
    """错误上下文"""
    error_type: ErrorType
    agent_id: str
    task_id: str
    message: str
    timestamp: str
    retry_count: int
    metadata: Dict[str, Any]


class ErrorHandler:
    """错误处理器"""
    
    # 错误策略映射
    ERROR_STRATEGIES = {
        ErrorType.NETWORK: {
            "max_retries": 5,
            "base_delay": 1.0,
            "max_delay": 60.0,
            "fallback_strategy": RecoveryStrategy.CHECKPOINT_RESTORE
        },
        ErrorType.API_RATE_LIMIT: {
            "max_retries": 3,
            "base_delay": 30.0,  # 等待 30 秒后重试
            "max_delay": 300.0,
            "fallback_strategy": RecoveryStrategy.DEGRADATION
        },
        ErrorType.TIMEOUT: {
            "max_retries": 3,
            "base_delay": 2.0,
            "max_delay": 30.0,
            "fallback_strategy": RecoveryStrategy.DEGRADATION
        },
        ErrorType.PERMISSION: {
            "max_retries": 0,  # 不重试
            "fallback_strategy": RecoveryStrategy.MANUAL_INTERVENTION
        },
        ErrorType.VALIDATION: {
            "max_retries": 1,
            "base_delay": 0.5,
            "fallback_strategy": RecoveryStrategy.ABORT
        },
        ErrorType.UNKNOWN: {
            "max_retries": 2,
            "base_delay": 1.0,
            "max_delay": 10.0,
            "fallback_strategy": RecoveryStrategy.MANUAL_INTERVENTION
        }
    }
    
    def __init__(self, checkpoint_manager=None):
        self.checkpoint_manager = checkpoint_manager
        self.error_log_path = Path.home() / ".hermes/logs/errors.jsonl"
        self.alarm_log_path = Path.home() / ".hermes/logs/alarms.jsonl"
        
        # 确保目录存在
        self.error_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.alarm_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def handle_error(self, error: Exception, agent_id: str, task_id: str,
                    context: Dict = None, retry_count: int = 0) -> Dict:
        """处理错误并返回执行建议"""
        error_type = self._classify_error(error)
        
        error_context = ErrorContext(
            error_type=error_type,
            agent_id=agent_id,
            task_id=task_id,
            message=str(error),
            timestamp=datetime.now().isoformat(),
            retry_count=retry_count,
            metadata=context or {}
        )
        
        strategy_config = self.ERROR_STRATEGIES.get(error_type, 
                                                    self.ERROR_STRATEGIES[ErrorType.UNKNOWN])
        
        result = {
            "error_type": error_type.value,
            "message": str(error),
            "strategy": "",
            "should_retry": False,
            "wait_time": 0,
            "retry_count": retry_count,
            "max_retries": strategy_config["max_retries"],
            "details": {}
        }
        
        # 决策逻辑
        if retry_count < strategy_config["max_retries"]:
            # 应该重试
            wait_time = self._calculate_backoff(
                retry_count,
                strategy_config["base_delay"],
                strategy_config["max_delay"]
            )
            
            result["should_retry"] = True
            result["wait_time"] = wait_time
            result["strategy"] = RecoveryStrategy.RETRY.value
            result["details"]["next_retry_at"] = (
                datetime.now().timestamp() + wait_time
            )
        else:
            # 达到最大重试次数，使用降级策略
            fallback = strategy_config["fallback_strategy"]
            result["strategy"] = fallback.value
            
            if fallback == RecoveryStrategy.CHECKPOINT_RESTORE:
                result["details"]["action"] = "restore_from_checkpoint"
            elif fallback == RecoveryStrategy.DEGRADATION:
                result["details"]["action"] = "use_fallback_method"
                result["details"]["degraded_mode"] = True
            elif fallback == RecoveryStrategy.MANUAL_INTERVENTION:
                result["details"]["action"] = "await_human_decision"
                self._send_alarm(error_context)
            else:
                result["details"]["action"] = "abort_task"
        
        # 记录错误
        self._log_error(error_context)
        
        return result
    
    def calculate_backoff(self, attempt: int, base_delay: float = 1.0, 
                         max_delay: float = 60.0) -> float:
        """计算指数退避延迟"""
        delay = base_delay * (2 ** attempt)
        return min(delay, max_delay)
    
    def _calculate_backoff(self, attempt: int, base_delay: float, 
                          max_delay: float) -> float:
        """内部退避计算（添加随机抖动）"""
        import random
        delay = base_delay * (2 ** attempt)
        # 添加最多 20% 的随机抖动，防止雪崩
        jitter = random.uniform(0, 0.2 * delay)
        return min(delay + jitter, max_delay)
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """分类错误类型"""
        error_msg = str(error).lower()
        
        if "timeout" in error_msg or "timed out" in error_msg:
            return ErrorType.TIMEOUT
        elif "rate limit" in error_msg or "429" in error_msg:
            return ErrorType.API_RATE_LIMIT
        elif "permission denied" in error_msg or "403" in error_msg:
            return ErrorType.PERMISSION
        elif "connection" in error_msg or "network" in error_msg:
            return ErrorType.NETWORK
        elif "invalid" in error_msg or "validation" in error_msg:
            return ErrorType.VALIDATION
        else:
            return ErrorType.UNKNOWN
    
    def _log_error(self, context: ErrorContext):
        """记录错误日志"""
        log_entry = {
            "timestamp": context.timestamp,
            "agent_id": context.agent_id,
            "task_id": context.task_id,
            "error_type": context.error_type.value,
            "message": context.message,
            "retry_count": context.retry_count,
            "metadata": context.metadata
        }
        
        with open(self.error_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        self.logger.warning(f"Error logged: {context.error_type.value} - {context.message}")
    
    def _send_alarm(self, context: ErrorContext):
        """发送告警通知"""
        alarm_entry = {
            "timestamp": context.timestamp,
            "severity": "high",
            "agent_id": context.agent_id,
            "task_id": context.task_id,
            "error_type": context.error_type.value,
            "message": context.message,
            "requires_action": True,
            "suggested_actions": self._get_suggested_actions(context.error_type)
        }
        
        with open(self.alarm_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(alarm_entry, ensure_ascii=False) + "\n")
        
        self.logger.critical(f"ALARM: {context.message} - Requires manual intervention")
    
    def _get_suggested_actions(self, error_type: ErrorType) -> list:
        """获取建议的修复操作"""
        actions = {
            ErrorType.PERMISSION: [
                "检查智能体的权限配置 (~/.hermes/config/agent_permissions.json)",
                "确认该操作是否需要升级权限",
                "考虑调整任务范围以避免需要高权限的操作"
            ],
            ErrorType.API_RATE_LIMIT: [
                "联系管理员获取更多 API配额",
                "考虑切换到备用 API 提供商",
                "优化提示词以减少 token 消耗"
            ],
            ErrorType.NETWORK: [
                "检查网络连接状态",
                "验证目标服务是否可用",
                "检查防火墙规则"
            ]
        }
        return actions.get(error_type, ["查看错误日志以获取更多信息"])
    
    def execute_with_retry(self, func: Callable, agent_id: str, task_id: str,
                          max_retries: int = 3, **kwargs) -> Any:
        """带重试装饰器的函数执行"""
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(**kwargs)
            except Exception as e:
                last_error = e
                
                if attempt == max_retries:
                    break
                
                # 获取错误处理建议
                result = self.handle_error(e, agent_id, task_id, retry_count=attempt)
                
                if not result["should_retry"]:
                    break
                
                # 等待后退时间
                self.logger.info(
                    f"Attempt {attempt + 1} failed. "
                    f"Retrying in {result['wait_time']:.1f}s..."
                )
                time.sleep(result["wait_time"])
        
        # 所有重试都失败
        raise last_error


def retry_on_error(agent_id: str, task_id: str, 
                   max_attempts: int = 3, backoff_base: float = 1.0):
    """装饰器：自动重试失败的函数"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler()
            return handler.execute_with_retry(
                func, agent_id, task_id, max_retries=max_attempts,
                *args, **kwargs
            )
        return wrapper
    return decorator


# ==================== 使用示例 ====================

if __name__ == "__main__":
    handler = ErrorHandler()
    
    # 模拟处理错误
    try:
        # 模拟网络错误
        raise Exception("Connection timed out after 30s")
    except Exception as e:
        result = handler.handle_error(
            e, 
            agent_id="research-analyst",
            task_id="market-research-001"
        )
        print(f"Error handling result: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 使用装饰器
    @retry_on_error(agent_id="test-agent", task_id="test-task", max_attempts=2)
    def flaky_operation():
        print("Executing operation...")
        raise Exception("Network connection lost")
    
    try:
        flaky_operation()
    except Exception as e:
        print(f"Final failure after retries: {e}")
