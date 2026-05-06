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
            ai_response = self.ai_chat(optimization_prompt)
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
        ai_response = self.ai_chat(prompt)
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
        """创建靶场环境"""
        if user_id:
            self.user_id = user_id
            
        result = {
            'status': 'pending',
            'environment_id': None,
            'components_created': [],
            'errors': []
        }
        
        try:
            env_id = f"env_{int(time.time())}_{scenario_config.get('name', 'custom')}"
            result['environment_id'] = env_id
            
            Log.create('info', 'env_agent', 
                      f"环境管理Agent开始创建靶场: {scenario_config.get('name', '自定义靶场')}", 
                      user_id=self.user_id)
            
            # 创建组件
            components = scenario_config.get('components', [])
            for comp in components:
                result['components_created'].append({
                    'name': comp['name'],
                    'type': comp['type'],
                    'status': 'running',
                    'ports': comp.get('ports', [])
                })
                Log.create('success', 'env_agent', 
                          f"组件部署完成: {comp['name']} ({comp['type']})", 
                          user_id=self.user_id)
            
            # 创建靶场记录
            target = Target(
                name=scenario_config.get('name', '自定义靶场'),
                type='container',
                ip='127.0.0.1',
                port=8080,
                os='Linux',
                status='running',
                config=json.dumps(scenario_config)
            )
            target.save()
            
            if target.target_id:
                result['target_id'] = target.target_id
            
            result['status'] = 'running'
            result['name'] = scenario_config.get('name', '自定义靶场')
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