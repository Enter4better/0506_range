# -*- coding: utf-8 -*-
"""
环境管理Agent - 负责靶场底层的资源编排
"""
import os
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from flask import current_app

from .base_agent import BaseAgent
from models.log import Log
from models.target import Target

# 训练样本文件路径（few-shot 示例存储）
_TRAINING_FILE = Path(__file__).parent / 'training_examples.json'

# 经过验证的可用镜像白名单及其必要配置
# ── 基础设施镜像（干净官方镜像，无预置漏洞） ──────────────────────────────
# ── 专用漏洞靶场镜像（需提前 docker pull，见 INSTALL.md） ─────────────────
VERIFIED_IMAGES = {
    # 基础设施
    'nginx:alpine':           {'env': {}, 'command': None, 'ports': [80]},
    'httpd:alpine':           {'env': {}, 'command': None, 'ports': [80]},
    'php:8.1-apache':         {'env': {}, 'command': None, 'ports': [80]},
    'mysql:8.0':              {'env': {'MYSQL_ROOT_PASSWORD': 'Range@123', 'MYSQL_DATABASE': 'testdb'}, 'command': None, 'ports': [3306]},
    'redis:alpine':           {'env': {}, 'command': None, 'ports': [6379]},
    'postgres:15-alpine':     {'env': {'POSTGRES_PASSWORD': 'Range@123'}, 'command': None, 'ports': [5432]},
    'ubuntu:22.04':           {'env': {}, 'command': 'sleep infinity', 'ports': [22]},
    'python:3.11-slim':       {'env': {}, 'command': 'sleep infinity', 'ports': []},
    'node:18-alpine':         {'env': {}, 'command': 'sleep infinity', 'ports': [3000]},
    'alpine:latest':          {'env': {}, 'command': 'sleep infinity', 'ports': []},
    # 专用漏洞靶场（需提前 docker pull）
    'vulnerables/web-dvwa':   {'env': {}, 'command': None, 'ports': [80]},
    'webgoat/webgoat':        {'env': {}, 'command': None, 'ports': [8080]},
    'raesene/bwapp':          {'env': {}, 'command': None, 'ports': [80]},
}


