# -*- coding: utf-8 -*-
"""
日志模型 - SQLite实现
"""
import sqlite3
from datetime import datetime, timedelta  # 添加 timedelta 导入
import json
import logging
import sys
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.database import db_service

logger = logging.getLogger('models.log')


class Log:
    """日志模型类"""
    
    def __init__(self, log_id=None, level=None, source=None, message=None, details=None, user_id=None, created_at=None):
        self.log_id = log_id
        self.level = level
        self.source = source
        self.message = message
        self.details = details
        self.user_id = user_id
        self.created_at = created_at
    
    @staticmethod
    def create(level, source, message, details=None, user_id=None, target_id=None, target=None):
        """创建日志"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO logs (level, source, message, details, user_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (level, source, message, details, user_id, datetime.now().isoformat()))
                conn.commit()
                log_id = cursor.lastrowid
                conn.close()
                return Log(
                    log_id=log_id,
                    level=level,
                    source=source,
                    message=message,
                    details=details,
                    user_id=user_id,
                    created_at=datetime.now().isoformat()
                )
        except Exception as e:
            logger.error(f"创建日志失败: {e}")
        return None
    
    @staticmethod
    def get_by_id(log_id):
        """根据ID获取日志"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM logs WHERE log_id = ?", (log_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return Log(
                        log_id=row['log_id'],
                        level=row['level'],
                        source=row['source'],
                        message=row['message'],
                        details=row['details'],
                        user_id=row['user_id'],
                        created_at=row['created_at']
                    )
        except Exception as e:
            logger.error(f"获取日志失败: {e}")
        return None
    

    @staticmethod
    def list_all(limit=100, offset=0, level=None, source=None, user_id=None):
        """获取日志列表"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM logs"
                params = []
                
                conditions = []
                if level:
                    conditions.append("level = ?")
                    params.append(level)
                
                if source:
                    conditions.append("source = ?")
                    params.append(source)
                
                if user_id:  # 只有当 user_id 有值时才添加条件
                    conditions.append("user_id = ?")
                    params.append(user_id)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                conn.close()
                
                logs = []
                for row in rows:
                    logs.append(Log(
                        log_id=row['log_id'],
                        level=row['level'],
                        source=row['source'],
                        message=row['message'],
                        details=row['details'],
                        user_id=row['user_id'],
                        created_at=row['created_at']
                    ))
                return logs
        except Exception as e:
            logger.error(f"获取日志列表失败: {e}")
        return []
   
    @staticmethod
    def get_attack_logs(limit=50):
        """获取攻击日志"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM logs WHERE source = 'attack' 
                    ORDER BY created_at DESC LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取攻击日志失败: {e}")
        return []
    
    @staticmethod
    def get_defense_logs(limit=50):
        """获取防御日志"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM logs WHERE source = 'defense' 
                    ORDER BY created_at DESC LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取防御日志失败: {e}")
        return []
    
    @staticmethod
    def get_system_logs(limit=50):
        """获取系统日志"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM logs WHERE source IN ('system', 'auth', 'env_agent') 
                    ORDER BY created_at DESC LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取系统日志失败: {e}")
        return []
    
    @staticmethod
    def get_docker_logs(limit=50):
        """获取Docker日志"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM logs WHERE source = 'docker' 
                    ORDER BY created_at DESC LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取Docker日志失败: {e}")
        return []
    
    @staticmethod
    def get_stats():
        """获取日志统计"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM logs")
                total = cursor.fetchone()[0]
                
                cursor.execute("SELECT level, COUNT(*) FROM logs GROUP BY level")
                level_counts = {row[0]: row[1] for row in cursor.fetchall()}
                
                conn.close()
                
                return {
                    'total': total,
                    'level_counts': level_counts
                }
        except Exception as e:
            logger.error(f"获取日志统计失败: {e}")
        return {'total': 0, 'level_counts': {}}
    
    @staticmethod
    def clear_logs(older_than_days=None):
        """清理日志"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                if older_than_days:
                    cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
                    cursor.execute("DELETE FROM logs WHERE created_at < ?", (cutoff,))
                else:
                    cursor.execute("DELETE FROM logs")
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                return deleted
        except Exception as e:
            logger.error(f"清理日志失败: {e}")
        return 0
    
    def delete(self):
        """删除日志"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM logs WHERE log_id = ?", (self.log_id,))
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.error(f"删除日志失败: {e}")
        return False
    
    def to_dict(self):
        """转换为字典"""
        return {
            'log_id': self.log_id,
            'level': self.level,
            'source': self.source,
            'message': self.message,
            'details': self.details,
            'user_id': self.user_id,
            'created_at': self.created_at
        }