#!/usr/bin/env python3
"""
生成毕业答辩 PPT：AI 驱动的靶场自动生成系统
科技深色风格 · 13 张幻灯片
"""
import sys
sys.path.insert(0, '/Users/gw/Library/Python/3.9/lib/python/site-packages')

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE as MSO

# ── 颜色常量 ──────────────────────────────────────────────────────────────
BG      = RGBColor(0x0A, 0x0F, 0x24)
CYAN    = RGBColor(0x00, 0xD4, 0xE8)
CYAN2   = RGBColor(0x00, 0x80, 0xAA)
PURPLE  = RGBColor(0x7B, 0x2F, 0xBE)
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
SILVER  = RGBColor(0xC0, 0xC0, 0xC0)
MUTED   = RGBColor(0x78, 0x88, 0xA0)
CARD    = RGBColor(0x12, 0x1A, 0x36)
CARD2   = RGBColor(0x1A, 0x24, 0x44)
GREEN   = RGBColor(0x67, 0xC2, 0x3A)
ORANGE  = RGBColor(0xE6, 0xA2, 0x3C)
RED     = RGBColor(0xF5, 0x6C, 0x6C)
YELLOW  = RGBColor(0xFC, 0xC4, 0x00)

W = Inches(13.33)
H = Inches(7.5)


