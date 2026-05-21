# -*- coding: utf-8 -*-
"""
防御警报模型 - 存储LLM生成的结构化防御建议
"""
import json
import sqlite3
from datetime import datetime
import logging
import sys
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.database import db_service

logger = logging.getLogger('models.defense_alert')


class DefenseAlert:
    """防御警报模型类 - 存储LLM生成的结构化防御建议"""

    def __init__(self, alert_id=None, session_id=None, attack_type=None, attack_phase=1,
                 defense_level=1, intercept_rate=0, mitre_tactic=None, mitre_technique=None,
                 impact_assessment=None, recommendations=None, rule_suggestions=None,
                 raw_llm_response=None, created_at=None):
        self.alert_id = alert_id
        self.session_id = session_id
        self.attack_type = attack_type
        self.attack_phase = attack_phase
        self.defense_level = defense_level
        self.intercept_rate = intercept_rate
        self.mitre_tactic = mitre_tactic
        self.mitre_technique = mitre_technique
        self.impact_assessment = impact_assessment
        self.recommendations = recommendations if recommendations else []
        self.rule_suggestions = rule_suggestions if rule_suggestions else []
        self.raw_llm_response = raw_llm_response
        self.created_at = created_at

    def save(self):
        """保存防御警报到数据库"""
        try:
            conn = db_service.get_connection()
            if not conn:
                return False

            cursor = conn.cursor()

            # 将列表序列化为JSON字符串
            recommendations_json = json.dumps(self.recommendations, ensure_ascii=False) if isinstance(self.recommendations, list) else self.recommendations
            rule_suggestions_json = json.dumps(self.rule_suggestions, ensure_ascii=False) if isinstance(self.rule_suggestions, list) else self.rule_suggestions

            if self.alert_id:
                # 更新
                cursor.execute("""
                    UPDATE defense_alerts SET
                        session_id=?, attack_type=?, attack_phase=?, defense_level=?,
                        intercept_rate=?, mitre_tactic=?, mitre_technique=?,
                        impact_assessment=?, recommendations=?, rule_suggestions=?,
                        raw_llm_response=?
                    WHERE alert_id=?
                """, (self.session_id, self.attack_type, self.attack_phase, self.defense_level,
                      self.intercept_rate, self.mitre_tactic, self.mitre_technique,
                      self.impact_assessment, recommendations_json, rule_suggestions_json,
                      self.raw_llm_response, self.alert_id))
            else:
                # 新增
                cursor.execute("""
                    INSERT INTO defense_alerts
                    (session_id, attack_type, attack_phase, defense_level, intercept_rate,
                     mitre_tactic, mitre_technique, impact_assessment, recommendations,
                     rule_suggestions, raw_llm_response, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (self.session_id, self.attack_type, self.attack_phase, self.defense_level,
                      self.intercept_rate, self.mitre_tactic, self.mitre_technique,
                      self.impact_assessment, recommendations_json, rule_suggestions_json,
                      self.raw_llm_response, datetime.now().isoformat()))
                self.alert_id = cursor.lastrowid

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"保存防御警报失败: {e}")
            return False

    @staticmethod
    def get_by_id(alert_id):
        """根据ID获取警报"""
        try:
            conn = db_service.get_connection()
            if not conn:
                return None

            cursor = conn.cursor()
            cursor.execute("SELECT * FROM defense_alerts WHERE alert_id=?", (alert_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                return DefenseAlert._from_row(row)
        except Exception as e:
            logger.error(f"获取警报失败: {e}")
        return None

    @staticmethod
    def get_by_session(session_id, limit=50):
        """获取特定会话的所有警报"""
        try:
            conn = db_service.get_connection()
            if not conn:
                return []

            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM defense_alerts WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit)
            )
            rows = cursor.fetchall()
            conn.close()

            return [DefenseAlert._from_row(row) for row in rows]
        except Exception as e:
            logger.error(f"获取会话警报失败: {e}")
            return []

    @staticmethod
    def list_all(limit=100, offset=0):
        """获取所有警报（分页）"""
        try:
            conn = db_service.get_connection()
            if not conn:
                return [], 0

            cursor = conn.cursor()

            # 获取总数
            cursor.execute("SELECT COUNT(*) FROM defense_alerts")
            total = cursor.fetchone()[0]

            # 获取列表
            cursor.execute(
                "SELECT * FROM defense_alerts ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            rows = cursor.fetchall()
            conn.close()

            return [DefenseAlert._from_row(row) for row in rows], total
        except Exception as e:
            logger.error(f"获取警报列表失败: {e}")
            return [], 0

    @staticmethod
    def get_recent(limit=20):
        """获取最近的警报"""
        try:
            conn = db_service.get_connection()
            if not conn:
                return []

            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM defense_alerts ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()

            return [DefenseAlert._from_row(row) for row in rows]
        except Exception as e:
            logger.error(f"获取最近警报失败: {e}")
            return []

    @staticmethod
    def _from_row(row):
        """从数据库行创建对象"""
        # 解析JSON字段
        recommendations = []
        rule_suggestions = []

        try:
            if row['recommendations']:
                recommendations = json.loads(row['recommendations'])
        except:
            pass

        try:
            if row['rule_suggestions']:
                rule_suggestions = json.loads(row['rule_suggestions'])
        except:
            pass

        return DefenseAlert(
            alert_id=row['alert_id'],
            session_id=row['session_id'],
            attack_type=row['attack_type'],
            attack_phase=row['attack_phase'],
            defense_level=row['defense_level'],
            intercept_rate=row['intercept_rate'],
            mitre_tactic=row['mitre_tactic'],
            mitre_technique=row['mitre_technique'],
            impact_assessment=row['impact_assessment'],
            recommendations=recommendations,
            rule_suggestions=rule_suggestions,
            raw_llm_response=row['raw_llm_response'],
            created_at=row['created_at']
        )

    def to_dict(self):
        """转换为字典"""
        return {
            'alert_id': self.alert_id,
            'session_id': self.session_id,
            'attack_type': self.attack_type,
            'attack_phase': self.attack_phase,
            'defense_level': self.defense_level,
            'intercept_rate': self.intercept_rate,
            'mitre_tactic': self.mitre_tactic,
            'mitre_technique': self.mitre_technique,
            'impact_assessment': self.impact_assessment,
            'recommendations': self.recommendations if isinstance(self.recommendations, list) else [],
            'rule_suggestions': self.rule_suggestions if isinstance(self.rule_suggestions, list) else [],
            'raw_llm_response': self.raw_llm_response,
            'created_at': self.created_at
        }
