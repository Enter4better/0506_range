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
    
    # 防御等级定义（对齐 NIST SP 800-61 Rev.3 事件响应阶段）
    DEFENSE_LEVELS = {
        1: {'name': '监控级', 'description': 'NIST: Detect — 日志采集，IDS旁路监听，不主动干预', 'color': '#909399'},
        2: {'name': '过滤级', 'description': 'NIST: Protect — WAF/邮件网关启用基础过滤与请求验证', 'color': '#409eff'},
        3: {'name': '阻断级', 'description': 'NIST: Contain — IPS主动阻断可疑流量，启用访问控制', 'color': '#e6a23c'},
        4: {'name': '封禁级', 'description': 'NIST: Eradicate — IP封禁与服务隔离，清除恶意驻留', 'color': '#f56c6c'},
        5: {'name': '极限级', 'description': 'NIST: Recover/Emergency — 全链路防护，紧急处置与溯源', 'color': '#f56c6c'}
    }

    # 攻击阶段 -> 推荐防御等级映射（Kill Chain 攻击深度与响应等级正相关）
    PHASE_DEFENSE_MAP = {
        1: 1,  # 侦察       -> 监控级（被动检测即可）
        2: 2,  # 武器化与投递-> 过滤级（邮件/文件过滤）
        3: 3,  # 漏洞利用   -> 阻断级（WAF/IPS阻断）
        4: 4,  # 持久化与提权-> 封禁级（隔离受损端点）
        5: 5,  # 横向移动   -> 极限级（全局响应）
        6: 5   # 目标行动   -> 极限级（紧急处置）
    }
    
    def __init__(self):
        super().__init__()
        self.session_defense = {}  # {session_id: {'level': 1, 'blocked_ips': [], 'coverage': 50}}
        self.defense_logs = []
        # 从数据库加载已启用的防御规则
        self._loaded_rules = []
        self._load_defense_rules()
    
    def _load_defense_rules(self):
        """从数据库加载已启用的防御规则"""
        try:
            from models.defense import Defense
            rules = Defense.list_all(enabled=1)
            self._loaded_rules = rules
            if rules:
                logger.info(f"已加载 {len(rules)} 条防御规则")
        except Exception as e:
            logger.warning(f"加载防御规则失败: {e}")
            self._loaded_rules = []
    
    def get_active_rules(self) -> list:
        """获取当前生效的防御规则列表"""
        return self._loaded_rules
    
    def refresh_rules(self):
        """刷新防御规则（用户启用/禁用后调用）"""
        self._load_defense_rules()
    
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
        
        # 3. 阶段因子（攻击越深入，防御体系检测难度越大；参考 MITRE D3FEND 对抗矩阵）
        phase_factor = {
            1: 0.90,   # 侦察       — IDS/IPS 对扫描流量检出率高
            2: 0.82,   # 武器化与投递— 邮件沙箱/终端AV可检出大部分载荷
            3: 0.72,   # 漏洞利用   — WAF 有效但存在 0day/混淆绕过
            4: 0.55,   # 持久化与提权— EDR 可检但对 Rootkit/无文件攻击有限
            5: 0.38,   # 横向移动   — 需 UEBA/NTA 才能有效检测横向渗透
            6: 0.25    # 目标行动   — DLP 检出率有限，深度隐蔽外传难检
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
        
        # 计算防御拦截率（结合数据库中的防御规则）
        coverage = session.get('coverage', 50)
        intercept_rate = self.calculate_defense_intercept_rate(attack_phase, intensity, current_level, coverage)
        
        # 从数据库加载的防御规则中查找匹配当前攻击类型的规则，提升拦截率
        matched_rules = []
        for rule in self._loaded_rules:
            rule_name = rule.name.lower() if rule.name else ''
            rule_type = rule.defense_type.lower() if rule.defense_type else ''
            attack_lower = attack_type.lower() if attack_type else ''
            # 规则名称或类型与攻击类型匹配时生效
            if (rule_name in attack_lower or attack_lower in rule_name or
                rule_type in attack_lower or attack_lower in rule_type):
                matched_rules.append(rule)
        
        # 每条匹配的规则提升 5%~15% 拦截率（取决于覆盖率）
        rule_boost = 0
        for rule in matched_rules:
            rule_boost += 0.05 + (rule.coverage / 100.0) * 0.10
        
        # 即使没有精确匹配，已启用的规则也提供基础加成（每条 2%）
        if not matched_rules and self._loaded_rules:
            base_boost = len(self._loaded_rules) * 0.02
            rule_boost = min(base_boost, 0.20)  # 最多 20%
        
        rule_boost = min(rule_boost, 0.40)  # 规则加成最多 40%
        final_intercept_rate = min(0.95, intercept_rate + rule_boost)
        
        # 执行防御动作
        actions = self._execute_defense_actions(
            attack_type=attack_type,
            defense_level=current_level,
            source_ip=source_ip,
            session=session
        )
        
        # 如果有匹配的规则，在动作中显示
        if matched_rules:
            for rule in matched_rules:
                actions.insert(0, f"📋 规则生效: {rule.name} (覆盖率{rule.coverage}%)")
        
        # 记录防御日志
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'attack_type': attack_type,
            'attack_phase': attack_phase,
            'defense_level': current_level,
            'level_name': self.DEFENSE_LEVELS[current_level]['name'],
            'intercept_rate': round(final_intercept_rate, 3),
            'actions': actions,
            'source_ip': source_ip,
            'session_id': session_id,
            'matched_rules': [r.name for r in matched_rules],
            'active_rules_count': len(self._loaded_rules)
        }
        self.defense_logs.append(log_entry)
        
        return {
            'detected': True,
            'attack_type': attack_type,
            'attack_phase': attack_phase,
            'defense_level': current_level,
            'level_name': self.DEFENSE_LEVELS[current_level]['name'],
            'intercept_rate': round(final_intercept_rate, 3),
            'actions_taken': actions,
            'blocked_ips': session['blocked_ips'],
            'responded_at': datetime.now().isoformat(),
            'matched_rules': [r.name for r in matched_rules],
            'active_rules_count': len(self._loaded_rules)
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
        """获取防御日志（最后 limit 条，供内部统计用）"""
        return self.defense_logs[-limit:]

    def get_defense_logs_paged(self, page: int = 1, limit: int = 10):
        """分页获取防御日志，按时间倒序返回"""
        total = len(self.defense_logs)
        reversed_logs = list(reversed(self.defense_logs))
        offset = (page - 1) * limit
        return reversed_logs[offset:offset + limit], total


_defense_agent = None

def get_defense_agent():
    global _defense_agent
    if _defense_agent is None:
        _defense_agent = DefenseAgent()
    return _defense_agent