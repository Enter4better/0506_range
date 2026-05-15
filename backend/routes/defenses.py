# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.defense import Defense
from models.defense_alert import DefenseAlert
from models.log import Log

defenses_bp = Blueprint('defenses', __name__, url_prefix='/api/defense')
defenses_alt_bp = Blueprint('defenses_alt', __name__, url_prefix='/api/defenses')


@defenses_bp.route('/list', methods=['GET'])
def list_defenses():
    """获取防御规则列表"""
    try:
        # 不传 user_id，获取所有防御规则
        defenses = Defense.list_all()
        
        # 转换为字典列表
        defense_list = []
        for d in defenses:
            defense_list.append({
                'defense_id': d.defense_id,
                'name': d.name,
                'defense_type': d.defense_type,
                'description': d.description,
                'enabled': bool(d.enabled),
                'coverage': d.coverage,
                'created_at': d.created_at,
                'updated_at': d.updated_at
            })
        
        return jsonify({
            'status': 'success',
            'defenses': defense_list,
            'data': defense_list
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取防御列表失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@defenses_bp.route('', methods=['GET'])
def list_defenses_alt():
    """获取防御规则列表（备用路由）"""
    return list_defenses()


@defenses_bp.route('/stats', methods=['GET'])
def get_defense_stats():
    """获取防御统计"""
    try:
        stats = Defense.get_stats()
        return jsonify({
            'status': 'success',
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@defenses_bp.route('/types', methods=['GET'])
def get_defense_types():
    """获取防御类型"""
    try:
        defense_types = Defense.get_defense_types()
        return jsonify({
            'status': 'success',
            'types': defense_types
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@defenses_alt_bp.route('', methods=['GET'])
def alt_list_defenses():
    """兼容前端的防御列表"""
    return list_defenses()


@defenses_bp.route('/create', methods=['POST'])
def create_defense():
    """创建新防御规则"""
    try:
        data = request.get_json()
        
        required_fields = ['name', 'defense_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'status': 'error', 'msg': f'{field} 是必填项'}), 400
        
        name = data['name']
        defense_type = data['defense_type']
        description = data.get('description', '')
        enabled = data.get('enabled', True)
        coverage = float(data.get('coverage', 0.0))
        
        if coverage < 0 or coverage > 100:
            return jsonify({'status': 'error', 'msg': '覆盖率必须在0-100之间'}), 400
        
        defense = Defense.create(name, defense_type, description, enabled, coverage)
        if not defense:
            return jsonify({'status': 'error', 'msg': '创建防御规则失败'}), 500
        
        Log.create('success', 'defense', f'创建防御规则: {name}')
        
        return jsonify({
            'status': 'success',
            'defense': defense.to_dict()
        }), 201
    except Exception as e:
        current_app.logger.error(f"创建防御规则失败: {e}")
        return jsonify({'status': 'error', 'msg': '创建防御规则失败'}), 500


@defenses_bp.route('/update/<defense_id>', methods=['PUT'])
def update_defense(defense_id):
    """更新防御规则"""
    try:
        defense = Defense.get_by_id(defense_id)
        
        if not defense:
            return jsonify({'status': 'error', 'msg': '防御规则不存在'}), 404
        
        data = request.get_json()
        
        success = defense.update(
            name=data.get('name'),
            defense_type=data.get('defense_type'),
            description=data.get('description'),
            enabled=data.get('enabled'),
            coverage=data.get('coverage')
        )
        
        if not success:
            return jsonify({'status': 'error', 'msg': '更新防御规则失败'}), 500
        
        Log.create('info', 'defense', f'更新防御规则: {defense.name}')
        
        return jsonify({
            'status': 'success',
            'defense': defense.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.error(f"更新防御规则失败: {e}")
        return jsonify({'status': 'error', 'msg': '更新防御规则失败'}), 500


@defenses_bp.route('/toggle/<defense_id>', methods=['POST'])
def toggle_defense(defense_id):
    """切换防御规则状态"""
    try:
        defense = Defense.get_by_id(defense_id)
        
        if not defense:
            return jsonify({'status': 'error', 'msg': '防御规则不存在'}), 404
        
        success = defense.toggle()
        
        if not success:
            return jsonify({'status': 'error', 'msg': '切换防御规则状态失败'}), 500
        
        status = '启用' if defense.enabled else '禁用'
        Log.create('info', 'defense', f'{status}防御规则: {defense.name}')
        
        return jsonify({
            'status': 'success',
            'defense': defense.to_dict(),
            'message': f'防御规则已{status}'
        }), 200
    except Exception as e:
        current_app.logger.error(f"切换防御规则状态失败: {e}")
        return jsonify({'status': 'error', 'msg': '切换防御规则状态失败'}), 500


@defenses_bp.route('/delete/<defense_id>', methods=['DELETE'])
def delete_defense(defense_id):
    """删除防御规则"""
    try:
        defense = Defense.get_by_id(defense_id)
        
        if not defense:
            return jsonify({'status': 'error', 'msg': '防御规则不存在'}), 404
        
        success = defense.delete()
        
        if not success:
            return jsonify({'status': 'error', 'msg': '删除防御规则失败'}), 500
        
        Log.create('info', 'defense', f'删除防御规则: {defense.name}')
        
        return jsonify({
            'status': 'success',
            'message': '防御规则已删除'
        }), 200
    except Exception as e:
        current_app.logger.error(f"删除防御规则失败: {e}")
        return jsonify({'status': 'error', 'msg': '删除防御规则失败'}), 500


@defenses_bp.route('/check', methods=['POST'])
def check_defense():
    """检查防御规则"""
    try:
        data = request.get_json()

        required_fields = ['defense_id', 'attack_type', 'intensity']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'status': 'error', 'msg': f'{field} 是必填项'}), 400

        defense_id = data['defense_id']
        attack_type = data['attack_type']
        intensity = int(data['intensity'])

        if intensity < 1 or intensity > 10:
            return jsonify({'status': 'error', 'msg': '攻击强度必须在1-10之间'}), 400

        defense = Defense.get_by_id(defense_id)

        if not defense:
            return jsonify({'status': 'error', 'msg': '防御规则不存在'}), 404

        result = defense.check_attack(attack_type, intensity)

        Log.create('info', 'defense', f'防御检查: {defense.name} - {attack_type}')

        return jsonify({
            'status': 'success',
            'result': result
        }), 200
    except Exception as e:
        current_app.logger.error(f"检查防御规则失败: {e}")
        return jsonify({'status': 'error', 'msg': '检查防御规则失败'}), 500


# ==================== 防御警报 API（LLM生成的结构化建议） ====================

@defenses_bp.route('/alerts', methods=['GET'])
def list_defense_alerts():
    """获取防御警报列表"""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        alerts, total = DefenseAlert.list_all(limit=limit, offset=offset)

        return jsonify({
            'status': 'success',
            'alerts': [alert.to_dict() for alert in alerts],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取防御警报失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@defenses_bp.route('/alerts/recent', methods=['GET'])
def recent_defense_alerts():
    """获取最近的防御警报"""
    try:
        limit = int(request.args.get('limit', 20))
        alerts = DefenseAlert.get_recent(limit=limit)

        return jsonify({
            'status': 'success',
            'alerts': [alert.to_dict() for alert in alerts]
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取最近警报失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@defenses_bp.route('/alerts/<session_id>', methods=['GET'])
def get_session_alerts(session_id):
    """获取特定会话的防御警报"""
    try:
        limit = int(request.args.get('limit', 50))
        alerts = DefenseAlert.get_by_session(session_id, limit=limit)

        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'alerts': [alert.to_dict() for alert in alerts],
            'count': len(alerts)
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取会话警报失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@defenses_bp.route('/alerts/<int:alert_id>', methods=['GET'])
def get_alert_by_id(alert_id):
    """根据ID获取单条警报"""
    try:
        alert = DefenseAlert.get_by_id(alert_id)

        if not alert:
            return jsonify({'status': 'error', 'msg': '警报不存在'}), 404

        return jsonify({
            'status': 'success',
            'alert': alert.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取警报详情失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500
