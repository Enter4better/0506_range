# -*- coding: utf-8 -*-
"""
Agent API路由 - 集成环境管理、攻击模拟、防御模拟三个AI Agent
"""
import os
import json
import sys
from pathlib import Path
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents import get_orchestrator
from agents.env_agent import get_env_agent
from agents.attack_agent import get_attack_agent
from agents.defense_agent import get_defense_agent
from models.log import Log

agents_bp = Blueprint('agents', __name__, url_prefix='/api/agents')


# ==================== 原有 Agent API ====================

@agents_bp.route('/env/scenarios', methods=['GET'])
@jwt_required()
def list_env_scenarios():
    try:
        user_id = get_jwt_identity()
        agent = get_env_agent(user_id)
        scenarios = agent.list_available_scenarios()
        return jsonify({'status': 'success', 'scenarios': scenarios}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@agents_bp.route('/env/analyze', methods=['POST'])
@jwt_required()
def analyze_env_scenario():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        scenario_desc = data.get('scenario_desc', '')
        if not scenario_desc:
            return jsonify({'status': 'error', 'msg': '请提供场景描述'}), 400
        agent = get_env_agent(user_id)
        config = agent.analyze_scenario(scenario_desc)
        return jsonify({'status': 'success', 'config': config}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@agents_bp.route('/env/create', methods=['POST'])
@jwt_required()
def create_env_environment():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        if 'scenario_desc' in data and 'config' not in data:
            agent = get_env_agent(user_id)
            config = agent.analyze_scenario(data['scenario_desc'])
        else:
            config = data.get('config', {})
        if not config:
            return jsonify({'status': 'error', 'msg': '请提供环境配置或场景描述'}), 400
        agent = get_env_agent(user_id)
        result = agent.create_environment(config, user_id)
        return jsonify({'status': 'success', 'result': result}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


# ==================== 攻击规划 API ====================

@agents_bp.route('/attack/plan', methods=['POST'])
def plan_attack():
    """AI攻击规划"""
    try:
        data = request.get_json()
        target = data.get('target', '')
        attack_type = data.get('attack_type', '')
        objective = data.get('objective', None)
        
        if not target:
            return jsonify({'status': 'error', 'msg': '请提供目标'}), 400
        
        agent = get_attack_agent()
        
        session_id = data.get('session_id')
        if session_id:
            session_status = agent.get_session_status(session_id)
            current_phase = session_status.get('current_phase', 1)
            phase_name = agent.ATTACK_PHASES[current_phase]['name']
            
            plan = {
                'target': target,
                'attack_type': attack_type or '自动选择',
                'current_phase': current_phase,
                'phase_name': phase_name,
                'recommended_attacks': agent.get_phase_attacks(current_phase),
                'estimated_success_rate': 0.6,
                'message': f'当前处于{phase_name}阶段，推荐使用针对性攻击'
            }
        else:
            plan = {
                'target': target,
                'attack_type': attack_type or '端口扫描',
                'steps': ['信息收集', '漏洞扫描', '漏洞利用'],
                'tools': ['nmap', 'sqlmap'],
                'estimated_success_rate': 0.6
            }
        
        return jsonify({'status': 'success', 'plan': plan}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


# ==================== 攻击阶段 API ====================

@agents_bp.route('/attack/phases', methods=['GET'])
def get_attack_phases():
    """获取攻击阶段定义"""
    try:
        agent = get_attack_agent()
        phases = agent.get_attack_phases()
        return jsonify({'status': 'success', 'phases': phases}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@agents_bp.route('/session/<session_id>/attack/execute', methods=['POST'])
def execute_session_attack(session_id):
    """执行攻击（带阶段管理）"""
    try:
        data = request.get_json()
        attack_type = data.get('attack_type')
        intensity = data.get('intensity', 5)
        
        agent = get_attack_agent()
        result = agent.execute_attack(session_id, attack_type, intensity)
        
        return jsonify({'status': 'success', 'result': result}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@agents_bp.route('/session/<session_id>/attack/status', methods=['GET'])
def get_session_attack_status(session_id):
    """获取会话攻击状态"""
    try:
        agent = get_attack_agent()
        status = agent.get_session_status(session_id)
        return jsonify({'status': 'success', 'data': status}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


# ==================== 防御 API ====================

@agents_bp.route('/defense/status', methods=['GET'])
def get_defense_status():
    """获取防御状态"""
    try:
        session_id = request.args.get('session_id')
        agent = get_defense_agent()
        status = agent.get_status(session_id)
        return jsonify({'status': 'success', 'data': status}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@agents_bp.route('/defense/logs', methods=['GET'])
def get_defense_logs():
    """获取防御日志"""
    try:
        agent = get_defense_agent()
        limit = int(request.args.get('limit', 30))
        logs = agent.get_defense_logs(limit)
        return jsonify({'status': 'success', 'logs': logs}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


# ==================== 编排器 API ====================

@agents_bp.route('/scenario', methods=['POST'])
def create_scenario():
    """创建演练场景"""
    try:
        data = request.get_json()
        description = data.get('description', '')
        if not description:
            return jsonify({'status': 'error', 'message': '请提供场景描述'}), 400
        orchestrator = get_orchestrator()
        result = orchestrator.create_scenario(description)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@agents_bp.route('/<session_id>/status', methods=['GET'])
def get_session_status(session_id):
    """获取会话状态"""
    try:
        orchestrator = get_orchestrator()
        result = orchestrator.get_status(session_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@agents_bp.route('/<session_id>/attack', methods=['POST'])
def execute_session_attack_legacy(session_id):
    """执行攻击（兼容旧接口）"""
    try:
        data = request.get_json()
        attack_type = data.get('attack_type')
        intensity = data.get('intensity', 5)
        orchestrator = get_orchestrator()
        result = orchestrator.execute_attack(session_id, attack_type, intensity)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@agents_bp.route('/<session_id>', methods=['DELETE'])
def destroy_session(session_id):
    """销毁会话"""
    try:
        orchestrator = get_orchestrator()
        result = orchestrator.cleanup(session_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@agents_bp.route('/sessions', methods=['GET'])
def list_sessions():
    """获取所有会话"""
    try:
        orchestrator = get_orchestrator()
        sessions = []
        for sid, sess in orchestrator.sessions.items():
            sessions.append({
                'session_id': sid,
                'environment': sess.get('environment', {}),
                'status': sess.get('status', 'active'),
                'created_at': sess.get('created_at')
            })
        return jsonify({'status': 'success', 'sessions': sessions})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@agents_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task_result(task_id):
    """获取异步任务结果"""
    try:
        from services.async_queue import async_queue_service
        result = async_queue_service.get_result(task_id)
        if result is None:
            return jsonify({'status': 'pending'})
        return jsonify({'status': 'completed', 'result': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@agents_bp.route('/status', methods=['GET'])
def get_agents_status():
    """获取所有Agent状态"""
    try:
        return jsonify({
            'status': 'success',
            'agents': {
                'env_agent': {'name': '环境管理Agent', 'llm_enabled': bool(os.environ.get('DEEPSEEK_API_KEY'))},
                'attack_agent': {'name': '模拟攻击Agent', 'llm_enabled': bool(os.environ.get('DEEPSEEK_API_KEY'))},
                'defense_agent': {'name': '模拟防御Agent', 'llm_enabled': bool(os.environ.get('DEEPSEEK_API_KEY'))}
            }
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500