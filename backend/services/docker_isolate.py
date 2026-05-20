# -*- coding: utf-8 -*-
"""
Docker 容器网络隔离服务
当防御等级升至封禁级(>=4)时，真实断开靶场容器的 Docker 网络连接，
实现从"文本仿真"到"真实 Docker 操作"的防御动作落地。

设计原则：
- 降级安全：Docker 不可用时自动回退到原有文本记录，不影响演练流程
- 自动恢复：隔离后 AUTO_UNBLOCK_SECONDS 秒自动重连网络
- 可手动解封：通过 /api/defense/unblock 接口提前恢复
- 单例管理：全局 _blocked 字典追踪隔离状态，防止重复操作
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger('services.docker_isolate')

# 自动恢复时间（秒），训练场景下不宜永久断网
AUTO_UNBLOCK_SECONDS = 60

# 隔离状态表：{container_name: {'networks': [...], 'blocked_at': '...', 'port': int, 'attack_type': str}}
_blocked: dict = {}
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

def block_container_by_port(container_port: int, attack_type: str = '') -> dict:
    """
    通过容器内部端口找到对应的运行中靶场容器，断开其所有 Docker bridge 网络。

    参数:
        container_port: 容器暴露的内部端口（如 80、3306），与 Target.config.container_port 对应
        attack_type:    触发封禁的攻击类型（仅用于记录）

    返回:
        {'success': bool, 'container_name': str, 'message': str}
    """
    client = _get_docker_client()
    if not client:
        return {'success': False, 'container_name': '', 'message': 'Docker 客户端不可用，降级为文本记录'}

    container_name = _find_container_name_by_port(container_port)
    if not container_name:
        return {
            'success': False,
            'container_name': '',
            'message': f'未找到 container_port={container_port} 对应的运行中靶场容器'
        }

    with _lock:
        if container_name in _blocked:
            return {
                'success': True,
                'container_name': container_name,
                'message': f'容器 {container_name} 已处于网络隔离状态'
            }

    try:
        container = client.containers.get(container_name)
        container.reload()

        all_networks = list(container.attrs['NetworkSettings']['Networks'].keys())
        # 只断开 bridge 类网络，保留 host/none（否则容器可能崩溃）
        disconnectable = [n for n in all_networks if n not in ('host', 'none')]

        if not disconnectable:
            return {
                'success': False,
                'container_name': container_name,
                'message': f'容器 {container_name} 没有可断开的 bridge 网络'
            }

        for net_name in disconnectable:
            net = client.networks.get(net_name)
            net.disconnect(container, force=True)
            logger.info(f"[DockerIsolate] 已断开 {container_name} ← 网络 {net_name}")

        with _lock:
            _blocked[container_name] = {
                'networks': disconnectable,
                'blocked_at': datetime.now().isoformat(),
                'port': container_port,
                'attack_type': attack_type,
            }

        # 到期自动恢复（守护线程，进程退出不阻塞）
        t = threading.Timer(AUTO_UNBLOCK_SECONDS, unblock_container, args=[container_name])
        t.daemon = True
        t.start()

        logger.info(
            f"[DockerIsolate] 封禁成功: {container_name}，"
            f"断开网络 {disconnectable}，{AUTO_UNBLOCK_SECONDS}s 后自动恢复"
        )
        return {
            'success': True,
            'container_name': container_name,
            'message': (
                f'容器 {container_name} 已从网络隔离'
                f'（断开: {", ".join(disconnectable)}，{AUTO_UNBLOCK_SECONDS}s 后自动恢复）'
            )
        }

    except Exception as e:
        logger.error(f"[DockerIsolate] 封禁失败 container={container_name}: {e}")
        return {'success': False, 'container_name': container_name, 'message': str(e)}


def unblock_container(container_name: str) -> dict:
    """
    恢复被隔离容器的网络连接，重新加入隔离前的所有 bridge 网络。

    参数:
        container_name: 容器名称（与 _blocked 字典的键一致）

    返回:
        {'success': bool, 'message': str}
    """
    with _lock:
        state = _blocked.get(container_name)

    if not state:
        return {'success': False, 'message': f'容器 {container_name} 不在封禁列表中'}

    client = _get_docker_client()
    if not client:
        with _lock:
            _blocked.pop(container_name, None)
        return {'success': False, 'message': 'Docker 客户端不可用，已从封禁列表移除'}

    try:
        container = client.containers.get(container_name)
        restored = []
        failed = []

        for net_name in state['networks']:
            try:
                net = client.networks.get(net_name)
                net.connect(container)
                restored.append(net_name)
                logger.info(f"[DockerIsolate] 已恢复 {container_name} → 网络 {net_name}")
            except Exception as e:
                failed.append(net_name)
                logger.warning(f"[DockerIsolate] 恢复网络 {net_name} 失败: {e}")

        with _lock:
            _blocked.pop(container_name, None)

        if failed:
            return {
                'success': False,
                'message': f'部分网络恢复失败: {failed}（已恢复: {restored}）'
            }
        return {
            'success': True,
            'message': f'容器 {container_name} 网络已恢复: {restored}'
        }

    except Exception as e:
        logger.error(f"[DockerIsolate] 恢复失败 container={container_name}: {e}")
        with _lock:
            _blocked.pop(container_name, None)
        return {'success': False, 'message': str(e)}


def get_blocked_containers() -> list:
    """
    返回当前所有处于网络隔离状态的容器信息。

    返回:
        [{'container_name': str, 'networks': [...], 'blocked_at': str, 'port': int, 'attack_type': str}, ...]
    """
    with _lock:
        return [
            {'container_name': name, **state}
            for name, state in _blocked.items()
        ]


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

def _get_docker_client():
    """获取 Docker 客户端，失败时静默返回 None（降级保护）"""
    try:
        import docker
        return docker.from_env()
    except Exception as e:
        logger.warning(f"[DockerIsolate] Docker 客户端初始化失败: {e}")
        return None


def _find_container_name_by_port(container_port: int) -> Optional[str]:
    """
    查询数据库，找到 container_port 匹配且状态为 running 的靶场容器名。
    匹配逻辑：Target.config JSON 中 container_port 字段与参数相等。
    """
    try:
        db_path = Path(__file__).parent.parent / 'data' / 'ai_security_range.db'
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name, config FROM targets WHERE status = 'running'")
        rows = cur.fetchall()
        conn.close()

        for row in rows:
            try:
                cfg = json.loads(row['config'] or '{}')
                if cfg.get('container_port') == container_port:
                    # 优先用 config 里的 container_name，其次用 targets.name
                    return cfg.get('container_name') or row['name']
            except (json.JSONDecodeError, TypeError):
                continue

    except Exception as e:
        logger.warning(f"[DockerIsolate] 数据库查询失败: {e}")

    return None
