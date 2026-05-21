# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import docker
import random
import json
import re
from datetime import datetime
import sys
from pathlib import Path
from urllib.parse import unquote

backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.target import Target
from models.log import Log
from services.database import db_service
from services.async_queue import async_queue_service
from config import DOCKER_CONFIG

targets_bp = Blueprint('targets', __name__, url_prefix='/api/env')

_IMAGE_REQUIRED_COMMANDS = {
    'ubuntu:22.04':      'sleep infinity',
    'python:3.11-slim':  'sleep infinity',
    'node:18-alpine':    'sleep infinity',
    'alpine:latest':     'sleep infinity',
}

_IMAGE_REQUIRED_ENVS = {
    'postgres:15-alpine': {'POSTGRES_PASSWORD': 'Range@123'},
    'mysql:8.0':          {'MYSQL_ROOT_PASSWORD': 'Range@123', 'MYSQL_DATABASE': 'testdb'},
}



def sanitize_container_name(name: str) -> str:
    """清理容器名称，符合Docker命名规则"""
    if not name:
        name = 'container'
    name = unquote(name)
    # 先替换冒号为下划线（Docker不允许冒号）
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


def _get_container_ports(container):
    """获取容器端口映射"""
    ports = []
    if container.ports:
        for container_port, host_bindings in container.ports.items():
            if host_bindings:
                for binding in host_bindings:
                    ports.append(f"{binding['HostPort']}:{container_port.split('/')[0]}")
    return ', '.join(ports) if ports else ''


_RANGE_PREFIXES = (DOCKER_CONFIG['container_prefix'], 'target_')


def _is_range_container(name: str) -> bool:
    return bool(name) and any(name.startswith(p) for p in _RANGE_PREFIXES)


def _cleanup_failed_containers():
    try:
        docker_client = docker.from_env()
        for c in docker_client.containers.list(all=True):
            if _is_range_container(c.name):
                if c.status in ('created', 'dead', 'exited'):
                    try:
                        c.remove(force=True)
                        current_app.logger.info(f"[CLEANUP] 移除残留容器: {c.name}")
                    except Exception as e:
                        current_app.logger.error(f"[CLEANUP] 移除 {c.name} 失败: {e}")
    except Exception as e:
        current_app.logger.error(f"[CLEANUP] 清理失败: {e}")


@targets_bp.route('/list', methods=['GET'])
def list_targets():
    try:
        targets = Target.list_all()
        docker_client = docker.from_env()
        
        result = []
        for target in targets:
            # 解析 config 获取镜像信息
            image_name = target.os or 'unknown'
            ports = target.port or ''
            container_name = None
            
            # 如果有 config，尝试从中提取更详细的信息
            if target.config:
                try:
                    config = json.loads(target.config) if isinstance(target.config, str) else target.config
                    if config.get('image'):
                        image_name = config.get('image')
                    if config.get('host_port'):
                        ports = f"{config.get('host_port')}:{config.get('container_port', 80)}"
                    container_name = config.get('container_name')
                except:
                    pass
            
            # 实时获取 Docker 容器状态（优先使用真实状态）
            real_status = target.status or 'stopped'
            if container_name:
                try:
                    container = docker_client.containers.get(container_name)
                    real_status = container.status  # running, exited, etc.
                    # 同步更新数据库状态
                    if target.status != real_status:
                        target.status = real_status
                        target.save()
                except:
                    # 容器不存在，标记为 stopped
                    real_status = 'stopped'
                    if target.status != 'stopped':
                        target.status = 'stopped'
                        target.save()
            
            result.append({
                'id': target.target_id,
                'target_id': target.target_id,
                'name': target.name or '未命名靶场',
                'image': image_name,
                'ports': ports,
                'status': real_status,
                'created': target.created_at,
                'created_at': target.created_at,
                'container_name': container_name  # 添加容器名用于删除匹配
            })
        
        return jsonify({'status': 'success', 'containers': result}), 200
        
    except Exception as e:
        current_app.logger.error(f"获取靶场列表失败: {e}")
        return jsonify({'status': 'error', 'containers': [], 'msg': str(e)}), 200


