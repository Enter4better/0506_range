# -*- coding: utf-8 -*-
"""
异步队列服务 - 任务队列管理
"""
import asyncio
import threading
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import logging
import sys
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import DB_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AsyncTask:
    """异步任务"""
    
    def __init__(self, task_id: str, task_type: str, func: Callable, args: tuple = (),
                 kwargs: dict = None, priority: int = 0, timeout: int = None):
        self.task_id = task_id
        self.task_type = task_type
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.timeout = timeout
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self.status = 'pending'  # pending, running, completed, failed
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'priority': self.priority,
            'timeout': self.timeout,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'result': self.result,
            'error': self.error
        }


class AsyncQueueService:
    """异步队列服务"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.queue = []
        self.running_tasks = {}
        self.completed_tasks = {}
        self.lock = threading.Lock()
        self.running = False
        self.workers = []
        self.app = None
    
    def set_app(self, app):
        """设置 Flask 应用实例，使后台线程能访问应用上下文"""
        self.app = app
    
    def start(self):
        """启动队列服务"""
        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.workers.append(worker)
        logger.info(f"异步队列服务启动，工作线程数: {self.max_workers}")
    
    def stop(self):
        """停止队列服务"""
        self.running = False
        logger.info("异步队列服务停止")
    
    def add_task(self, task_type: str, func: Callable, args: tuple = (),
                 kwargs: dict = None, priority: int = 0, timeout: int = None) -> str:
        """添加任务到队列"""
        task_id = str(uuid.uuid4())
        task = AsyncTask(task_id, task_type, func, args, kwargs, priority, timeout)
        
        with self.lock:
            self.queue.append(task)
            # 按优先级排序
            self.queue.sort(key=lambda t: t.priority, reverse=True)
        
        logger.info(f"任务添加到队列: {task_id} ({task_type})")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self.lock:
            # 检查运行中的任务
            if task_id in self.running_tasks:
                return self.running_tasks[task_id].to_dict()
            
            # 检查已完成的任务
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id].to_dict()
            
            # 检查队列中的任务
            for task in self.queue:
                if task.task_id == task_id:
                    return task.to_dict()
        
        return None
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务"""
        tasks = []
        with self.lock:
            # 队列中的任务
            for task in self.queue:
                tasks.append(task.to_dict())
            
            # 运行中的任务
            for task_id, task in self.running_tasks.items():
                tasks.append(task.to_dict())
            
            # 已完成的任务
            for task_id, task in self.completed_tasks.items():
                tasks.append(task.to_dict())
        
        return tasks
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.lock:
            # 从队列中移除
            for i, task in enumerate(self.queue):
                if task.task_id == task_id:
                    self.queue.pop(i)
                    logger.info(f"任务已取消: {task_id}")
                    return True
        
        return False
    
    def clear_completed_tasks(self):
        """清理已完成任务"""
        with self.lock:
            self.completed_tasks.clear()
        logger.info("已完成任务已清理")
    
    def _worker_loop(self):
        """工作线程循环"""
        while self.running:
            task = None
            
            with self.lock:
                if self.queue:
                    task = self.queue.pop(0)
                    self.running_tasks[task.task_id] = task
            
            if task:
                self._execute_task(task)
            else:
                # 没有任务时休眠
                threading.Event().wait(0.1)
    
    def _execute_task(self, task: AsyncTask):
        """执行任务"""
        task.status = 'running'
        task.started_at = datetime.now()
        
        try:
            logger.info(f"开始执行任务: {task.task_id}")
            
            # 在 Flask 应用上下文中执行，支持后台线程中使用 current_app
            if self.app:
                with self.app.app_context():
                    result = task.func(*task.args, **task.kwargs)
            else:
                result = task.func(*task.args, **task.kwargs)
            
            task.result = result
            task.status = 'completed'
            task.completed_at = datetime.now()
            logger.info(f"任务执行成功: {task.task_id}")
        except Exception as e:
            task.error = str(e)
            task.status = 'failed'
            task.completed_at = datetime.now()
            logger.error(f"任务执行失败: {task.task_id} - {e}")
        
        # 移动到已完成队列
        with self.lock:
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
            self.completed_tasks[task.task_id] = task
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        with self.lock:
            return {
                'queue_size': len(self.queue),
                'running_size': len(self.running_tasks),
                'completed_size': len(self.completed_tasks),
                'max_workers': self.max_workers,
                'running': self.running
            }


# 全局异步队列服务实例
async_queue_service = AsyncQueueService()