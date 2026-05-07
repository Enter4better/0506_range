# -*- coding: utf-8 -*-
"""
兼容路由 - 前端API路径向后兼容
提供 /api/env/ 等路由以兼容前端调用
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import sys
from pathlib import Path
import docker
import json
from datetime import datetime

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.target import Target
from models.attack import Attack
from models.defense import Defense
from models.log import Log
from services.database import db_service

compat_bp = Blueprint('compat', __name__, url_prefix='/api')


# ==================== 环境管理兼容路由 /api/env/... ====================

@compat_bp.route('/env/list', methods=['GET'])
def compat_env_list():
    """获取环境列表（兼容前端）"""
    try:
        targets = Target.list_all()
        
        # 获取Docker容器信息
        docker_info = {}
        try:
            docker_client = docker.from_env()
            for container in docker_client.containers.list(all=True):
                if container.name.startswith('target_'):
                    ports = ''
                    if container.ports:
                        port_list = []
                        for k, v in container.ports.items():
                            if v:
                                port_list.append(f"{v[0]['HostPort']}:{k}")
                        ports = ', '.join(port_list)
                    
                    docker_info[container.name] = {
                        'id': container.short_id,
                        'image': container.image.tags[0] if container.image.tags else container.image.short_id,
                        'status': container.status,
                        'ports': ports
                    }
        except Exception as e:
            current_app.logger.error(f"获取Docker信息失败: {e}")
        
        containers = []
        for target in targets:
            container_info = target.to_dict()
            if target.name in docker_info:
                container_info.update(docker_info[target.name])
            containers.append(container_info)
        
        return jsonify({
            'status': 'success',
            'containers': containers
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取环境列表失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取环境列表失败'}), 500


def _create_container_direct(data):
    """直接创建Docker容器"""
    try:
        image = data.get('image', 'nginx')
        port = data.get('port', '8080:80')
        name = data.get('name', f'target_{image}_{datetime.now().strftime("%H%M%S")}')
        
        # 解析端口
        container_port = 80
        host_port = 8080
        
        if ':' in port:
            port_parts = port.split(':')
            try:
                host_port = int(port_parts[0])
                container_port = int(port_parts[1])
            except ValueError:
                pass
        else:
            try:
                host_port = int(port)
            except ValueError:
                pass
        
        # 检查端口是否可用
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port_available = sock.connect_ex(('127.0.0.1', host_port)) != 0
        sock.close()
        
        if not port_available:
            for new_port in range(host_port + 1, host_port + 100):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if sock.connect_ex(('127.0.0.1', new_port)) != 0:
                    host_port = new_port
                    sock.close()
                    break
                sock.close()
        
        docker_client = docker.from_env()
        port_bindings = {f'{container_port}/tcp': ('127.0.0.1', host_port)}
        
        container = docker_client.containers.run(
            image,
            name=name,
            detach=True,
            ports=port_bindings,
            remove=False
        )
        
        # 保存到数据库
        target = Target(
            name=name,
            type='docker',
            port=f'{host_port}:{container_port}',
            os=image,
            status='running',
            config=json.dumps({
                'image': image,
                'host_port': host_port,
                'container_port': container_port,
                'container_id': container.id
            })
        )
        target.save()
        
        Log.create('success', 'target', f'靶场创建成功: {name}', user_id=1)
        
        return jsonify({
            'status': 'success',
            'container_id': container.short_id,
            'name': name,
            'port': host_port,
            'image': image,
            'container_port': container_port
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"创建容器失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@compat_bp.route('/env/create', methods=['POST'])
def compat_env_create():
    """创建环境（兼容前端）"""
    try:
        data = request.get_json() or {}
        return _create_container_direct(data)
    except Exception as e:
        current_app.logger.error(f"创建环境失败: {e}")
        return jsonify({'status': 'error', 'msg': f'创建环境失败: {str(e)}'}), 500


@compat_bp.route('/env/<target_id>', methods=['GET'])
def compat_env_get(target_id):
    """获取环境详情（兼容前端）"""
    try:
        target = Target.get_by_id(target_id)
        
        if not target:
            return jsonify({'status': 'error', 'msg': '环境不存在'}), 404
        
        return jsonify({
            'status': 'success',
            'data': target.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取环境详情失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取环境详情失败'}), 500


@compat_bp.route('/env/<target_id>', methods=['PUT'])
def compat_env_update(target_id):
    """更新环境（兼容前端）"""
    try:
        data = request.get_json()
        target = Target.get_by_id(target_id)
        
        if not target:
            return jsonify({'status': 'error', 'msg': '环境不存在'}), 404
        
        success = target.update(
            name=data.get('name'),
            description=data.get('description'),
            env_type=data.get('type'),
            config=data.get('config'),
            status=data.get('status')
        )
        
        if not success:
            return jsonify({'status': 'error', 'msg': '更新环境失败'}), 500
        
        # 记录日志
        Log.create('info', 'target', f'更新环境: {target.name}', user_id=1)
        
        return jsonify({
            'status': 'success',
            'data': target.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.error(f"更新环境失败: {e}")
        return jsonify({'status': 'error', 'msg': '更新环境失败'}), 500


@compat_bp.route('/env/delete/<target_id>', methods=['POST'])
def compat_env_delete(target_id):
    """删除环境（兼容前端）"""
    try:
        target = Target.get_by_id(target_id)
        
        if not target:
            return jsonify({'status': 'error', 'msg': '环境不存在'}), 404
        
        # 尝试删除Docker容器
        try:
            docker_client = docker.from_env()
            if target.name:
                container = docker_client.containers.get(target.name)
                try:
                    container.stop(timeout=5)
                except Exception:
                    pass
                container.remove(force=True)
        except Exception as e:
            current_app.logger.warning(f"删除容器失败: {e}")
        
        success = target.delete()
        
        if not success:
            return jsonify({'status': 'error', 'msg': '删除环境失败'}), 500
        
        # 记录日志
        Log.create('info', 'target', f'删除环境: {target.name}', user_id=1)
        
        return jsonify({
            'status': 'success',
            'msg': '删除成功'
        }), 200
    except Exception as e:
        current_app.logger.error(f"删除环境失败: {e}")
        return jsonify({'status': 'error', 'msg': '删除环境失败'}), 500


@compat_bp.route('/env/start/<target_id>', methods=['POST'])
def compat_env_start(target_id):
    """启动环境（兼容前端）"""
    try:
        target = Target.get_by_id(target_id)
        
        if not target:
            return jsonify({'status': 'error', 'msg': '环境不存在'}), 404
        
        # 尝试启动Docker容器
        try:
            docker_client = docker.from_env()
            if target.name:
                container = docker_client.containers.get(target.name)
                container.start()
        except Exception as e:
            current_app.logger.warning(f"启动容器失败: {e}")
        
        success = target.update(status='running')
        
        if not success:
            return jsonify({'status': 'error', 'msg': '启动环境失败'}), 500
        
        # 记录日志
        Log.create('success', 'target', f'启动环境: {target.name}', user_id=1)
        
        return jsonify({
            'status': 'success',
            'data': target.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.error(f"启动环境失败: {e}")
        return jsonify({'status': 'error', 'msg': '启动环境失败'}), 500


@compat_bp.route('/env/stop/<target_id>', methods=['POST'])
def compat_env_stop(target_id):
    """停止环境（兼容前端）"""
    try:
        target = Target.get_by_id(target_id)
        
        if not target:
            return jsonify({'status': 'error', 'msg': '环境不存在'}), 404
        
        # 尝试停止Docker容器
        try:
            docker_client = docker.from_env()
            if target.name:
                container = docker_client.containers.get(target.name)
                container.stop(timeout=10)
        except Exception as e:
            current_app.logger.warning(f"停止容器失败: {e}")
        
        success = target.update(status='stopped')
        
        if not success:
            return jsonify({'status': 'error', 'msg': '停止环境失败'}), 500
        
        # 记录日志
        Log.create('info', 'target', f'停止环境: {target.name}', user_id=1)
        
        return jsonify({
            'status': 'success',
            'data': target.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.error(f"停止环境失败: {e}")
        return jsonify({'status': 'error', 'msg': '停止环境失败'}), 500


@compat_bp.route('/env/stats', methods=['GET'])
def compat_env_stats():
    """获取环境统计（兼容前端）"""
    try:
        targets = Target.list_all()
        
        stats = {
            'total': len(targets),
            'running': len([t for t in targets if t.status == 'running']),
            'stopped': len([t for t in targets if t.status == 'stopped']),
            'error': len([t for t in targets if t.status == 'error'])
        }
        
        return jsonify({
            'status': 'success',
            'data': stats
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取环境统计失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取环境统计失败'}), 500


# ==================== 攻击管理兼容路由 /api/attack/... ====================

@compat_bp.route('/attack/list', methods=['GET'])
def compat_attack_list():
    """获取攻击列表（兼容前端）"""
    try:
        attacks = Attack.list_all('1')
        
        return jsonify({
            'status': 'success',
            'attacks': [a.to_dict() for a in attacks]
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取攻击列表失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取攻击列表失败'}), 500


@compat_bp.route('/attack/create', methods=['POST'])
def compat_attack_create():
    """创建攻击（兼容前端）"""
    try:
        data = request.get_json()
        
        attack = Attack.create(
            name=data.get('name', '未命名攻击'),
            attack_type=data.get('attack_type', 'SQL注入'),
            target=data.get('target', 'localhost'),
            port=data.get('port', '80'),
            intensity=data.get('intensity', 5),
            user_id='1'
        )
        
        if not attack:
            return jsonify({'status': 'error', 'msg': '创建攻击失败'}), 500
        
        # 记录日志
        Log.create('info', 'attack', f'创建攻击: {attack.name}', user_id='1')
        
        return jsonify({
            'status': 'success',
            'attack': attack.to_dict()
        }), 201
    except Exception as e:
        current_app.logger.error(f"创建攻击失败: {e}")
        return jsonify({'status': 'error', 'msg': '创建攻击失败'}), 500


@compat_bp.route('/attack/types', methods=['GET'])
def compat_attack_types():
    """获取攻击类型列表（兼容前端）"""
    try:
        types = Attack.get_attack_types()
        return jsonify({
            'status': 'success',
            'types': types
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取攻击类型失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取攻击类型失败'}), 500


@compat_bp.route('/attack/stats', methods=['GET'])
def compat_attack_stats():
    """获取攻击统计（兼容前端）"""
    try:
        stats = Attack.get_stats()
        return jsonify({
            'status': 'success',
            'data': stats
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取攻击统计失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取攻击统计失败'}), 500


# ==================== 防御管理兼容路由 /api/defense/... ====================

@compat_bp.route('/defense/list', methods=['GET'])
def compat_defense_list():
    """获取防御列表（兼容前端）"""
    try:
        defenses = Defense.list_all()
        
        return jsonify({
            'status': 'success',
            'data': [d.to_dict() for d in defenses]
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取防御列表失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取防御列表失败'}), 500


@compat_bp.route('/defense/types', methods=['GET'])
def compat_defense_types():
    """获取防御类型（兼容前端）"""
    try:
        types = Defense.get_defense_types()
        return jsonify({
            'status': 'success',
            'types': types
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取防御类型失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取防御类型失败'}), 500


@compat_bp.route('/defense/stats', methods=['GET'])
def compat_defense_stats():
    """获取防御统计（兼容前端）"""
    try:
        stats = Defense.get_stats()
        return jsonify({
            'status': 'success',
            'data': stats
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取防御统计失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取防御统计失败'}), 500


# ==================== 统计数据兼容路由 /api/stats/... ====================

@compat_bp.route('/stats', methods=['GET'])
def compat_stats():
    """获取统计数据（兼容前端）"""
    try:
        targets = Target.list_all()
        attacks = Attack.list_all()
        defenses = Defense.list_all()
        log_stats = Log.get_stats()
        
        stats = {
            'environments': len(targets),
            'attacks': len(attacks),
            'defenses': len(defenses),
            'logs': log_stats.get('total', 0),
            'health': 95,
            'alerts': log_stats.get('danger', 0) + log_stats.get('warning', 0)
        }
        
        return jsonify({
            'status': 'success',
            **stats
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取统计数据失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取统计数据失败'}), 500


@compat_bp.route('/stats/overview', methods=['GET'])
def compat_stats_overview():
    """获取统计概览（兼容前端）"""
    try:
        from datetime import datetime, timedelta
        
        # 基础统计
        targets = Target.list_all()
        attacks = Attack.list_all()
        defenses = Defense.list_all()
        log_stats = Log.get_stats()
        
        stats = {
            'environments': len(targets),
            'attacks': len(attacks),
            'defenses': len(defenses),
            'logs': log_stats.get('total', 0),
            'health': 95,
            'alerts': log_stats.get('danger', 0) + log_stats.get('warning', 0)
        }
        
        # 攻击类型分布
        attack_distribution = []
        attack_stats = Attack.get_stats()
        type_counts = attack_stats.get('type_counts', {})
        for attack_type, count in type_counts.items():
            attack_distribution.append({
                'name': attack_type,
                'value': count
            })
        
        # 防御分布
        defense_distribution = []
        for d in defenses:
            defense_distribution.append({
                'name': d.name,
                'value': d.coverage
            })
        
        return jsonify({
            'status': 'success',
            'stats': stats,
            'attack_distribution': attack_distribution,
            'defense_distribution': defense_distribution
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取统计概览失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@compat_bp.route('/stats/dashboard', methods=['GET'])
def compat_stats_dashboard():
    """获取仪表盘数据（兼容前端）"""
    try:
        targets = Target.list_all()
        attacks = Attack.list_all()
        defenses = Defense.list_all()
        recent_logs = Log.list_all(limit=10)
        
        stats_data = {
            'environments': len(targets),
            'attacks': len(attacks),
            'defenses': len(defenses),
            'logs': len(recent_logs) if recent_logs else 0,
            'health': 95
        }
        
        # 活跃攻击
        active_attacks = []
        for a in attacks:
            if a.status == 'running':
                active_attacks.append(a.to_dict())
        
        # 防御状态
        defense_status = []
        for d in defenses:
            if d.enabled:
                defense_status.append(d.to_dict())
        
        # 转换日志格式
        logs_list = []
        for log in recent_logs:
            logs_list.append({
                'id': log.log_id,
                'level': log.level,
                'source': log.source,
                'message': log.message,
                'time': log.created_at
            })
        
        return jsonify({
            'status': 'success',
            'stats': stats_data,
            'recent_logs': logs_list,
            'active_attacks': active_attacks,
            'defense_status': defense_status
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取仪表盘数据失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取仪表盘数据失败'}), 500