@targets_bp.route('/create', methods=['POST'])
def create_target():
    try:
        user_id = 1  # 临时使用默认用户
        data = request.get_json()
        
        required_fields = ['image', 'port']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'status': 'error', 'msg': f'{field} 是必填项'}), 400
        
        original_image = data.get('image')
        port_mapping = data.get('port')
        custom_name = data.get('name', '')
        env_vars = data.get('env', '')
        
        _cleanup_failed_containers()
        
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 生成容器名称和显示名称
        if custom_name:
            clean_name = sanitize_container_name(custom_name)
            container_name = f'{DOCKER_CONFIG["container_prefix"]}{clean_name}_{ts}'
            display_name = custom_name
        else:
            # 从镜像名提取显示名称（去掉标签部分如 :latest）
            base_name = original_image.split(':')[0].replace('/', '_')
            # 进一步清理，确保符合Docker命名规则
            clean_base = sanitize_container_name(base_name)
            container_name = f'{DOCKER_CONFIG["container_prefix"]}{clean_base}_{ts}'
            display_name = f'{base_name}靶场'
        
        current_app.logger.info(f"原始镜像: {original_image}")
        current_app.logger.info(f"容器名称: {container_name}")
        current_app.logger.info(f"显示名称: {display_name}")
        
        try:
            container_port = port_mapping.split(':')[1] if ':' in port_mapping else '80'
            host_port = int(port_mapping.split(':')[0]) if ':' in port_mapping else 8080
            
            assigned_port = None
            for attempt_port in [host_port] + list(range(8100, 8950, 50)):
                try:
                    docker_client = docker.from_env()
                    port_bindings = {f'{container_port}/tcp': ('0.0.0.0', attempt_port)}
                    env_list = [e.strip() for e in env_vars.split(',')] if env_vars else None
                    
                    req_env = dict(_IMAGE_REQUIRED_ENVS.get(original_image, {}))
                    if env_list:
                        for e in env_list:
                            if '=' in e:
                                k, v = e.split('=', 1)
                                req_env[k.strip()] = v.strip()
                    cmd = _IMAGE_REQUIRED_COMMANDS.get(original_image)
                    run_kwargs = {
                        'name': container_name, 'detach': True,
                        'ports': port_bindings, 'remove': False,
                        'environment': req_env if req_env else None,
                    }
                    if cmd:
                        run_kwargs['command'] = cmd
                    container = docker_client.containers.run(original_image, **run_kwargs)
                    assigned_port = attempt_port
                    break
                except Exception as port_err:
                    if 'port is already allocated' in str(port_err) or 'bind' in str(port_err).lower():
                        continue
                    else:
                        raise
            
            if assigned_port is None:
                return jsonify({'status': 'error', 'msg': '所有候选端口均被占用'}), 500
            
            import time
            time.sleep(1.5)
            container.reload()
            
            # 保存到数据库 - 使用显示名称
            target = Target(
                name=display_name,  # 重要：使用可读的名称
                type='docker',
                port=f'{assigned_port}:{container_port}',
                os=original_image,
                status='running',
                config=json.dumps({
                    'image': original_image,
                    'host_port': assigned_port,
                    'container_port': container_port,
                    'container_name': container_name,
                    'environment': env_list
                })
            )
            target.save()
            
            Log.create('success', 'target', f'靶场创建成功: {display_name} (端口: {assigned_port})', 
                      details=f'target_id: {target.target_id}', user_id=user_id)
            
            return jsonify({
                'status': 'success',
                'container_id': container.short_id,
                'name': display_name,
                'port': assigned_port,
                'image': original_image,
                'container_port': container_port
            }), 201
            
        except docker.errors.NotFound:
            return jsonify({'status': 'error', 'msg': f'镜像 {original_image} 不存在'}), 400
        except docker.errors.APIError as e:
            return jsonify({'status': 'error', 'msg': f'Docker错误: {str(e)}'}), 500
        except Exception as e:
            return jsonify({'status': 'error', 'msg': str(e)}), 500
            
    except Exception as e:
        current_app.logger.error(f"创建容器失败: {e}")
        return jsonify({'status': 'error', 'msg': f'创建靶场失败: {str(e)}'}), 500