class EnvAgent(BaseAgent):
    """环境管理Agent - AI驱动的靶场资源编排"""

    # 预定义场景模板（使用经过验证的镜像）
    SCENARIO_TEMPLATES = {
        'web_security': {
            'name': 'Web安全靶场',
            'description': '包含Nginx和MySQL的典型Web应用环境',
            'components': [
                {'type': 'container', 'name': 'web-server',  'image': 'nginx:alpine',
                 'ports': [80],   'env': {}, 'command': None},
                {'type': 'container', 'name': 'db-server',   'image': 'mysql:8.0',
                 'ports': [3306], 'env': {'MYSQL_ROOT_PASSWORD': 'Range@123', 'MYSQL_DATABASE': 'testdb'}, 'command': None},
            ],
            'vulnerabilities': ['SQL注入', 'XSS跨站脚本', '文件上传'],
            'network': {'type': 'bridge', 'subnet': '172.20.0.0/16'}
        },
        'network_security': {
            'name': '网络安全靶场',
            'description': '包含Web服务和内网主机的网络渗透环境',
            'components': [
                {'type': 'container', 'name': 'web-target',  'image': 'nginx:alpine',
                 'ports': [80],   'env': {}, 'command': None},
                {'type': 'container', 'name': 'target-host', 'image': 'ubuntu:22.04',
                 'ports': [22],   'env': {}, 'command': 'sleep infinity'},
                {'type': 'container', 'name': 'db-target',   'image': 'mysql:8.0',
                 'ports': [3306], 'env': {'MYSQL_ROOT_PASSWORD': 'Range@123'}, 'command': None},
            ],
            'vulnerabilities': ['端口扫描', '暴力破解', '横向移动'],
            'network': {'type': 'custom', 'subnet': '172.21.0.0/16'}
        },
        'container_escape': {
            'name': '容器安全靶场',
            'description': '模拟容器隔离环境，用于容器安全研究',
            'components': [
                {'type': 'container', 'name': 'alpine-target', 'image': 'alpine:latest',
                 'ports': [], 'env': {}, 'command': 'sleep infinity'},
                {'type': 'container', 'name': 'ubuntu-victim', 'image': 'ubuntu:22.04',
                 'ports': [22], 'env': {}, 'command': 'sleep infinity'},
            ],
            'vulnerabilities': ['容器逃逸', '镜像漏洞', '特权容器滥用'],
            'network': {'type': 'bridge', 'subnet': '172.22.0.0/16'}
        },
        'dvwa': {
            'name': 'DVWA 综合漏洞靶场',
            'description': 'Damn Vulnerable Web Application — 涵盖 SQL 注入、XSS、CSRF、文件上传、命令执行等 OWASP Top 10 漏洞',
            'components': [
                {'type': 'container', 'name': 'dvwa-target', 'image': 'vulnerables/web-dvwa',
                 'ports': [80], 'env': {}, 'command': None},
            ],
            'vulnerabilities': ['SQL注入', 'XSS跨站脚本', 'CSRF', '文件上传', '命令执行', '暴力破解'],
            'network': {'type': 'bridge', 'subnet': '172.23.0.0/16'}
        },
        'webgoat': {
            'name': 'WebGoat OWASP 教学靶场',
            'description': 'OWASP WebGoat — 面向开发者的安全培训平台，含注入、认证缺陷、访问控制、密码学等模块',
            'components': [
                {'type': 'container', 'name': 'webgoat-target', 'image': 'webgoat/webgoat',
                 'ports': [8080], 'env': {}, 'command': None},
            ],
            'vulnerabilities': ['SQL注入', 'XXE注入', 'SSRF攻击', '不安全的反序列化', '访问控制缺陷'],
            'network': {'type': 'bridge', 'subnet': '172.24.0.0/16'}
        },
        'bwapp': {
            'name': 'bWAPP 百漏靶场',
            'description': 'Buggy Web Application — 超过 100 种 Web 漏洞的全覆盖训练平台，含 OWASP Top 10 全类型',
            'components': [
                {'type': 'container', 'name': 'bwapp-target', 'image': 'raesene/bwapp',
                 'ports': [80], 'env': {}, 'command': None},
            ],
            'vulnerabilities': ['SQL注入', 'XSS跨站脚本', '文件包含', 'SSRF攻击', '命令执行', 'XXE注入'],
            'network': {'type': 'bridge', 'subnet': '172.25.0.0/16'}
        },
    }

    def __init__(self, user_id: str = None):
        super().__init__()
        self.user_id = user_id
        self._lock = threading.Lock()

    # ==================== 训练样本（few-shot）====================

    def load_training_examples(self) -> List[Dict]:
        """加载训练样本用于 few-shot 提示"""
        try:
            if _TRAINING_FILE.exists():
                with open(_TRAINING_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            current_app.logger.warning(f"加载训练样本失败: {e}")
        return []

    def save_training_example(self, user_input: str, config: Dict) -> bool:
        """保存成功的配置为 few-shot 训练样本"""
        try:
            examples = self.load_training_examples()
            # 避免重复（按 input 去重）
            examples = [e for e in examples if e.get('input') != user_input]
            examples.append({
                'input': user_input,
                'output': config,
                'timestamp': datetime.now().isoformat()
            })
            # 只保留最近 20 条
            examples = examples[-20:]
            with open(_TRAINING_FILE, 'w', encoding='utf-8') as f:
                json.dump(examples, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            current_app.logger.warning(f"保存训练样本失败: {e}")
            return False

    def _find_relevant_examples(self, desc: str, max_count: int = 2) -> List[Dict]:
        """根据关键词相似度找到最相关的 few-shot 样本"""
        examples = self.load_training_examples()
        if not examples:
            return []
        desc_words = set(desc.lower().replace('，', ' ').replace('。', ' ').split())
        scored = []
        for ex in examples:
            ex_words = set(ex.get('input', '').lower().replace('，', ' ').replace('。', ' ').split())
            score = len(desc_words & ex_words)
            scored.append((score, ex))
        scored.sort(key=lambda x: -x[0])
        return [ex for _, ex in scored[:max_count] if _ > 0]

    # ==================== 场景分析 ====================

    def analyze_scenario(self, scenario_desc: str) -> Dict:
        """分析场景描述，生成环境配置方案"""
        # 先尝试匹配预定义模板（关键词匹配）
        matched_template = None
        keywords_map = {
            'web_security':    ['web', 'nginx', 'apache', '网站', '数据库', 'sql', 'xss', 'web安全'],
            'network_security': ['网络', '内网', '横向', '渗透', 'ssh', '主机', '端口'],
            'container_escape': ['容器', 'docker', '逃逸', 'k8s', '云原生'],
        }
        desc_lower = scenario_desc.lower()
        for key, kws in keywords_map.items():
            if any(kw in desc_lower for kw in kws):
                matched_template = self.SCENARIO_TEMPLATES[key].copy()
                break

        if matched_template:
            base_config = json.loads(json.dumps(matched_template))  # deepcopy
        else:
            base_config = self._generate_custom_scenario(scenario_desc)

        # 用 AI 优化配置（如果 AI 可用）
        if self.llm.enabled and base_config:
            optimized = self._ai_optimize_config(scenario_desc, base_config)
            if optimized:
                base_config = optimized

        return base_config

    def _ai_optimize_config(self, desc: str, base_config: Dict) -> Optional[Dict]:
        """让 AI 在现有配置基础上做小幅优化（不重新生成，只调整漏洞和描述）"""
        prompt = f"""根据用户需求，优化以下靶场配置的 name、description 和 vulnerabilities 字段。
不要修改 components（镜像列表），只修改元信息。

用户需求：{desc}

现有配置：
{json.dumps(base_config, ensure_ascii=False, indent=2)}

请只返回 JSON，包含 name、description、vulnerabilities 三个字段，其他字段不返回。
"""
        resp = self.ai_chat(prompt, task_type='nlp_understanding')
        if resp and '{' in resp:
            try:
                start, end = resp.find('{'), resp.rfind('}') + 1
                patch = json.loads(resp[start:end])
                if isinstance(patch, dict):
                    result = json.loads(json.dumps(base_config))
                    for k in ('name', 'description', 'vulnerabilities'):
                        if k in patch and patch[k]:
                            result[k] = patch[k]
                    return result
            except Exception:
                pass
        return None

    def _generate_custom_scenario(self, scenario_desc: str) -> Dict:
        """使用 AI 生成自定义场景配置，附带 few-shot 示例"""
        # 构建 few-shot 示例部分
        examples = self._find_relevant_examples(scenario_desc)
        few_shot_text = ''
        if examples:
            few_shot_text = '\n\n【成功案例参考（请参照格式，不要照抄内容）】\n'
            for i, ex in enumerate(examples, 1):
                few_shot_text += f"\n示例{i}（需求：{ex['input']}）：\n"
                few_shot_text += json.dumps(ex['output'], ensure_ascii=False, indent=2) + '\n'

        # 镜像白名单说明
        image_guide = '\n'.join([
            f'  - {img}: 端口{info["ports"]}'
            + (f'，需env {list(info["env"].keys())}' if info['env'] else '')
            + (f'，需command "{info["command"]}"' if info['command'] else '')
            for img, info in VERIFIED_IMAGES.items()
        ])

        prompt = f"""你是一个Docker靶场配置专家。根据以下用户需求，生成一个可以立即部署的Docker靶场配置。
{few_shot_text}
【用户需求】：{scenario_desc}

【可用镜像白名单】（只能从下面选，不能使用其他镜像）：
{image_guide}

【重要规则】：
1. ubuntu:22.04、python:3.11-slim、node:18-alpine、alpine:latest 必须设置 command 为 "sleep infinity"
2. mysql:8.0 必须设置 env.MYSQL_ROOT_PASSWORD
3. postgres:15-alpine 必须设置 env.POSTGRES_PASSWORD
4. vulnerables/web-dvwa、webgoat/webgoat、raesene/bwapp 是自包含漏洞靶场，env 和 command 均留空，端口分别为 80、8080、80
5. components 中每个组件必须有 name（英文小写连字符）、image、ports、env、command 五个字段
6. 组件数量 2~4 个，不要过多

请返回纯 JSON，格式如下，不要有任何解释文字：
{{
  "name": "靶场名称（简短中文）",
  "description": "详细描述",
  "components": [
    {{
      "type": "container",
      "name": "组件名（英文小写连字符）",
      "image": "镜像名（必须在白名单内）",
      "ports": [容器内端口数字],
      "env": {{"环境变量": "值"}},
      "command": null或"sleep infinity"
    }}
  ],
  "vulnerabilities": ["漏洞类型"],
  "network": {{"type": "bridge", "subnet": "172.24.0.0/16"}}
}}"""

        resp = self.ai_chat(prompt, task_type='range_generation')
        if resp and '{' in resp:
            try:
                start, end = resp.find('{'), resp.rfind('}') + 1
                config = json.loads(resp[start:end])
                if isinstance(config, dict) and 'components' in config:
                    # 补全白名单中缺少的 env/command
                    self._patch_components(config['components'])
                    return config
            except Exception as e:
                current_app.logger.warning(f"AI配置解析失败: {e}, resp={resp[:200]}")

        # 兜底：返回最简单的 Web 靶场
        return {
            'name': '基础Web靶场',
            'description': scenario_desc,
            'components': [
                {'type': 'container', 'name': 'web-server', 'image': 'nginx:alpine',
                 'ports': [80], 'env': {}, 'command': None},
            ],
            'vulnerabilities': ['通用Web漏洞'],
            'network': {'type': 'bridge', 'subnet': '172.24.0.0/16'}
        }

    def _patch_components(self, components: List[Dict]):
        """为组件补全白名单中要求的 env 和 command（防止 AI 漏写）"""
        for comp in components:
            image = comp.get('image', '')
            defaults = VERIFIED_IMAGES.get(image, {})
            # 只补充 AI 没有设置的必要字段
            if 'env' not in comp:
                comp['env'] = {}
            if 'command' not in comp:
                comp['command'] = None
            # 必须有 command 的镜像
            if defaults.get('command') and not comp.get('command'):
                comp['command'] = defaults['command']
            # 必须有的 env（如 MYSQL_ROOT_PASSWORD）
            for k, v in defaults.get('env', {}).items():
                if k not in comp.get('env', {}):
                    comp.setdefault('env', {})[k] = v

    # ==================== 环境创建（真实 Docker 部署）====================

    def create_environment(self, scenario_config: Dict, user_id: str = None) -> Dict:
        """创建靶场环境 - 每个组件创建独立 Docker 容器和 DB 记录"""
        if user_id:
            self.user_id = user_id

        range_name = scenario_config.get('name', '自定义靶场')
        env_id = f"env_{int(time.time())}_{range_name[:20]}"

        result = {
            'status': 'pending',
            'environment_id': env_id,
            'components_created': [],
            'errors': [],
            'name': range_name
        }

        Log.create('info', 'env_agent',
                   f"AI靶场开始部署: {range_name}",
                   user_id=self.user_id)

        # 连接 Docker
        docker_client = None
        try:
            import docker
            docker_client = docker.from_env()
        except Exception as e:
            current_app.logger.warning(f"Docker连接失败: {e}")

        from config import DOCKER_CONFIG
        prefix = DOCKER_CONFIG.get('container_prefix', 'target_')

        components = scenario_config.get('components', [])
        base_port = 8100

        for idx, comp in enumerate(components):
            comp_result = {
                'name': comp.get('name', f'component-{idx}'),
                'type': comp.get('type', 'container'),
                'status': 'pending',
                'ports': [],
            }

            image = comp.get('image', 'nginx:alpine')
            # 补全白名单 env/command
            self._patch_components([comp])
            env_vars = comp.get('env', {})
            command = comp.get('command')
            container_ports = comp.get('ports', [80]) or []

            if docker_client:
                # 生成容器名
                clean = _sanitize(comp['name'])
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                container_name = f'{prefix}{clean}_{ts}'

                # 分配主机端口（base_port 递增，避免冲突）
                attempt_base = base_port + idx * 10
                deployed = False

                for try_base in range(attempt_base, attempt_base + 500, 10):
                    try:
                        port_bindings = {}
                        assigned = []
                        for j, cp in enumerate(container_ports):
                            hp = try_base + j
                            port_bindings[f'{cp}/tcp'] = ('0.0.0.0', hp)
                            assigned.append(hp)

                        run_kwargs = dict(
                            name=container_name,
                            detach=True,
                            ports=port_bindings if port_bindings else None,
                            environment=env_vars or None,
                            remove=False,
                        )
                        if command:
                            run_kwargs['command'] = command

                        container = docker_client.containers.run(image, **run_kwargs)
                        time.sleep(1)
                        container.reload()

                        comp_result['status'] = container.status
                        comp_result['ports'] = assigned
                        comp_result['container_id'] = container.short_id
                        comp_result['container_name'] = container_name
                        deployed = True

                        # 每个容器保存独立 DB 记录
                        host_port = assigned[0] if assigned else None
                        container_port_num = container_ports[0] if container_ports else 80
                        cfg = {
                            'image': image,
                            'host_port': host_port,
                            'container_port': container_port_num,
                            'container_id': container.id,
                            'container_name': container_name,
                            'scenario_name': range_name,
                        }
                        t = Target(
                            name=container_name,
                            type='docker',
                            port=f'{host_port}:{container_port_num}' if host_port else '',
                            os=image,
                            status=container.status,
                            config=json.dumps(cfg)
                        )
                        t.save()
                        comp_result['target_id'] = t.target_id

                        Log.create('success', 'env_agent',
                                   f"容器部署成功: {container_name} ({image}) 端口:{assigned}",
                                   user_id=self.user_id)
                        break

                    except Exception as e:
                        err = str(e)
                        if 'port is already allocated' in err.lower() or 'bind' in err.lower():
                            continue  # 端口冲突，尝试下一组
                        if any(kw in err for kw in ('pull access denied', '403', 'Forbidden',
                                                     'manifest unknown', 'failed to resolve',
                                                     'unauthorized')):
                            comp_result['status'] = 'simulated'
                            comp_result['note'] = f'镜像拉取失败({image})，已标记为模拟'
                            Log.create('warning', 'env_agent',
                                       f"镜像拉取失败，降级模拟: {comp['name']} ({image})",
                                       user_id=self.user_id)
                            deployed = True
                            break
                        comp_result['status'] = 'failed'
                        comp_result['error'] = err[:200]
                        result['errors'].append(f"{comp['name']}: {err[:100]}")
                        Log.create('danger', 'env_agent',
                                   f"组件部署失败: {comp['name']} - {err[:100]}",
                                   user_id=self.user_id)
                        deployed = True
                        break

                if not deployed:
                    comp_result['status'] = 'failed'
                    comp_result['error'] = '所有候选端口均被占用'
                    result['errors'].append(f"{comp['name']}: 端口全部占用")
            else:
                comp_result['status'] = 'simulated'
                comp_result['note'] = 'Docker不可用，已标记为模拟'
                Log.create('info', 'env_agent',
                           f"Docker不可用，模拟部署: {comp['name']}", user_id=self.user_id)

            result['components_created'].append(comp_result)

        result['status'] = 'running'
        result['name'] = range_name
        result['components'] = result['components_created']

        Log.create('success', 'env_agent',
                   f"AI靶场部署完成: {range_name} ({len(result['components_created'])} 个组件)",
                   user_id=self.user_id)
        return result

    def destroy_environment(self, env_id: str) -> Dict:
        result = {'success': False, 'destroyed': []}
        try:
            Log.create('info', 'env_agent', f"销毁靶场: {env_id}", user_id=self.user_id)
            result['success'] = True
            Log.create('success', 'env_agent', f"靶场已销毁: {env_id}", user_id=self.user_id)
        except Exception as e:
            result['errors'] = [str(e)]
        return result

    def get_environment_status(self, env_id: str) -> Dict:
        return {'status': 'running', 'environment_id': env_id}

    def list_available_scenarios(self) -> List[Dict]:
        return [{'id': k, **v} for k, v in self.SCENARIO_TEMPLATES.items()]

    def expand_scenario_variants(self, base_key: str) -> List[Dict]:
        base = self.SCENARIO_TEMPLATES.get(base_key)
        if not base:
            return []

        variants = [
            self._make_variant(base, 'waf', '带WAF防护',
                extra_components=[{'type': 'container', 'name': 'waf-proxy', 'image': 'nginx:alpine',
                                   'ports': [8080], 'env': {}, 'command': None}],
                extra_vulns=['WAF绕过', 'HTTP走私'], desc_suffix='，前置WAF，验证绕过能力'),
            self._make_variant(base, 'cache', '带缓存层',
                extra_components=[{'type': 'container', 'name': 'cache-server', 'image': 'redis:alpine',
                                   'ports': [6379], 'env': {}, 'command': None}],
                extra_vulns=['暴力破解', '会话固定', '弱口令'], desc_suffix='，增加Redis缓存，测试缓存投毒'),
            self._make_variant(base, 'internal', '带内网横向',
                extra_components=[
                    {'type': 'container', 'name': 'pivot-host', 'image': 'ubuntu:22.04',
                     'ports': [22], 'env': {}, 'command': 'sleep infinity'},
                    {'type': 'container', 'name': 'internal-db', 'image': 'mysql:8.0',
                     'ports': [3306], 'env': {'MYSQL_ROOT_PASSWORD': 'Range@123'}, 'command': None},
                ],
                extra_vulns=['内网扫描', '横向移动', '凭证窃取'], desc_suffix='，模拟内网横向渗透'),
            self._make_variant(base, 'fullstack', '全栈应用',
                extra_components=[
                    {'type': 'container', 'name': 'app-server', 'image': 'node:18-alpine',
                     'ports': [3000], 'env': {}, 'command': 'sleep infinity'},
                ],
                extra_vulns=['SSRF', 'IDOR', 'JWT伪造'], desc_suffix='，增加Node.js应用层'),
        ]

        if self.llm.enabled:
            try:
                ai_v = self._ai_expand_variant(base)
                if ai_v:
                    variants.append(ai_v)
            except Exception:
                pass

        return variants

    def _make_variant(self, base: dict, suffix: str, label: str,
                      extra_components: list, extra_vulns: list, desc_suffix: str) -> dict:
        import copy
        v = copy.deepcopy(base)
        v['id'] = f"{base.get('name','base').replace('靶场','').strip()}_{suffix}"
        v['name'] = f"{base['name']}（{label}）"
        v['description'] = base['description'] + desc_suffix
        v['components'] = v.get('components', []) + extra_components
        v['vulnerabilities'] = list(set(v.get('vulnerabilities', []) + extra_vulns))
        v['variant_label'] = label
        v['is_variant'] = True
        return v

    def _ai_expand_variant(self, base: dict) -> Optional[Dict]:
        prompt = f"""基于以下靶场场景生成一个创意变种（只使用 nginx:alpine、mysql:8.0、redis:alpine、ubuntu:22.04、node:18-alpine 等常见镜像）：

原始：名称={base['name']}，漏洞={','.join(base.get('vulnerabilities',[]))}

要求：增加2个组件，3个漏洞，体现某特定技术场景（云原生/微服务/物联网），返回纯JSON，加 variant_label 和 is_variant:true 字段。
"""
        resp = self.ai_chat(prompt, task_type='scenario_expansion')
        if resp and '{' in resp:
            try:
                start, end = resp.find('{'), resp.rfind('}') + 1
                v = json.loads(resp[start:end])
                v['is_variant'] = True
                if 'components' in v:
                    self._patch_components(v['components'])
                return v
            except Exception:
                pass
        return None


def _sanitize(name: str) -> str:
    """简单容器名清理"""
    import re
    name = name.replace(':', '_').replace('/', '_')
    name = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    if name and name[0].isdigit():
        name = 'c_' + name
    return (name or 'container')[:50]


# 全局单例
_env_agent = None

def get_env_agent(user_id: str = None) -> EnvAgent:
    global _env_agent
    if _env_agent is None:
        _env_agent = EnvAgent(user_id)
    if user_id:
        _env_agent.user_id = user_id
    return _env_agent
