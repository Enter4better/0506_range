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
    """AI攻击规划 - 真正调用AI生成多样化规划"""
    try:
        data = request.get_json()
        target = data.get('target', '')
        port = data.get('port', '80')
        description = data.get('description', '')
        attack_type = data.get('attack_type', '')

        if not target:
            return jsonify({'status': 'error', 'msg': '请提供目标'}), 400

        agent = get_attack_agent()

        # 构建真正的AI提示词
        target_info = f"{target}:{port}"
        prompt = f"""你是一个专业的渗透测试专家。请对目标 {target_info} 进行安全测试规划。

{'额外说明: ' + description if description else ''}

请以JSON格式返回以下信息：
{{
  "target": "{target_info}",
  "attack_type": "推荐的攻击类型（如：端口扫描、SQL注入、XSS、CSRF等）",
  "steps": ["详细的攻击步骤1", "步骤2", "步骤3"],
  "tools": ["推荐使用的工具列表"],
  "estimated_success_rate": 0.0-1.0之间的数字,
  "recommended_intensity": 1-10之间的推荐攻击强度,
  "vulnerabilities": ["可能存在的漏洞列表"],
  "message": "简短的规划说明"
}}

请返回纯粹的JSON，不要有其他解释文字。
"""

        # 调用AI
        try:
            ai_response = agent.llm_client.generate(prompt, temperature=0.9)

            # 尝试从响应中提取JSON
            import re

            json_match = re.search(r'\{[\s\S]*\}', ai_response)
            if json_match:
                plan = json.loads(json_match.group())
            else:
                # 如果AI没返回JSON，使用agent的分析能力
                plan = agent.analyze_target(target_info)

        except Exception as ai_error:
            current_app.logger.warning(f"AI调用失败，使用备用规划: {ai_error}")
            # AI失败时的备用规划
            plan = agent.analyze_target(target_info)

        Log.create('info', 'attack_agent', f'完成攻击规划: {target_info}', user_id=1)

        return jsonify({'status': 'success', 'plan': plan}), 200
    except Exception as e:
        current_app.logger.error(f"规划攻击失败: {e}")
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
    """获取防御状态 - 包含检测攻击总数、活跃封禁等"""
    try:
        session_id = request.args.get('session_id')
        agent = get_defense_agent()
        status = agent.get_status(session_id)

        # 计算检测攻击总数（从防御日志中统计）
        all_logs = agent.get_defense_logs(1000)
        total_attacks = len(all_logs)

        # 构建活跃封禁列表
        active_blocks = {}
        if session_id and session_id in agent.session_defense:
            session = agent.session_defense[session_id]
            blocked_ips = session.get('blocked_ips', [])
            if blocked_ips:
                active_blocks['ip_blocks'] = {
                    'level': session.get('level', 1),
                    'ips': blocked_ips
                }

        return jsonify({
            'status': 'success',
            'data': {
                **status,
                'total_attacks': total_attacks,
                'defense_logs_count': len(all_logs),
                'active_blocks': active_blocks
            }
        }), 200
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
    """获取所有会话 - 优先从内存获取，同时从数据库补充"""
    try:
        orchestrator = get_orchestrator()
        sessions = []
        seen_ids = set()
        
        # 1. 从内存中的 orchestrator sessions 获取
        for sid, sess in orchestrator.sessions.items():
            sessions.append({
                'session_id': sid,
                'environment': sess.get('environment', {}),
                'status': sess.get('status', 'active'),
                'created_at': sess.get('created_at')
            })
            seen_ids.add(sid)
        
        # 2. 从数据库 Target 表补充（用于报告页面展示）
        try:
            from models.target import Target
            targets = Target.list_all()
            for t in targets:
                tid = str(t.target_id) if t.target_id else None
                if tid and tid not in seen_ids:
                    sessions.append({
                        'session_id': tid,
                        'environment': {
                            'name': t.name or '靶场',
                            'components': []
                        },
                        'status': t.status or 'unknown',
                        'created_at': t.created_at or datetime.now().isoformat()
                    })
                    seen_ids.add(tid)
        except Exception as db_err:
            current_app.logger.warning(f"从数据库补充会话失败: {db_err}")
        
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