def _get_container_name(target):
    """从数据库记录中获取真实的Docker容器名称"""
    if not target:
        return None
    # 优先从config中获取container_name（创建时保存的真实Docker容器名）
    if target.config:
        try:
            config = json.loads(target.config) if isinstance(target.config, str) else target.config
            container_name = config.get('container_name')
            if container_name:
                return container_name
        except:
            pass
    # 回退：使用target.name（可能是显示名称，不一定匹配Docker容器名）
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
            # 尝试通过名称前缀查找
            containers = docker_client.containers.list(all=True, filters={'name': container_name})
            if containers:
                return containers[0]
    except:
        pass
    return None


@targets_bp.route('/start/<container_id>', methods=['POST'])
def start_target(container_id):
    try:
        user_id = 1
        
        target = None
        container = None
        
        # 1. 先查找数据库记录
        target = Target.get_by_id(container_id)
        if not target:
            targets = Target.list_all()
            for t in targets:
                if t.name == container_id or str(t.target_id) == container_id:
                    target = t
                    break
        
        # 2. 从数据库记录获取Docker容器
        if target:
            real_name = _get_container_name(target)
            container = _find_container(real_name)
        
        # 3. 如果还没找到容器，直接用 container_id 查找Docker容器（可能是 short_id）
        if not container:
            try:
                docker_client = docker.from_env()
                try:
                    container = docker_client.containers.get(container_id)
                except:
                    # 遍历所有带前缀的容器匹配
                    for c in docker_client.containers.list(all=True):
                        if c.short_id == container_id or c.id == container_id or c.name == container_id:
                            container = c
                            break
            except:
                pass
        
        if not container:
            # 4. 如果容器不存在但有数据库记录，尝试重新创建
            if target and target.config:
                try:
                    config = json.loads(target.config) if isinstance(target.config, str) else target.config
                    image = config.get('image', 'nginx')
                    host_port = config.get('host_port', 8080)
                    container_port = config.get('container_port', 80)
                    real_name = config.get('container_name', f'target_{container_id}')
                    
                    docker_client = docker.from_env()
                    port_bindings = {f'{container_port}/tcp': ('0.0.0.0', host_port)}
                    
                    new_container = docker_client.containers.run(
                        image,
                        name=real_name,
                        detach=True,
                        ports=port_bindings,
                        remove=False
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
                return jsonify({'status': 'error', 'msg': f'未找到Docker容器: {container_id}'}), 404
        
        # 5. 启动Docker容器
        try:
            container.start()
            current_app.logger.info(f"Docker容器已启动: {container.name}")
        except Exception as e:
            current_app.logger.error(f"Docker启动失败: {e}")
            return jsonify({'status': 'error', 'msg': f'Docker容器启动失败: {str(e)}'}), 500
        
        # 6. 更新数据库状态（如果有记录）
        if target:
            target.status = 'running'
            target.save()
        
        Log.create('success', 'target', f'靶场启动成功: {container.name}', 
                  user_id=user_id)
        
        return jsonify({'status': 'success', 'container': container.name}), 200
        
    except Exception as e:
        current_app.logger.error(f"启动靶场失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@targets_bp.route('/stop/<container_id>', methods=['POST'])
def stop_target(container_id):
    try:
        user_id = 1
        
        target = None
        container = None
        
        # 1. 先查找数据库记录
        target = Target.get_by_id(container_id)
        if not target:
            targets = Target.list_all()
            for t in targets:
                if t.name == container_id or str(t.target_id) == container_id:
                    target = t
                    break
        
        # 2. 从数据库记录获取Docker容器
        if target:
            real_name = _get_container_name(target)
            container = _find_container(real_name)
        
        # 3. 如果还没找到容器，直接用 container_id 查找Docker容器（可能是 short_id）
        if not container:
            try:
                docker_client = docker.from_env()
                try:
                    container = docker_client.containers.get(container_id)
                except:
                    # 遍历所有带前缀的容器匹配
                    for c in docker_client.containers.list(all=True):
                        if c.short_id == container_id or c.id == container_id or c.name == container_id:
                            container = c
                            break
            except:
                pass
        
        if not container:
            return jsonify({'status': 'error', 'msg': f'未找到Docker容器: {container_id}'}), 404
        
        # 4. 停止Docker容器
        try:
            container.stop(timeout=10)
            current_app.logger.info(f"Docker容器已停止: {container.name}")
        except Exception as e:
            current_app.logger.error(f"Docker停止失败: {e}")
            return jsonify({'status': 'error', 'msg': f'Docker容器停止失败: {str(e)}'}), 500
        
        # 5. 更新数据库状态（如果有记录）
        if target:
            target.status = 'stopped'
            target.save()
        
        Log.create('info', 'target', f'靶场停止成功: {container.name}', user_id=user_id)
        
        return jsonify({'status': 'success', 'container': container.name}), 200
        
    except Exception as e:
        current_app.logger.error(f"停止靶场失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@targets_bp.route('/delete/<container_id>', methods=['POST'])
def delete_target(container_id):
    try:
        user_id = 1
        
        container = None
        target = None
        container_name = None
        
        # 1. 先查找数据库记录（支持 target_id 数字ID 或 name）
        target = Target.get_by_id(container_id)
        if not target:
            target = Target.get_by_name(container_id)
        if not target:
            # 尝试通过名称模糊匹配
            all_targets = Target.list_all()
            for t in all_targets:
                if t.name == container_id or str(t.target_id) == container_id:
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
        docker_client = docker.from_env()
        
        # 方式1: 通过 container_name 精确查找
        if container_name:
            try:
                container = docker_client.containers.get(container_name)
            except:
                pass
        
        # 方式2: 通过 container_name 前缀模糊查找
        if not container and container_name:
            try:
                containers = docker_client.containers.list(all=True, filters={'name': container_name})
                if containers:
                    container = containers[0]
            except:
                pass
        
        # 方式3: 通过 container_id 查找（可能是 short_id）
        if not container:
            try:
                container = docker_client.containers.get(container_id)
            except:
                pass
        
        # 方式4: 遍历所有带前缀的容器，匹配名称或ID
        if not container:
            try:
                for c in docker_client.containers.list(all=True):
                    if c.name and c.name.startswith(DOCKER_CONFIG['container_prefix']):
                        if c.short_id == container_id or c.id == container_id or c.name == container_id:
                            container = c
                            break
            except:
                pass
        
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
                current_app.logger.info(f"Docker容器已删除: {container.name} (id: {container.short_id})")
            except Exception as e:
                current_app.logger.error(f"删除Docker容器失败: {e}")
                # 即使删除失败，也继续删除数据库记录
        else:
            current_app.logger.warning(f"未找到Docker容器: container_name={container_name}, container_id={container_id}")
        
        # 5. 删除数据库记录
        db_deleted = False
        if target:
            target.delete()
            db_deleted = True
            current_app.logger.info(f"数据库记录已删除: {target.name} (id: {target.target_id})")
        
        if db_deleted or docker_deleted:
            Log.create('info', 'target', f'靶场删除成功: {container_id}', user_id=user_id)
            return jsonify({
                'status': 'success',
                'deleted': container_id,
                'docker_deleted': docker_deleted,
                'db_deleted': db_deleted
            }), 200
        else:
            return jsonify({'status': 'error', 'msg': f'未找到靶场记录或Docker容器: {container_id}'}), 404
        
    except Exception as e:
        current_app.logger.error(f"删除靶场失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@targets_bp.route('/clean', methods=['POST'])
def clean_targets():
    try:
        user_id = 1
        docker_client = docker.from_env()
        count = 0
        failed = []
        
        for c in docker_client.containers.list(all=True):
            if _is_range_container(c.name):
                try:
                    try:
                        c.stop(timeout=5)
                    except:
                        pass
                    c.remove(force=True)
                    count += 1
                    target = Target.get_by_name(c.name)
                    if target:
                        target.delete()
                except Exception as e:
                    failed.append(f"{c.name}: {e}")
        
        all_targets = Target.list_all()
        for target in all_targets:
            try:
                docker_client.containers.get(target.name)
            except:
                target.delete()
        
        Log.create('info', 'target', f'批量清理: 成功 {count} 个', user_id=user_id)
        
        return jsonify({'status': 'success', 'cleaned': count, 'failed': failed}), 200
        
    except Exception as e:
        current_app.logger.error(f"清理靶场失败: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500