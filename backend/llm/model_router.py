# -*- coding: utf-8 -*-
"""
多模型路由器 - 根据任务类型自动选择最适合的模型配置

设计思路：
  不同任务对模型有不同要求：
  - 自然语言理解：通用大模型，中等温度，理解意图
  - 靶场/配置生成：低温度，结构化输出，精确可靠
  - 攻击规划：高温度，创造性强，策略多样
  - 防御分析：极低温度，确定性判断，不能误判
  - 报告生成：中等温度，长文本，结构清晰
  - 安全分类：零温度，只做标签分类

  所有任务都走 DeepSeek API，通过不同 model + temperature + max_tokens 区分。
  若将来接入其他API（如本地微调模型），只需在此修改路由表即可。
"""
import logging
import os

logger = logging.getLogger('llm.model_router')


# 任务类型 -> 模型配置路由表
TASK_ROUTE_MAP = {
    # 自然语言理解：用户输入解析、场景描述分析
    'nlp_understanding': {
        'model': os.getenv('MODEL_NLP', 'deepseek-chat'),
        'temperature': 0.3,
        'max_tokens': 800,
        'description': '自然语言理解 - 通用大模型，中等确定性'
    },
    # 靶场/环境配置生成：输出JSON，需要高精确度
    'range_generation': {
        'model': os.getenv('MODEL_CODEGEN', 'deepseek-chat'),
        'temperature': 0.15,
        'max_tokens': 1200,
        'description': '配置生成 - 低温度，结构化JSON输出'
    },
    # 攻击规划：需要创造性和多样性
    'attack_planning': {
        'model': os.getenv('MODEL_ATTACK', 'deepseek-chat'),
        'temperature': 0.85,
        'max_tokens': 600,
        'description': '攻击规划 - 高温度，策略创造性强'
    },
    # 攻击结果分析：单次攻击后的技术解读
    'attack_analysis': {
        'model': os.getenv('MODEL_ATTACK', 'deepseek-chat'),
        'temperature': 0.7,
        'max_tokens': 400,
        'description': '攻击分析 - 中高温度，多角度解读'
    },
    # 防御决策：检测到攻击后的应对判断，需要稳定准确
    'defense_decision': {
        'model': os.getenv('MODEL_DEFENSE', 'deepseek-chat'),
        'temperature': 0.05,
        'max_tokens': 350,
        'description': '防御决策 - 极低温度，确定性强'
    },
    # 安全分类：威胁等级/类型快速分类，极快响应
    'security_classification': {
        'model': os.getenv('MODEL_CLASSIFY', 'deepseek-chat'),
        'temperature': 0.0,
        'max_tokens': 120,
        'description': '安全分类 - 零温度，确定性标签'
    },
    # 报告生成：长文本，结构化，需要一定流畅性
    'report_generation': {
        'model': os.getenv('MODEL_REPORT', 'deepseek-chat'),
        'temperature': 0.45,
        'max_tokens': 2048,
        'description': '报告生成 - 中等温度，长文本结构输出'
    },
    # 场景扩展：从基础场景生成变种，需要创造性
    'scenario_expansion': {
        'model': os.getenv('MODEL_NLP', 'deepseek-chat'),
        'temperature': 0.65,
        'max_tokens': 1500,
        'description': '场景扩展 - 中高温度，场景变种生成'
    },
    # 可解释性推理：生成"因X，故Y"决策链
    'explainability': {
        'model': os.getenv('MODEL_NLP', 'deepseek-chat'),
        'temperature': 0.2,
        'max_tokens': 250,
        'description': '可解释推理 - 低温度，逻辑链条清晰'
    },
}

# 默认回退配置
_DEFAULT_CONFIG = {
    'model': 'deepseek-chat',
    'temperature': 0.3,
    'max_tokens': 500,
    'description': '默认配置'
}


def get_model_config(task_type: str) -> dict:
    """根据任务类型获取模型配置"""
    config = TASK_ROUTE_MAP.get(task_type, _DEFAULT_CONFIG)
    logger.debug(f"[ModelRouter] task={task_type} → model={config['model']} "
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
