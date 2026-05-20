# -*- coding: utf-8 -*-
"""
攻击路由 - 攻击管理API，集成动态攻防演练
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import random
import threading
import time
import uuid
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
from agents.attack_agent import get_attack_agent
from agents.defense_agent import get_defense_agent

attacks_bp = Blueprint('attacks', __name__, url_prefix='/api/attack')

# 攻击任务队列
attack_results = {}
attack_lock = threading.Lock()

# 演练会话管理
exercise_sessions = {}
sessions_lock = threading.Lock()


def _execute_dynamic_attack_async(attack_id: str, attack: Attack, session_id: str, target_image: str = ''):
    """异步执行动态攻防演练"""
    try:
        attack.update_status('running')
        Log.create('info', 'attack', f'攻击发起: {attack.name}', user_id=attack.user_id)

        # 获取攻击Agent和防御Agent
        attack_agent = get_attack_agent()
        defense_agent = get_defense_agent()

        # 使用attack_agent执行阶段化攻击（传入target_image以启用综合靶场加成）
        attack_result = attack_agent.execute_attack(
            session_id=session_id,
            attack_type=attack.attack_type,
            intensity=attack.intensity,
            target_image=target_image
        )

        # 获取攻击阶段信息
        attack_phase = attack_result.get('attack_phase', 1)
        attack_success = attack_result.get('status') == 'success'

        # 调用defense_agent进行自适应防御（根据攻击阶段自动升级）
        # port 字段传给 docker_isolate 以精准定位靶场容器
        try:
            attack_port = int(attack.port) if attack.port else 80
        except (ValueError, TypeError):
            attack_port = 80

        defense_result = defense_agent.detect_and_respond(
            session_id=session_id,
            attack_data={
                'attack_type': attack.attack_type,
                'attack_phase': attack_phase,
                'intensity': attack.intensity,
                'source_ip': f'192.168.1.{random.randint(1, 255)}',
                'target': attack.target,
                'port': attack_port,
                'payload': attack_result.get('ai_analysis', '')
            }
        )

        # 记录防御日志到数据库
        defense_level = defense_result.get('defense_level', 1)
        level_name = defense_result.get('level_name', '监控级')
        actions_taken = defense_result.get('actions_taken', [])
        Log.create(
            'info' if defense_level < 3 else 'warning',
            'defense',
            f'防御响应: {attack.attack_type} → 等级{defense_level}({level_name}) | {" | ".join(actions_taken[:2])}',
            user_id=attack.user_id
        )

        # 记录攻击日志
        if attack_success:
            Log.create('success', 'attack', f'攻击成功: {attack.name} (阶段{attack_phase})', user_id=attack.user_id)
        else:
            Log.create('danger', 'attack', f'攻击失败: {attack.name} (阶段{attack_phase})', user_id=attack.user_id)

        # 构建完整攻防结果
        result = {
            'success': attack_success,
            'blocked': defense_level >= 3 and attack_success,
            'attack': {
                'attack_id': attack_id,
                'attack_type': attack.attack_type,
                'attack_phase': attack_phase,
                'phase_name': attack_result.get('phase_name', ''),
                'intensity': attack.intensity,
                'ai_analysis': attack_result.get('ai_analysis', ''),
                'executed_at': attack_result.get('executed_at', '')
            },
            'defense': {
                'defense_level': defense_level,
                'level_name': level_name,
                'actions_taken': actions_taken,
                'blocked_ips': defense_result.get('blocked_ips', []),
                'responded_at': defense_result.get('responded_at', '')
            },
            'session_id': session_id,
            'message': f'攻击阶段{attack_phase}完成，防御等级{defense_level}({level_name})'
        }

        # 更新攻击状态
        if attack_success:
            attack.update_status('completed')
        else:
            attack.update_status('failed')

        with attack_lock:
            attack_results[attack_id] = result

        # 更新会话状态
        with sessions_lock:
            if session_id in exercise_sessions:
                exercise_sessions[session_id]['attacks_count'] = exercise_sessions[session_id].get('attacks_count', 0) + 1
                exercise_sessions[session_id]['current_phase'] = attack_phase
                exercise_sessions[session_id]['defense_level'] = defense_level
                exercise_sessions[session_id]['last_activity'] = datetime.now().isoformat()

    except Exception as e:
        current_app.logger.error(f"动态攻防执行异常: {e}")
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
    """获取攻击记录列表（支持分页）"""
    try:
        user_id = '1'
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        offset = (page - 1) * limit
        attacks = Attack.list_all(user_id, limit, offset)

        for attack in attacks:
            if attack.attack_id in attack_results:
                attack.result = attack_results[attack.attack_id]

        # 获取总数
        total = Attack.count(user_id)

        return jsonify({
            'status': 'success',
            'attacks': [a.to_dict() for a in attacks],
            'total': total,
            'page': page,
            'limit': limit
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
    """执行攻击 - 自动创建演练会话并触发动态防御"""
    try:
        user_id = '1'
        attack = Attack.get_by_id(attack_id)

        if not attack:
            return jsonify({'status': 'error', 'msg': '攻击不存在'}), 404
        if attack.status != 'pending':
            return jsonify({'status': 'error', 'msg': '攻击任务状态不正确'}), 400

        # 从请求体读取靶场镜像（可选，用于综合靶场成功率加成）
        req_data = request.get_json(silent=True) or {}
        target_image = req_data.get('target_image', '')

        # 自动创建演练会话
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        with sessions_lock:
            exercise_sessions[session_id] = {
                'session_id': session_id,
                'attack_id': attack_id,
                'attack_type': attack.attack_type,
                'target': attack.target,
                'target_image': target_image,
                'current_phase': 1,
                'defense_level': 1,
                'attacks_count': 0,
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat()
            }

        Log.create('info', 'system', f'创建演练会话: {session_id}', user_id=user_id)

        # 异步执行动态攻防
        task_id = f"attack_{attack_id}_{int(time.time())}"
        async_queue_service.add_task(
            task_type='attack',
            func=_execute_dynamic_attack_async,
            args=(attack_id, attack, session_id, target_image),
            priority=attack.intensity
        )

        Log.create('info', 'attack', f'动态攻防任务已加入队列: {attack.name}', user_id=user_id)

        return jsonify({
            'status': 'success',
            'task_id': task_id,
            'session_id': session_id,
            'message': '动态攻防已启动，防御已激活'
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@attacks_bp.route('/result/<attack_id>', methods=['GET'])
def get_attack_result(attack_id):
    """获取攻击结果（含防御响应）"""
    try:
        attack = Attack.get_by_id(attack_id)

        if not attack:
            return jsonify({'status': 'error', 'msg': '攻击不存在'}), 404

        result = attack_results.get(attack_id)

        # 查找关联的会话
        session_info = None
        with sessions_lock:
            for sid, sess in exercise_sessions.items():
                if sess.get('attack_id') == attack_id:
                    session_info = sess
                    break

        return jsonify({
            'status': 'success',
            'attack': attack.to_dict(),
            'result': result,
            'session': session_info
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


@attacks_bp.route('/session/<session_id>', methods=['GET'])
def get_session_status(session_id):
    """获取演练会话状态"""
    try:
        with sessions_lock:
            if session_id not in exercise_sessions:
                return jsonify({'status': 'error', 'msg': '会话不存在'}), 404
            session = exercise_sessions[session_id]

        # 获取攻击Agent的会话状态
        attack_agent = get_attack_agent()
        attack_status = attack_agent.get_session_status(session_id)

        # 获取防御Agent的会话状态
        defense_agent = get_defense_agent()
        defense_status = defense_agent.get_status(session_id)

        return jsonify({
            'status': 'success',
            'session': session,
            'attack_status': attack_status,
            'defense_status': defense_status
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@attacks_bp.route('/sessions', methods=['GET'])
def list_sessions():
    """获取所有演练会话"""
    try:
        with sessions_lock:
            sessions_list = []
            for sid, sess in exercise_sessions.items():
                sessions_list.append({
                    'session_id': sid,
                    'attack_type': sess.get('attack_type'),
                    'target': sess.get('target'),
                    'current_phase': sess.get('current_phase', 1),
                    'defense_level': sess.get('defense_level', 1),
                    'attacks_count': sess.get('attacks_count', 0),
                    'status': sess.get('status'),
                    'created_at': sess.get('created_at'),
                    'last_activity': sess.get('last_activity')
                })
            return jsonify({'status': 'success', 'sessions': sessions_list}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500
