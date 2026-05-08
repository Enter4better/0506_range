# -*- coding: utf-8 -*-
"""
环境管理Agent - 负责靶场底层的资源编排
"""
import os
import json
import time
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from flask import current_app

from .base_agent import BaseAgent
from models.log import Log
from models.target import Target


class EnvAgent(BaseAgent):
    """环境管理Agent - AI驱动的靶场资源编排"""
    
    # 预定义场景模板
    SCENARIO_TEMPLATES = {
        'web_security': {
            'name': 'Web安全靶场',
            'description': '包含Web服务器、数据库的典型Web应用环境',
            'components': [
                {'type': 'container', 'name': 'web-server', 'image': 'nginx:latest', 'ports': [80, 443]},
                {'type': 'container', 'name': 'db-server', 'image': 'mysql:5.7', 'ports': [3306]},
            ],
            'vulnerabilities': ['SQL注入', 'XSS', '文件上传'],
            'network': {'type': 'bridge', 'subnet': '172.20.0.0/16'}
        },
        'network_security': {
            'name': '网络安全靶场',
            'description': '包含多种网络设备和服务的复杂网络环境',
            'components': [
                {'type': 'container', 'name': 'firewall', 'image': 'iptables-demo', 'ports': [22, 80]},
                {'type': 'container', 'name': 'ids', 'image': 'snort:latest', 'ports': [9090]},
                {'type': 'container', 'name': 'target-host', 'image': 'ubuntu:20.04', 'ports': [22, 80, 443]}
            ],
            'vulnerabilities': ['端口扫描', '暴力破解', '中间人攻击'],
            'network': {'type': 'custom', 'subnet': '172.21.0.0/16'}
        },
        'container_escape': {
            'name': '容器逃逸靶场',
            'description': '模拟容器环境，用于容器安全研究',
            'components': [
                {'type': 'container', 'name': 'docker-host', 'image': 'docker:dind', 'ports': [2375]},
                {'type': 'container', 'name': 'victim-container', 'image': 'alpine:latest', 'ports': [22]}
            ],
            'vulnerabilities': ['容器逃逸', '特权容器滥用', '镜像漏洞'],
            'network': {'type': 'bridge', 'subnet': '172.22.0.0/16'}
        }
    }
    
    def __init__(self, user_id: str = None):
        super().__init__()
        self.user_id = user_id
        self._lock = threading.Lock()
    
    def analyze_scenario(self, scenario_desc: str) -> Dict:
        """分析场景描述，生成环境配置方案"""
        # 首先尝试匹配预定义模板
        matched_template = None
        for key, template in self.SCENARIO_TEMPLATES.items():
            if any(keyword in scenario_desc.lower() for keyword in 
                   [key, template['name'], template['description']]):
                matched_template = template
                break
        
        if matched_template:
            base_config = matched_template.copy()
        else:
            # 使用 AI 生成自定义配置
            base_config = self._generate_custom_scenario(scenario_desc)
        
        # 使用 AI 优化配置
        if self.llm.enabled:
            optimization_prompt = f"""
作为环境管理Agent，请分析以下靶场场景需求并优化配置：

场景描述：{scenario_desc}

基础配置：
{json.dumps(base_config, ensure_ascii=False, indent=2)}

请从以下方面进行优化：
1. 资源分配合理性
2. 网络拓扑安全性
3. 漏洞配置真实性

请返回优化后的JSON配置，保持原有结构。
"""
            ai_response = self.ai_chat(optimization_prompt, task_type='range_generation')
            if ai_response:
                try:
                    optimized = json.loads(ai_response)
                    if isinstance(optimized, dict):
                        base_config.update(optimized)
                except:
                    pass
        
        return base_config
    
    def _generate_custom_scenario(self, scenario_desc: str) -> Dict:
        """使用 AI 生成自定义场景配置"""
        prompt = f"""
作为环境管理Agent，请根据以下场景描述生成靶场配置JSON：

场景描述：{scenario_desc}

请返回包含以下字段的JSON：
{{
    "name": "靶场名称",
    "description": "详细描述",
    "components": [
        {{"type": "container", "name": "服务名", "image": "镜像名", "ports": [端口列表]}}
    ],
    "vulnerabilities": ["漏洞类型列表"],
    "network": {{"type": "bridge", "subnet": "网段"}}
}}
"""
        ai_response = self.ai_chat(prompt, task_type='range_generation')
        if ai_response:
            try:
                config = json.loads(ai_response)
                if isinstance(config, dict) and 'components' in config:
                    return config
            except:
                pass
        
        return {
            'name': '自定义靶场',
            'description': scenario_desc,
            'components': [
                {'type': 'container', 'name': 'target-1', 'image': 'ubuntu:20.04', 'ports': [22, 80]}
            ],
            'vulnerabilities': ['通用漏洞'],
            'network': {'type': 'bridge', 'subnet': '172.24.0.0/16'}
        }
    
    def create_environment(self, scenario_config: Dict, user_id: str = None) -> Dict:
        """创建靶场环境 - 真正调用Docker部署容器"""
        if user_id:
            self.user_id = user_id
        
        # 从配置中提取靶场名称，优先使用AI生成的名称
        range_name = scenario_config.get('name', '自定义靶场')
        if range_name == '自定义靶场' and scenario_config.get('description'):
            # 如果名称为默认值，尝试从描述中提取有意义的名称
            desc = scenario_config['description']
            # 取描述前12个字符作为名称
            short_name = desc[:12].rstrip('，。、；：')
            if short_name:
                range_name = short_name + '靶场'
        
        env_id = f"env_{int(time.time())}_{range_name[:20]}"
        
        result = {
            'status': 'pending',
            'environment_id': env_id,
            'components_created': [],
            'errors': [],
            'name': range_name
        }
        
        try:
            
            Log.create('info', 'env_agent', 
                      f"环境管理Agent开始创建靶场: {scenario_config.get('name', '自定义靶场')}", 
                      user_id=self.user_id)
            
            # 尝试连接Docker
            docker_client = None
            try:
                import docker
                docker_client = docker.from_env()
            except Exception as e:
                current_app.logger.warning(f"Docker连接失败，将仅创建数据库记录: {e}")
            
            # 创建组件（Docker容器）
            components = scenario_config.get('components', [])
            for comp in components:
                comp_result = {
                    'name': comp.get('name', 'component'),
                    'type': comp.get('type', 'container'),
                    'status': 'pending',
                    'ports': []
                }

                if docker_client:
                    image = comp.get('image', 'nginx:latest')
                    container_ports = comp.get('ports', [80])
                    
                    # 生成容器名称
                    from routes.targets import sanitize_container_name
                    from config import DOCKER_CONFIG
                    clean_name = sanitize_container_name(comp['name'])
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    container_name = f'{DOCKER_CONFIG["container_prefix"]}{clean_name}_{ts}'
                    
                    # 为每个容器端口分配主机端口，从8100开始尝试
                    # 策略：为每个容器端口分配一个独立的主机端口，所有端口一起尝试
                    container_deployed = False
                    # 起始偏移量，每个容器端口分配不同的起始端口
                    base_port = 8100 + (len(result['components_created']) * 100)
                    
                    for attempt_base in range(base_port, 8950, 50):
                        if container_deployed:
                            break
                        try:
                            port_bindings = {}
                            assigned_ports = []
                            for idx, cp in enumerate(container_ports):
                                host_port = attempt_base + idx * 10
                                port_bindings[f'{cp}/tcp'] = ('127.0.0.1', host_port)
                                assigned_ports.append(host_port)
                            
                            # 运行容器（一次性传入所有端口映射）
                            container = docker_client.containers.run(
                                image,
                                name=container_name,
                                detach=True,
                                ports=port_bindings,
                                remove=False
                            )
                            
                            import time
                            time.sleep(1)
                            container.reload()
                            
                            comp_result['status'] = 'running'
                            comp_result['ports'] = assigned_ports
                            comp_result['container_id'] = container.short_id
                            comp_result['container_name'] = container_name
                            container_deployed = True
                            
                            Log.create('success', 'env_agent',
                                      f"Docker容器部署完成: {comp['name']} ({image}) 端口: {assigned_ports}",
                                      user_id=self.user_id)
                            
                        except Exception as port_err:
                            err_str = str(port_err)
                            # 端口冲突则尝试下一组端口
                            if 'port is already allocated' in err_str or 'bind' in err_str.lower():
                                continue
                            # 镜像拉取失败（403/网络问题）→ 降级为模拟模式
                            if ('403' in err_str or 'Forbidden' in err_str or
                                    'pull access denied' in err_str or
                                    'failed to resolve' in err_str or
                                    'manifest unknown' in err_str or
                                    'unauthorized' in err_str.lower()):
                                comp_result['status'] = 'simulated'
                                comp_result['ports'] = comp.get('ports', [])
                                comp_result['note'] = f'镜像拉取失败（{image}），已降级为模拟模式'
                                Log.create('warning', 'env_agent',
                                          f"镜像拉取失败，降级为模拟: {comp.get('name', 'component')} ({image}): {err_str[:120]}",
                                          user_id=self.user_id)
                                container_deployed = True
                                break
                            # 其他错误
                            comp_result['status'] = 'failed'
                            comp_result['error'] = err_str
                            result['errors'].append(f"{comp.get('name', 'component')}: {err_str}")
                            Log.create('danger', 'env_agent',
                                      f"组件部署失败: {comp.get('name', 'component')} - {err_str}",
                                      user_id=self.user_id)
                            container_deployed = True
                            break
                    
                    if not container_deployed:
                        comp_result['status'] = 'failed'
                        comp_result['error'] = '所有候选端口均被占用'
                        result['errors'].append(f"{comp['name']}: 所有候选端口均被占用")
                        Log.create('danger', 'env_agent',
                                  f"组件部署失败: {comp['name']} - 所有候选端口均被占用",
                                  user_id=self.user_id)
                else:
                    # 无Docker时仅记录
                    comp_result['status'] = 'simulated'
                    comp_result['ports'] = comp.get('ports', [])
                    Log.create('info', 'env_agent',
                              f"组件模拟部署: {comp['name']} (Docker不可用)",
                              user_id=self.user_id)
                
                result['components_created'].append(comp_result)
            
            # 创建靶场数据库记录
            all_ports = []
            for c in result['components_created']:
                for p in c.get('ports', []):
                    all_ports.append(str(p))
            
            target = Target(
                name=range_name,
                type='container',
                ip='127.0.0.1',
                port=','.join(all_ports) if all_ports else '8080',
                os='Linux',
                status='running',
                config=json.dumps(scenario_config)
            )
            target.save()
            
            if target.target_id:
                result['target_id'] = target.target_id
            
            result['status'] = 'running'
            result['name'] = range_name
            result['components'] = result['components_created']
            
            Log.create('success', 'env_agent', 
                      f"靶场环境创建完成: {env_id}", 
                      user_id=self.user_id)
            
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(str(e))
            Log.create('danger', 'env_agent', 
                      f"靶场环境创建失败: {str(e)}", 
                      user_id=self.user_id)
        
        return result
    
    def destroy_environment(self, env_id: str) -> Dict:
        """销毁靶场环境"""
        result = {'success': False, 'destroyed': []}
        
        try:
            Log.create('info', 'env_agent', 
                      f"开始销毁靶场环境: {env_id}", 
                      user_id=self.user_id)
            
            result['success'] = True
            Log.create('success', 'env_agent', 
                      f"靶场环境已销毁: {env_id}", 
                      user_id=self.user_id)
            
        except Exception as e:
            result['errors'] = [str(e)]
        
        return result
    
    def get_environment_status(self, env_id: str) -> Dict:
        """获取环境状态"""
        return {'status': 'running', 'environment_id': env_id}
    
    def list_available_scenarios(self) -> List[Dict]:
        """列出可用场景模板"""
        return [
            {'id': key, **template}
            for key, template in self.SCENARIO_TEMPLATES.items()
        ]

    def expand_scenario_variants(self, base_key: str) -> List[Dict]:
        """
        从基础场景自动扩展出多个变种（零代码）：
          WAF变种、登录防护变种、内网横向变种、域控变种
        若 AI 可用则让 AI 生成更多创意变种，否则使用规则模板。
        """
        base = self.SCENARIO_TEMPLATES.get(base_key)
        if not base:
            return []

        # 规则模板变种
        variants = [
            self._make_variant(base, 'waf', '带WAF防护',
                               extra_components=[{'type': 'container', 'name': 'waf', 'image': 'nginx:latest', 'ports': [8080]}],
                               extra_vulns=['WAF绕过', 'HTTP走私'],
                               desc_suffix='，前置部署WAF，验证规则绕过能力'),
            self._make_variant(base, 'login', '带登录认证',
                               extra_components=[{'type': 'container', 'name': 'auth-server', 'image': 'redis:alpine', 'ports': [6379]}],
                               extra_vulns=['暴力破解', '会话固定', '弱口令'],
                               desc_suffix='，增加登录认证环节，测试认证绕过'),
            self._make_variant(base, 'internal', '带内网横向',
                               extra_components=[
                                   {'type': 'container', 'name': 'pivot-host', 'image': 'ubuntu:20.04', 'ports': [22]},
                                   {'type': 'container', 'name': 'internal-db', 'image': 'mysql:5.7', 'ports': [3306]},
                               ],
                               extra_vulns=['内网扫描', '横向移动', '凭证窃取'],
                               desc_suffix='，模拟内网环境，验证横向渗透防御'),
            self._make_variant(base, 'domain', '带域控环境',
                               extra_components=[
                                   {'type': 'container', 'name': 'dc-server', 'image': 'ubuntu:20.04', 'ports': [389, 445, 88]},
                               ],
                               extra_vulns=['Pass-the-Hash', 'Kerberoasting', 'DCSync', '域提权'],
                               desc_suffix='，模拟域控环境，验证AD安全防护'),
        ]

        # 若 AI 可用，追加一个AI创意变种
        if self.llm.enabled:
            try:
                ai_variant = self._ai_expand_variant(base)
                if ai_variant:
                    variants.append(ai_variant)
            except Exception as e:
                pass

        return variants

    def _make_variant(self, base: dict, suffix: str, label: str,
                      extra_components: list, extra_vulns: list, desc_suffix: str) -> dict:
        import copy
        v = copy.deepcopy(base)
        v['id'] = f"{base.get('name', 'base').replace('靶场', '').strip()}_{suffix}"
        v['name'] = f"{base['name']}（{label}）"
        v['description'] = base['description'] + desc_suffix
        v['components'] = v.get('components', []) + extra_components
        v['vulnerabilities'] = list(set(v.get('vulnerabilities', []) + extra_vulns))
        v['variant_label'] = label
        v['is_variant'] = True
        return v

    def _ai_expand_variant(self, base: dict) -> dict:
        """让AI生成一个创意变种"""
        prompt = f"""基于以下网络安全靶场场景，生成一个有创意的变种靶场配置：

原始场景：
名称：{base['name']}
描述：{base['description']}
漏洞类型：{', '.join(base.get('vulnerabilities', []))}

要求：
1. 变种名称在原名称后加括号说明（如"（带云原生环境）"）
2. 增加2-3个新组件
3. 增加3-4个新漏洞类型
4. 体现某种特定技术场景（云原生/物联网/移动端/供应链等）

请返回纯JSON，格式同原始场景，额外加 "variant_label" 和 "is_variant": true 字段。
"""
        resp = self.ai_chat(prompt, task_type='scenario_expansion')
        if resp and '{' in resp:
            try:
                import json
                start = resp.find('{')
                end = resp.rfind('}') + 1
                v = json.loads(resp[start:end])
                v['is_variant'] = True
                return v
            except Exception:
                pass
        return None


# 全局实例 - 放在类定义之后
_env_agent = None

def get_env_agent(user_id: str = None) -> EnvAgent:
    """获取环境管理Agent实例"""
    global _env_agent
    if _env_agent is None:
        _env_agent = EnvAgent(user_id)
    if user_id:
        _env_agent.user_id = user_id
    return _env_agent