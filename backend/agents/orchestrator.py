# -*- coding: utf-8 -*-
import threading
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from .env_agent import get_env_agent
from .attack_agent import get_attack_agent
from .defense_agent import get_defense_agent
from services.async_queue import async_queue_service

logger = logging.getLogger('agents.orchestrator')


class Orchestrator:
    """攻防演练编排器 - 协调三个 Agent 进行自动化演练"""
    
    def __init__(self):
        self.env_agent = get_env_agent()
        self.attack_agent = get_attack_agent()
        self.defense_agent = get_defense_agent()
        self.sessions = {}
    
    def create_scenario(self, description: str, user_id: str = None) -> Dict:
        """创建演练场景"""
        env_result = self.env_agent.create_environment(description, user_id)
        
        if env_result.get('status') != 'running':
            return {'status': 'error', 'message': '环境创建失败'}
        
        session_id = env_result['environment_id']
        self.sessions[session_id] = {
            'session_id': session_id,
            'environment': {
                'name': env_result.get('name', '自定义靶场'),
                'components': env_result.get('components', [])
            },
            'defense_status': self.defense_agent.get_status(),
            'attacks': [],
            'status': 'active',
            'created_at': datetime.now().isoformat()
        }
        
        logger.info(f"演练场景创建成功: {session_id}")
        return {'status': 'success', 'session_id': session_id, 'environment': env_result}
    
   
        """执行单次攻击"""
        if session_id not in self.sessions:
            return {'status': 'error', 'message': '会话不存在'}
        
        session = self.sessions[session_id]
        target = session['environment'].get('name', '靶场')
        
        # 规划攻击
        if attack_type:
            plan = {'attack_type': attack_type, 'target': target, 'estimated_success_rate': 0.6}
        else:
            plan = self.attack_agent.plan_attack(target)
        
        def do_attack():
            attack_result = self.attack_agent.execute_attack(plan, intensity)
            
            # 检测攻击
            detection = self.defense_agent.detect_attack(attack_result)
            # 响应攻击
            response = self.defense_agent.respond_to_attack(detection) if detection.get('detected') else {}
            
            attack_record = {
                'attack': attack_result,
                'detection': detection,
                'response': response,
                'executed_at': datetime.now().isoformat()
            }
            
            if 'attacks' not in session:
                session['attacks'] = []
            session['attacks'].append(attack_record)
            
            logger.info(f"攻击执行完成: {attack_result.get('attack_type', 'unknown')}")
            return attack_result
        
        task_id = async_queue_service.add_task(do_attack)
        return {'status': 'accepted', 'task_id': task_id, 'message': '攻击任务已提交'}
def execute_attack(self, session_id: str, attack_type: str = None, intensity: int = 5) -> Dict:
    """执行攻击 - 自动触发防御"""
    if session_id not in self.sessions:
        return {'status': 'error', 'message': '会话不存在'}
    
    session = self.sessions[session_id]
    target = session['environment'].get('name', '靶场')
    
    # 规划攻击
    if attack_type:
        plan = {'attack_type': attack_type, 'target': target, 'estimated_success_rate': 0.6}
    else:
        plan = self.attack_agent.plan_attack(target)
    
    def do_attack():
        # 执行攻击
        attack_result = self.attack_agent.execute_attack(plan, intensity)
        
        # ========== 关键：自动触发防御 ==========
        defense_result = self.defense_agent.detect_and_respond({
            'attack_type': attack_result.get('attack_type'),
            'intensity': intensity,
            'source_ip': f'192.168.1.{random.randint(1,255)}',
            'target': target,
            'payload': attack_result.get('payload', '')
        })
        
        attack_record = {
            'attack': attack_result,
            'defense': defense_result,
            'executed_at': datetime.now().isoformat()
        }
        
        if 'attacks' not in session:
            session['attacks'] = []
        session['attacks'].append(attack_record)
        
        logger.info(f"攻击执行完成: {attack_result.get('attack_type')}, 防御等级: {defense_result.get('defense_level')}")
        return {'attack': attack_result, 'defense': defense_result}
    
    task_id = async_queue_service.add_task(do_attack)
    return {'status': 'accepted', 'task_id': task_id, 'message': '攻击任务已提交，防御已激活'} 
    def get_status(self, session_id: str) -> Dict:
        """获取会话状态"""
        if session_id not in self.sessions:
            return {'status': 'error', 'message': '会话不存在'}
        
        session = self.sessions[session_id]
        attacks_list = session.get('attacks', [])
        
        return {
            'status': 'success',
            'session': {
                'session_id': session_id,
                'environment': session.get('environment', {}),
                'defense_status': self.defense_agent.get_status(),
                'total_attacks': len(attacks_list),
                'attacks': attacks_list[-10:],
                'continuous_active': session.get('continuous_active', False),
                'status': session.get('status', 'active'),
                'created_at': session.get('created_at')
            }
        }
    
    def cleanup(self, session_id: str) -> Dict:
        """清理会话"""
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