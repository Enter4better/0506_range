# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.defense import Defense
from models.log import Log

defenses_bp = Blueprint('defenses', __name__, url_prefix='/api/defense')
defenses_alt_bp = Blueprint('defenses_alt', __name__, url_prefix='/api/defenses')


@defenses_bp.route('/list', methods=['GET'])
@jwt_required()
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
@jwt_required()
def list_defenses_alt():
    """获取防御规则列表（备用路由）"""
    return list_defenses()


@defenses_bp.route('/stats', methods=['GET'])
@jwt_required()
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
@jwt_required()
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
@jwt_required()
def alt_list_defenses():
    """兼容前端的防御列表"""
    return list_defenses()


@defenses_bp.route('/create', methods=['POST'])
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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