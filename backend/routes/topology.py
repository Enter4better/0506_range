# -*- coding: utf-8 -*-
"""
拓扑路由 - 显示攻击-防御动态对抗拓扑
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.target import Target
from agents.attack_agent import get_attack_agent
from agents.defense_agent import get_defense_agent

topology_bp = Blueprint('topology', __name__, url_prefix='/api/topology')


@topology_bp.route('', methods=['GET'])
@jwt_required()
def get_topology():
    """获取动态拓扑 - 显示攻击阶段和防御等级"""
    target_id = request.args.get('target_id')
    session_id = request.args.get('session_id')  # 可选，用于显示攻击状态
    
    if not target_id:
        # 返回所有靶场列表供选择
        targets = Target.list_all()
        return jsonify({
            'status': 'success',
            'targets': [{'id': t.target_id, 'name': t.name, 'os': t.os} for t in targets],
            'message': '请选择要查看拓扑的靶场'
        }), 200
    
    # 获取靶场信息
    target = Target.get_by_id(target_id)
    if not target:
        return jsonify({'status': 'error', 'msg': '靶场不存在'}), 404
    
    # 获取攻击和防御状态
    attack_agent = get_attack_agent()
    defense_agent = get_defense_agent()
    
    attack_status = attack_agent.get_session_status(session_id) if session_id else {'current_phase': 1, 'phase_name': '未开始'}
    defense_status = defense_agent.get_status(session_id) if session_id else {'current_level': 1, 'level_name': '监控级'}
    
    # 生成动态拓扑
    topology = _generate_dynamic_topology(target, attack_status, defense_status)
    
    return jsonify({
        'status': 'success',
        'target': {'id': target.target_id, 'name': target.name},
        'attack_status': attack_status,
        'defense_status': defense_status,
        'topology': topology
    }), 200


def _generate_dynamic_topology(target, attack_status, defense_status):
    """根据攻击阶段和防御等级生成动态拓扑"""
    image = target.os or ''
    attack_phase = attack_status.get('current_phase', 1)
    defense_level = defense_status.get('current_level', 1)
    
    # 节点威胁等级（根据攻击阶段）
    node_threats = {
        'web': 'high' if attack_phase >= 3 else 'medium' if attack_phase >= 2 else 'low',
        'database': 'critical' if attack_phase >= 5 else 'high' if attack_phase >= 3 else 'low',
        'app': 'high' if attack_phase >= 3 else 'low',
        'backup': 'critical' if attack_phase >= 5 else 'low'
    }
    
    # 节点防御强度（根据防御等级）
    node_defense = {
        'waf': 'active' if defense_level >= 2 else 'standby',
        'firewall': 'active' if defense_level >= 4 else 'standby',
        'monitor': 'active' if defense_level >= 1 else 'standby'
    }
    
    # 根据镜像类型生成拓扑
    if 'mysql' in image.lower() or 'postgres' in image.lower():
        nodes = [
            {'id': 'app', 'name': '应用服务器', 'type': 'app', 'ip': '10.0.0.10', 'threat': node_threats['app']},
            {'id': 'db', 'name': f'数据库({target.name})', 'type': 'database', 'ip': target.ip or '10.0.0.20', 
             'port': target.port or 3306, 'threat': node_threats['database']},
            {'id': 'backup', 'name': '备份服务器', 'type': 'backup', 'ip': '10.0.0.30', 'threat': node_threats['backup']},
            {'id': 'waf', 'name': 'WAF', 'type': 'waf', 'ip': '10.0.0.1', 'defense': node_defense['waf']}
        ]
        edges = [
            {'source': 'app', 'target': 'waf', 'protocol': 'HTTP', 'port': 80},
            {'source': 'waf', 'target': 'db', 'protocol': 'SQL', 'port': 3306},
            {'source': 'db', 'target': 'backup', 'protocol': 'sync', 'port': 873}
        ]
    
    elif 'nginx' in image.lower() or 'apache' in image.lower() or 'php' in image.lower():
        nodes = [
            {'id': 'attacker', 'name': '攻击机', 'type': 'attacker', 'ip': '192.168.1.100', 'is_attacker': True},
            {'id': 'waf', 'name': 'WAF', 'type': 'waf', 'ip': '10.0.0.1', 'defense': node_defense['waf']},
            {'id': 'web', 'name': f'Web服务器({target.name})', 'type': 'web', 'ip': target.ip or '10.0.0.10', 
             'port': target.port or 80, 'threat': node_threats['web']},
            {'id': 'db', 'name': '数据库', 'type': 'database', 'ip': '10.0.0.20', 'port': 3306, 'threat': node_threats['database']},
            {'id': 'monitor', 'name': '监控系统', 'type': 'monitor', 'ip': '10.0.0.200', 'defense': node_defense['monitor']}
        ]
        edges = [
            {'source': 'attacker', 'target': 'waf', 'protocol': 'HTTP', 'port': 443},
            {'source': 'waf', 'target': 'web', 'protocol': 'HTTP', 'port': 80},
            {'source': 'web', 'target': 'db', 'protocol': 'SQL', 'port': 3306},
            {'source': 'web', 'target': 'monitor', 'protocol': 'LOG', 'port': 514}
        ]
    
    else:
        # 通用拓扑
        nodes = [
            {'id': 'attacker', 'name': '攻击机', 'type': 'attacker', 'ip': '192.168.1.100', 'is_attacker': True},
            {'id': 'target', 'name': f'靶场({target.name})', 'type': 'target', 'ip': target.ip or '127.0.0.1', 
             'port': target.port or 22, 'threat': 'high' if attack_phase >= 3 else 'low'},
            {'id': 'firewall', 'name': '防火墙', 'type': 'firewall', 'ip': '10.0.0.1', 'defense': node_defense['firewall']}
        ]
        edges = [
            {'source': 'attacker', 'target': 'firewall', 'protocol': 'SSH', 'port': 22},
            {'source': 'firewall', 'target': 'target', 'protocol': 'SSH', 'port': 22}
        ]
    
    return {
        'nodes': nodes,
        'edges': edges,
        'attack_phase': attack_phase,
        'defense_level': defense_level,
        'phase_name': attack_status.get('phase_name', '未开始'),
        'level_name': defense_status.get('level_name', '监控级')
    }