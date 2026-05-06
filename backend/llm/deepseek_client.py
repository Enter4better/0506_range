# -*- coding: utf-8 -*-
import os
import json
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('llm.deepseek')


class DeepSeekClient:
    """DeepSeek API 客户端 - 真正的 AI 大模型接入"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('DEEPSEEK_API_KEY', '')
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            logger.info("DeepSeek 客户端初始化成功")
        else:
            logger.warning("DeepSeek API Key 未配置，将使用模拟模式")
    
    def chat(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """调用 DeepSeek 大模型"""
        if not self.enabled:
            return self._mock_response(prompt)
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": kwargs.get('temperature', 0.3),
                    "max_tokens": kwargs.get('max_tokens', 500)
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                logger.debug(f"AI 响应成功: {content[:100]}...")
                return content
            else:
                logger.error(f"API 错误: {response.status_code}")
                return self._mock_response(prompt)
                
        except Exception as e:
            logger.error(f"API 调用失败: {e}")
            return self._mock_response(prompt)
    
    def analyze_security(self, text: str) -> Dict[str, Any]:
        """专门的安全分析接口"""
        prompt = f"""请分析以下安全相关内容，并以 JSON 格式返回结果：

{text}

返回格式：
{{
    "risk_level": "low/medium/high/critical",
    "threat_type": "威胁类型",
    "confidence": 0.0-1.0,
    "recommendations": ["建议1", "建议2"],
    "analysis": "简要分析"
}}
"""
        response = self.chat(prompt, system_prompt="你是一个网络安全专家，请用JSON格式返回分析结果。")
        
        try:
            # 提取 JSON
            if '{' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                return json.loads(response[start:end])
        except:
            pass
        
        return {
            'risk_level': 'medium',
            'threat_type': 'unknown',
            'confidence': 0.5,
            'recommendations': ['请人工分析'],
            'analysis': response[:200]
        }
    
    def _mock_response(self, prompt: str) -> str:
        """模拟响应（API 不可用时）"""
        prompt_lower = prompt.lower()
        
        if 'sql注入' in prompt_lower or 'injection' in prompt_lower:
            return '{"attack_type":"SQL注入","steps":["检测注入点","构造payload","获取数据"],"success_rate":0.7}'
        elif 'xss' in prompt_lower or '跨站' in prompt_lower:
            return '{"attack_type":"XSS","steps":["寻找输入点","构造脚本","窃取信息"],"success_rate":0.6}'
        elif '场景' in prompt_lower or '靶场' in prompt_lower:
            return '{"name":"Web安全靶场","components":[{"image":"nginx:alpine","ports":[80]},{"image":"mysql:8.0","ports":[3306]}]}'
        else:
            return '{"analysis":"分析完成","recommendations":["持续监控"]}'


_deepseek = None

def get_deepseek_client() -> DeepSeekClient:
    global _deepseek
    if _deepseek is None:
        _deepseek = DeepSeekClient()
    return _deepseek