# -*- coding: utf-8 -*-
"""
端口修复脚本 - 根据 Docker 容器实际端口映射，回填数据库中缺失的 port 字段

用法:
    cd backend && python scripts/fix_ports.py

功能:
    1. 遍历数据库中 port 字段为空或 '-' 的靶场记录
    2. 根据 container_name 查找对应的 Docker 容器
    3. 读取容器的实际端口映射
    4. 更新数据库中的 port 字段
"""

import sys
import json
from pathlib import Path

# 添加 backend 目录到路径
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import docker
from models.target import Target
from services.database import db_service


def get_container_ports(container):
    """获取容器的端口映射列表 [(host_port, container_port), ...]"""
    ports = []
    if container.ports:
        for container_port, host_bindings in container.ports.items():
            if host_bindings:
                for binding in host_bindings:
                    hp = binding.get('HostPort', '')
                    cp = container_port.split('/')[0]
                    if hp:
                        ports.append((hp, cp))
    return ports


def fix_missing_ports():
    """修复数据库中缺失端口的靶场记录"""
    print("=" * 60)
    print("靶场端口修复工具")
    print("=" * 60)

    try:
        docker_client = docker.from_env()
    except Exception as e:
        print(f"[错误] Docker 连接失败: {e}")
        return

    targets = Target.list_all()
    fixed = 0
    skipped = 0
    failed = 0

    for target in targets:
        # 检查 port 是否为空或无效
        current_port = target.port or ''
        if current_port and current_port != '-' and ':' in current_port:
            skipped += 1
            continue

        print(f"\n[处理] target_id={target.target_id}, name={target.name}")
        print(f"       当前 port='{current_port}'")

        # 从 config 中获取容器名
        container_name = None
        if target.config:
            try:
                cfg = json.loads(target.config) if isinstance(target.config, str) else target.config
                container_name = cfg.get('container_name')
            except:
                pass

        if not container_name:
            print(f"       [跳过] 无 container_name，无法定位 Docker 容器")
            failed += 1
            continue

        # 查找 Docker 容器
        try:
            container = docker_client.containers.get(container_name)
        except docker.errors.NotFound:
            # 尝试通过名称前缀查找
            found = False
            for c in docker_client.containers.list(all=True):
                if c.name == container_name or container_name in c.name:
                    container = c
                    found = True
                    break
            if not found:
                print(f"       [跳过] Docker 容器不存在: {container_name}")
                failed += 1
                continue

        # 获取实际端口映射
        ports = get_container_ports(container)
        if not ports:
            print(f"       [跳过] 容器无端口映射")
            failed += 1
            continue

        # 更新数据库（取第一个端口映射）
        host_port, container_port = ports[0]
        new_port = f"{host_port}:{container_port}"

        try:
            target.port = new_port
            target.status = container.status
            target.save()

            # 同时更新 config 中的 host_port/container_port
            if target.config:
                try:
                    cfg = json.loads(target.config) if isinstance(target.config, str) else target.config
                    cfg['host_port'] = int(host_port)
                    cfg['container_port'] = int(container_port)
                    target.config = json.dumps(cfg)
                    target.save()
                except:
                    pass

            print(f"       [修复] port → '{new_port}', status={container.status}")
            fixed += 1
        except Exception as e:
            print(f"       [失败] 更新数据库失败: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"修复完成: 修复 {fixed} 个, 跳过 {skipped} 个, 失败 {failed} 个")
    print("=" * 60)


if __name__ == '__main__':
    fix_missing_ports()
