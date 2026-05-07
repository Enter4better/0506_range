# -*- coding: utf-8 -*-
"""
防御模拟Agent - 根据攻击阶段和强度自适应防御
"""
import logging
import random
from datetime import datetime
from typing import Dict, List, Any

from .base_agent import BaseAgent

logger = logging.getLogger('agents.defense')


class DefenseAgent(BaseAgent):
    """AI 自适应防御Agent - 根据攻击阶段动态调整防御等级"""
    
    # 防御等级定义
    DEFENSE_LEVELS = {
        1: {'name': '监控级', 'description': '记录日志，不阻断', 'color': '#909399'},
        2: {'name': '过滤级', 'description': '基础过滤，验证请求', 'color': '#409eff'},
        3: {'name': '阻断级', 'description': '主动阻断可疑请求', 'color': '#e6a23c'},
        4: {'name': '封禁级', 'description': 'IP封禁，服务隔离', 'color': '#f56c6c'},
        5: {'name': '极限级', 'description': '全链路防护，紧急响应', 'color': '#f56c6c'}
    }
    
    # 攻击阶段 -> 推荐防御等级映射
    PHASE_DEFENSE_MAP = {
        1: 1,  # 信息收集 -> 监控级
        2: 2,  # 漏洞探测 -> 过滤级
        3: 3,  # 漏洞利用 -> 阻断级
        4: 4,  # 权限维持 -> 封禁级
        5: 5,  # 横向移动 -> 极限级
        6: 5   # 痕迹清理 -> 极限级
    }
    
    def __init__(self):
        super().__init__()
        self.session_defense = {}  # {session_id: {'level': 1, 'blocked_ips': [], 'coverage': 50}}
        self.defense_logs = []
    
    @staticmethod
    def calculate_defense_intercept_rate(attack_phase: int, intensity: int, defense_level: int, coverage: float = 50.0) -> float:
        """
        防御拦截率 = 防御等级因子 × 覆盖率因子 × 阶段因子
        
        参数说明：
        - attack_phase: 1-6，攻击阶段
        - intensity: 1-10，攻击强度
        - defense_level: 0-5，防御等级
        - coverage: 0-100，防御覆盖率
        """
        # 1. 防御等级因子（0 ~ 0.6）
        level_factor = defense_level / 8
        
        # 2. 覆盖率因子（0 ~ 0.3）
        coverage_factor = coverage / 100 * 0.35
        
        # 3. 阶段因子（攻击越深越难拦截）
        phase_factor = {
            1: 0.95,   # 信息收集 - 易拦截
            2: 0.90,   # 漏洞探测
            3: 0.70,   # 漏洞利用
            4: 0.50,   # 权限维持
            5: 0.35,   # 横向移动
            6: 0.20    # 痕迹清理 - 难拦截
        }.get(attack_phase, 0.70)
        
        # 4. 强度负面影响（强度越高越难拦截）
        intensity_penalty = 1.0 - (intensity / 10) * 0.15
        
        # 5. 最终拦截率
        intercept_rate = (level_factor + coverage_factor) * phase_factor * intensity_penalty
        intercept_rate = min(0.95, max(0.05, intercept_rate))  # 限制在 5% ~ 95%
        
        return round(intercept_rate, 3)
    
    def detect_and_respond(self, session_id: str, attack_data: Dict) -> Dict:
        """检测并响应攻击（根据攻击阶段调整防御等级）"""
        attack_phase = attack_data.get('attack_phase', 1)
        attack_type = attack_data.get('attack_type', 'unknown')
        intensity = attack_data.get('intensity', 5)
        source_ip = attack_data.get('source_ip', f'192.168.1.{random.randint(1,255)}')
        
        # 初始化会话防御状态
        if session_id not in self.session_defense:
            self.session_defense[session_id] = {
                'level': 1,
                'blocked_ips': [],
                'alert_history': [],
                'coverage': 50
            }
        
        session = self.session_defense[session_id]
        
        # 根据攻击阶段确定目标防御等级
        target_level = self.PHASE_DEFENSE_MAP.get(attack_phase, 2)
        
        # 根据攻击强度额外加成
        intensity_bonus = 0 if intensity < 5 else 1 if intensity < 8 else 2
        target_level = min(5, target_level + intensity_bonus)
        
        # 逐渐提升防御等级（不降级）
        if target_level > session['level']:
            old_level = session['level']
            session['level'] = target_level
            logger.info(f"[{session_id}] 防御等级升级: {old_level} -> {target_level} ({self.DEFENSE_LEVELS[target_level]['name']})")
        
        current_level = session['level']
        
        # 计算防御拦截率
        coverage = session.get('coverage', 50)
        intercept_rate = self.calculate_defense_intercept_rate(attack_phase, intensity, current_level, coverage)
        
        # 执行防御动作
        actions = self._execute_defense_actions(
            attack_type=attack_type,
            defense_level=current_level,
            source_ip=source_ip,
            session=session
        )
        
        # 记录防御日志
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'attack_type': attack_type,
            'attack_phase': attack_phase,
            'defense_level': current_level,
            'level_name': self.DEFENSE_LEVELS[current_level]['name'],
            'intercept_rate': intercept_rate,
            'actions': actions,
            'source_ip': source_ip,
            'session_id': session_id
        }
        self.defense_logs.append(log_entry)
        
        return {
            'detected': True,
            'attack_type': attack_type,
            'attack_phase': attack_phase,
            'defense_level': current_level,
            'level_name': self.DEFENSE_LEVELS[current_level]['name'],
            'intercept_rate': intercept_rate,
            'actions_taken': actions,
            'blocked_ips': session['blocked_ips'],
            'responded_at': datetime.now().isoformat()
        }
    
    def _execute_defense_actions(self, attack_type: str, defense_level: int, 
                                  source_ip: str, session: Dict) -> List[str]:
        """根据防御等级执行具体动作"""
        actions = []
        
        # 等级1: 监控
        if defense_level >= 1:
            actions.append(f"📝 监控记录: {attack_type}攻击已记录")
        
        # 等级2: 过滤
        if defense_level >= 2:
            actions.append(f"🛡️ 请求过滤: 对{attack_type}启用基础过滤")
        
        # 等级3: 阻断
        if defense_level >= 3:
            actions.append(f"⚡ 主动阻断: {attack_type}请求已被拦截")
        
        # 等级4: 封禁IP
        if defense_level >= 4:
            if source_ip not in session['blocked_ips']:
                session['blocked_ips'].append(source_ip)
                actions.append(f"🔒 IP封禁: {source_ip}已加入黑名单")
            actions.append(f"🚨 服务隔离: 目标服务已隔离")
        
        # 等级5: 极限防护
        if defense_level >= 5:
            actions.append(f"💀 极限防护: 全链路防御已启动")
            actions.append(f"🔔 紧急告警: 高危攻击已上报")
        
        return actions
    
    def get_status(self, session_id: str = None) -> Dict:
        """获取防御状态"""
        if session_id and session_id in self.session_defense:
            session = self.session_defense[session_id]
            return {
                'status': 'active',
                'current_level': session['level'],
                'level_name': self.DEFENSE_LEVELS[session['level']]['name'],
                'blocked_ips': session['blocked_ips'],
                'total_alerts': len(session['alert_history'])
            }
        
        return {
            'status': 'active',
            'current_level': 1,
            'level_name': self.DEFENSE_LEVELS[1]['name'],
            'blocked_ips': [],
            'total_alerts': 0
        }
    
    def get_defense_logs(self, limit: int = 30) -> List[Dict]:
        """获取防御日志"""
        return self.defense_logs[-limit:]


_defense_agent = None

def get_defense_agent():
    global _defense_agent
    if _defense_agent is None:
        _defense_agent = DefenseAgent()
    return _defense_agent