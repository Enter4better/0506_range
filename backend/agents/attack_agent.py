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
    
   
    # 攻击阶段定义：基于 Lockheed Martin Cyber Kill Chain（2011）6 阶段压缩映射
    # Stage 2(武器化) + Stage 3(投递) 合并为 Phase 2，其余与 Kill Chain 一一对应
    # 每阶段同时标注对应的 MITRE ATT&CK Enterprise 战术 ID
    ATTACK_PHASES = {
        1: {'name': '侦察',        'description': 'Kill Chain 1 · MITRE TA0043/TA0007 — 主动扫描与被动信息收集', 'color': '#909399'},
        2: {'name': '武器化与投递', 'description': 'Kill Chain 2+3 · MITRE TA0042/TA0001 — 制作 Exploit 并送达目标', 'color': '#409eff'},
        3: {'name': '漏洞利用',    'description': 'Kill Chain 4 · MITRE TA0002/TA0004 — 触发漏洞获取初始执行权', 'color': '#e6a23c'},
        4: {'name': '持久化与提权', 'description': 'Kill Chain 5 · MITRE TA0003/TA0004 — 植入后门并提升至高权限', 'color': '#f56c6c'},
        5: {'name': '横向移动',    'description': 'Kill Chain 6 · MITRE TA0008/TA0011 — 内网扩散并建立 C2 信道', 'color': '#f56c6c'},
        6: {'name': '目标行动',    'description': 'Kill Chain 7 · MITRE TA0009/TA0010/TA0040/TA0005 — 数据窃取、破坏与痕迹清除', 'color': '#909399'}
    }

    # 各阶段典型攻击技术（与 MITRE ATT&CK 技术子项对齐）
    PHASE_ATTACKS = {
        1: ['端口扫描', '服务识别', 'OSINT信息收集', 'Web目录枚举'],
        2: ['漏洞扫描', '鱼叉式钓鱼', 'Exploit定制', '供应链攻击'],
        3: ['SQL注入利用', 'RCE远程代码执行', 'Web Shell上传', '反序列化攻击'],
        4: ['后门植入', '创建隐藏账户', '提权利用', '持久化服务注册'],
        5: ['内网扫描', '凭证窃取', '哈希传递攻击', 'C2通道建立'],
        6: ['敏感数据窃取', '数据隐蔽外传', '日志清除', '业务破坏']
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
        # 1. 基础成功率（根据攻击阶段，依据 Verizon DBIR 2024 渗透测试实测数据校准）
        #    攻击越深入、防御层数越多，单次成功率递减
        base_rate = {
            1: 0.80,   # 侦察       — 扫描稳定成功，接近确定性
            2: 0.68,   # 武器化与投递— 邮件网关/沙箱约拦截 30%
            3: 0.55,   # 漏洞利用   — 与目标是否存在漏洞强相关
            4: 0.44,   # 持久化与提权— EDR/终端检测增加阻力
            5: 0.36,   # 横向移动   — 网络微分段显著增加难度
            6: 0.30    # 目标行动   — DLP/行为分析多重阻碍
        }.get(attack_phase, 0.50)
        
        # 2. 强度因子（1.0 ~ 1.5）
        intensity_factor = 0.8 + (intensity / 10) * 0.7
        
        # 3. 防御等级因子（0 ~ 0.8）
        defense_factor = defense_level / 6
        
        # 4. 最终成功率
        success_rate = base_rate * intensity_factor * (1 - defense_factor)
        
        return round(success_rate, 3)

    def execute_attack(self, session_id: str, attack_type: str = None, intensity: int = 5,
                       target_image: str = '') -> Dict:
        """执行攻击 - 自动管理阶段升级，对综合漏洞靶场应用成功率加成"""
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

        # 基础成功率（Kill Chain 模型）
        defense_level = session.get('defense_level', 1)
        success_rate = self.calculate_attack_success_rate(current_phase, intensity, defense_level)

        # 综合漏洞靶场加成（这些靶场是刻意脆弱的，成功率应高于普通容器）
        vuln_match = False
        target_meta = None
        try:
            from .env_agent import COMPREHENSIVE_TARGETS
            target_meta = COMPREHENSIVE_TARGETS.get(target_image)
        except Exception:
            pass

        if target_meta:
            success_rate += target_meta.get('base_rate_boost', 0)
            if attack_type and attack_type in target_meta.get('vuln_types', []):
                success_rate += target_meta.get('match_bonus', 0)
                vuln_match = True
            success_rate = min(0.95, success_rate)

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

        # AI 攻击结果分析
        ai_analysis = self._ai_analyze_attack(attack_type, success, intensity, current_phase,
                                              target_meta=target_meta, vuln_match=vuln_match)

        result = {
            'status': 'success' if success else 'failed',
            'attack_type': attack_type,
            'attack_phase': current_phase,
            'phase_name': self.ATTACK_PHASES[current_phase]['name'],
            'intensity': intensity,
            'success_rate': round(success_rate, 3),
            'target_image': target_image,
            'target_label': target_meta['label'] if target_meta else '',
            'vuln_match': vuln_match,
            'ai_analysis': ai_analysis,
            'executed_at': datetime.now().isoformat()
        }

        # 记录历史
        session['attempts'].append(result)
        self.attack_history.append(result)

        match_info = '(漏洞类型命中)' if vuln_match else ('(综合靶场)' if target_meta else '')
        logger.info(f"[{session_id}] 攻击执行: 阶段{current_phase}-{attack_type} -> {'成功' if success else '失败'} "
                    f"(成功率={success_rate:.1%}) {match_info}")

        return result
    
    def _ai_analyze_attack(self, attack_type: str, success: bool, intensity: int, phase: int,
                           target_meta: dict = None, vuln_match: bool = False) -> str:
        """使用 AI 分析攻击结果 - 攻击Agent使用高temperature(0.8)增加策略多样性"""
        phase_name = self.ATTACK_PHASES[phase]['name']
        target_ctx = ''
        if target_meta:
            target_ctx = f'\n靶场类型：{target_meta["label"]}（{target_meta["description"]}）'
            if vuln_match:
                target_ctx += f'\n漏洞类型命中：该靶场已知存在 {attack_type} 漏洞，攻击成功率提升'

        prompt = f"""你是一个红队攻击专家。刚刚执行了一次攻击，请分析结果：

攻击类型：{attack_type}
攻击阶段：{phase_name}（第{phase}阶段）
攻击强度：{intensity}/10
攻击结果：{'成功' if success else '失败'}{target_ctx}

请用2-3句话简要分析这次攻击的技术细节、成功/失败原因，以及下一步建议。"""

        try:
            analysis = self.ai_chat(prompt, task_type='attack_analysis')
            return analysis.strip()
        except Exception as e:
            logger.warning(f"AI分析失败，使用默认分析: {e}")
            if not success:
                return f"{attack_type}攻击未成功，目标防御机制生效"
            if vuln_match:
                return f"{attack_type}攻击成功（命中靶场已知漏洞），已进入{phase_name}阶段"
            return f"{attack_type}攻击成功，已进入{phase_name}阶段，发现安全短板"
    
    def get_session_status(self, session_id: str) -> Dict:
        """获取会话攻击状态"""
        total_phases = len(self.ATTACK_PHASES)
        if session_id not in self.session_data:
            return {'current_phase': 0, 'phase_name': '未开始', 'total_phases': total_phases, 'total_attempts': 0, 'successes': 0}

        session = self.session_data[session_id]
        return {
            'current_phase': session['phase'],
            'total_phases': total_phases,
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