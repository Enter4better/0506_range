# -*- coding: utf-8 -*-
"""
多模型路由器 - 根据任务类型自动选择最适合的模型配置

设计思路：
  不同任务对模型有不同要求：
  - 自然语言理解：低温度，语义解析稳定性优先
  - 靶场/配置生成：极低温度，结构化 JSON 输出，精确可靠
  - 场景扩展：中高温度，生成场景变种，需要一定创造性
  - 攻击分析：需要推理，多角度解读（用 Reasoner）
  - 防御决策：极低温度，确定性判断，不能误判（用 Reasoner 更稳定）

  Chat vs Reasoner 分工策略：
  - deepseek-chat（V3）：免费，响应快，适合配置生成、语义理解、场景扩展
  - deepseek-reasoner（R1）：深度推理，适合攻击分析、防御决策等需要深度分析的任务
"""
import logging
import os

logger = logging.getLogger('llm.model_router')


# 任务类型 -> 模型配置路由表（共5种实际使用的任务类型）
TASK_ROUTE_MAP = {
    # ========== Chat 模型 ==========
    # 自然语言理解：用户输入解析、场景描述分析
    'nlp_understanding': {
        'model': 'deepseek-chat',
        'temperature': 0.2,
        'max_tokens': 1000,
        'description': '自然语言理解 - Chat模型，低温度，语义解析稳定性优先'
    },
    # 靶场/环境配置生成：输出完整JSON，需要高精确度
    'range_generation': {
        'model': 'deepseek-chat',
        'temperature': 0.1,
        'max_tokens': 2500,
        'description': '配置生成 - Chat模型，极低温度，完整JSON结构输出'
    },
    # 场景扩展：从基础场景生成变种，需要创造性
    'scenario_expansion': {
        'model': 'deepseek-chat',
        'temperature': 0.65,
        'max_tokens': 1500,
        'description': '场景扩展 - Chat模型，中高温度，场景变种生成'
    },

    # ========== Reasoner 模型（深度推理） ==========
    # 攻击结果分析：单次攻击后的技术解读，需要深度分析
    'attack_analysis': {
        'model': 'deepseek-reasoner',
        'temperature': 0.7,
        'max_tokens': 400,
        'description': '攻击分析 - Reasoner模型，中高温度，多角度深度解读'
    },
    # 防御决策：检测到攻击后的应对判断，需要稳定准确
    'defense_decision': {
        'model': 'deepseek-reasoner',
        'temperature': 0.05,
        'max_tokens': 800,
        'description': '防御决策 - Reasoner模型，极低温度，确定性强，深度推理'
    },
}

# 默认回退配置
_DEFAULT_CONFIG = {
    'model': 'deepseek-chat',
    'temperature': 0.3,
    'max_tokens': 500,
    'description': '默认配置 - Chat模型'
}


def get_model_config(task_type: str) -> dict:
    """根据任务类型获取模型配置"""
    config = TASK_ROUTE_MAP.get(task_type, _DEFAULT_CONFIG)
    logger.info(f"[ModelRouter] task={task_type} → model={config['model']} "
                f"temperature={config['temperature']} max_tokens={config['max_tokens']}")
    return config


def list_task_routes() -> list:
    """列出所有任务路由（供前端展示）"""
    return [
        {
            'task_type': k,
            'model': v['model'],
            'temperature': v['temperature'],
            'max_tokens': v['max_tokens'],
            'description': v['description']
        }
        for k, v in TASK_ROUTE_MAP.items()
    ]
