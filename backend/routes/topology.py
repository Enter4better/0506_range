# -*- coding: utf-8 -*-
"""
拓扑路由 - 显示攻击-防御动态对抗拓扑
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import json

from models.target import Target
from agents.attack_agent import get_attack_agent
from agents.defense_agent import get_defense_agent


topology_bp = Blueprint('topology', __name__, url_prefix='/api/topology')


def _parse_container_info(target):
    """从 Target 对象解析容器真实信息"""
    try:
        cfg = json.loads(target.config) if target.config else {}
    except Exception:
        cfg = {}

    host_port = cfg.get('host_port', target.port)
    container_port = cfg.get('container_port', '')
    container_name = cfg.get('container_name', target.name)
    image = cfg.get('image', target.os or '')

    # 从容器名推断节点类型
    name_lower = container_name.lower()
    if 'waf' in name_lower or 'proxy' in name_lower:
        node_type = 'waf'
        label = 'WAF'
    elif any(k in name_lower for k in ['db', 'database', 'mysql', 'postgres', 'mongo']):
        node_type = 'database'
        label = '数据库'
    elif any(k in name_lower for k in ['web', 'apache', 'nginx', 'http']):
        node_type = 'web'
        label = 'Web服务器'
    elif 'backup' in name_lower:
        node_type = 'backup'
        label = '备份服务器'
    elif 'monitor' in name_lower:
        node_type = 'monitor'
        label = '监控系统'
    elif 'firewall' in name_lower:
        node_type = 'firewall'
        label = '防火墙'
    elif 'app' in name_lower:
        node_type = 'app'
        label = '应用服务器'
    else:
        node_type = 'target'
        label = '靶场'

    return {
        'container_name': container_name,
        'host_port': host_port,
        'container_port': container_port,
        'image': image,
        'node_type': node_type,
        'label': label
    }


@topology_bp.route('', methods=['GET'])
def get_topology():
    """获取动态拓扑 - 显示攻击阶段和防御等级"""
    try:
        target_id = request.args.get('target_id')
        session_id = request.args.get('session_id')  # 可选

        if not target_id:
            # 返回按场景分组的靶场列表（供前端下拉选择）
            scenarios = Target.list_scenarios()
            return jsonify({
                'status': 'success',
                'scenarios': [
                    {
                        'scenario_name': s['scenario_name'],
                        'containers': [
                            {
                                'id': c.target_id,
                                'name': c.name,
                                'os': c.os,
                                'port': c.port,
                                'status': c.status,
                                'session_id': c.session_id
                            }
                            for c in s['containers']
                        ]
                    }
                    for s in scenarios
                ],
                'message': '请选择要查看拓扑的靶场'
            }), 200

        # 获取靶场信息
        target = Target.get_by_id(target_id)
        if not target:
            return jsonify({'status': 'error', 'msg': '靶场不存在'}), 404

        # 找出同一场景的所有容器
        scenario_name = Target.get_scenario_name(target)
        if scenario_name:
            scenario_targets = Target.get_scenario_containers(scenario_name)
        else:
            scenario_targets = [target]

        # 获取攻击和防御状态
        attack_agent = get_attack_agent()
        defense_agent = get_defense_agent()

        attack_status = attack_agent.get_session_status(session_id) if session_id else \
            {'current_phase': 0, 'total_phases': 6, 'phase_name': '未开始', 'successes': 0}
        defense_status = defense_agent.get_status(session_id) if session_id else \
            {'current_level': 1, 'level_name': '监控级', 'blocked_ips': []}

        # 生成动态拓扑（使用真实容器数据）
        topology = _generate_dynamic_topology(scenario_targets, scenario_name, attack_status, defense_status)

        return jsonify({
            'status': 'success',
            'scenario_name': scenario_name,
            'target': {'id': target.target_id, 'name': target.name},
            'attack_status': attack_status,
            'defense_status': defense_status,
            'topology': topology
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取拓扑失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@topology_bp.route('/export', methods=['GET'])
def export_topology():
    """导出拓扑数据"""
    try:
        target_id = request.args.get('target_id')
        session_id = request.args.get('session_id')
        format_type = request.args.get('format', 'json')

        if not target_id:
            return jsonify({'status': 'error', 'msg': '请提供target_id'}), 400

        target = Target.get_by_id(target_id)
        if not target:
            return jsonify({'status': 'error', 'msg': '靶场不存在'}), 404

        scenario_name = Target.get_scenario_name(target)
        scenario_targets = Target.get_scenario_containers(scenario_name) if scenario_name else [target]

        attack_agent = get_attack_agent()
        defense_agent = get_defense_agent()

        attack_status = attack_agent.get_session_status(session_id) if session_id else \
            {'current_phase': 0, 'total_phases': 6, 'phase_name': '未开始', 'successes': 0}
        defense_status = defense_agent.get_status(session_id) if session_id else \
            {'current_level': 1, 'level_name': '监控级', 'blocked_ips': []}

        topology = _generate_dynamic_topology(scenario_targets, scenario_name, attack_status, defense_status)

        export_data = {
            'exported_at': datetime.now().isoformat(),
            'scenario_name': scenario_name,
            'target': {'id': target.target_id, 'name': target.name, 'ip': target.ip, 'port': target.port, 'os': target.os},
            'attack_status': attack_status,
            'defense_status': defense_status,
            'topology': topology
        }

        if format_type == 'json':
            output = json.dumps(export_data, ensure_ascii=False, indent=2)
            return output, 200, {
                'Content-Type': 'application/json; charset=utf-8',
                'Content-Disposition': f'attachment; filename=topology_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            }
        else:
            return jsonify({'status': 'success', 'data': export_data}), 200
    except Exception as e:
        current_app.logger.error(f"导出拓扑失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500


def _generate_dynamic_topology(scenario_targets, scenario_name, attack_status, defense_status):
    """
    根据真实容器数据生成动态拓扑

    scenario_targets: 同一场景的所有 Target 对象列表
    attack_status: 攻击状态字典
    defense_status: 防御状态字典
    """
    attack_phase = attack_status.get('current_phase', 1)
    defense_level = defense_status.get('current_level', 1)

    # 节点威胁等级（根据攻击阶段）
    node_threats = {
        'web':      'high' if attack_phase >= 3 else 'medium' if attack_phase >= 2 else 'low',
        'database': 'critical' if attack_phase >= 5 else 'high' if attack_phase >= 3 else 'low',
        'app':      'high' if attack_phase >= 3 else 'low',
        'backup':   'critical' if attack_phase >= 5 else 'low',
        'waf':      'low',
        'firewall': 'low',
        'monitor':  'low',
        'target':   'high' if attack_phase >= 3 else 'low',
    }

    # 节点防御状态（根据防御等级）
    node_defense = {
        'waf':      'active' if defense_level >= 2 else 'standby',
        'firewall': 'active' if defense_level >= 4 else 'standby',
        'monitor':  'active' if defense_level >= 1 else 'standby',
    }

    nodes = []
    edges = []
    node_map = {}  # type -> node_id，用于构建连接关系

    # ========== 第一步：基于真实容器构建节点 ==========
    for target in scenario_targets:
        info = _parse_container_info(target)
        node_id = f"node_{target.target_id}"

        node_map[info['node_type']] = node_id

        nodes.append({
            'id': node_id,
            'name': _clean_node_name(info['container_name']),
            'type': info['node_type'],
            'label': info['label'],
            'ip': f"127.0.0.1:{info['host_port']}",
            'port': info['container_port'],
            'host_port': info['host_port'],
            'image': info['image'],
            'target_id': target.target_id,
            'container_name': info['container_name'],
            'threat': node_threats.get(info['node_type'], 'low'),
            'defense': node_defense.get(info['node_type'], 'standby'),
        })

    # ========== 第二步：如果没有 attacker 节点，添加攻击机 ==========
    if 'attacker' not in node_map:
        attacker_id = 'node_attacker'
        node_map['attacker'] = attacker_id
        nodes.append({
            'id': attacker_id,
            'name': '攻击机',
            'type': 'attacker',
            'label': '攻击者',
            'ip': '192.168.1.100',
            'port': None,
            'target_id': None,
            'threat': 'low',
            'defense': 'standby',
            'is_attacker': True,
        })

    # ========== 第三步：根据节点类型推断连接关系 ==========
    # 标准连接逻辑（推断而非硬编码）
    # attacker -> waf/firewall -> web/app -> database/backup
    _build_edges(nodes, node_map, edges)

    # 如果没有任何标准节点，添加默认连接
    if not edges and len(nodes) >= 2:
        # 攻击机连向第一个非攻击节点
        attacker_node = next((n for n in nodes if n.get('is_attacker')), None)
        other_node = next((n for n in nodes if not n.get('is_attacker')), None)
        if attacker_node and other_node:
            edges.append({
                'source': attacker_node['id'],
                'target': other_node['id'],
                'protocol': 'TCP',
                'port': other_node.get('port', '')
            })

    return {
        'nodes': nodes,
        'edges': edges,
        'attack_phase': attack_phase,
        'defense_level': defense_level,
        'phase_name': attack_status.get('phase_name', '未开始'),
        'level_name': defense_status.get('level_name', '监控级'),
        'scenario_name': scenario_name,
        'total_containers': len(scenario_targets),
    }


def _clean_node_name(container_name):
    """清理容器名为显示友好的名称"""
    # 去掉 cyber_range_ 前缀和 os 镜像名后缀
    name = container_name.replace('cyber_range_', '')
    # 去掉常见镜像名后缀
    for suffix in ['_nginx:alpine', '_mysql:8.0', '_apache', '_alpine', ':alpine', ':8.0']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name


def _build_edges(nodes, node_map, edges):
    """根据节点类型智能推断连接关系"""
    # 确定入口节点（waf > firewall > web > app）
    entry_type = None
    if 'waf' in node_map:
        entry_type = 'waf'
    elif 'firewall' in node_map:
        entry_type = 'firewall'
    elif 'web' in node_map:
        entry_type = 'web'
    elif 'app' in node_map:
        entry_type = 'app'

    # 确定后端节点（database > backup）
    backend_types = []
    for t in ['database', 'backup']:
        if t in node_map:
            backend_types.append(t)

    attacker_id = node_map.get('attacker')
    entry_id = node_map.get(entry_type) if entry_type else None

    # attacker -> entry
    if attacker_id and entry_id:
        edges.append({
            'source': attacker_id,
            'target': entry_id,
            'protocol': 'HTTP',
            'port': 443 if entry_type == 'waf' else 80,
        })

    # entry -> web/app
    if entry_type in ('waf', 'firewall'):
        for web_type in ['web', 'app']:
            if web_type in node_map:
                edges.append({
                    'source': entry_id,
                    'target': node_map[web_type],
                    'protocol': 'HTTP',
                    'port': 80,
                })

    # web/app -> database
    for backend_type in backend_types:
        source_type = 'web' if 'web' in node_map else ('app' if 'app' in node_map else None)
        if source_type:
            edges.append({
                'source': node_map[source_type],
                'target': node_map[backend_type],
                'protocol': 'SQL',
                'port': 3306 if backend_type == 'database' else 873,
            })

    # web -> monitor（可选监控连接）
    if 'web' in node_map and 'monitor' in node_map:
        edges.append({
            'source': node_map['web'],
            'target': node_map['monitor'],
            'protocol': 'LOG',
            'port': 514,
        })

    # app -> backup（备份连接）
    if 'app' in node_map and 'backup' in node_map:
        edges.append({
            'source': node_map['app'],
            'target': node_map['backup'],
            'protocol': 'sync',
            'port': 873,
        })
