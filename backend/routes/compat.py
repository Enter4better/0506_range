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
import socket
import re
import subprocess
import time

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.target import Target
from models.attack import Attack
from models.defense import Defense
from models.log import Log
from config import DOCKER_CONFIG

compat_bp = Blueprint('compat', __name__, url_prefix='/api')

# Docker客户端缓存
_docker_client = None

def get_docker_client():
    """获取Docker客户端（单例模式，带连接活性检测）"""
    global _docker_client
    if _docker_client is not None:
        try:
            _docker_client.ping()
        except Exception:
            _docker_client = None
    if _docker_client is None:
        try:
            _docker_client = docker.from_env()
        except Exception as e:
            current_app.logger.error(f"Docker服务连接失败: {e}")
            return None
    return _docker_client


def get_current_user_id():
    """获取当前用户ID"""
    try:
        user_id = get_jwt_identity()
        return user_id if user_id else 1
    except:
        return 1


def sanitize_container_name(name: str) -> str:
    """清理容器名称，符合Docker命名规则 [a-zA-Z0-9][a-zA-Z0-9_.-]"""
    if not name:
        name = 'container'
    
    # 替换冒号为下划线（Docker不允许冒号）
    name = name.replace(':', '_')
    cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
    cleaned = re.sub(r'_+', '_', cleaned)
    cleaned = cleaned.strip('_')
    
    # 不能以数字开头
    if cleaned and cleaned[0].isdigit():
        cleaned = 'c_' + cleaned
    
    # 长度限制
    if len(cleaned) > 60:
        cleaned = cleaned[:60]
    
    if not cleaned:
        cleaned = 'container'
    
    return cleaned


def find_target_by_id(target_id):
    """根据ID或名称查找目标"""
    if not target_id:
        return None
    
    # 1. 按ID查找
    target = Target.get_by_id(target_id)
    if target:
        return target
    
    # 2. 按名称查找
    target = Target.get_by_name(target_id)
    if target:
        return target
    
    # 3. 遍历查找
    all_targets = Target.list_all()
    for t in all_targets:
        if (str(t.target_id) == str(target_id) or 
            t.name == target_id):
            return t
    
    return None


def get_container_name_from_target(target):
    """从数据库记录中获取真实的Docker容器名称"""
    if not target:
        return None
    
    # 优先从config中获取container_name
    if target.config:
        try:
            config = (json.loads(target.config) 
                     if isinstance(target.config, str) 
                     else target.config)
            container_name = config.get('container_name')
            if container_name:
                return container_name
        except Exception as e:
            current_app.logger.warning(f"解析target config失败: {e}")
    
    # 回退到target.name
    return target.name


