# -*- coding: utf-8 -*-
"""
攻击路由 - 攻击管理API
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import random
import threading
import time
from datetime import datetime
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.attack import Attack
from models.defense import Defense
from models.log import Log
from services.database import db_service
from services.async_queue import async_queue_service

attacks_bp = Blueprint('attacks', __name__, url_prefix='/api/attack')

# 攻击任务队列
attack_results = {}
attack_lock = threading.Lock()


def _trigger_defense_response(attack: Attack, user_id: str):
    """触发防御响应"""
    try:
        defenses = Defense.list_all()
        active_defenses = [d for d in defenses if d.enabled]
        
        defense_responses = []
        for defense in active_defenses:
            check_result = defense.check_attack(attack.attack_type, attack.intensity)
            defense_responses.append({
                'defense_id': defense.defense_id,
                'defense_name': defense.name,
                'blocked': check_result['blocked'],
                'message': check_result['message']
            })
            if check_result['blocked']:
                Log.create('success', 'defense', 
                          f'防御触发: {defense.name} 拦截了 {attack.attack_type} 攻击', 
                          user_id=user_id)
        return defense_responses
    except Exception as e:
        current_app.logger.error(f"触发防御响应失败: {e}")
        return []


def _execute_attack_async(attack_id: str, attack: Attack):
    """异步执行攻击"""
    try:
        attack.update_status('running')
        Log.create('info', 'attack', f'攻击发起: {attack.name}', user_id=attack.user_id)
        
        defense_responses = _trigger_defense_response(attack, attack.user_id)
        blocked_by = [d for d in defense_responses if d['blocked']]
        
        time.sleep(random.uniform(0.5, 2.0) * (attack.intensity / 5))
        
        if blocked_by:
            result = {
                'success': False,
                'blocked': True,
                'blocked_by': blocked_by,
                'message': f'攻击被 {len(blocked_by)} 个防御规则拦截',
                'defense_responses': defense_responses
            }
            attack.update_status('blocked')
            Log.create('warning', 'attack', f'攻击被拦截: {attack.name}', user_id=attack.user_id)
        else:
            result = attack.execute()
            result['blocked'] = False
            result['defense_responses'] = defense_responses
            if result['success']:
                Log.create('success', 'attack', f'攻击成功: {attack.name}', user_id=attack.user_id)
            else:
                Log.create('danger', 'attack', f'攻击失败: {attack.name}', user_id=attack.user_id)
        
        with attack_lock:
            attack_results[attack_id] = result
    except Exception as e:
        Log.create('danger', 'attack', f'攻击执行异常: {attack.name} - {str(e)}', user_id=attack.user_id)
        with attack_lock:
            attack_results[attack_id] = {'success': False, 'blocked': False, 'message': str(e)}


@attacks_bp.route('/types', methods=['GET'])
def get_attack_types():
    """获取攻击类型列表"""
    try:
        attack_types = Attack.get_attack_types()
        return jsonify({'status': 'success', 'types': attack_types}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@attacks_bp.route('/list', methods=['GET'])
def list_attacks():
    """获取攻击记录列表"""
    try:
        user_id = '1'
        limit = int(request.args.get('limit', 50))
        attacks = Attack.list_all(user_id, limit)
        
        for attack in attacks:
            if attack.attack_id in attack_results:
                attack.result = attack_results[attack.attack_id]
        
        return jsonify({
            'status': 'success',
            'attacks': [a.to_dict() for a in attacks]
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@attacks_bp.route('/create', methods=['POST'])
def create_attack():
    try:
        user_id = '1'
        data = request.get_json()
        
        required_fields = ['name', 'attack_type', 'target', 'port', 'intensity']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'status': 'error', 'msg': f'{field} 是必填项'}), 400
        
        name = data['name']
        attack_type = data['attack_type']
        target = data['target']
        port = data['port']
        intensity = int(data['intensity'])
        
        if intensity < 1 or intensity > 10:
            return jsonify({'status': 'error', 'msg': '攻击强度必须在1-10之间'}), 400
        
        # 只传5个参数，不要传 config
        attack = Attack.create(name, attack_type, target, port, intensity, user_id)
        if not attack:
            return jsonify({'status': 'error', 'msg': '创建攻击失败'}), 500
        
        Log.create('info', 'attack', f'创建攻击任务: {name}', user_id=user_id)
        
        return jsonify({'status': 'success', 'attack': attack.to_dict()}), 201
    except Exception as e:
        current_app.logger.error(f"创建攻击失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@attacks_bp.route('/execute/<attack_id>', methods=['POST'])
def execute_attack(attack_id):
    """执行攻击"""
    try:
        user_id = '1'
        attack = Attack.get_by_id(attack_id)
        
        if not attack:
            return jsonify({'status': 'error', 'msg': '攻击不存在'}), 404
        if attack.status != 'pending':
            return jsonify({'status': 'error', 'msg': '攻击任务状态不正确'}), 400
        
        task_id = f"attack_{attack_id}_{int(time.time())}"
        async_queue_service.add_task(
            task_type='attack',
            func=_execute_attack_async,
            args=(attack_id, attack),
            priority=attack.intensity
        )
        
        Log.create('info', 'attack', f'攻击任务已加入队列: {attack.name}', user_id=user_id)
        
        return jsonify({
            'status': 'success',
            'task_id': task_id,
            'message': '攻击任务已加入队列'
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@attacks_bp.route('/result/<attack_id>', methods=['GET'])
def get_attack_result(attack_id):
    """获取攻击结果"""
    try:
        attack = Attack.get_by_id(attack_id)
        
        if not attack:
            return jsonify({'status': 'error', 'msg': '攻击不存在'}), 404
        
        result = attack_results.get(attack_id)
        return jsonify({
            'status': 'success',
            'attack': attack.to_dict(),
            'result': result
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@attacks_bp.route('/stats', methods=['GET'])
def get_attack_stats():
    """获取攻击统计"""
    try:
        user_id = '1'
        stats = Attack.get_stats()
        user_attacks = Attack.list_all(user_id, 1000)
        
        user_stats = {
            'total': len(user_attacks),
            'success': len([a for a in user_attacks if a.status == 'completed']),
            'failed': len([a for a in user_attacks if a.status == 'failed']),
            'running': len([a for a in user_attacks if a.status == 'running'])
        }
        
        return jsonify({
            'status': 'success',
            'stats': stats,
            'user_stats': user_stats
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500
