# -*- coding: utf-8 -*-
"""
目标环境模型 - SQLite实现
"""
import sqlite3
from datetime import datetime
import json
import logging
import sys
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.database import db_service

logger = logging.getLogger('models.target')


class Target:
    """目标环境模型类"""
    
    def __init__(self, target_id=None, name=None, type='vm', ip=None, port=None, os=None, status='offline', config=None, session_id=None, created_at=None, updated_at=None):
        self.target_id = target_id
        self.name = name
        self.type = type
        self.ip = ip
        self.port = port
        self.os = os
        self.status = status
        self.config = config
        self.session_id = session_id
        self.created_at = created_at
        self.updated_at = updated_at
    
    @staticmethod
    def get_by_id(target_id):
        """根据ID获取目标"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM targets WHERE target_id = ?", (target_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return Target(
                        target_id=row['target_id'],
                        name=row['name'],
                        type=row['type'],
                        ip=row['ip'],
                        port=row['port'],
                        os=row['os'],
                        status=row['status'],
                        config=row['config'],
                        session_id=row['session_id'] if 'session_id' in row.keys() else None,
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
        except Exception as e:
            logger.error(f"获取目标失败: {e}")
        return None

    @staticmethod
    def get_scenario_name(target_or_config):
        """从 config JSON 提取 scenario_name"""
        config = target_or_config.config if hasattr(target_or_config, 'config') else target_or_config
        if config:
            try:
                c = json.loads(config) if isinstance(config, str) else config
                return c.get('scenario_name', '')
            except Exception:
                pass
        return ''
    
    @staticmethod
    def get_by_name(name):
        """根据名称获取目标"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM targets WHERE name = ?", (name,))
                row = cursor.fetchone()
                conn.close()

                if row:
                    return Target(
                        target_id=row['target_id'],
                        name=row['name'],
                        type=row['type'],
                        ip=row['ip'],
                        port=row['port'],
                        os=row['os'],
                        status=row['status'],
                        config=row['config'],
                        session_id=row['session_id'] if 'session_id' in row.keys() else None,
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
        except Exception as e:
            logger.error(f"获取目标失败: {e}")
        return None

    @staticmethod
    def get_scenario_containers(scenario_name):
        """获取同一场景的所有容器"""
        try:
            all_targets = Target.list_all()
            return [t for t in all_targets if Target.get_scenario_name(t) == scenario_name]
        except Exception:
            return []

    @staticmethod
    def list_scenarios():
        """按场景分组返回靶场（用于拓扑下拉）"""
        try:
            from collections import defaultdict
            all_targets = Target.list_all()
            groups = defaultdict(list)
            for t in all_targets:
                sn = Target.get_scenario_name(t)
                if sn:
                    groups[sn].append(t)
            return [{'scenario_name': sn, 'containers': containers} for sn, containers in groups.items()]
        except Exception as e:
            logger.error(f"获取场景列表失败: {e}")
            return []

    @staticmethod
    def create(name=None, image=None, status=None, ports=None, user_id=None, **kwargs):
        """创建目标环境"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO targets (name, type, ip, port, os, status, config, session_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name or f"target_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    kwargs.get('type', 'container'),
                    kwargs.get('ip', '127.0.0.1'),
                    kwargs.get('port', 8080),
                    image or kwargs.get('os', 'Linux'),
                    status or 'creating',
                    kwargs.get('config', '{}'),
                    kwargs.get('session_id'),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                target_id = cursor.lastrowid
                conn.commit()
                conn.close()
                return Target.get_by_id(target_id)
        except Exception as e:
            logger.error(f"创建目标失败: {e}")
        return None

    @staticmethod
    def list_all():
        """获取所有目标"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM targets ORDER BY created_at DESC")
                rows = cursor.fetchall()
                conn.close()
                
                targets = []
                for row in rows:
                    targets.append(Target(
                        target_id=row['target_id'],
                        name=row['name'],
                        type=row['type'],
                        ip=row['ip'],
                        port=row['port'],
                        os=row['os'],
                        status=row['status'],
                        config=row['config'],
                        session_id=row['session_id'] if 'session_id' in row.keys() else None,
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    ))
                return targets
        except Exception as e:
            logger.error(f"获取目标列表失败: {e}")
        return []
    
    @staticmethod
    def count():
        """统计目标数量"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM targets")
                count = cursor.fetchone()[0]
                conn.close()
                return count
        except Exception as e:
            logger.error(f"统计目标数量失败: {e}")
        return 0
    
    def save(self):
        """保存目标"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                
                if self.target_id:
                    # 更新现有目标
                    cursor.execute("""
                        UPDATE targets SET
                        name = ?, type = ?, ip = ?, port = ?, os = ?, status = ?, config = ?, session_id = ?, updated_at = ?
                        WHERE target_id = ?
                    """, (self.name, self.type, self.ip, self.port, self.os, self.status, self.config, self.session_id, datetime.now().isoformat(), self.target_id))
                else:
                    # 创建新目标
                    cursor.execute("""
                        INSERT INTO targets (name, type, ip, port, os, status, config, session_id, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (self.name, self.type, self.ip, self.port, self.os, self.status, self.config, self.session_id, datetime.now().isoformat(), datetime.now().isoformat()))
                    self.target_id = cursor.lastrowid
                
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.error(f"保存目标失败: {e}")
        return False
    
    def delete(self):
        """删除目标"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM targets WHERE target_id = ?", (self.target_id,))
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.error(f"删除目标失败: {e}")
        return False
    
    def update_status(self, status):
        """更新状态"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE targets SET status = ?, updated_at = ? WHERE target_id = ?
                """, (status, datetime.now().isoformat(), self.target_id))
                conn.commit()
                conn.close()
                self.status = status
                return True
        except Exception as e:
            logger.error(f"更新目标状态失败: {e}")
        return False
    
    def to_dict(self):
        """转换为字典"""
        return {
            'target_id': self.target_id,
            'name': self.name,
            'type': self.type,
            'ip': self.ip,
            'port': self.port,
            'os': self.os,
            'status': self.status,
            'config': self.config,
            'session_id': self.session_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    

    def update(self, **kwargs):
        """更新靶场属性"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                if 'name' in kwargs and kwargs['name'] is not None:
                    updates.append("name = ?")
                    params.append(kwargs['name'])
                if 'status' in kwargs and kwargs['status'] is not None:
                    updates.append("status = ?")
                    params.append(kwargs['status'])
                if 'port' in kwargs and kwargs['port'] is not None:
                    updates.append("port = ?")
                    params.append(kwargs['port'])
                if 'os' in kwargs and kwargs['os'] is not None:
                    updates.append("os = ?")
                    params.append(kwargs['os'])
                if 'type' in kwargs and kwargs['type'] is not None:
                    updates.append("type = ?")
                    params.append(kwargs['type'])
                if 'session_id' in kwargs and kwargs['session_id'] is not None:
                    updates.append("session_id = ?")
                    params.append(kwargs['session_id'])
                
                if updates:
                    query = f"UPDATE targets SET {', '.join(updates)}, updated_at = ? WHERE target_id = ?"
                    params.append(datetime.now().isoformat())
                    params.append(self.target_id)
                    cursor.execute(query, params)
                    conn.commit()
                    
                    # 更新当前对象属性
                    for key, value in kwargs.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
                
                conn.close()
                return True
        except Exception as e:
            logger.error(f"更新靶场失败: {e}")
        return False

    