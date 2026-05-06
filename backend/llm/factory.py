# -*- coding: utf-8 -*-
"""
LLM工厂 - 只使用 DeepSeek
"""
import logging

logger = logging.getLogger('llm.factory')


def get_llm():
    """获取 DeepSeek LLM 实例"""
    from .deepseek_api import get_deepseek_llm
    logger.info("使用 DeepSeek API")
    return get_deepseek_llm()