# -*- coding: utf-8 -*-
"""
统计路由 - 统计数据API (SQLite版本)
"""
from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import sys
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import DB_CONFIG
from services.database import db_service
from models.log import Log
from models.attack import Attack
from models.defense import Defense
from models.target import Target

stats_bp = Blueprint('stats', __name__, url_prefix='/api')


@stats_bp.route('/stats', methods=['GET'])
def get_stats():
    """获取系统统计数据"""
    try:
        stats = {
            'environments': 0,
            'attacks': 0,
            'defenses': 0,
            'logs': 0,
            'health': 0,
            'alerts': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        # 获取环境数量
        try:
            targets = Target.list_all()
            stats['environments'] = len(targets) if targets else 0
        except Exception as e:
            current_app.logger.error(f"Error listing targets: {e}")
        
        # 获取攻击数量
        try:
            attacks = Attack.list_all()
            stats['attacks'] = len(attacks) if attacks else 0
        except Exception as e:
            current_app.logger.error(f"Error listing attacks: {e}")
        
        # 获取防御数量
        try:
            defenses = Defense.list_all()
            stats['defenses'] = len(defenses) if defenses else 0
        except Exception as e:
            current_app.logger.error(f"Error listing defenses: {e}")
        
        # 获取日志数量
        try:
            log_stats = Log.get_stats()
            stats['logs'] = log_stats.get('total', 0)
        except Exception as e:
            current_app.logger.error(f"Error getting log count: {e}")
        
        # 获取告警数量
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM logs WHERE level = 'warning' OR level = 'danger'")
                result = cursor.fetchone()
                stats['alerts'] = result[0] if result else 0
                conn.close()
        except Exception as e:
            current_app.logger.error(f"Error getting alerts count: {e}")
        
        # 计算健康度
        if stats['alerts'] > 10:
            stats['health'] = 60
        elif stats['alerts'] > 5:
            stats['health'] = 75
        elif stats['alerts'] > 0:
            stats['health'] = 85
        else:
            stats['health'] = 95
        
        return jsonify({
            'status': 'success',
            **stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取统计数据失败: {e}")
        return jsonify({
            'status': 'error',
            'msg': '获取统计数据失败，请检查数据库连接'
        }), 500


@stats_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """获取仪表盘数据"""
    try:
        # 获取统计数据
        stats_data = {
            'environments': 0,
            'attacks': 0,
            'defenses': 0,
            'logs': 0,
            'health': 0,
            'alerts': 0
        }
        
        # 获取最近日志
        recent_logs = []
        try:
            logs = Log.list_all(limit=10)
            for log in logs:
                recent_logs.append({
                    'id': log.log_id,
                    'level': log.level,
                    'source': log.source,
                    'message': log.message,
                    'time': log.created_at
                })
        except Exception as e:
            current_app.logger.error(f"Error getting recent logs: {e}")
        
        # 获取活跃攻击
        active_attacks = []
        try:
            attacks = Attack.list_all()
            if attacks:
                active_attacks = [a.to_dict() for a in attacks if a.status == 'running'][:5]
        except Exception as e:
            current_app.logger.error(f"Error getting active attacks: {e}")
        
        # 获取防御状态
        defense_status = []
        try:
            defenses = Defense.list_all()
            if defenses:
                defense_status = [d.to_dict() for d in defenses if d.enabled][:5]
        except Exception as e:
            current_app.logger.error(f"Error getting defense status: {e}")
        
        return jsonify({
            'status': 'success',
            'stats': stats_data,
            'recent_logs': recent_logs,
            'active_attacks': active_attacks,
            'defense_status': defense_status,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取仪表盘数据失败: {e}")
        return jsonify({
            'status': 'error',
            'msg': '获取仪表盘数据失败'
        }), 500


@stats_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        # 检查数据库连接
        db_connected = db_service.test_connection()
        
        status = 'ok' if db_connected else 'error'
        
        return jsonify({
            'status': status,
            'database': 'connected' if db_connected else 'disconnected',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'msg': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@stats_bp.route('/stats/overview', methods=['GET'])
def get_stats_overview():
    """获取统计概览数据（用于Dashboard）"""
    try:
        # 获取基础统计数据
        stats = {
            'environments': 0,
            'attacks': 0,
            'today_attacks': 0,
            'today_alerts': 0,
            'defenses': 0,
            'logs': 0,
            'health': 0,
            'alerts': 0
        }
        
        # 尝试从数据库获取真实数据
        try:
            targets = Target.list_all()
            stats['environments'] = len(targets) if targets else 0
        except Exception as e:
            current_app.logger.error(f"Error listing targets: {e}")
        
        try:
            attacks = Attack.list_all()
            stats['attacks'] = len(attacks) if attacks else 0
        except Exception as e:
            current_app.logger.error(f"Error listing attacks: {e}")

        # 今日攻击统计
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM attacks WHERE DATE(created_at) = ?",
                    (today,)
                )
                result = cursor.fetchone()
                stats['today_attacks'] = result[0] if result else 0

                cursor.execute(
                    "SELECT COUNT(*) FROM attacks WHERE DATE(created_at) = ? AND status = 'blocked'",
                    (today,)
                )
                result = cursor.fetchone()
                stats['today_alerts'] = result[0] if result else 0
                conn.close()
        except Exception as e:
            current_app.logger.error(f"Error getting today attack stats: {e}")

        try:
            defenses = Defense.list_all()
            stats['defenses'] = len(defenses) if defenses else 0
        except Exception as e:
            current_app.logger.error(f"Error listing defenses: {e}")
        
        try:
            log_stats = Log.get_stats()
            stats['logs'] = log_stats.get('total', 0)
        except Exception as e:
            current_app.logger.error(f"Error getting log stats: {e}")
        
        # 计算健康度
        try:
            attack_stats = Attack.get_stats()
            defense_stats = Defense.get_stats()
            
            # 基于攻击成功率和防御覆盖率计算健康度
            total_attacks = attack_stats.get('total', 0)
            if total_attacks > 0:
                attack_success_rate = attack_stats.get('success', 0) / total_attacks
            else:
                attack_success_rate = 0
            
            defense_coverage = defense_stats.get('avg_coverage', 0)
            
            health = int(100 - (attack_success_rate * 30) + (defense_coverage * 0.5))
            stats['health'] = max(60, min(95, health))
        except Exception as e:
            current_app.logger.error(f"Error calculating health: {e}")
            stats['health'] = 95
        
        # 获取攻击类型分布
        attack_distribution = []
        try:
            attack_stats = Attack.get_stats()
            type_counts = attack_stats.get('type_counts', {})
            for attack_type, count in type_counts.items():
                attack_distribution.append({
                    'name': attack_type,
                    'value': count
                })
        except Exception as e:
            current_app.logger.error(f"Error getting attack stats: {e}")
        
        # 获取防御覆盖率分布
        defense_distribution = []
        try:
            defenses = Defense.list_all()
            for d in defenses:
                defense_distribution.append({
                    'name': d.name,
                    'value': d.coverage
                })
        except Exception as e:
            current_app.logger.error(f"Error listing defenses: {e}")
        
        # 获取最近7天的攻击趋势
        attack_trend = []
        try:
            conn = db_service.get_connection()
            if conn:
                cursor = conn.cursor()
                for i in range(7):
                    date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                    # SQLite使用DATE函数和?参数
                    cursor.execute(
                        "SELECT COUNT(*) FROM attacks WHERE DATE(created_at) = ?",
                        (date,)
                    )
                    result = cursor.fetchone()
                    attack_count = result[0] if result else 0
                    
                    cursor.execute(
                        "SELECT COUNT(*) FROM attacks WHERE DATE(created_at) = ? AND status = 'blocked'",
                        (date,)
                    )
                    result = cursor.fetchone()
                    blocked_count = result[0] if result else 0
                    
                    attack_trend.append({
                        'date': date,
                        'attacks': attack_count,
                        'blocked': blocked_count
                    })
                conn.close()
        except Exception as e:
            current_app.logger.error(f"Error getting attack trend: {e}")
        
        return jsonify({
            'status': 'success',
            'stats': stats,
            'attack_distribution': attack_distribution,
            'defense_distribution': defense_distribution,
            'attack_trend': attack_trend,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取统计概览失败: {e}")
        return jsonify({
            'status': 'error',
            'msg': str(e)
        }), 500