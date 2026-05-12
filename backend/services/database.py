# -*- coding: utf-8 -*-
"""
数据库服务 - SQLite实现
"""
import sqlite3
import os
import logging
from pathlib import Path
from threading import Lock
from contextlib import contextmanager
import sys
from werkzeug.security import generate_password_hash

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import DB_CONFIG

logger = logging.getLogger('services.database')


class DatabaseService:
    """SQLite数据库服务"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.db_path = DB_CONFIG.get('path', 'data/ai_security_range.db')
        self._local_conn = None
        self._initialized = True
        
        # 确保数据目录存在
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"数据库路径: {self.db_path}")
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return None
    
    @contextmanager
    def connection(self):
        """连接上下文管理器"""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            if conn:
                conn.close()
    
    def test_connection(self):
        """测试数据库连接"""
        try:
            conn = self.get_connection()
            if conn:
                conn.execute("SELECT 1")
                conn.close()
                return True
            return False
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    def init_database(self):
        """初始化数据库表"""
        try:
            conn = self.get_connection()
            if not conn:
                logger.error("无法获取数据库连接")
                return False
            
            cursor = conn.cursor()
            
            # 创建用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            
            # 创建目标环境表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS targets (
                    target_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT DEFAULT 'vm',
                    ip TEXT,
                    port INTEGER,
                    os TEXT,
                    status TEXT DEFAULT 'offline',
                    config TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建攻击记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attacks (
                    attack_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_id INTEGER,
                    attack_type TEXT NOT NULL,
                    attack_name TEXT,
                    status TEXT DEFAULT 'pending',
                    result TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (target_id) REFERENCES targets(target_id)
                )
            """)
            
            # 创建防御规则表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS defenses (
                    defense_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    defense_type TEXT NOT NULL,
                    description TEXT,
                    enabled INTEGER DEFAULT 1,
                    coverage INTEGER DEFAULT 0,
                    config TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    source TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # 创建默认账号（密码均为 123456）
            for uname, email, role in [
                ('admin', 'admin@example.com', 'admin'),
                ('user',  'user@example.com',  'user'),
            ]:
                cursor.execute("""
                    INSERT OR IGNORE INTO users (username, password, email, role)
                    VALUES (?, ?, ?, ?)
                """, (uname, generate_password_hash('123456'), email, role))
            
            conn.commit()
            conn.close()
            
            logger.info("数据库初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            return False
    
    def execute_query(self, query, params=None):
        """执行查询"""
        try:
            with self.connection() as conn:
                if conn:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            return None
    
    def execute_insert(self, query, params=None):
        """执行插入"""
        try:
            with self.connection() as conn:
                if conn:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"插入执行失败: {e}")
            return None
    
    def execute_update(self, query, params=None):
        """执行更新"""
        try:
            with self.connection() as conn:
                if conn:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"更新执行失败: {e}")
            return None
    
    def execute_delete(self, query, params=None):
        """执行删除"""
        try:
            with self.connection() as conn:
                if conn:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"删除执行失败: {e}")
            return None


# 全局数据库服务实例
db_service = DatabaseService()