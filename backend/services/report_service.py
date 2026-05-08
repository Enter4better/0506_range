# -*- coding: utf-8 -*-
"""
攻防演练报告生成服务

自动从 session 数据中提取：
  - 攻击路径（阶段时间线）
  - 防御效果（拦截率趋势）
  - 漏洞分布（攻击类型占比）
  - 可解释决策链
  - AI生成安全建议
"""
import json
import logging
from datetime import datetime
from collections import Counter
from typing import Dict, List, Optional

logger = logging.getLogger('services.report')


class ReportService:

    def generate(self, session_id: str, session: Dict,
                 attack_agent, defense_agent) -> Dict:
        """生成完整演练报告"""
        attacks = session.get('attacks', [])
        env = session.get('environment', {})
        decision_log = session.get('decision_log', [])
        env_adjustments = session.get('env_adjustments', [])

        # 1. 攻击路径时间线
        attack_path = self._build_attack_path(attacks)

        # 2. 防御效果统计
        defense_stats = self._build_defense_stats(attacks)

        # 3. 漏洞分布
        vuln_distribution = self._build_vuln_distribution(attacks)

        # 4. 难度演化曲线
        difficulty_curve = self._build_difficulty_curve(attacks, session)

        # 5. AI生成安全建议
        ai_recommendations = self._generate_ai_recommendations(
            attack_agent, vuln_distribution, defense_stats, session
        )

        # 6. 总体评分
        score = self._calculate_score(defense_stats)

        return {
            'report_id': f'rpt_{session_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'generated_at': datetime.now().isoformat(),
            'session_id': session_id,
            'range_name': env.get('name', '未知靶场'),
            'duration_desc': self._calc_duration(session),
            'total_attacks': len(attacks),
            'overall_score': score,
            'attack_path': attack_path,
            'defense_stats': defense_stats,
            'vuln_distribution': vuln_distribution,
            'difficulty_curve': difficulty_curve,
            'decision_log': decision_log[-20:],
            'env_adjustments': env_adjustments,
            'ai_recommendations': ai_recommendations,
            'summary': self._build_summary(score, defense_stats, vuln_distribution),
        }

    # ── 攻击路径 ──────────────────────────────────────────────────

    def _build_attack_path(self, attacks: List) -> List[Dict]:
        path = []
        for i, record in enumerate(attacks):
            atk = record.get('attack', {})
            dfs = record.get('defense', {})
            path.append({
                'step': i + 1,
                'time': record.get('executed_at', ''),
                'attack_type': atk.get('attack_type', ''),
                'phase': atk.get('attack_phase', 1),
                'phase_name': atk.get('phase_name', ''),
                'intensity': atk.get('intensity', 5),
                'success': atk.get('status') == 'success',
                'combo_chain': atk.get('combo_chain', []),
                'defense_level': dfs.get('defense_level', 1),
                'intercepted': dfs.get('intercept_rate', 0) > 0.5,
                'reasoning': record.get('reasoning', ''),
            })
        return path

    # ── 防御效果 ──────────────────────────────────────────────────

    def _build_defense_stats(self, attacks: List) -> Dict:
        if not attacks:
            return {'intercept_avg': 0, 'max_level': 0, 'blocked_ips': 0,
                    'intercept_trend': [], 'actions_summary': {}}

        intercept_rates = []
        max_level = 0
        blocked_ips = set()
        all_actions = []

        for record in attacks:
            dfs = record.get('defense', {})
            intercept_rates.append(dfs.get('intercept_rate', 0))
            lv = dfs.get('defense_level', 0)
            if lv > max_level:
                max_level = lv
            for ip in dfs.get('blocked_ips', []):
                blocked_ips.add(ip)
            all_actions.extend(dfs.get('actions_taken', []))

        # 动作分类统计（去除 emoji）
        action_counter = Counter()
        for a in all_actions:
            clean = a.split('：')[0].strip().lstrip('📝🛡️⚡🔒🚨💀🔔 ')
            action_counter[clean] += 1

        return {
            'intercept_avg': round(sum(intercept_rates) / len(intercept_rates), 3),
            'intercept_trend': [round(r, 3) for r in intercept_rates],
            'max_level': max_level,
            'blocked_ips': len(blocked_ips),
            'actions_summary': dict(action_counter.most_common(8)),
        }

    # ── 漏洞分布 ──────────────────────────────────────────────────

    def _build_vuln_distribution(self, attacks: List) -> List[Dict]:
        counter = Counter()
        for record in attacks:
            atk = record.get('attack', {})
            t = atk.get('attack_type', '未知')
            counter[t] += 1
        total = sum(counter.values()) or 1
        return [
            {'name': k, 'count': v, 'percent': round(v / total * 100, 1)}
            for k, v in counter.most_common()
        ]

    # ── 难度演化 ──────────────────────────────────────────────────

    def _build_difficulty_curve(self, attacks: List, session: Dict) -> List[Dict]:
        curve = []
        for i, record in enumerate(attacks):
            atk = record.get('attack', {})
            curve.append({
                'step': i + 1,
                'intensity': atk.get('intensity', 5),
                'phase': atk.get('attack_phase', 1),
                'combo': len(atk.get('combo_chain', [])) > 1,
                'adapt_msg': record.get('adapt_msg', ''),
            })
        return curve

    # ── AI 安全建议 ───────────────────────────────────────────────

    def _generate_ai_recommendations(self, attack_agent, vuln_dist: List,
                                      defense_stats: Dict, session: Dict) -> List[str]:
        top_vulns = [v['name'] for v in vuln_dist[:5]]
        avg_intercept = defense_stats.get('intercept_avg', 0)

        prompt = f"""你是一位高级网络安全顾问，请根据以下攻防演练数据生成安全建议：

主要漏洞类型：{', '.join(top_vulns)}
平均防御拦截率：{avg_intercept:.0%}
最高防御等级：{defense_stats.get('max_level', 1)}级
封禁IP数：{defense_stats.get('blocked_ips', 0)}
环境调整次数：{len(session.get('env_adjustments', []))}

请给出5条具体、可操作的安全加固建议，每条50字以内，用JSON数组格式返回：
["建议1", "建议2", "建议3", "建议4", "建议5"]
"""
        try:
            resp = attack_agent.ai_chat(prompt, task_type='report_generation')
            import re
            match = re.search(r'\[.*?\]', resp, re.DOTALL)
            if match:
                recs = json.loads(match.group())
                if isinstance(recs, list):
                    return [str(r) for r in recs[:5]]
        except Exception as e:
            logger.warning(f"AI建议生成失败: {e}")

        # 降级：基于规则的建议
        fallback = []
        if top_vulns:
            fallback.append(f'针对{top_vulns[0]}实施参数化查询或输入过滤')
        if avg_intercept < 0.5:
            fallback.append('当前防御拦截率偏低，建议升级WAF规则库并开启IPS模式')
        if defense_stats.get('max_level', 1) >= 4:
            fallback.append('演练中触发IP封禁，建议定期审查黑名单并实施地理围栏')
        fallback += ['定期进行红蓝对抗演练以持续验证防御效果',
                     '建立安全事件响应手册，缩短MTTR（平均响应时间）']
        return fallback[:5]

    # ── 评分 & 摘要 ───────────────────────────────────────────────

    def _calculate_score(self, defense_stats: Dict) -> Dict:
        avg = defense_stats.get('intercept_avg', 0)
        level = defense_stats.get('max_level', 1)
        score = round(avg * 60 + level / 5 * 40)
        if score >= 80:
            grade, label = 'A', '优秀'
        elif score >= 60:
            grade, label = 'B', '良好'
        elif score >= 40:
            grade, label = 'C', '一般'
        else:
            grade, label = 'D', '待提升'
        return {'score': score, 'grade': grade, 'label': label}

    def _calc_duration(self, session: Dict) -> str:
        created = session.get('created_at', '')
        if not created:
            return '未知'
        try:
            start = datetime.fromisoformat(created)
            minutes = int((datetime.now() - start).total_seconds() / 60)
            return f'{minutes} 分钟' if minutes < 60 else f'{minutes // 60}小时{minutes % 60}分钟'
        except Exception:
            return '未知'

    def _build_summary(self, score: Dict, defense_stats: Dict, vuln_dist: List) -> str:
        top = vuln_dist[0]['name'] if vuln_dist else '未知'
        avg = defense_stats.get('intercept_avg', 0)
        return (
            f"本次演练整体评分{score['score']}分（{score['grade']}级-{score['label']}）。"
            f"主要威胁为【{top}】，平均防御拦截率{avg:.0%}。"
            f"共触发{defense_stats.get('max_level', 1)}级最高防御响应，"
            f"封禁{defense_stats.get('blocked_ips', 0)}个恶意IP。"
        )


_report_service = None

def get_report_service() -> ReportService:
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service
