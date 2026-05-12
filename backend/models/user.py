# -*- coding: utf-8 -*-
"""
用户模型 - SQLite实现
"""
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import sys
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.database import db_service

logger = logging.getLogger('models.user')


class User:
    """用户模型类"""
    
    def __init__(self, user_id=None, username=None, password=None, email=None, role='user', created_at=None, last_login=None):
        self.user_id = user_id
        self.username = username
        self.password = password
        self.email = email
        self.role = role
        self.created_at = created_at
        self.last_login = last_login
    
    @staticmethod
    def get_by_id(user_id):
        """根据ID获取用户"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return User(
                        user_id=row['user_id'],
                        username=row['username'],
                        password=row['password'],
                        email=row['email'],
                        role=row['role'],
                        created_at=row['created_at'],
                        last_login=row['last_login']
                    )
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
        return None
    
    @staticmethod
    def get_by_username(username):
        """根据用户名获取用户"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return User(
                        user_id=row['user_id'],
                        username=row['username'],
                        password=row['password'],
                        email=row['email'],
                        role=row['role'],
                        created_at=row['created_at'],
                        last_login=row['last_login']
                    )
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
        return None
    
    @staticmethod
    def list_all():
        """获取所有用户"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
                rows = cursor.fetchall()
                conn.close()
                
                users = []
                for row in rows:
                    users.append(User(
                        user_id=row['user_id'],
                        username=row['username'],
                        password=row['password'],
                        email=row['email'],
                        role=row['role'],
                        created_at=row['created_at'],
                        last_login=row['last_login']
                    ))
                return users
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
        return []
    
    def save(self):
        """保存用户"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                
                if self.user_id:
                    # 更新现有用户
                    cursor.execute("""
                        UPDATE users SET 
                        username = ?, email = ?, role = ?, last_login = ?
                        WHERE user_id = ?
                    """, (self.username, self.email, self.role, self.last_login, self.user_id))
                else:
                    # 创建新用户
                    hashed_password = generate_password_hash(self.password, method='pbkdf2:sha256')
                    cursor.execute("""
                        INSERT INTO users (username, password, email, role)
                        VALUES (?, ?, ?, ?)
                    """, (self.username, hashed_password, self.email, self.role))
                    self.user_id = cursor.lastrowid
                
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.error(f"保存用户失败: {e}")
        return False
    
    def delete(self):
        """删除用户"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE user_id = ?", (self.user_id,))
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.error(f"删除用户失败: {e}")
        return False
    
    def update_last_login(self):
        """更新最后登录时间"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET last_login = ? WHERE user_id = ?
                """, (datetime.now().isoformat(), self.user_id))
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.error(f"更新登录时间失败: {e}")
        return False
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password, password)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at,
            'last_login': self.last_login
        }