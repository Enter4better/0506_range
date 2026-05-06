# -*- coding: utf-8 -*-
import logging
from typing import Dict, Any
from llm import get_deepseek_client

logger = logging.getLogger('agents.base')


class BaseAgent:
    """Agent 基类 - 所有 Agent 继承此类获得 AI 能力"""
    
    def __init__(self):
        self.llm = get_deepseek_client()
    
    def ai_analyze(self, content: str) -> Dict[str, Any]:
        """使用 AI 分析内容"""
        return self.llm.analyze_security(content)
    
    def ai_chat(self, prompt: str, system_prompt: str = None) -> str:
        """使用 AI 聊天"""
        return self.llm.chat(prompt, system_prompt)