def darken(c, factor=5):
    s = str(c)
    return RGBColor(int(s[0:2], 16) // factor, int(s[2:4], 16) // factor, int(s[4:6], 16) // factor)

prs = Presentation()
prs.slide_width  = W
prs.slide_height = H
BLANK = prs.slide_layouts[6]


# ── 工具函数 ──────────────────────────────────────────────────────────────
def slide():
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    return s


def rect(s, x, y, w, h, fill=CARD, border=CYAN2, bw=1.2, shape=MSO.ROUNDED_RECTANGLE):
    sh = s.shapes.add_shape(shape, x, y, w, h)
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = border
    sh.line.width = Pt(bw)
    return sh


def txt(s, text, x, y, w, h, size=14, bold=False, color=WHITE,
        align=PP_ALIGN.LEFT, italic=False):
    tb = s.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    return tb


def title_bar(s, title, subtitle=''):
    # 顶部细条
    rect(s, 0, 0, W, Inches(0.055), fill=CYAN, border=CYAN, bw=0,
         shape=MSO.RECTANGLE)
    # 标题
    txt(s, title, Inches(0.5), Inches(0.1), Inches(12.3), Inches(0.65),
        size=24, bold=True, color=CYAN)
    if subtitle:
        txt(s, subtitle, Inches(0.5), Inches(0.7), Inches(12.3), Inches(0.35),
            size=12, color=MUTED)
    # 分隔线
    rect(s, Inches(0.5), Inches(0.98), Inches(12.3), Inches(0.015),
         fill=CYAN2, border=CYAN2, bw=0, shape=MSO.RECTANGLE)


def card(s, x, y, w, h, header='', body_lines=None,
         border_color=CYAN2, fill=CARD, header_color=CYAN, body_color=SILVER):
    rect(s, x, y, w, h, fill=fill, border=border_color, bw=1.5)
    cx = x + Inches(0.15)
    cw = w - Inches(0.3)
    cy = y + Inches(0.12)
    if header:
        txt(s, header, cx, cy, cw, Inches(0.4), size=13, bold=True,
            color=header_color)
        cy += Inches(0.38)
    if body_lines:
        for line in body_lines:
            txt(s, line, cx, cy, cw, Inches(0.35), size=11, color=body_color)
            cy += Inches(0.3)


def badge(s, text, x, y, color=GREEN, text_color=WHITE):
    rect(s, x, y, Inches(1.6), Inches(0.32), fill=darken(color, 4), border=color, bw=1.2)
    txt(s, text, x, y, Inches(1.6), Inches(0.32), size=10, bold=True,
        color=color, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════
# Slide 1 · 封面
# ═══════════════════════════════════════════════════════════════════════════
s1 = slide()
rect(s1, 0, 0, W, Inches(0.1), fill=CYAN, border=CYAN, bw=0, shape=MSO.RECTANGLE)
rect(s1, 0, Inches(7.4), W, Inches(0.1), fill=PURPLE, border=PURPLE, bw=0,
     shape=MSO.RECTANGLE)

# 中央卡片
rect(s1, Inches(1.2), Inches(1.2), Inches(10.93), Inches(4.8),
     fill=CARD, border=CYAN, bw=2)

txt(s1, 'AI 驱动的靶场自动生成系统',
    Inches(1.8), Inches(1.7), Inches(9.73), Inches(1.1),
    size=34, bold=True, color=CYAN, align=PP_ALIGN.CENTER)

txt(s1, 'AI-Driven Cybersecurity Range Auto-Generation System',
    Inches(1.8), Inches(2.75), Inches(9.73), Inches(0.45),
    size=13, italic=True, color=SILVER, align=PP_ALIGN.CENTER)

txt(s1, '计算机科学与技术专业  ·  本科毕业设计',
    Inches(1.8), Inches(3.3), Inches(9.73), Inches(0.4),
    size=12, color=MUTED, align=PP_ALIGN.CENTER)

txt(s1, '汇报人：XXX          指导老师：XXX          2026 年 5 月',
    Inches(1.8), Inches(3.75), Inches(9.73), Inches(0.4),
    size=11, color=MUTED, align=PP_ALIGN.CENTER)

# 技术栈标签
tags = ['Flask + Vue 3', 'Docker SDK', 'DeepSeek LLM', 'Multi-Agent']
colors_tag = [CYAN, GREEN, ORANGE, PURPLE]
for i, (tag, c) in enumerate(zip(tags, colors_tag)):
    bx = Inches(2.1) + Inches(2.35) * i
    rect(s1, bx, Inches(5.3), Inches(2.0), Inches(0.38),
         fill=darken(c, 5), border=c, bw=1.2)
    txt(s1, tag, bx, Inches(5.3), Inches(2.0), Inches(0.38),
        size=11, bold=True, color=c, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════
# Slide 2 · 研究背景
# ═══════════════════════════════════════════════════════════════════════════
s2 = slide()
title_bar(s2, '研究背景：传统靶场的三大痛点',
          '奇安信2024年度报告指出当前网络安全威胁依然复杂，对实战演训环境提出更高要求')

# 三列痛点卡
pain_points = [
    ('⏳  部署周期长', ['从需求到靶场上线', '通常需要数天至数周', '严重制约演练节奏']),
    ('🔒  场景固化', ['靶场配置一旦完成难以更改', '不同培训目标需重复配置', '缺乏动态适应能力']),
    ('👨‍💻  依赖人工配置', ['需熟悉 Docker/网络/漏洞', '人工成本高、易出错', '门槛高阻碍小团队使用']),
]
for i, (hdr, lines) in enumerate(pain_points):
    cx = Inches(0.5) + Inches(4.22) * i
    card(s2, cx, Inches(1.3), Inches(3.9), Inches(3.6),
         header=hdr, body_lines=lines,
         border_color=RED, header_color=RED, body_color=SILVER)

# 解决方向
rect(s2, Inches(0.5), Inches(5.25), Inches(12.33), Inches(1.6),
     fill=RGBColor(0, 40, 60), border=CYAN, bw=1.5)
txt(s2, '💡  本文方案：自然语言 → LLM 解析 → JSON 配置 → Docker 自动部署',
    Inches(0.8), Inches(5.4), Inches(11.73), Inches(0.45),
    size=14, bold=True, color=CYAN)
txt(s2, '目标：将传统需要数天的靶场搭建工作压缩至分钟级，用户无需具备 Docker 配置知识',
    Inches(0.8), Inches(5.85), Inches(11.73), Inches(0.4),
    size=12, color=SILVER)
txt(s2, '适用场景：轻量级教学实验 · 基础攻防演练 · 快速原型验证',
    Inches(0.8), Inches(6.25), Inches(11.73), Inches(0.35),
    size=11, color=MUTED)


# ═══════════════════════════════════════════════════════════════════════════
# Slide 3 · 系统总体架构
# ═══════════════════════════════════════════════════════════════════════════
s3 = slide()
title_bar(s3, '系统总体架构', 'Flask + Vue 3 前后端分离 · Docker 容器底座 · 三层结构')

layers = [
    ('🖥️  表示层（Vue 3 + Element Plus）',
     ['AI 场景生成页 · 靶场管理页', '攻击面板 · 防御告警 · 拓扑图'],
     CYAN, RGBColor(0,50,70)),
    ('⚙️  服务层（Flask · 多智能体 · LLM · WatchdogService）',
     ['Orchestrator · EnvAgent · AttackAgent · DefenseAgent', 'JWT 认证 · 异步队列 · 模型路由'],
     PURPLE, RGBColor(40,10,70)),
    ('🐳  基础设施层（Docker Engine · SQLite）',
     ['容器生命周期管理 · bridge 网络隔离', '靶场容器 · 攻击容器 · 元数据持久化'],
     GREEN, RGBColor(0,40,10)),
]
for i, (hdr, lines, bc, fc) in enumerate(layers):
    cy = Inches(1.3) + Inches(1.9) * i
    rect(s3, Inches(0.5), cy, Inches(12.33), Inches(1.7),
         fill=fc, border=bc, bw=2)
    txt(s3, hdr, Inches(0.8), cy + Inches(0.12),
        Inches(11.7), Inches(0.45), size=13, bold=True, color=bc)
    for j, line in enumerate(lines):
        txt(s3, '  • ' + line,
            Inches(0.8), cy + Inches(0.55) + Inches(0.38) * j,
            Inches(11.7), Inches(0.35), size=11, color=SILVER)


# ═══════════════════════════════════════════════════════════════════════════
# Slide 4 · 多智能体协同架构
# ═══════════════════════════════════════════════════════════════════════════
s4 = slide()
title_bar(s4, '多智能体协同架构（MAS）',
          'Orchestrator 统一调度 · 三专用 Agent 分工 · 自动化攻防闭环')

# Orchestrator 中心
rect(s4, Inches(4.8), Inches(1.3), Inches(3.73), Inches(1.2),
     fill=RGBColor(0,40,70), border=CYAN, bw=2)
txt(s4, '🎯  Orchestrator 编排器',
    Inches(4.9), Inches(1.42), Inches(3.5), Inches(0.4),
    size=13, bold=True, color=CYAN, align=PP_ALIGN.CENTER)
txt(s4, '任务分发 · 状态管理 · 错误恢复',
    Inches(4.9), Inches(1.82), Inches(3.5), Inches(0.35),
    size=10, color=SILVER, align=PP_ALIGN.CENTER)

# 三个 Agent
agents = [
    ('🌐  EnvAgent\n环境管理智能体',
     ['自然语言 → JSON 配置', 'Docker SDK 创建容器', '少样本样本库管理', '状态同步与数据库写入'],
     GREEN, Inches(0.4)),
    ('⚔️  AttackAgent\n攻击模拟智能体',
     ['6阶段 Kill Chain 建模', '16类攻击类型支持', 'LLM 生成攻击分析', '沙箱模式真实执行'],
     RED, Inches(4.8)),
    ('🛡️  DefenseAgent\n防御分析智能体',
     ['5级防御状态机', 'NIST SP 800-61 参考', 'Docker 容器网络隔离', 'LLM 结构化防御建议'],
     ORANGE, Inches(9.2)),
]
for hdr, lines, bc, ax in agents:
    rect(s4, ax, Inches(2.9), Inches(3.73), Inches(3.8),
         fill=darken(bc, 6), border=bc, bw=1.8)
    txt(s4, hdr, ax + Inches(0.15), Inches(3.0),
        Inches(3.43), Inches(0.65), size=12, bold=True, color=bc)
    for j, line in enumerate(lines):
        txt(s4, '  ▸ ' + line,
            ax + Inches(0.15), Inches(3.7) + Inches(0.35) * j,
            Inches(3.43), Inches(0.32), size=10, color=SILVER)

# 流程箭头文字
txt(s4, '→  环境创建  →  攻击执行  →  防御响应  →  完整闭环',
    Inches(0.5), Inches(6.95), Inches(12.33), Inches(0.4),
    size=12, bold=True, color=MUTED, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════
# Slide 5 · 创新1：多任务模型路由
# ═══════════════════════════════════════════════════════════════════════════
s5 = slide()
title_bar(s5, '创新1 · 多任务模型路由机制',
          '基于 DeepSeek API · Chat (V3) 与 Reasoner (R1) 按任务自动分流 · 差异化温度参数')

rows = [
    ('nlp_understanding', 'Chat',    '0.20', '1000', '语义解析更稳，温度偏低',      CYAN),
    ('range_generation',  'Chat',    '0.10', '2500', '极低温度确保 JSON 结构完整',  GREEN),
    ('attack_analysis',   'Reasoner','0.70', '400',  '中高温度，支持多角度威胁解读', RED),
    ('defense_decision',  'Reasoner','0.05', '800',  '接近零温度，防御判断需确定性', ORANGE),
    ('scenario_expansion','Chat',    '0.65', '1500', '中高温度，生成场景变种',       PURPLE),
]
headers = ['任务类型', '模型', '温度', 'max_tokens', '设计依据']
col_w = [Inches(2.6), Inches(1.4), Inches(0.9), Inches(1.4), Inches(5.5)]
col_x = [Inches(0.4), Inches(3.1), Inches(4.6), Inches(5.6), Inches(7.1)]

# 表头
for hdr, cx, cw in zip(headers, col_x, col_w):
    rect(s5, cx, Inches(1.2), cw, Inches(0.45),
         fill=CARD2, border=CYAN2, bw=1)
    txt(s5, hdr, cx + Inches(0.05), Inches(1.2), cw, Inches(0.45),
        size=11, bold=True, color=CYAN, align=PP_ALIGN.CENTER)

# 数据行
for i, (task, model, temp, tok, desc, bc) in enumerate(rows):
    ry = Inches(1.7) + Inches(0.8) * i
    vals = [task, model, temp, tok, desc]
    for cx, cw, val in zip(col_x, col_w, vals):
        fill = darken(bc, 8) if val == task else CARD
        brd = bc if val == task else CYAN2
        rect(s5, cx, ry, cw, Inches(0.72), fill=fill, border=brd, bw=0.8)
        c = bc if val == task else SILVER
        txt(s5, val, cx + Inches(0.05), ry, cw, Inches(0.72),
            size=10 if val != desc else 9, color=c)

txt(s5, '每次路由调用均记录日志：task_type → model + temperature + max_tokens，便于性能分析',
    Inches(0.4), Inches(6.0), Inches(12.5), Inches(0.38),
    size=10, italic=True, color=MUTED)


# ═══════════════════════════════════════════════════════════════════════════
# Slide 6 · 创新2：少样本学习机制
# ═══════════════════════════════════════════════════════════════════════════
s6 = slide()
title_bar(s6, '创新2 · 少样本学习机制（In-Context Learning）',
          '不对模型做参数训练，利用历史成功部署案例引导 LLM 输出结构稳定的靶场配置')

steps = [
    ('① 样本积累', GREEN,
     ['每次靶场成功部署后', '自动保存"用户描述 → 最终配置"对', '附时间戳存至 training_examples.json']),
    ('② 关键词匹配', CYAN,
     ['新请求到来时', '计算与历史样本的词汇重叠度', '取得分最高的 1~3 条作为参考案例']),
    ('③ Prompt 注入', ORANGE,
     ['以"输入→输出"对的形式注入系统提示', '引导模型按相似结构生成配置', '无需额外存储或向量数据库']),
]
for i, (hdr, bc, lines) in enumerate(steps):
    cx = Inches(0.4) + Inches(4.25) * i
    rect(s6, cx, Inches(1.3), Inches(3.95), Inches(3.5),
         fill=darken(bc, 7), border=bc, bw=2)
    txt(s6, hdr, cx + Inches(0.15), Inches(1.45), Inches(3.6), Inches(0.45),
        size=14, bold=True, color=bc)
    for j, line in enumerate(lines):
        txt(s6, '  • ' + line,
            cx + Inches(0.15), Inches(1.95) + Inches(0.4) * j,
            Inches(3.6), Inches(0.36), size=11, color=SILVER)

# 效果数据
rect(s6, Inches(0.4), Inches(5.1), Inches(12.5), Inches(1.75),
     fill=RGBColor(0,40,10), border=GREEN, bw=1.5)
txt(s6, '📊  少样本学习效果验证结果',
    Inches(0.7), Inches(5.2), Inches(11.9), Inches(0.4),
    size=13, bold=True, color=GREEN)
metrics = [
    '0-shot 基线：约 19% 准确率',
    '5-shot 最优：约 70% 准确率（+51个百分点）',
    '10-shot 回落至 64%（样本过多引入噪声）',
    '配合 JSON Schema 校验+白名单补全，实际可用性可达 90% 以上',
]
for j, m in enumerate(metrics):
    txt(s6, '  ✓  ' + m,
        Inches(0.7), Inches(5.65) + Inches(0.26) * j,
        Inches(11.9), Inches(0.25), size=10, color=SILVER)


# ═══════════════════════════════════════════════════════════════════════════
# Slide 7 · 创新3：配置可靠性双重保障
# ═══════════════════════════════════════════════════════════════════════════
s7 = slide()
title_bar(s7, '创新3 · 配置可靠性双重保障',
          '针对 LLM 输出不稳定问题，Prompt 层约束 + 代码层补全，缺一不可')

# 左：白名单
rect(s7, Inches(0.4), Inches(1.3), Inches(6.0), Inches(5.55),
     fill=RGBColor(0,40,70), border=CYAN, bw=2)
txt(s7, '🛡️  第一道防线：镜像白名单（Prompt层）',
    Inches(0.6), Inches(1.42), Inches(5.7), Inches(0.45),
    size=12, bold=True, color=CYAN)
wl_items = [
    '共 13 种经过实测验证的镜像',
    '基础设施镜像（10种）：',
    '  nginx · httpd · php · mysql · redis',
    '  postgres · ubuntu · python · node · alpine',
    '漏洞靶场镜像（3种）：',
    '  DVWA · WebGoat · JuiceShop',
    '',
    '每个条目包含：正确 tag · 必需环境变量',
    '  · 启动命令 · 暴露端口',
    '',
    '以约束条件形式写入 Prompt 传给 LLM',
]
for j, item in enumerate(wl_items):
    txt(s7, item, Inches(0.65), Inches(1.9) + Inches(0.32) * j,
        Inches(5.5), Inches(0.3), size=10,
        color=CYAN if ('镜像' in item and '：' in item) else SILVER)

# 右：代码补全
rect(s7, Inches(6.7), Inches(1.3), Inches(6.23), Inches(5.55),
     fill=RGBColor(40,20,0), border=ORANGE, bw=2)
txt(s7, '🔧  第二道防线：代码层自动补全（_patch_components）',
    Inches(6.9), Inches(1.42), Inches(5.93), Inches(0.45),
    size=12, bold=True, color=ORANGE)
patch_items = [
    '对 LLM 返回的每个容器配置自动校验：',
    '',
    '  ✓  镜像名不在白名单 → 替换为最近似镜像',
    '  ✓  缺少必需环境变量 → 从白名单填入默认值',
    '  ✓  缺少启动命令 → 自动补 sleep infinity',
    '  ✓  端口号异常 → 用镜像默认端口覆盖',
    '',
    '降级策略（LLM 连续 3 次解析失败）：',
    '  → 降低 temperature 重试',
    '  → 最终回退到预设默认靶场模板',
    '  → 保证任务流程不中断',
]
for j, item in enumerate(patch_items):
    txt(s7, item, Inches(6.9), Inches(1.9) + Inches(0.32) * j,
        Inches(5.93), Inches(0.3), size=10,
        color=ORANGE if item.startswith('  ✓') or '降级' in item else SILVER)


# ═══════════════════════════════════════════════════════════════════════════
# Slide 8 · 真实化落地1：Docker 容器网络隔离
# ═══════════════════════════════════════════════════════════════════════════
s8 = slide()
title_bar(s8, '真实化落地 Level 1 · Docker 容器网络隔离',
          '防御等级 ≥ 4（封禁级）时，通过 Docker SDK 真实断开靶场容器的网络连接')

# 左：触发条件
rect(s8, Inches(0.4), Inches(1.3), Inches(5.5), Inches(5.6),
     fill=RGBColor(50,10,10), border=RED, bw=2)
txt(s8, '🔴  触发条件', Inches(0.6), Inches(1.42), Inches(5.2), Inches(0.4),
    size=12, bold=True, color=RED)
trigger_items = [
    '攻击阶段4（持久化/提权）+ 任意强度',
    '攻击阶段3（漏洞利用）+ 强度 ≥ 5',
    '攻击阶段2（武器化）+ 强度 ≥ 8',
    '',
    '强度加成规则：',
    '  < 5 → +0    5-7 → +1    ≥ 8 → +2',
    '',
    '本次实现前：',
    '  所有"封禁"= 追加字符串 + 内存列表',
    '  ← 纯仿真，无实际网络效果',
    '',
    '本次实现后：',
    '  调用 docker.networks.get(net)',
    '  .disconnect(container, force=True)',
    '  ← 可通过 docker inspect 验证',
]
for j, item in enumerate(trigger_items):
    c = RED if '本次实现' in item else (ORANGE if item.startswith('  <') else SILVER)
    txt(s8, item, Inches(0.65), Inches(1.88) + Inches(0.295) * j,
        Inches(5.1), Inches(0.28), size=9.5, color=c)

# 右：实现细节
rect(s8, Inches(6.2), Inches(1.3), Inches(6.73), Inches(5.6),
     fill=RGBColor(0,30,50), border=CYAN, bw=2)
txt(s8, '🔒  实现细节', Inches(6.4), Inches(1.42), Inches(6.4), Inches(0.4),
    size=12, bold=True, color=CYAN)
impl_items = [
    'services/docker_isolate.py',
    '',
    '1. 通过端口查 targets 表，找 container_name',
    '2. 断开所有 bridge 网络（host/none 保留）',
    '3. 写入 _blocked 字典，记录隔离时间戳',
    '4. 60s 后守护线程自动重连网络',
    '',
    '新增 API 端点：',
    '  GET  /api/defense/blocked',
    '       → 查询当前隔离中的容器列表',
    '  POST /api/defense/unblock/<name>',
    '       → 手动提前解除隔离',
    '',
    '降级保护：Docker 不可用时回退文本记录',
    '  演练流程不中断',
]
for j, item in enumerate(impl_items):
    c = GREEN if 'GET' in item or 'POST' in item else (CYAN if item.startswith('services') else SILVER)
    txt(s8, item, Inches(6.4), Inches(1.88) + Inches(0.295) * j,
        Inches(6.4), Inches(0.28), size=9.5, color=c)


# ═══════════════════════════════════════════════════════════════════════════
# Slide 9 · 真实化落地2：沙箱攻击模式
# ═══════════════════════════════════════════════════════════════════════════
s9 = slide()
title_bar(s9, '真实化落地 Level 2 · 沙箱攻击模式',
          '使用 python:3.11-slim 容器执行真实命令，产生真实网络请求与输出')

# 左：原理
rect(s9, Inches(0.4), Inches(1.3), Inches(5.5), Inches(5.6),
     fill=RGBColor(40,20,0), border=ORANGE, bw=2)
txt(s9, '🔥  工作原理', Inches(0.6), Inches(1.42), Inches(5.2), Inches(0.4),
    size=12, bold=True, color=ORANGE)
principle = [
    '1.  查询目标容器的 Docker 内网 IP',
    '2.  启动 python:3.11-slim 攻击容器',
    '    接入目标容器所在 bridge 网络',
    '3.  执行对应攻击的 Python 脚本',
    '    (socket/urllib 实现，无需额外工具)',
    '4.  收集真实输出（JSON 格式化）',
    '5.  超时(20s)后强制销毁，不留残留',
    '',
    '支持的 9 类攻击（真实执行）：',
    '  端口扫描 · 服务识别 · SQL注入',
    '  XSS · SSRF · 目录枚举',
    '  暴力破解 · 横向移动 · 数据外传',
    '',
    '其余类型：自动降级为 LLM 仿真模式',
]
for j, item in enumerate(principle):
    c = GREEN if '支持' in item else (ORANGE if '端口' in item or 'XSS' in item or '暴' in item else SILVER)
    txt(s9, item, Inches(0.65), Inches(1.88) + Inches(0.3) * j,
        Inches(5.1), Inches(0.28), size=9.5, color=c)

# 右：前端展示
rect(s9, Inches(6.2), Inches(1.3), Inches(6.73), Inches(5.6),
     fill=RGBColor(0,20,40), border=CYAN, bw=2)
txt(s9, '💻  前端沙箱输出卡片（示例）', Inches(6.4), Inches(1.42), Inches(6.4), Inches(0.4),
    size=12, bold=True, color=CYAN)

# 模拟终端输出
rect(s9, Inches(6.45), Inches(1.88), Inches(6.23), Inches(4.0),
     fill=RGBColor(0x0d, 0x11, 0x17), border=ORANGE, bw=1)
terminal_lines = [
    ('// 端口扫描真实输出', MUTED),
    ('{', SILVER),
    ('  "target": "172.17.0.3",', SILVER),
    ('  "open_ports": [', SILVER),
    ('    {"port": 80, "state": "open",', GREEN),
    ('     "banner": "HTTP/1.1 200 OK"},', GREEN),
    ('    {"port": 3306, "state": "open",', GREEN),
    ('     "banner": "5.7.38-MySQL"}', GREEN),
    ('  ],', SILVER),
    ('  "total": 2', CYAN),
    ('}', SILVER),
]
for j, (line, c) in enumerate(terminal_lines):
    txt(s9, line, Inches(6.55), Inches(1.95) + Inches(0.34) * j,
        Inches(6.0), Inches(0.32), size=9.5, color=c)

txt(s9, '前端攻击面板新增"执行模式"卡片切换器，沙箱激活时橙色高亮',
    Inches(6.4), Inches(6.1), Inches(6.4), Inches(0.35),
    size=9.5, italic=True, color=MUTED)


# ═══════════════════════════════════════════════════════════════════════════
# Slide 10 · WatchdogService
# ═══════════════════════════════════════════════════════════════════════════
s10 = slide()
title_bar(s10, '后台守护 · WatchdogService 监控服务',
          '"注册-巡检-告警"三阶段设计 · 守护线程 · 不占用主线程资源')

monitors = [
    ('🔴  CPU 使用率',    '80%',  '30s', 'check_cpu_usage()',    RED),
    ('🟡  内存使用率',   '85%',  '30s', 'check_memory_usage()', ORANGE),
    ('🔵  磁盘使用率',   '90%',  '60s', 'check_disk_usage()',   CYAN),
    ('🟢  Docker 容器数', '无阈值','30s', 'check_docker_containers()', GREEN),
]
for i, (name, threshold, interval, func, bc) in enumerate(monitors):
    cy = Inches(1.3) + Inches(1.27) * i
    rect(s10, Inches(0.4), cy, Inches(12.5), Inches(1.18),
         fill=darken(bc, 8), border=bc, bw=1.5)
    txt(s10, name, Inches(0.65), cy + Inches(0.1), Inches(3.5), Inches(0.45),
        size=12, bold=True, color=bc)
    txt(s10, f'阈值：{threshold}    巡检间隔：{interval}',
        Inches(4.3), cy + Inches(0.1), Inches(4.0), Inches(0.45),
        size=11, color=SILVER)
    txt(s10, func, Inches(8.5), cy + Inches(0.1), Inches(4.0), Inches(0.45),
        size=10, color=MUTED, italic=True)
    desc = '超阈值时写入内存告警队列（滚动保留100条），logging.WARNING 输出' if threshold != '无阈值' \
           else '仅记录容器数量，用于基线分析和趋势追踪，不触发告警'
    txt(s10, '  → ' + desc, Inches(0.65), cy + Inches(0.6), Inches(12.0), Inches(0.35),
        size=9.5, color=MUTED)

txt(s10, 'psutil 提供跨平台系统指标采集 · 依赖缺失时返回合理默认值（CPU 25%）保证服务正常启动',
    Inches(0.4), Inches(6.5), Inches(12.5), Inches(0.38),
    size=10, italic=True, color=MUTED)


# ═══════════════════════════════════════════════════════════════════════════
# Slide 11 · 测试结果
# ═══════════════════════════════════════════════════════════════════════════
s11 = slide()
title_bar(s11, '测试与性能评估',
          '测试环境：Windows 11 · i7-12700H · 16GB · Docker Desktop · DeepSeek API')

# 三列关键数字
kpi = [
    ('⏱️  靶场生成时间', [
        '配置生成（LLM）：平均 4.56s',
        '容器创建（缓存镜像）：平均 2.10s',
        '端到端总耗时：平均 6.65s',
        '最快（单组件+缓存）：~5.35s',
    ], CYAN),
    ('📊  少样本学习效果', [
        '0-shot 准确率：~19%',
        '5-shot 准确率：~70%（+51pp）',
        '10-shot 回落：~64%（噪声影响）',
        '配合白名单补全：实际可用率 >90%',
    ], GREEN),
    ('🌐  API 响应时间', [
        '主要接口响应：~2050ms',
        '（含 WatchdogService 2s 轮询开销）',
        '波动范围：±10ms 以内',
        'LLM 接口（异步处理）：3-5s',
    ], ORANGE),
]
for i, (hdr, lines, bc) in enumerate(kpi):
    cx = Inches(0.4) + Inches(4.25) * i
    rect(s11, cx, Inches(1.3), Inches(3.95), Inches(3.5),
         fill=darken(bc, 7), border=bc, bw=2)
    txt(s11, hdr, cx + Inches(0.15), Inches(1.42), Inches(3.6), Inches(0.45),
        size=12, bold=True, color=bc)
    for j, line in enumerate(lines):
        txt(s11, '  • ' + line, cx + Inches(0.15),
            Inches(1.92) + Inches(0.42) * j, Inches(3.6), Inches(0.38),
            size=10, color=SILVER)

# 底部局限性
rect(s11, Inches(0.4), Inches(5.05), Inches(12.5), Inches(1.75),
     fill=RGBColor(30,20,0), border=ORANGE, bw=1.5)
txt(s11, '⚠️  当前局限性',
    Inches(0.7), Inches(5.15), Inches(11.9), Inches(0.38),
    size=11, bold=True, color=ORANGE)
lims = [
    '单机 Docker 部署：靶场规模受宿主机资源限制（WatchdogService 85% 内存阈值提前预警）',
    'LLM 输出偶发不稳定：多层降级策略兜底（3次重试 → 回退默认模板）',
    '镜像白名单范围：目前 13 种，扩展新镜像需手工验证参数（持续维护成本）',
]
for j, lim in enumerate(lims):
    txt(s11, '  • ' + lim, Inches(0.7), Inches(5.55) + Inches(0.38) * j,
        Inches(11.9), Inches(0.35), size=10, color=SILVER)


# ═══════════════════════════════════════════════════════════════════════════
# Slide 12 · 总结与展望
# ═══════════════════════════════════════════════════════════════════════════
s12 = slide()
title_bar(s12, '总结与展望')

# 完成项
rect(s12, Inches(0.4), Inches(1.3), Inches(6.0), Inches(5.5),
     fill=RGBColor(0,35,10), border=GREEN, bw=2)
txt(s12, '✅  已完成的主要工作', Inches(0.6), Inches(1.42), Inches(5.7), Inches(0.4),
    size=13, bold=True, color=GREEN)
done = [
    '多智能体协同靶场自动生成架构',
    '  EnvAgent / AttackAgent / DefenseAgent',
    '多任务模型路由（5种任务类型）',
    '  Chat & Reasoner 差异化温度参数',
    '少样本学习机制（关键词频率匹配）',
    '  0-shot→5-shot 准确率提升 51pp',
    '双重配置保障（白名单 + 代码补全）',
    '  AI 生成靶场实际可用率 >90%',
    'WatchdogService（CPU/内存/磁盘/容器）',
    'Docker 容器网络隔离（level≥4 真实断网）',
    '沙箱攻击模式（9类真实命令执行）',
    '前端全功能管理面板（Vue 3）',
]
for j, item in enumerate(done):
    c = GREEN if not item.startswith('  ') else SILVER
    txt(s12, item, Inches(0.65), Inches(1.88) + Inches(0.3) * j,
        Inches(5.5), Inches(0.28), size=9.5, color=c)

# 展望
rect(s12, Inches(6.7), Inches(1.3), Inches(6.23), Inches(5.5),
     fill=RGBColor(0,20,50), border=CYAN, bw=2)
txt(s12, '🔭  未来工作方向', Inches(6.9), Inches(1.42), Inches(5.9), Inches(0.4),
    size=13, bold=True, color=CYAN)
future = [
    '① Kubernetes 多节点扩展',
    '  跨节点分布式靶场编排',
    '  弹性伸缩，突破单机资源瓶颈',
    '',
    '② 强化学习驱动攻防对抗',
    '  攻防 Agent 改造为 RL 智能体',
    '  LLM + RL 结合，早期训练 2× 奖励提升',
    '  （参考 Tholl 等人研究）',
    '',
    '③ CVE/NVD 知识图谱增强',
    '  根据 CVE 编号自动生成漏洞靶场',
    '  提升训练场景与真实威胁的对应精度',
]
for j, item in enumerate(future):
    c = CYAN if item.startswith('①') or item.startswith('②') or item.startswith('③') else SILVER
    txt(s12, item, Inches(6.9), Inches(1.88) + Inches(0.3) * j,
        Inches(5.9), Inches(0.28), size=9.5, color=c)


# ═══════════════════════════════════════════════════════════════════════════
# Slide 13 · 致谢
# ═══════════════════════════════════════════════════════════════════════════
s13 = slide()
rect(s13, 0, 0, W, Inches(0.1), fill=CYAN, border=CYAN, bw=0, shape=MSO.RECTANGLE)
rect(s13, 0, Inches(7.4), W, Inches(0.1), fill=PURPLE, border=PURPLE, bw=0,
     shape=MSO.RECTANGLE)

rect(s13, Inches(1.8), Inches(1.8), Inches(9.73), Inches(3.5),
     fill=CARD, border=CYAN, bw=2)
txt(s13, '感谢各位评委老师聆听与指导！',
    Inches(2.3), Inches(2.2), Inches(8.73), Inches(1.0),
    size=28, bold=True, color=CYAN, align=PP_ALIGN.CENTER)
txt(s13, '恳请各位老师批评指正',
    Inches(2.3), Inches(3.2), Inches(8.73), Inches(0.5),
    size=16, color=SILVER, align=PP_ALIGN.CENTER)

# 代码指标小结
for i, (k, v, c) in enumerate([
    ('代码文件', '~30+', CYAN),
    ('攻击类型', '16 种', RED),
    ('支持镜像', '13 种', GREEN),
    ('API 端点', '40+', ORANGE),
]):
    bx = Inches(2.1) + Inches(2.35) * i
    rect(s13, bx, Inches(5.3), Inches(2.0), Inches(1.1),
         fill=darken(c, 6), border=c, bw=1.2)
    txt(s13, v, bx, Inches(5.35), Inches(2.0), Inches(0.55),
        size=22, bold=True, color=c, align=PP_ALIGN.CENTER)
    txt(s13, k, bx, Inches(5.87), Inches(2.0), Inches(0.35),
        size=10, color=MUTED, align=PP_ALIGN.CENTER)


# ── 保存 ──────────────────────────────────────────────────────────────────
out = '/Applications/AI-range/0506_range/答辩PPT_AI靶场系统.pptx'
prs.save(out)
print(f'✓ 已生成：{out}')
print(f'  共 {len(prs.slides)} 张幻灯片')
