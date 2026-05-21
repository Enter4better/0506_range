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


def sanitize_container_name(name: str) -> str:
    """清理容器名称，符合Docker命名规则 [a-zA-Z0-9][a-zA-Z0-9_.-]"""
    if not name:
        name = 'container'
    import re
    # 替换冒号为下划线（Docker不允许冒号）
    name = name.replace(':', '_')
    cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
    cleaned = re.sub(r'_+', '_', cleaned)
    cleaned = cleaned.strip('_')
    if cleaned and cleaned[0].isdigit():
        cleaned = 'c_' + cleaned
    if len(cleaned) > 60:
        cleaned = cleaned[:60]
    if not cleaned:
        cleaned = 'container'
    return cleaned


def _create_container_direct(data):
    """直接创建Docker容器"""
    try:
        image = data.get('image', 'nginx')
        port = data.get('port', '8080:80')
        custom_name = data.get('name', '')
        
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 生成容器名称（必须符合Docker命名规则）
        if custom_name:
            clean_name = sanitize_container_name(custom_name)
            name = f'target_{clean_name}_{ts}'
        else:
            # 从镜像名提取基础名称
            base_name = image.split(':')[0].replace('/', '_')
            clean_base = sanitize_container_name(base_name)
            name = f'target_{clean_base}_{ts}'
        
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
        
        try:
            docker_client = docker.from_env()
        except Exception as e:
            current_app.logger.error(f"Docker服务连接失败: {e}")
            return jsonify({'status': 'error', 'msg': '无法连接到Docker服务，请确保Docker Desktop已启动'}), 503

        port_bindings = {f'{container_port}/tcp': ('0.0.0.0', host_port)}

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
        user_id = 1
        container = None
        target = None
        container_name = None
        
        # 1. 先查找数据库记录
        target = Target.get_by_id(target_id)
        if not target:
            target = Target.get_by_name(target_id)
        if not target:
            all_targets = Target.list_all()
            for t in all_targets:
                if t.name == target_id or str(t.target_id) == target_id:
                    target = t
                    break
        
        # 2. 从数据库记录中获取真实的Docker容器名称
        if target:
            if target.config:
                try:
                    config = json.loads(target.config) if isinstance(target.config, str) else target.config
                    container_name = config.get('container_name')
                except:
                    pass
            if not container_name:
                container_name = target.name
        
        # 3. 查找Docker容器（多种方式）
        try:
            docker_client = docker.from_env()

            if container_name:
                try:
                    container = docker_client.containers.get(container_name)
                except:
                    containers = docker_client.containers.list(all=True, filters={'name': container_name})
                    if containers:
                        container = containers[0]

            if not container:
                try:
                    container = docker_client.containers.get(target_id)
                except:
                    pass

            if not container:
                try:
                    for c in docker_client.containers.list(all=True):
                        if c.short_id == target_id or c.id == target_id or c.name == target_id:
                            container = c
                            break
                except:
                    pass
        except Exception as docker_err:
            current_app.logger.warning(f"Docker服务不可用，仅删除数据库记录: {docker_err}")

        # 4. 强制删除Docker容器
        docker_deleted = False
        if container:
            try:
                container.stop(timeout=5)
            except:
                pass
            try:
                container.remove(force=True)
                docker_deleted = True
                current_app.logger.info(f"Docker容器已删除: {container.name}")
            except Exception as e:
                current_app.logger.warning(f"删除Docker容器失败: {e}")
        
        # 5. 删除数据库记录
        db_deleted = False
        if target:
            target.delete()
            db_deleted = True
            current_app.logger.info(f"数据库记录已删除: {target.name}")
        
        if db_deleted or docker_deleted:
            Log.create('info', 'target', f'删除环境: {target_id}', user_id=user_id)
            return jsonify({
                'status': 'success',
                'msg': '删除成功',
                'docker_deleted': docker_deleted,
                'db_deleted': db_deleted
            }), 200
        else:
            return jsonify({'status': 'error', 'msg': f'未找到靶场记录或Docker容器: {target_id}'}), 404
            
    except Exception as e:
        current_app.logger.error(f"删除环境失败: {e}")
        return jsonify({'status': 'error', 'msg': '删除环境失败'}), 500


def _get_container_name(target):
    """从数据库记录中获取真实的Docker容器名称"""
    if not target:
        return None
    if target.config:
        try:
            config = json.loads(target.config) if isinstance(target.config, str) else target.config
            container_name = config.get('container_name')
            if container_name:
                return container_name
        except:
            pass
    return target.name


def _find_container(container_name):
    """根据名称查找Docker容器"""
    if not container_name:
        return None
    try:
        docker_client = docker.from_env()
        try:
            return docker_client.containers.get(container_name)
        except:
            containers = docker_client.containers.list(all=True, filters={'name': container_name})
            if containers:
                return containers[0]
    except:
        pass
    return None