def _docker_cli_exec(args):
    """通过 Docker CLI 执行命令并返回输出"""
    try:
        result = subprocess.run(
            ['docker'] + args,
            capture_output=True, text=True, timeout=30
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return -1, '', 'docker command not found'
    except subprocess.TimeoutExpired:
        return -2, '', 'docker command timed out'
    except Exception as e:
        return -3, '', str(e)


def find_docker_container(identifier):
    """根据标识符查找 Docker 容器（仅精确匹配名称、short_id 或完整 ID）。

    禁止使用 Docker ``name`` 过滤器的子串匹配：前端常用数字 target_id 调用
    ``/env/start/<id>``，子串匹配会命中无关容器，导致接口返回成功却未启动真实靶场。
    """
    if not identifier:
        return None

    client = get_docker_client()
    if not client:
        current_app.logger.warning(f"find_docker_container: Docker SDK 不可用, identifier={identifier}")
        return None

    ident_raw = str(identifier).strip()
    ident_norm = ident_raw.lstrip('/')

    try:
        for cand in (ident_raw, ident_norm, f'/{ident_norm}'):
            try:
                container = client.containers.get(cand)
                current_app.logger.info(f"find_docker_container: SDK get('{cand}') 成功, name={container.name}")
                return container
            except docker.errors.NotFound:
                pass
            except Exception:
                pass

        for c in client.containers.list(all=True):
            cname = (c.name or '').lstrip('/')
            if cname == ident_norm:
                current_app.logger.info(f"find_docker_container: 遍历匹配 name='{cname}' 成功")
                return c
            if c.short_id == ident_norm:
                current_app.logger.info(f"find_docker_container: 遍历匹配 short_id='{c.short_id}' 成功")
                return c
            if c.id == ident_raw or c.id == ident_norm:
                current_app.logger.info(f"find_docker_container: 遍历匹配 id 成功")
                return c

        current_app.logger.warning(f"find_docker_container: 未找到匹配容器 '{ident_raw}', "
                                   f"现有容器: {[c.name for c in client.containers.list(all=True)]}")
    except Exception as e:
        current_app.logger.warning(f"find_docker_container: SDK 查找失败: {e}")

    return None


def docker_container_start_cli(container_name):
    """通过 Docker CLI 启动容器（SDK 失败时的备选方案）"""
    rc, out, err = _docker_cli_exec(['start', container_name])
    if rc == 0:
        current_app.logger.info(f"docker CLI start 成功: {container_name}")
        return True, out
    else:
        current_app.logger.warning(f"docker CLI start 失败: {container_name}, err={err}")
        return False, err


def docker_container_stop_cli(container_name):
    """通过 Docker CLI 停止容器（SDK 失败时的备选方案）"""
    rc, out, err = _docker_cli_exec(['stop', '--time=10', container_name])
    if rc == 0:
        current_app.logger.info(f"docker CLI stop 成功: {container_name}")
        return True, out
    else:
        current_app.logger.warning(f"docker CLI stop 失败: {container_name}, err={err}")
        return False, err


def find_available_port(start_port=8080, max_attempts=100):
    """查找可用端口"""
    for port in range(start_port, start_port + max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result != 0:  # 端口可用
                return port
        except:
            pass
    return None


def parse_port(port_str, default_host=8080, default_container=80):
    """解析端口字符串"""
    host_port = default_host
    container_port = default_container
    
    if not port_str:
        return host_port, container_port
    
    if ':' in str(port_str):
        parts = str(port_str).split(':')
        try:
            host_port = int(parts[0])
            container_port = int(parts[1])
        except (ValueError, IndexError):
            pass
    else:
        try:
            host_port = int(port_str)
        except ValueError:
            pass
    
    return host_port, container_port


# ==================== 环境管理兼容路由 /api/env/... ====================

@compat_bp.route('/env/list', methods=['GET'])
def compat_env_list():
    """获取环境列表 - 以Docker为准，自动与数据库双向同步"""
    try:
        client = get_docker_client()
        prefix_legacy = 'target_'
        prefix_range = (DOCKER_CONFIG.get('container_prefix') or 'cyber_range_')

        # Docker不可用时降级返回DB数据，不做任何删除
        if not client:
            current_app.logger.warning("Docker不可用，降级返回数据库记录")
            targets = Target.list_all()
            return jsonify({
                'status': 'success',
                'containers': [t.to_dict() for t in targets],
                'docker_unavailable': True
            }), 200

        # 1. 读取Docker中所有属于本系统的容器
        docker_containers = {}   # raw_name -> container
        try:
            for c in client.containers.list(all=True):
                raw_name = (c.name or '').lstrip('/')
                if raw_name.startswith(prefix_legacy) or raw_name.startswith(prefix_range):
                    docker_containers[raw_name] = c
        except Exception as e:
            current_app.logger.error(f"获取Docker容器列表失败: {e}")

        docker_names = set(docker_containers.keys())

        # 2. 构建DB记录映射（name -> target）
        all_targets = Target.list_all()
        db_by_name = {}
        for t in all_targets:
            cfg_name = (get_container_name_from_target(t) or '').lstrip('/')
            key = cfg_name or (t.name or '').lstrip('/')
            if key:
                db_by_name[key] = t

        # 3. 清理DB中Docker已不存在的孤立记录
        for name, t in list(db_by_name.items()):
            if name not in docker_names:
                current_app.logger.info(f"自动清理孤立DB记录（Docker已无此容器）: {name}")
                try:
                    t.delete()
                except Exception as e:
                    current_app.logger.warning(f"清理DB记录失败: {e}")

        # 4. 以Docker容器为基准构建列表，并补录DB中没有记录的容器
        containers = []
        for raw_name, container in docker_containers.items():
            # 解析端口
            ports = ''
            host_port = None
            container_port = None
            if container.ports:
                port_list = []
                for k, v in container.ports.items():
                    if v:
                        port_list.append(f"{v[0]['HostPort']}:{k}")
                        if host_port is None:
                            host_port = int(v[0]['HostPort'])
                            container_port = int(k.split('/')[0])
                ports = ', '.join(port_list)

            image = container.image.tags[0] if container.image.tags else container.image.short_id

            # 格式化创建时间
            created_raw = (container.attrs or {}).get('Created', '')
            created = created_raw[:19].replace('T', ' ') if created_raw else ''

            db_target = db_by_name.get(raw_name)

            if db_target:
                # 同步Docker状态到DB
                if db_target.status != container.status:
                    db_target.status = container.status
                    try:
                        db_target.save()
                    except Exception:
                        pass
                info = {
                    'target_id': db_target.target_id,
                    'name': raw_name,
                    'image': image,
                    'status': container.status,
                    'ports': ports,
                    'created': db_target.created_at or created,
                    'docker_id': container.short_id,
                    'os': db_target.os or image,
                    'config': db_target.config,
                }
            else:
                # Docker有但DB没有 → 补录
                config = {
                    'image': image,
                    'container_name': raw_name,
                    'docker_id': container.short_id,
                    'host_port': host_port,
                    'container_port': container_port,
                }
                new_target = Target(
                    name=raw_name,
                    type='docker',
                    port=f'{host_port}:{container_port}' if host_port else '',
                    os=image,
                    status=container.status,
                    config=json.dumps(config)
                )
                try:
                    new_target.save()
                except Exception as e:
                    current_app.logger.warning(f"补录DB记录失败: {e}")
                info = {
                    'target_id': new_target.target_id,
                    'name': raw_name,
                    'image': image,
                    'status': container.status,
                    'ports': ports,
                    'created': created,
                    'docker_id': container.short_id,
                    'os': image,
                    'config': json.dumps(config),
                }

            containers.append(info)

        return jsonify({
            'status': 'success',
            'containers': containers
        }), 200

    except Exception as e:
        current_app.logger.error(f"获取环境列表失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取环境列表失败'}), 500


@compat_bp.route('/env/create', methods=['POST'])
def compat_env_create():
    """创建环境（兼容前端）"""
    try:
        data = request.get_json() or {}
        
        # 参数验证
        image = data.get('image', 'nginx')
        if not image:
            return jsonify({'status': 'error', 'msg': '镜像名称不能为空'}), 400
        
        port_str = data.get('port', '8080:80')
        custom_name = data.get('name', '')
        
        # 生成容器名称
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        if custom_name:
            clean_name = sanitize_container_name(custom_name)
            name = f'target_{clean_name}_{ts}'
        else:
            base_name = image.split(':')[0].replace('/', '_')
            clean_base = sanitize_container_name(base_name)
            name = f'target_{clean_base}_{ts}'
        
        # 解析端口
        host_port, container_port = parse_port(port_str)
        
        # 检查端口可用性
        if not find_available_port(host_port, 1):
            host_port = find_available_port(host_port)
            if not host_port:
                return jsonify({'status': 'error', 'msg': '无法找到可用端口'}), 500
        
        # 创建Docker容器
        client = get_docker_client()
        if not client:
            return jsonify({'status': 'error', 'msg': '无法连接到Docker服务，请确保Docker Desktop已启动'}), 503
        
        port_bindings = {f'{container_port}/tcp': ('127.0.0.1', host_port)}
        
        current_app.logger.info(f"创建容器: name={name}, image={image}, ports={port_bindings}")
        
        try:
            container = client.containers.run(
                image,
                name=name,
                detach=True,
                ports=port_bindings,
                remove=False
            )
        except docker.errors.ImageNotFound:
            return jsonify({'status': 'error', 'msg': f'镜像 {image} 不存在，请先执行: docker pull {image}'}), 400
        except docker.errors.APIError as e:
            err_str = str(e)
            if 'port is already allocated' in err_str.lower() or 'address already in use' in err_str.lower() or 'bind:' in err_str.lower():
                return jsonify({'status': 'error', 'msg': f'端口 {host_port} 已被占用，请更换其他端口'}), 409
            return jsonify({'status': 'error', 'msg': f'Docker创建失败: {err_str}'}), 500

        # 保存到数据库
        config = {
            'image': image,
            'host_port': host_port,
            'container_port': container_port,
            'container_id': container.id,
            'container_name': name
        }
        
        target = Target(
            name=name,
            type='docker',
            port=f'{host_port}:{container_port}',
            os=image,
            status='running',
            config=json.dumps(config)
        )
        target.save()
        
        user_id = get_current_user_id()
        Log.create('success', 'target', f'靶场创建成功: {name}', user_id=user_id)
        
        return jsonify({
            'status': 'success',
            'container_id': container.short_id,
            'name': name,
            'port': host_port,
            'image': image,
            'container_port': container_port
        }), 201
        
    except docker.errors.APIError as e:
        current_app.logger.error(f"Docker API错误: {e}")
        return jsonify({'status': 'error', 'msg': f'Docker错误: {str(e)}'}), 500
    except Exception as e:
        current_app.logger.error(f"创建环境失败: {e}")
        return jsonify({'status': 'error', 'msg': f'创建环境失败: {str(e)}'}), 500


@compat_bp.route('/env/<target_id>', methods=['GET'])
def compat_env_get(target_id):
    """获取环境详情（兼容前端）"""
    try:
        target = find_target_by_id(target_id)
        
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
        
        if not data:
            return jsonify({'status': 'error', 'msg': '请求数据不能为空'}), 400
        
        target = find_target_by_id(target_id)
        
        if not target:
            return jsonify({'status': 'error', 'msg': '环境不存在'}), 404
        
        # 更新字段
        update_fields = {}
        if 'name' in data:
            update_fields['name'] = data['name']
        if 'description' in data:
            update_fields['description'] = data['description']
        if 'type' in data:
            update_fields['type'] = data['type']
        if 'config' in data:
            update_fields['config'] = data['config']
        if 'status' in data:
            update_fields['status'] = data['status']
        
        if update_fields:
            success = target.update(**update_fields)
            if not success:
                return jsonify({'status': 'error', 'msg': '更新环境失败'}), 500
        
        user_id = get_current_user_id()
        Log.create('info', 'target', f'更新环境: {target.name}', user_id=user_id)
        
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
        user_id = get_current_user_id()
        
        # 1. 查找数据库记录
        target = find_target_by_id(target_id)
        
        # 2. 查找Docker容器
        container = None
        if target:
            container_name = get_container_name_from_target(target)
            container = find_docker_container(container_name)

        if not container:
            container = find_docker_container(target_id)

        # 4. 删除Docker容器
        docker_deleted = False
        container_name_for_log = target_id
        
        if container:
            container_name_for_log = container.name
            try:
                container.stop(timeout=5)
                current_app.logger.info(f"容器已停止: {container.name}")
            except Exception as e:
                current_app.logger.warning(f"停止容器失败: {e}")
            
            try:
                container.remove(force=True)
                docker_deleted = True
                current_app.logger.info(f"Docker容器已删除: {container.name}")
            except Exception as e:
                current_app.logger.warning(f"删除Docker容器失败: {e}")
        
        # 5. 删除数据库记录
        db_deleted = False
        if target:
            try:
                target.delete()
                db_deleted = True
                current_app.logger.info(f"数据库记录已删除: {target.name}")
            except Exception as e:
                current_app.logger.error(f"删除数据库记录失败: {e}")
        
        if db_deleted or docker_deleted:
            Log.create('info', 'target', f'删除环境: {container_name_for_log}', user_id=user_id)
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


@compat_bp.route('/env/start/<target_id>', methods=['POST'])
def compat_env_start(target_id):
    """启动环境（兼容前端）"""
    try:
        user_id = get_current_user_id()
        log_tag = f"start_target({target_id})"
        current_app.logger.info(f"[{log_tag}] 开始执行")
        
        # 1. 查找数据库记录
        target = find_target_by_id(target_id)
        current_app.logger.info(f"[{log_tag}] 查找数据库记录: {'FOUND' if target else 'NOT_FOUND'}"
                                f"{f' name={target.name}' if target else ''}")
        
        # 2. 查找Docker容器
        container = None
        container_name = None
        if target:
            container_name = get_container_name_from_target(target)
            current_app.logger.info(f"[{log_tag}] 从数据库获取容器名: {container_name}")
            if container_name:
                container = find_docker_container(container_name)
                current_app.logger.info(f"[{log_tag}] 按名查找容器: {'FOUND' if container else 'NOT_FOUND'}"
                                        f"{f' status={container.status}' if container else ''}")

        # ★【修复】始终尝试用 target_id 直接查找容器（不论 target 是否找到）
        if not container:
            current_app.logger.info(f"[{log_tag}] 尝试用 target_id 直接查找容器: {target_id}")
            container = find_docker_container(target_id)
            current_app.logger.info(f"[{log_tag}] target_id 查找: {'FOUND' if container else 'NOT_FOUND'}"
                                    f"{f' name={container.name} status={container.status}' if container else ''}")

        # 3. 如果容器不存在，尝试重新创建
        if not container and target and target.config:
            current_app.logger.info(f"[{log_tag}] 容器不存在，尝试重新创建")
            try:
                config = (json.loads(target.config) 
                         if isinstance(target.config, str) 
                         else target.config)
                
                image = config.get('image', 'nginx')
                host_port = config.get('host_port', 8080)
                container_port = config.get('container_port', 80)
                recreate_name = config.get('container_name', f'target_{target_id}')
                
                client = get_docker_client()
                if not client:
                    return jsonify({'status': 'error', 'msg': '无法连接到Docker服务'}), 503
                
                # 检查端口可用性
                if not find_available_port(host_port, 1):
                    host_port = find_available_port(host_port)
                    if not host_port:
                        return jsonify({'status': 'error', 'msg': '无法找到可用端口'}), 500
                
                port_bindings = {f'{container_port}/tcp': ('127.0.0.1', host_port)}
                
                new_container = client.containers.run(
                    image, 
                    name=recreate_name, 
                    detach=True,
                    ports=port_bindings, 
                    remove=False
                )
                container = new_container
                current_app.logger.info(f"[{log_tag}] 容器已重新创建: {new_container.name}")
                
                config['container_id'] = new_container.id
                target.config = json.dumps(config)
                target.save()
                
            except Exception as recreate_error:
                current_app.logger.error(f"[{log_tag}] 重新创建容器失败: {recreate_error}")
                return jsonify({'status': 'error', 'msg': f'容器不存在，重新创建失败: {str(recreate_error)}'}), 500
        
        if not container:
            current_app.logger.warning(f"[{log_tag}] 未找到任何 Docker 容器")
            return jsonify({'status': 'error', 'msg': f'未找到Docker容器: {target_id}'}), 404
        
        # 4. 检查当前状态
        try:
            container.reload()
        except:
            pass
        current_status = getattr(container, 'status', 'unknown')
        current_app.logger.info(f"[{log_tag}] 启动前容器状态: {current_status}")
        
        if current_status == 'running':
            current_app.logger.info(f"[{log_tag}] 容器已在运行中，仅更新数据库状态")
            if target:
                target.status = 'running'
                target.save()
            return jsonify({'status': 'success', 'container': container.name, 'note': 'already_running'}), 200
        
        # 5. 启动Docker容器（优先SDK，端口冲突自动重建，失败降级到CLI）
        try:
            container.start()
            current_app.logger.info(f"[{log_tag}] SDK start 成功: {container.name}")
        except docker.errors.APIError as api_err:
            err_str = str(api_err)
            is_port_conflict = ('port is already allocated' in err_str.lower() or
                                'address already in use' in err_str.lower() or
                                'bind:' in err_str.lower())
            if is_port_conflict and target and target.config:
                current_app.logger.warning(f"[{log_tag}] 端口冲突，尝试重建容器: {api_err}")
                try:
                    cfg = json.loads(target.config) if isinstance(target.config, str) else target.config
                    image = cfg.get('image') or (container.image.tags[0] if container.image.tags else None)
                    container_port = cfg.get('container_port', 80)
                    old_name = (container.name or '').lstrip('/')
                    if not image:
                        return jsonify({'status': 'error', 'msg': f'端口冲突且无法获取镜像信息: {err_str}'}), 500
                    new_host_port = find_available_port(8080)
                    if not new_host_port:
                        return jsonify({'status': 'error', 'msg': '端口全部占用，无法启动'}), 500
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass
                    docker_client = get_docker_client()
                    new_container = docker_client.containers.run(
                        image, name=old_name, detach=True,
                        ports={f'{container_port}/tcp': ('127.0.0.1', new_host_port)},
                        remove=False
                    )
                    container = new_container
                    cfg['host_port'] = new_host_port
                    target.port = f'{new_host_port}:{container_port}'
                    target.config = json.dumps(cfg)
                    target.status = 'running'
                    target.save()
                    current_app.logger.info(f"[{log_tag}] 端口冲突重建成功: {old_name}, 新端口: {new_host_port}")
                    Log.create('success', 'target', f'端口冲突重建: {old_name} (新端口 {new_host_port})', user_id=user_id)
                    return jsonify({'status': 'success', 'container': old_name, 'port': new_host_port, 'note': 'port_conflict_recreated'}), 200
                except Exception as recreate_err:
                    current_app.logger.error(f"[{log_tag}] 重建容器失败: {recreate_err}")
                    return jsonify({'status': 'error', 'msg': f'端口冲突，重建失败: {str(recreate_err)}'}), 500
            else:
                current_app.logger.error(f"[{log_tag}] Docker API 错误: {api_err}")
                return jsonify({'status': 'error', 'msg': f'Docker容器启动失败: {err_str}'}), 500
        except Exception as sdk_err:
            current_app.logger.warning(f"[{log_tag}] SDK start 失败，尝试 CLI 降级: {sdk_err}")
            container_cli_name = (container.name or '').lstrip('/')
            cli_ok, cli_msg = docker_container_start_cli(container_cli_name)
            if not cli_ok:
                current_app.logger.error(f"[{log_tag}] CLI start 也失败: {cli_msg}")
                return jsonify({'status': 'error', 'msg': f'Docker容器启动失败: {str(sdk_err)} (CLI: {cli_msg})'}), 500
            current_app.logger.info(f"[{log_tag}] CLI start 成功")
        
        # 验证启动结果
        time.sleep(1)
        try:
            container.reload()
        except:
            pass
        final_status = getattr(container, 'status', 'unknown')
        current_app.logger.info(f"[{log_tag}] 启动后容器状态: {final_status}")
        
        # 6. 更新数据库状态
        if not target:
            target = find_target_by_id((container.name or '').lstrip('/'))
        
        if target:
            target.status = 'running'
            target.save()
            current_app.logger.info(f"[{log_tag}] 数据库状态已更新为 running: {target.name}")
        else:
            current_app.logger.warning(f"[{log_tag}] 未找到对应的数据库记录: {container.name}")
        
        Log.create('success', 'target', f'启动环境: {container.name} (状态: {final_status})', user_id=user_id)
        
        return jsonify({'status': 'success', 'container': container.name, 'final_status': final_status}), 200
    
    except Exception as e:
        current_app.logger.error(f"启动环境失败: {e}")
        return jsonify({'status': 'error', 'msg': '启动环境失败'}), 500


@compat_bp.route('/env/stop/<target_id>', methods=['POST'])
def compat_env_stop(target_id):
    """停止环境（兼容前端）"""
    try:
        user_id = get_current_user_id()
        log_tag = f"stop_target({target_id})"
        current_app.logger.info(f"[{log_tag}] 开始执行")
        
        # 1. 查找数据库记录
        target = find_target_by_id(target_id)
        current_app.logger.info(f"[{log_tag}] 查找数据库记录: {'FOUND' if target else 'NOT_FOUND'}"
                                f"{f' name={target.name}' if target else ''}")
        
        # 2. 查找Docker容器
        container = None
        if target:
            container_name = get_container_name_from_target(target)
            current_app.logger.info(f"[{log_tag}] 从数据库获取容器名: {container_name}")
            if container_name:
                container = find_docker_container(container_name)
                current_app.logger.info(f"[{log_tag}] 按名查找容器: {'FOUND' if container else 'NOT_FOUND'}")

        # ★【修复】始终尝试用 target_id 直接查找
        if not container:
            current_app.logger.info(f"[{log_tag}] 尝试用 target_id 直接查找: {target_id}")
            container = find_docker_container(target_id)
            current_app.logger.info(f"[{log_tag}] target_id 查找: {'FOUND' if container else 'NOT_FOUND'}")

        if not container:
            current_app.logger.warning(f"[{log_tag}] 未找到 Docker 容器")
            return jsonify({'status': 'error', 'msg': f'未找到Docker容器: {target_id}'}), 404

        # 3. 检查当前状态
        try:
            container.reload()
        except:
            pass
        current_status = getattr(container, 'status', 'unknown')
        current_app.logger.info(f"[{log_tag}] 停止前容器状态: {current_status}")
        
        if current_status in ('exited', 'stopped'):
            current_app.logger.info(f"[{log_tag}] 容器已停止，仅更新数据库")
            if target:
                target.status = 'stopped'
                target.save()
            return jsonify({'status': 'success', 'container': container.name, 'note': 'already_stopped'}), 200

        # 4. 停止Docker容器（优先SDK，失败降级到CLI）
        try:
            container.stop(timeout=10)
            current_app.logger.info(f"[{log_tag}] SDK stop 成功: {container.name}")
        except Exception as sdk_err:
            current_app.logger.warning(f"[{log_tag}] SDK stop 失败，尝试 CLI 降级: {sdk_err}")
            container_cli_name = (container.name or '').lstrip('/')
            cli_ok, cli_msg = docker_container_stop_cli(container_cli_name)
            if not cli_ok:
                current_app.logger.error(f"[{log_tag}] CLI stop 也失败: {cli_msg}")
                return jsonify({'status': 'error', 'msg': f'Docker容器停止失败: {str(sdk_err)}'}), 500
            current_app.logger.info(f"[{log_tag}] CLI stop 成功")
        
        # 验证停止结果
        time.sleep(1)
        try:
            container.reload()
        except:
            pass
        final_status = getattr(container, 'status', 'unknown')
        current_app.logger.info(f"[{log_tag}] 停止后容器状态: {final_status}")
        
        # 5. 更新数据库状态
        if not target:
            all_targets = Target.list_all()
            for t in all_targets:
                if t.name == container.name:
                    target = t
                    break
        
        if target:
            target.status = 'stopped'
            target.save()
            current_app.logger.info(f"[{log_tag}] 数据库状态已更新为 stopped: {target.name}")
        else:
            current_app.logger.warning(f"[{log_tag}] 未找到对应的数据库记录: {container.name}")
        
        Log.create('info', 'target', f'停止环境: {container.name} (状态: {final_status})', user_id=user_id)
        
        return jsonify({'status': 'success', 'container': container.name, 'final_status': final_status}), 200
    
    except Exception as e:
        current_app.logger.error(f"停止环境失败: {e}")
        return jsonify({'status': 'error', 'msg': '停止环境失败'}), 500


@compat_bp.route('/env/stats', methods=['GET'])
def compat_env_stats():
    """获取环境统计 - 以Docker为准"""
    try:
        client = get_docker_client()
        prefix_legacy = 'target_'
        prefix_range = (DOCKER_CONFIG.get('container_prefix') or 'cyber_range_')

        if client:
            try:
                all_containers = [
                    c for c in client.containers.list(all=True)
                    if (c.name or '').lstrip('/').startswith(prefix_legacy)
                    or (c.name or '').lstrip('/').startswith(prefix_range)
                ]
                stats = {
                    'total': len(all_containers),
                    'running': sum(1 for c in all_containers if c.status == 'running'),
                    'stopped': sum(1 for c in all_containers if c.status in ('exited', 'stopped', 'created')),
                    'error': sum(1 for c in all_containers if c.status not in ('running', 'exited', 'stopped', 'created')),
                }
                return jsonify({'status': 'success', 'data': stats}), 200
            except Exception as e:
                current_app.logger.warning(f"Docker统计失败，降级使用DB: {e}")

        # 降级：Docker不可用时从DB读
        targets = Target.list_all()
        stats = {
            'total': len(targets),
            'running': len([t for t in targets if t.status == 'running']),
            'stopped': len([t for t in targets if t.status in ('stopped', 'exited')]),
            'error': len([t for t in targets if t.status == 'error']),
        }
        return jsonify({'status': 'success', 'data': stats}), 200

    except Exception as e:
        current_app.logger.error(f"获取环境统计失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取环境统计失败'}), 500


# ==================== 攻击管理兼容路由 /api/attack/... ====================

@compat_bp.route('/attack/list', methods=['GET'])
def compat_attack_list():
    """获取攻击列表（兼容前端）"""
    try:
        user_id = get_current_user_id()
        attacks = Attack.list_all(str(user_id))
        
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
        
        if not data:
            return jsonify({'status': 'error', 'msg': '请求数据不能为空'}), 400
        
        user_id = get_current_user_id()
        
        attack = Attack.create(
            name=data.get('name', '未命名攻击'),
            attack_type=data.get('attack_type', 'SQL注入'),
            target=data.get('target', 'localhost'),
            port=data.get('port', '80'),
            intensity=data.get('intensity', 5),
            user_id=str(user_id)
        )
        
        if not attack:
            return jsonify({'status': 'error', 'msg': '创建攻击失败'}), 500
        
        # 记录日志
        Log.create('info', 'attack', f'创建攻击: {attack.name}', user_id=user_id)
        
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
