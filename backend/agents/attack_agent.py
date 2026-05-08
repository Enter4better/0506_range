# -*- coding: utf-8 -*-
"""
攻击模拟Agent - 分阶段攻击，可升级
"""
import os
import json
import time
import random
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from .base_agent import BaseAgent

logger = logging.getLogger('agents.attack')


class AttackAgent(BaseAgent):
    """攻击模拟Agent - 分阶段攻击，自动升级"""
    
   
    ATTACK_PHASES = {
        1: {'name': '信息收集', 'description': '探测目标信息', 'color': '#909399'},
        2: {'name': '漏洞探测', 'description': '发现可利用漏洞', 'color': '#409eff'},
        3: {'name': '漏洞利用', 'description': '实施攻击获取权限', 'color': '#e6a23c'},
        4: {'name': '权限维持', 'description': '保持访问权限', 'color': '#f56c6c'},
        5: {'name': '横向移动', 'description': '内网渗透扩散', 'color': '#f56c6c'},
        6: {'name': '痕迹清理', 'description': '清除攻击痕迹', 'color': '#909399'}
    }
    
    # 阶段对应的具体攻击
    PHASE_ATTACKS = {
        1: ['端口扫描', '服务识别', '操作系统指纹', '目录扫描'],
        2: ['SQL注入探测', 'XSS探测', '命令注入探测', '弱口令尝试', '文件包含探测'],
        3: ['SQL注入利用', 'XSS利用', '命令执行', '文件上传', '权限提升'],
        4: ['后门植入', 'Webshell上传', '创建隐藏账户', '持久化服务'],
        5: ['内网扫描', '凭证窃取', '横向渗透', '提权扩散'],
        6: ['日志清理', '痕迹隐藏', '进程隐藏', '后门隐藏']
    }
    
    def __init__(self):
        super().__init__()
        self.session_data = {}  # {session_id: {'phase': 1, 'attempts': [], 'successes': 0}}
        self.attack_history = []
    
    def get_attack_phases(self) -> Dict:
        """获取攻击阶段定义"""
        return self.ATTACK_PHASES
    
    def get_phase_attacks(self, phase: int) -> List[str]:
        """获取某阶段可用的攻击类型"""
        return self.PHASE_ATTACKS.get(phase, self.PHASE_ATTACKS[1])
    
    @staticmethod
    def calculate_attack_success_rate(attack_phase: int, intensity: int, defense_level: int = 0) -> float:
        """
        攻击成功率 = 基础成功率 × 强度因子 × (1 - 防御等级因子)
        
        参数说明：
        - attack_phase: 1-6，攻击越深入成功率越高
        - intensity: 1-10，攻击强度
        - defense_level: 0-5，防御等级（0=无防御）
        """
        # 1. 基础成功率（根据攻击阶段）
        base_rate = {
            1: 0.75,   # 信息收集
            2: 0.65,   # 漏洞探测
            3: 0.50,   # 漏洞利用
            4: 0.40,   # 权限维持
            5: 0.35,   # 横向移动
            6: 0.30    # 痕迹清理
        }.get(attack_phase, 0.50)
        
        # 2. 强度因子（1.0 ~ 1.5）
        intensity_factor = 0.8 + (intensity / 10) * 0.7
        
        # 3. 防御等级因子（0 ~ 0.8）
        defense_factor = defense_level / 6
        
        # 4. 最终成功率
        success_rate = base_rate * intensity_factor * (1 - defense_factor)
        
        return round(success_rate, 3)

    def execute_attack(self, session_id: str, attack_type: str = None, intensity: int = 5) -> Dict:
        """执行攻击 - 自动管理阶段升级"""
        # 初始化会话数据
        if session_id not in self.session_data:
            self.session_data[session_id] = {
                'phase': 1,
                'attempts': [],
                'successes': 0,
                'started_at': datetime.now().isoformat()
            }
        
        session = self.session_data[session_id]
        current_phase = session['phase']
        
        # 使用新的攻防概率模型计算成功率（默认防御等级1）
        defense_level = session.get('defense_level', 1)
        success_rate = self.calculate_attack_success_rate(current_phase, intensity, defense_level)
        success = random.random() < success_rate
        
        # 如果成功，增加成功计数
        if success:
            session['successes'] += 1
        
        # 检查是否升级阶段（每成功2次升一级，最高6级）
        if session['successes'] >= 2 and current_phase < 6:
            old_phase = current_phase
            current_phase += 1
            session['phase'] = current_phase
            logger.info(f"[{session_id}] 攻击阶段升级: {old_phase} -> {current_phase} ({self.ATTACK_PHASES[current_phase]['name']})")
        
        # 选择当前阶段的攻击类型
        if not attack_type:
            phase_attacks = self.PHASE_ATTACKS.get(current_phase, self.PHASE_ATTACKS[1])
            attack_type = random.choice(phase_attacks)
        
        # 使用 AI 生成攻击结果分析（攻击Agent使用高temperature增加创造性）
        ai_analysis = self._ai_analyze_attack(attack_type, success, intensity, current_phase)
        
        result = {
            'status': 'success' if success else 'failed',
            'attack_type': attack_type,
            'attack_phase': current_phase,
            'phase_name': self.ATTACK_PHASES[current_phase]['name'],
            'intensity': intensity,
            'success_rate': success_rate,
            'ai_analysis': ai_analysis,
            'executed_at': datetime.now().isoformat()
        }
        
        # 记录历史
        session['attempts'].append(result)
        self.attack_history.append(result)
        
        logger.info(f"[{session_id}] 攻击执行: 阶段{current_phase}-{attack_type} -> {'成功' if success else '失败'} (成功率={success_rate:.1%})")
        
        return result
    
    def _ai_analyze_attack(self, attack_type: str, success: bool, intensity: int, phase: int) -> str:
        """使用 AI 分析攻击结果 - 攻击Agent使用高temperature(0.8)增加策略多样性"""
        phase_name = self.ATTACK_PHASES[phase]['name']
        
        prompt = f"""你是一个红队攻击专家。刚刚执行了一次攻击，请分析结果：

攻击类型：{attack_type}
攻击阶段：{phase_name}（第{phase}阶段）
攻击强度：{intensity}/10
攻击结果：{'成功' if success else '失败'}

请用2-3句话简要分析这次攻击的技术细节、成功/失败原因，以及下一步建议。"""

        try:
            analysis = self.ai_chat(prompt, task_type='attack_analysis')
            return analysis.strip()
        except Exception as e:
            logger.warning(f"AI分析失败，使用默认分析: {e}")
            if not success:
                return f"{attack_type}攻击未成功，目标防御机制生效"
            return f"{attack_type}攻击成功，已进入{phase_name}阶段，发现安全短板"
    
    def get_session_status(self, session_id: str) -> Dict:
        """获取会话攻击状态"""
        if session_id not in self.session_data:
            return {'phase': 1, 'phase_name': '未开始', 'attempts': 0, 'successes': 0}
        
        session = self.session_data[session_id]
        return {
            'current_phase': session['phase'],
            'phase_name': self.ATTACK_PHASES[session['phase']]['name'],
            'total_attempts': len(session['attempts']),
            'successes': session['successes'],
            'started_at': session['started_at']
        }
    
    def reset_session(self, session_id: str):
        """重置会话攻击状态"""
        if session_id in self.session_data:
            del self.session_data[session_id]


_attack_agent = None

def get_attack_agent():
    global _attack_agent
    if _attack_agent is None:
        _attack_agent = AttackAgent()
    return _attack_agent