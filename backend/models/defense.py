# -*- coding: utf-8 -*-
"""
防御规则模型 - SQLite实现
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

logger = logging.getLogger('models.defense')


class Defense:
    """防御规则模型类"""
    
    def __init__(self, defense_id=None, name=None, defense_type=None, description=None, enabled=1, coverage=0, config=None, created_at=None, updated_at=None):
        self.defense_id = defense_id
        self.name = name
        self.defense_type = defense_type
        self.description = description
        self.enabled = enabled
        self.coverage = coverage
        self.config = config
        self.created_at = created_at
        self.updated_at = updated_at
    
    @staticmethod
    def get_by_id(defense_id):
        """根据ID获取防御规则"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM defenses WHERE defense_id = ?", (defense_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return Defense(
                        defense_id=row['defense_id'],
                        name=row['name'],
                        defense_type=row['defense_type'],
                        description=row['description'],
                        enabled=row['enabled'],
                        coverage=row['coverage'],
                        config=row['config'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
        except Exception as e:
            logger.error(f"获取防御规则失败: {e}")
        return None
    
    @staticmethod
    def list_all(enabled=None):
        """获取所有防御规则"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                
                if enabled is not None:
                    cursor.execute("SELECT * FROM defenses WHERE enabled = ? ORDER BY created_at DESC", (enabled,))
                else:
                    cursor.execute("SELECT * FROM defenses ORDER BY created_at DESC")
                
                rows = cursor.fetchall()
                conn.close()
                
                defenses = []
                for row in rows:
                    defenses.append(Defense(
                        defense_id=row['defense_id'],
                        name=row['name'],
                        defense_type=row['defense_type'],
                        description=row['description'],
                        enabled=row['enabled'],
                        coverage=row['coverage'],
                        config=row['config'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    ))
                return defenses
        except Exception as e:
            logger.error(f"获取防御规则列表失败: {e}")
        return []
    
    @staticmethod
    def count(enabled=None):
        """统计防御规则数量"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                
                if enabled is not None:
                    cursor.execute("SELECT COUNT(*) FROM defenses WHERE enabled = ?", (enabled,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM defenses")
                
                count = cursor.fetchone()[0]
                conn.close()
                return count
        except Exception as e:
            logger.error(f"统计防御规则数量失败: {e}")
        return 0
    
    @staticmethod
    def get_stats():
        """获取防御统计"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                
                # 总数
                cursor.execute("SELECT COUNT(*) FROM defenses")
                total = cursor.fetchone()[0]
                
                # 启用数量
                cursor.execute("SELECT COUNT(*) FROM defenses WHERE enabled = 1")
                enabled_count = cursor.fetchone()[0]
                
                # 按类型统计
                cursor.execute("SELECT defense_type, COUNT(*) FROM defenses GROUP BY defense_type")
                type_counts = {row[0]: row[1] for row in cursor.fetchall()}
                
                # 平均覆盖率
                cursor.execute("SELECT AVG(coverage) FROM defenses")
                avg_coverage = cursor.fetchone()[0] or 0
                
                conn.close()
                
                return {
                    'total': total,
                    'enabled': enabled_count,
                    'disabled': total - enabled_count,
                    'type_counts': type_counts,
                    'avg_coverage': round(avg_coverage, 2)
                }
        except Exception as e:
            logger.error(f"获取防御统计失败: {e}")
        return {'total': 0, 'enabled': 0, 'disabled': 0, 'type_counts': {}, 'avg_coverage': 0}
    
    def save(self):
        """保存防御规则"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                
                if self.defense_id:
                    # 更新现有规则
                    cursor.execute("""
                        UPDATE defenses SET 
                        name = ?, defense_type = ?, description = ?, enabled = ?, coverage = ?, config = ?, updated_at = ?
                        WHERE defense_id = ?
                    """, (self.name, self.defense_type, self.description, self.enabled, self.coverage, self.config, datetime.now().isoformat(), self.defense_id))
                else:
                    # 创建新规则
                    cursor.execute("""
                        INSERT INTO defenses (name, defense_type, description, enabled, coverage, config, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (self.name, self.defense_type, self.description, self.enabled, self.coverage, self.config, datetime.now().isoformat(), datetime.now().isoformat()))
                    self.defense_id = cursor.lastrowid
                
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.error(f"保存防御规则失败: {e}")
        return False
    
    def delete(self):
        """删除防御规则"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM defenses WHERE defense_id = ?", (self.defense_id,))
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.error(f"删除防御规则失败: {e}")
        return False
    
    def toggle(self):
        """切换启用状态"""
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                new_enabled = 0 if self.enabled else 1
                cursor.execute("""
                    UPDATE defenses SET enabled = ?, updated_at = ? WHERE defense_id = ?
                """, (new_enabled, datetime.now().isoformat(), self.defense_id))
                conn.commit()
                conn.close()
                self.enabled = new_enabled
                return True
        except Exception as e:
            logger.error(f"切换防御状态失败: {e}")
        return False
    
    def check_attack(self, attack_type: str, intensity: int):
        """检查攻击是否被防御规则拦截"""
        try:
            import random
            
            # 基础拦截率基于 coverage
            base_block_rate = self.coverage / 100.0
            
            # 根据攻击类型调整拦截率
            type_boost = {
                'SQL Injection': 0.1,
                'XSS': 0.1,
                'Port Scan': 0.15,
                'Brute Force': 0.1,
                'CSRF': 0.05
            }
            
            # 根据防御类型调整
            defense_boost = {
                'WAF': 0.1,
                'IPS': 0.15,
                'Firewall': 0.1,
                'IDS': 0.05
            }
            
            boost = type_boost.get(attack_type, 0) + defense_boost.get(self.defense_type, 0)
            block_rate = min(0.95, base_block_rate + boost)
            
            # 根据攻击强度降低拦截率（高强度攻击更难防御）
            intensity_factor = 1.0 - (intensity - 5) * 0.05
            block_rate = max(0.05, block_rate * intensity_factor)
            
            blocked = random.random() < block_rate
            
            messages = {
                True: [
                    f'{self.name} 成功拦截了 {attack_type} 攻击',
                    f'{self.defense_type} 防御系统阻断了恶意请求',
                    f'攻击流量被 {self.name} 过滤',
                    f'威胁检测: {attack_type} 攻击已被阻止'
                ],
                False: [
                    f'{self.name} 未能完全阻止攻击',
                    f'{attack_type} 攻击绕过了防御检查',
                    f'防御系统未能识别此次攻击'
                ]
            }
            
            message = random.choice(messages[blocked])
            
            return {
                'blocked': blocked,
                'block_rate': round(block_rate * 100, 2),
                'message': message,
                'defense_name': self.name,
                'defense_type': self.defense_type
            }
        except Exception as e:
            logger.error(f"防御检查失败: {e}")
            return {
                'blocked': False,
                'block_rate': 0,
                'message': f'防御检查出错: {str(e)}',
                'defense_name': self.name,
                'defense_type': self.defense_type
            }
    
    @staticmethod
    def get_defense_types():
        """获取防御类型列表 - 使用标准安全防御类型"""
        try:
            # 返回标准的网络安全防御类型，基于开源安全工具的常见分类
            defense_types = [
                {'type': 'WAF', 'category': 'Web应用防护', 'description': 'Web应用防火墙，防护SQL注入、XSS等Web攻击'},
                {'type': 'IDS', 'category': '入侵检测', 'description': '入侵检测系统，监控网络流量中的恶意活动'},
                {'type': 'IPS', 'category': '入侵防御', 'description': '入侵防御系统，主动阻断已知攻击'},
                {'type': 'Firewall', 'category': '网络层防护', 'description': '网络防火墙，控制进出网络的流量'},
                {'type': 'Honeypot', 'category': '欺骗技术', 'description': '蜜罐系统，诱捕攻击者并收集攻击信息'},
                {'type': 'Antivirus', 'category': '终端防护', 'description': '反病毒软件，检测和清除恶意软件'},
                {'type': 'SIEM', 'category': '安全信息管理', 'description': '安全信息和事件管理系统，集中分析安全日志'},
                {'type': 'NAC', 'category': '网络接入控制', 'description': '网络准入控制，确保设备符合安全策略'},
                {'type': 'DLP', 'category': '数据泄露防护', 'description': '数据泄露防护，防止敏感数据外泄'},
                {'type': 'EDR', 'category': '终端检测响应', 'description': '终端检测与响应，持续监控终端安全状况'},
                {'type': 'IAM', 'category': '身份认证管理', 'description': '身份与访问管理，控制用户权限'},
                {'type': 'Vulnerability Scanner', 'category': '漏洞管理', 'description': '漏洞扫描器，定期检测系统漏洞'}
            ]
            return defense_types
        except Exception as e:
            logger.error(f"获取防御类型失败: {e}")
            # 出错时返回默认类型
            return [
                {'type': 'WAF', 'category': 'Web应用防护', 'description': 'Web应用防火墙，防护SQL注入、XSS等Web攻击'},
                {'type': 'IDS', 'category': '入侵检测', 'description': '入侵检测系统，监控网络流量中的恶意活动'},
                {'type': 'IPS', 'category': '入侵防御', 'description': '入侵防御系统，主动阻断已知攻击'},
                {'type': 'Firewall', 'category': '网络层防护', 'description': '网络防火墙，控制进出网络的流量'},
                {'type': 'Honeypot', 'category': '欺骗技术', 'description': '蜜罐系统，诱捕攻击者并收集攻击信息'}
            ]
    
    def to_dict(self):
        """转换为字典"""
        return {
            'defense_id': self.defense_id,
            'name': self.name,
            'defense_type': self.defense_type,
            'description': self.description,
            'enabled': bool(self.enabled),
            'coverage': self.coverage,
            'config': self.config,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
