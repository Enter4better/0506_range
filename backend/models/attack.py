# -*- coding: utf-8 -*-
"""
攻击记录模型 - SQLite实现
"""
import sqlite3
from datetime import datetime
import json
import logging
import random  # 添加 random 导入
import sys
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.database import db_service

logger = logging.getLogger('models.attack')


class Attack:
    """攻击记录模型类"""
    
    def __init__(self, attack_id=None, user_id=None, name=None, attack_type=None, target=None, port=None, intensity=None, status='pending', result=None, start_time=None, end_time=None, created_at=None):
        self.attack_id = attack_id
        self.user_id = user_id
        self.name = name
        self.attack_type = attack_type
        self.target = target
        self.port = port
        self.intensity = intensity
        self.status = status
        self.result = result
        self.start_time = start_time
        self.end_time = end_time
        self.created_at = created_at
    

    @staticmethod
    def create(name, attack_type, target, port, intensity, user_id, target_id=None, config=None):
        """创建新的攻击记录"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO attacks (user_id, name, attack_type, target, port, intensity, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, name, attack_type, target, port, intensity, 'pending', datetime.now().isoformat()))
                attack_id = cursor.lastrowid
                conn.commit()
                conn.close()
                return Attack(attack_id=attack_id, user_id=user_id, name=name, attack_type=attack_type, 
                            target=target, port=port, intensity=intensity, status='pending', 
                            created_at=datetime.now().isoformat())
        except Exception as e:
            logger.error(f"创建攻击记录失败: {e}")
        return None

    @staticmethod
    def get_by_id(attack_id):
        """根据ID获取攻击记录"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM attacks WHERE attack_id = ?", (attack_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return Attack(
                        attack_id=row['attack_id'],
                        user_id=row['user_id'],
                        name=row['name'],
                        attack_type=row['attack_type'],
                        target=row['target'],
                        port=row['port'],
                        intensity=row['intensity'],
                        status=row['status'],
                        result=row['result'],
                        start_time=row['start_time'],
                        end_time=row['end_time'],
                        created_at=row['created_at']
                    )
        except Exception as e:
            logger.error(f"获取攻击记录失败: {e}")
        return None
    
    @staticmethod
    def list_all(user_id=None, limit=100, offset=0, status=None, attack_type=None):
        """获取攻击记录列表"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                
                if user_id:
                    query = "SELECT * FROM attacks WHERE user_id = ?"
                    params = [user_id]
                else:
                    query = "SELECT * FROM attacks"
                    params = []
                
                conditions = []
                if status:
                    conditions.append("status = ?")
                    params.append(status)
                if attack_type:
                    conditions.append("attack_type = ?")
                    params.append(attack_type)
                
                if conditions:
                    query += " AND " + " AND ".join(conditions)
                
                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                conn.close()
                
                attacks = []
                for row in rows:
                    attacks.append(Attack(
                        attack_id=row['attack_id'],
                        user_id=row['user_id'],
                        name=row['name'],
                        attack_type=row['attack_type'],
                        target=row['target'],
                        port=row['port'],
                        intensity=row['intensity'],
                        status=row['status'],
                        result=row['result'],
                        start_time=row['start_time'],
                        end_time=row['end_time'],
                        created_at=row['created_at']
                    ))
                return attacks
        except Exception as e:
            logger.error(f"获取攻击记录列表失败: {e}")
        return []
    
    @staticmethod
    def count(user_id=None, status=None):
        """统计攻击记录数量"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                
                if user_id:
                    query = "SELECT COUNT(*) FROM attacks WHERE user_id = ?"
                    params = [user_id]
                else:
                    query = "SELECT COUNT(*) FROM attacks"
                    params = []
                
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                cursor.execute(query, params)
                count = cursor.fetchone()[0]
                conn.close()
                return count
        except Exception as e:
            logger.error(f"统计攻击记录数量失败: {e}")
        return 0
    
    @staticmethod
    def get_stats(user_id=None):
        """获取攻击统计"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                
                if user_id:
                    # 总数
                    cursor.execute("SELECT COUNT(*) FROM attacks WHERE user_id = ?", (user_id,))
                    total = cursor.fetchone()[0]
                    
                    # 按状态统计
                    cursor.execute("SELECT status, COUNT(*) FROM attacks WHERE user_id = ? GROUP BY status", (user_id,))
                    status_counts = {row[0]: row[1] for row in cursor.fetchall()}
                    
                    # 按类型统计
                    cursor.execute("SELECT attack_type, COUNT(*) FROM attacks WHERE user_id = ? GROUP BY attack_type", (user_id,))
                    type_counts = {row[0]: row[1] for row in cursor.fetchall()}
                else:
                    # 全局统计
                    cursor.execute("SELECT COUNT(*) FROM attacks")
                    total = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT status, COUNT(*) FROM attacks GROUP BY status")
                    status_counts = {row[0]: row[1] for row in cursor.fetchall()}
                    
                    cursor.execute("SELECT attack_type, COUNT(*) FROM attacks GROUP BY attack_type")
                    type_counts = {row[0]: row[1] for row in cursor.fetchall()}
                
                conn.close()
                
                return {
                    'total': total,
                    'status_counts': status_counts,
                    'type_counts': type_counts
                }
        except Exception as e:
            logger.error(f"获取攻击统计失败: {e}")
        return {'total': 0, 'status_counts': {}, 'type_counts': {}}
    
    @staticmethod
    def get_attack_types():
        """获取攻击类型列表"""
        return [
            {'type': 'SQL注入', 'category': 'Web攻击', 'description': 'SQL注入攻击'},
            {'type': 'XSS攻击', 'category': 'Web攻击', 'description': '跨站脚本攻击'},
            {'type': 'CSRF攻击', 'category': 'Web攻击', 'description': '跨站请求伪造'},
            {'type': '命令执行', 'category': '系统攻击', 'description': '命令注入攻击'},
            {'type': '端口扫描', 'category': '信息收集', 'description': '端口扫描'},
            {'type': '暴力破解', 'category': '认证攻击', 'description': '暴力破解'}
        ]
    
    def save(self):
        """保存攻击记录"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                
                if self.attack_id:
                    cursor.execute("""
                        UPDATE attacks SET 
                        user_id = ?, name = ?, attack_type = ?, target = ?, port = ?, 
                        intensity = ?, status = ?, result = ?, start_time = ?, end_time = ?
                        WHERE attack_id = ?
                    """, (self.user_id, self.name, self.attack_type, self.target, self.port,
                          self.intensity, self.status, self.result, self.start_time, self.end_time, self.attack_id))
                else:
                    cursor.execute("""
                        INSERT INTO attacks (user_id, name, attack_type, target, port, intensity, status, result, start_time, end_time, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (self.user_id, self.name, self.attack_type, self.target, self.port,
                          self.intensity, self.status, self.result, self.start_time, self.end_time, datetime.now().isoformat()))
                    self.attack_id = cursor.lastrowid
                
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.error(f"保存攻击记录失败: {e}")
        return False
    
    def delete(self):
        """删除攻击记录"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM attacks WHERE attack_id = ?", (self.attack_id,))
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.error(f"删除攻击记录失败: {e}")
        return False
    
    def update_status(self, status, result=None):
        """更新状态"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                if result:
                    cursor.execute("""
                        UPDATE attacks SET status = ?, result = ?, end_time = ? WHERE attack_id = ?
                    """, (status, json.dumps(result), datetime.now().isoformat(), self.attack_id))
                else:
                    cursor.execute("""
                        UPDATE attacks SET status = ? WHERE attack_id = ?
                    """, (status, self.attack_id))
                conn.commit()
                conn.close()
                self.status = status
                self.result = result
                return True
        except Exception as e:
            logger.error(f"更新攻击状态失败: {e}")
        return False
    
    def execute(self):
        """执行攻击"""
        success = random.choice([True, False])
        message = "攻击成功" if success else "攻击失败"
        
        vulnerabilities = []
        if success and random.random() > 0.3:
            vulnerabilities.append({'name': 'SQL注入漏洞', 'severity': '高'})
        if success and random.random() > 0.6:
            vulnerabilities.append({'name': 'XSS漏洞', 'severity': '中'})
            
        return {
            'success': success,
            'message': message,
            'details': f"对 {self.target}:{self.port} 进行了 {self.attack_type} 攻击，强度为 {self.intensity}",
            'vulnerabilities_found': vulnerabilities
        }
    
    def to_dict(self):
        """转换为字典"""
        return {
            'attack_id': self.attack_id,
            'user_id': self.user_id,
            'name': self.name,
            'attack_type': self.attack_type,
            'target': self.target,
            'port': self.port,
            'intensity': self.intensity,
            'status': self.status,
            'result': json.loads(self.result) if self.result else None,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'created_at': self.created_at
        }