@agents_bp.route('/model-routes', methods=['GET'])
def get_model_routes():
    """获取多模型路由配置（供前端展示各任务使用的模型策略）"""
    try:
        from llm.model_router import list_task_routes
        return jsonify({'status': 'success', 'routes': list_task_routes()}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


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


# ==================== AI靶场自动生成 API ====================

@agents_bp.route('/ai-range/generate', methods=['POST'])
def ai_generate_range():
    """AI靶场自动生成 - 根据自然语言描述自动构建靶场"""
    try:
        data = request.get_json()
        scenario_desc = data.get('description', '')
        
        if not scenario_desc:
            return jsonify({'status': 'error', 'msg': '请提供场景描述'}), 400
        
        # 1. 使用EnvAgent分析场景
        env_agent = get_env_agent(1)
        config = env_agent.analyze_scenario(scenario_desc)
        
        # 2. 记录日志
        Log.create('info', 'env_agent', 
                  f"AI靶场生成: 场景分析完成 - {config.get('name', '自定义靶场')}", 
                  user_id=1)
        
        return jsonify({
            'status': 'success',
            'config': config,
            'message': '场景分析完成，请确认配置后点击部署'
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500



@agents_bp.route('/ai-range/deploy', methods=['POST'])
def ai_deploy_range():
    """AI靶场自动部署 - 根据确认的配置创建靶场环境"""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'status': 'error', 'msg': '请求体无效，请以JSON格式提交'}), 400

        config = data.get('config', {})

        if not config or 'components' not in config:
            return jsonify({'status': 'error', 'msg': '请提供有效的靶场配置（需包含components字段）'}), 400

        # 1. 使用EnvAgent创建环境
        env_agent = get_env_agent(1)
        result = env_agent.create_environment(config, 1)

        # 2. 直接用已部署的环境结果构建编排器会话，避免二次create_environment
        orchestrator = get_orchestrator()
        # 优先使用result中的environment_id，它已在create_environment中生成
        session_id = result.get('environment_id')
        if not session_id:
            session_id = f"env_{int(__import__('time').time())}"
        # 优先使用result中的name（已在create_environment中优化）
        range_name = result.get('name') or config.get('name', '自定义靶场')
        session_info = {
            'status': 'success',
            'session_id': session_id,
            'environment': {
                'name': range_name,
                'components': result.get('components', [])
            }
        }
        with orchestrator._lock:
            orchestrator.sessions[session_id] = {
                'session_id': session_id,
                'environment': session_info['environment'],
                'attacks': [],
                'decision_log': [],
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'current_intensity': 5,
                'difficulty_mode': 'single',
                'recent_intercept_rates': [],
                'env_adjustments': [],
            }

        Log.create('success', 'env_agent',
                  f"AI靶场部署成功: {range_name} (环境ID: {session_id})",
                  user_id=1)

        return jsonify({
            'status': 'success',
            'result': result,
            'session': session_info,
            'message': '靶场部署成功，攻防演练已就绪'
        }), 200

    except Exception as e:
        current_app.logger.error(f"AI靶场部署失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500



@agents_bp.route('/ai-range/expand-variants', methods=['GET'])
def ai_expand_variants():
    """场景变种自动扩展：从基础场景派生WAF/登录/内网/域控等变种"""
    try:
        base_key = request.args.get('base', 'web_security')
        env_agent = get_env_agent(1)
        variants = env_agent.expand_scenario_variants(base_key)
        return jsonify({'status': 'success', 'variants': variants, 'base_key': base_key}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@agents_bp.route('/ai-range/scenarios', methods=['GET'])
def ai_list_scenarios():
    """获取AI可用的场景模板列表"""
    try:
        env_agent = get_env_agent(1)
        scenarios = env_agent.list_available_scenarios()
        return jsonify({
            'status': 'success',
            'scenarios': scenarios
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500