@compat_bp.route('/env/start/<target_id>', methods=['POST'])
def compat_env_start(target_id):
    """启动环境（兼容前端）"""
    try:
        user_id = 1
        target = None
        container = None
        
        # 1. 先查找数据库记录
        target = Target.get_by_id(target_id)
        if not target:
            targets = Target.list_all()
            for t in targets:
                if t.name == target_id or str(t.target_id) == target_id:
                    target = t
                    break
        
        # 2. 从数据库记录获取Docker容器
        if target:
            real_name = _get_container_name(target)
            container = _find_container(real_name)
        
        # 3. 如果还没找到，直接用 target_id 查找Docker容器（可能是 short_id）
        if not container:
            try:
                docker_client = docker.from_env()
                try:
                    container = docker_client.containers.get(target_id)
                except:
                    for c in docker_client.containers.list(all=True):
                        if c.short_id == target_id or c.id == target_id or c.name == target_id:
                            container = c
                            break
            except:
                pass
        
        if not container:
            # 4. 有数据库记录但容器不存在，尝试重新创建
            if target and target.config:
                try:
                    config = json.loads(target.config) if isinstance(target.config, str) else target.config
                    image = config.get('image', 'nginx')
                    host_port = config.get('host_port', 8080)
                    container_port = config.get('container_port', 80)
                    real_name = config.get('container_name', f'target_{target_id}')
                    
                    docker_client = docker.from_env()
                    port_bindings = {f'{container_port}/tcp': ('0.0.0.0', host_port)}
                    
                    new_container = docker_client.containers.run(
                        image, name=real_name, detach=True,
                        ports=port_bindings, remove=False
                    )
                    container = new_container
                    current_app.logger.info(f"容器已重新创建: {new_container.name}")
                    config['container_id'] = new_container.id
                    target.config = json.dumps(config)
                    target.save()
                except Exception as recreate_error:
                    current_app.logger.error(f"重新创建容器失败: {recreate_error}")
                    return jsonify({'status': 'error', 'msg': f'容器不存在，重新创建失败: {str(recreate_error)}'}), 500
            else:
                return jsonify({'status': 'error', 'msg': f'未找到Docker容器: {target_id}'}), 404
        
        # 5. 启动Docker容器
        try:
            container.start()
            current_app.logger.info(f"Docker容器已启动: {container.name}")
        except Exception as e:
            current_app.logger.error(f"Docker启动失败: {e}")
            return jsonify({'status': 'error', 'msg': f'Docker容器启动失败: {str(e)}'}), 500
        
        # 6. 更新数据库状态 - 如果之前没找到target，通过容器名称重新查找
        if not target:
            all_targets = Target.list_all()
            for t in all_targets:
                if t.name == container.name:
                    target = t
                    break
        
        if target:
            target.status = 'running'
            target.save()
            current_app.logger.info(f"数据库状态已更新为 running: {target.name}")
        else:
            current_app.logger.warning(f"未找到对应的数据库记录: {container.name}")
        
        Log.create('success', 'target', f'启动环境: {container.name}', user_id=user_id)
        
        return jsonify({'status': 'success', 'container': container.name}), 200
    except Exception as e:
        current_app.logger.error(f"启动环境失败: {e}")
        return jsonify({'status': 'error', 'msg': '启动环境失败'}), 500


@compat_bp.route('/env/stop/<target_id>', methods=['POST'])
def compat_env_stop(target_id):
    """停止环境（兼容前端）"""
    try:
        user_id = 1
        target = None
        container = None
        
        # 1. 先查找数据库记录
        target = Target.get_by_id(target_id)
        if not target:
            targets = Target.list_all()
            for t in targets:
                if t.name == target_id or str(t.target_id) == target_id:
                    target = t
                    break
        
        # 2. 从数据库记录获取Docker容器
        if target:
            real_name = _get_container_name(target)
            container = _find_container(real_name)
        
        # 3. 如果还没找到，直接用 target_id 查找Docker容器（可能是 short_id）
        if not container:
            try:
                docker_client = docker.from_env()
                try:
                    container = docker_client.containers.get(target_id)
                except:
                    for c in docker_client.containers.list(all=True):
                        if c.short_id == target_id or c.id == target_id or c.name == target_id:
                            container = c
                            break
            except:
                pass
        
        if not container:
            return jsonify({'status': 'error', 'msg': f'未找到Docker容器: {target_id}'}), 404
        
        # 4. 停止Docker容器
        try:
            container.stop(timeout=10)
            current_app.logger.info(f"Docker容器已停止: {container.name}")
        except Exception as e:
            current_app.logger.error(f"Docker停止失败: {e}")
            return jsonify({'status': 'error', 'msg': f'Docker容器停止失败: {str(e)}'}), 500
        
        # 5. 更新数据库状态 - 如果之前没找到target，通过容器名称重新查找
        if not target:
            all_targets = Target.list_all()
            for t in all_targets:
                if t.name == container.name:
                    target = t
                    break
        
        if target:
            target.status = 'stopped'
            target.save()
            current_app.logger.info(f"数据库状态已更新为 stopped: {target.name}")
        else:
            current_app.logger.warning(f"未找到对应的数据库记录: {container.name}")
        
        Log.create('info', 'target', f'停止环境: {container.name}', user_id=user_id)
        
        return jsonify({'status': 'success', 'container': container.name}), 200
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