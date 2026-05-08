# -*- coding: utf-8 -*-
"""
多智能体编排器 - 实现真正的闭环自主演化

闭环流程：
  攻击Agent执行攻击
    → 结果实时通知防御Agent
      → 防御Agent检测并响应，更新防御等级
        → 防御结果通知环境Agent（隔离/扩容/重建）
          → 攻击Agent获取防御反馈，自适应调整策略
            → 循环

自适应难度：
  防御拦截率 > 70% → 升级为组合漏洞攻击，提高强度
  防御拦截率 < 30% → 降级为单一攻击，降低强度（保证训练效果）

可解释性：
  每一步动作都生成 "因为X，故触发Y，结果Z" 推理链
"""
import random
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional

from .env_agent import get_env_agent
from .attack_agent import get_attack_agent
from .defense_agent import get_defense_agent
from services.async_queue import async_queue_service

logger = logging.getLogger('agents.orchestrator')

# 组合漏洞攻击定义（防御强时触发）
COMBO_ATTACKS = [
    ['SQL注入', 'XSS利用'],
    ['文件上传', '命令执行'],
    ['权限提升', '横向移动'],
    ['弱口令尝试', '暴力破解', '凭证窃取'],
    ['目录遍历', '文件包含', '信息泄露'],
]


class Orchestrator:
    """攻防演练编排器 - 多智能体闭环自主演化"""

    def __init__(self):
        self.env_agent = get_env_agent()
        self.attack_agent = get_attack_agent()
        self.defense_agent = get_defense_agent()
        self.sessions = {}
        self._lock = threading.Lock()

    # ───────────────────────── 场景创建 ─────────────────────────

    def create_scenario(self, description: str, user_id: str = None) -> Dict:
        """创建演练场景"""
        env_result = self.env_agent.create_environment(
            self.env_agent.analyze_scenario(description), user_id
        )

        if env_result.get('status') != 'running':
            return {'status': 'error', 'message': '环境创建失败'}

        session_id = env_result['environment_id']
        with self._lock:
            self.sessions[session_id] = {
                'session_id': session_id,
                'environment': {
                    'name': env_result.get('name', '自定义靶场'),
                    'components': env_result.get('components', [])
                },
                'attacks': [],
                'decision_log': [],       # 可解释性决策日志
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                # 自适应难度状态
                'current_intensity': 5,
                'difficulty_mode': 'single',  # 'single' | 'combo'
                'recent_intercept_rates': [],  # 最近5次拦截率
                # 闭环统计
                'env_adjustments': [],    # 环境Agent做过的调整
            }

        logger.info(f"演练场景创建成功: {session_id}")
        return {'status': 'success', 'session_id': session_id, 'environment': env_result}

    # ───────────────────────── 核心闭环攻击 ──────────────────────

    def execute_attack(self, session_id: str, attack_type: str = None, intensity: int = None) -> Dict:
        """执行攻击 - 闭环：攻击→防御通知→环境响应→难度自适应"""
        if session_id not in self.sessions:
            return {'status': 'error', 'message': '会话不存在'}

        session = self.sessions[session_id]

        # 自适应难度：使用会话维护的强度，外部传入仅作初始参考
        if intensity is None:
            intensity = session.get('current_intensity', 5)

        # 选择攻击类型（组合模式 vs 单一模式）
        resolved_attack_type, combo_list = self._resolve_attack_type(session, attack_type)

        target = session['environment'].get('name', '靶场')

        def do_attack():
            # ── STEP 1: 攻击Agent执行攻击 ──
            attack_result = self.attack_agent.execute_attack(
                session_id, resolved_attack_type, intensity
            )
            attack_result['combo_chain'] = combo_list

            # ── STEP 2: 防御Agent实时接收攻击通知，检测并响应 ──
            defense_result = self.defense_agent.detect_and_respond(
                session_id,
                {
                    'attack_type': resolved_attack_type,
                    'attack_phase': attack_result.get('attack_phase', 1),
                    'intensity': intensity,
                    'source_ip': f'10.0.{random.randint(1,254)}.{random.randint(1,254)}',
                    'target': target,
                    'success': attack_result.get('status') == 'success',
                    'combo': len(combo_list) > 1,
                }
            )

            # ── STEP 3: 可解释性 - 为每一步生成推理链 ──
            reasoning = self._build_reasoning_chain(attack_result, defense_result)
            attack_result['reasoning'] = reasoning
            defense_result['reasoning'] = reasoning

            # ── STEP 4: 环境Agent根据防御决策动态调整环境 ──
            env_action = self._notify_env_agent(session_id, session, defense_result)

            # ── STEP 5: 攻击Agent获取防御反馈，自适应调整难度 ──
            adapt_msg = self._adapt_difficulty(session, defense_result)

            record = {
                'attack': attack_result,
                'defense': defense_result,
                'env_action': env_action,
                'adapt_msg': adapt_msg,
                'reasoning': reasoning,
                'executed_at': datetime.now().isoformat(),
            }

            with self._lock:
                session.setdefault('attacks', []).append(record)
                session.setdefault('decision_log', []).append({
                    'time': datetime.now().isoformat(),
                    'reasoning': reasoning,
                    'env_action': env_action,
                    'adapt_msg': adapt_msg,
                })

            logger.info(
                f"[{session_id}] 攻击={resolved_attack_type} 拦截率={defense_result.get('intercept_rate', 0):.0%} "
                f"难度={session.get('difficulty_mode')} 强度={session.get('current_intensity')}"
            )
            return record

        task_id = async_queue_service.add_task(do_attack)
        return {'status': 'accepted', 'task_id': task_id, 'message': '闭环攻防任务已提交'}

    # ───────────────────────── 自适应难度 ────────────────────────

    def _resolve_attack_type(self, session: Dict, requested_type: Optional[str]):
        """根据难度模式决定本次攻击类型（单一 or 组合）"""
        mode = session.get('difficulty_mode', 'single')
        if mode == 'combo' and not requested_type:
            combo = random.choice(COMBO_ATTACKS)
            return combo[0], combo           # 主攻击类型 + 完整链
        return requested_type, ([requested_type] if requested_type else [])

    def _adapt_difficulty(self, session: Dict, defense_result: Dict) -> str:
        """
        根据防御拦截率自适应调整攻击难度：
          拦截率 > 70% 连续2次 → 升级为组合漏洞，强度+1
          拦截率 < 30% 连续2次 → 降为单一攻击，强度-1
        """
        intercept_rate = defense_result.get('intercept_rate', 0.5)
        rates = session.setdefault('recent_intercept_rates', [])
        rates.append(intercept_rate)
        if len(rates) > 5:
            rates.pop(0)

        if len(rates) < 2:
            return '样本不足，保持当前难度'

        avg = sum(rates[-2:]) / 2
        intensity = session.get('current_intensity', 5)
        old_mode = session.get('difficulty_mode', 'single')
        msg_parts = []

        if avg > 0.70:
            session['difficulty_mode'] = 'combo'
            new_intensity = min(10, intensity + 1)
            session['current_intensity'] = new_intensity
            msg_parts.append(
                f'防御拦截率={avg:.0%}>70%，升级为组合漏洞攻击'
                + (f'，强度 {intensity}→{new_intensity}' if new_intensity != intensity else '')
            )
        elif avg < 0.30:
            session['difficulty_mode'] = 'single'
            new_intensity = max(1, intensity - 1)
            session['current_intensity'] = new_intensity
            msg_parts.append(
                f'防御拦截率={avg:.0%}<30%，降为单一攻击保障训练效果'
                + (f'，强度 {intensity}→{new_intensity}' if new_intensity != intensity else '')
            )
        else:
            msg_parts.append(f'防御拦截率={avg:.0%}，难度维持（{old_mode}）')

        return '；'.join(msg_parts)

    # ───────────────────────── 环境Agent响应 ─────────────────────

    def _notify_env_agent(self, session_id: str, session: Dict, defense_result: Dict) -> str:
        """
        防御Agent高级别告警时，通知环境Agent动态调整：
          等级5（极限）→ 隔离受攻击组件
          等级4（封禁）→ 通知扩容（增加监控节点）
          等级≤3       → 记录，不干预
        """
        level = defense_result.get('defense_level', 1)
        actions_taken = defense_result.get('actions_taken', [])
        action_msg = '无需环境干预'

        if level >= 5:
            # 模拟环境隔离：标记受攻击组件为 isolated
            components = session['environment'].get('components', [])
            for comp in components:
                if comp.get('status') == 'running':
                    comp['status'] = 'isolated'
                    break
            action_msg = f'环境Agent：检测到极限级威胁，已隔离受攻击组件'
            session.setdefault('env_adjustments', []).append({
                'type': 'isolate',
                'reason': '极限级防御触发',
                'time': datetime.now().isoformat()
            })
            logger.info(f"[{session_id}] 环境Agent：组件隔离")

        elif level >= 4:
            # 模拟扩容：增加一个监控节点记录
            session.setdefault('env_adjustments', []).append({
                'type': 'scale_monitor',
                'reason': '封禁级防御，增强监控',
                'time': datetime.now().isoformat()
            })
            action_msg = f'环境Agent：封禁级防御，已扩容监控节点'
            logger.info(f"[{session_id}] 环境Agent：扩容监控")

        elif level >= 3 and any('重建' in a for a in actions_taken):
            session.setdefault('env_adjustments', []).append({
                'type': 'rebuild_hint',
                'reason': '阻断级防御，建议重建受损组件',
                'time': datetime.now().isoformat()
            })
            action_msg = '环境Agent：建议重建受损组件（已记录，待人工确认）'

        return action_msg

    # ───────────────────────── 可解释性推理链 ────────────────────

    def _build_reasoning_chain(self, attack_result: Dict, defense_result: Dict) -> str:
        """
        生成可解释性推理链：
          "因检测到{攻击类型}（阶段{N}），防御等级升至{L}，故触发{动作}策略，拦截率{R}%"
        """
        attack_type = attack_result.get('attack_type', '未知攻击')
        phase = attack_result.get('attack_phase', 1)
        phase_name = attack_result.get('phase_name', '')
        level = defense_result.get('defense_level', 1)
        level_name = defense_result.get('level_name', '')
        intercept_rate = defense_result.get('intercept_rate', 0)
        actions = defense_result.get('actions_taken', [])

        first_action = actions[0].replace('📝', '').replace('🛡️', '').replace('⚡', '').replace('🔒', '').replace('🚨', '').replace('💀', '').replace('🔔', '').strip() if actions else '无动作'

        success_str = '成功渗透' if attack_result.get('status') == 'success' else '攻击被拦截'

        reasoning = (
            f"因检测到【{attack_type}】（攻击阶段{phase}/{phase_name}），"
            f"防御等级升至{level}级（{level_name}），"
            f"故触发【{first_action}】策略；"
            f"拦截率{intercept_rate:.0%}，本次攻击{success_str}。"
        )
        return reasoning

    # ───────────────────────── 状态查询 ──────────────────────────

    def get_status(self, session_id: str) -> Dict:
        if session_id not in self.sessions:
            return {'status': 'error', 'message': '会话不存在'}

        session = self.sessions[session_id]
        attacks_list = session.get('attacks', [])

        return {
            'status': 'success',
            'session': {
                'session_id': session_id,
                'environment': session.get('environment', {}),
                'defense_status': self.defense_agent.get_status(session_id),
                'total_attacks': len(attacks_list),
                'attacks': attacks_list[-10:],
                'decision_log': session.get('decision_log', [])[-10:],
                'env_adjustments': session.get('env_adjustments', []),
                'current_intensity': session.get('current_intensity', 5),
                'difficulty_mode': session.get('difficulty_mode', 'single'),
                'recent_intercept_rates': session.get('recent_intercept_rates', []),
                'status': session.get('status', 'active'),
                'created_at': session.get('created_at'),
            }
        }

    def cleanup(self, session_id: str) -> Dict:
        if session_id in self.sessions:
            self.env_agent.destroy_environment(session_id)
            del self.sessions[session_id]
            return {'status': 'success', 'message': f'会话 {session_id} 已清理'}
        return {'status': 'error', 'message': '会话不存在'}


_orchestrator = None

def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
