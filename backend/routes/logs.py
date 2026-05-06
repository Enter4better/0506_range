# -*- coding: utf-8 -*-
"""
日志路由 - 日志管理API
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.log import Log
from services.database import db_service
from services.watchdog import watchdog_service

logs_bp = Blueprint('logs', __name__, url_prefix='/api/logs')


@logs_bp.route('', methods=['GET'])
@jwt_required()
def list_logs_root():
    """获取日志列表（根路由）"""
    return list_logs()


@logs_bp.route('/list', methods=['GET'])
@jwt_required()
def list_logs():
    """获取日志列表"""
    try:
        # 不传 user_id，获取所有日志（或者传 None）
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        level = request.args.get('level')
        source = request.args.get('source')
        
        # 不传 user_id，获取所有日志
        log_objects = Log.list_all(limit=limit, offset=offset, level=level, source=source)
        
        logs = [log.to_dict() for log in log_objects]
        
        return jsonify({
            'status': 'success',
            'data': logs,
            'logs': logs,
            'total': len(logs)
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取日志列表失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@logs_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_log_stats():
    """获取日志统计"""
    try:
        stats = Log.get_stats()
        return jsonify({'status': 'success', 'stats': stats}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@logs_bp.route('/clear', methods=['POST'])
@jwt_required()
def clear_logs():
    """清理日志"""
    try:
        data = request.get_json()
        older_than_days = data.get('older_than_days')
        
        count = Log.clear_logs(older_than_days)
        
        message = f'清理了 {count} 条 {older_than_days} 天前的日志' if older_than_days else f'清理了所有日志，共 {count} 条'
        current_app.logger.info(message)
        
        return jsonify({'status': 'success', 'message': message, 'cleared_count': count}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


# ==================== Watchdog 监控路由 ====================

@logs_bp.route('/watchdog/status', methods=['GET'])
@jwt_required()
def get_watchdog_status():
    """获取监控服务状态"""
    try:
        monitors = watchdog_service.get_all_monitors()
        alerts = watchdog_service.get_alerts()
        
        return jsonify({
            'status': 'success',
            'watchdog': {
                'running': watchdog_service.running,
                'monitors': monitors,
                'alerts': alerts
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取监控服务状态失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@logs_bp.route('/watchdog/start', methods=['POST'])
@jwt_required()
def start_watchdog():
    """启动监控服务"""
    try:
        watchdog_service.start()
        return jsonify({'status': 'success', 'message': '监控服务已启动'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@logs_bp.route('/watchdog/stop', methods=['POST'])
@jwt_required()
def stop_watchdog():
    """停止监控服务"""
    try:
        watchdog_service.stop()
        return jsonify({'status': 'success', 'message': '监控服务已停止'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@logs_bp.route('/watchdog/clear', methods=['POST'])
@jwt_required()
def clear_watchdog_stats():
    """清空监控统计"""
    try:
        watchdog_service.clear_alerts()
        return jsonify({'status': 'success', 'message': '监控告警已清空'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@logs_bp.route('/attack', methods=['GET'])
@jwt_required()
def get_attack_logs():
    """获取攻击日志"""
    try:
        limit = int(request.args.get('limit', 50))
        logs = Log.get_attack_logs(limit)
        return jsonify({'status': 'success', 'logs': logs, 'total': len(logs)}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@logs_bp.route('/defense', methods=['GET'])
@jwt_required()
def get_defense_logs():
    """获取防御日志"""
    try:
        limit = int(request.args.get('limit', 50))
        logs = Log.get_defense_logs(limit)
        return jsonify({'status': 'success', 'logs': logs, 'total': len(logs)}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@logs_bp.route('/system', methods=['GET'])
@jwt_required()
def get_system_logs():
    """获取系统日志"""
    try:
        limit = int(request.args.get('limit', 50))
        logs = Log.get_system_logs(limit)
        return jsonify({'status': 'success', 'logs': logs, 'total': len(logs)}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@logs_bp.route('/docker', methods=['GET'])
@jwt_required()
def get_docker_logs():
    """获取Docker日志"""
    try:
        limit = int(request.args.get('limit', 50))
        logs = Log.get_docker_logs(limit)
        return jsonify({'status': 'success', 'logs': logs, 'total': len(logs)}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@logs_bp.route('/search', methods=['GET'])
@jwt_required()
def search_logs():
    """搜索日志"""
    try:
        keyword = request.args.get('keyword', '')
        level = request.args.get('level')
        source = request.args.get('source')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 100))
        
        conditions = []
        params = []
        
        if keyword:
            conditions.append("message LIKE ?")
            params.append(f"%{keyword}%")
        
        if level:
            conditions.append("level = ?")
            params.append(level)
        
        if source:
            conditions.append("source = ?")
            params.append(source)
        
        if start_date:
            conditions.append("created_at >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("created_at <= ?")
            params.append(end_date)
        
        sql = "SELECT * FROM logs WHERE 1=1"
        if conditions:
            sql += " AND " + " AND ".join(conditions)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        connection = db_service.get_connection()
        cursor = connection.cursor()
        cursor.execute(sql, params)
        results = cursor.fetchall()
        
        columns = [description[0] for description in cursor.description]
        logs = [dict(zip(columns, row)) for row in results]
        
        connection.close()
        
        return jsonify({'status': 'success', 'logs': logs, 'total': len(logs), 'keyword': keyword}), 200
    except Exception as e:
        current_app.logger.error(f"搜索日志失败: {e}")
        return jsonify({'status': 'error', 'msg': '搜索日志失败'}), 500


@logs_bp.route('/export', methods=['GET'])
@jwt_required()
def export_logs():
    """导出日志"""
    try:
        format_type = request.args.get('format', 'json')
        
        connection = db_service.get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM logs ORDER BY created_at DESC")
        results = cursor.fetchall()
        
        columns = [description[0] for description in cursor.description]
        logs = [dict(zip(columns, row)) for row in results]
        connection.close()
        
        if format_type == 'csv':
            import csv
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            writer.writerows(logs)
            return output.getvalue(), 200, {'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename=logs_export.csv'}
        else:
            return jsonify({'status': 'success', 'logs': logs, 'total': len(logs)}), 200
    except Exception as e:
        current_app.logger.error(f"导出日志失败: {e}")
        return jsonify({'status': 'error', 'msg': '导出日志失败'}), 500