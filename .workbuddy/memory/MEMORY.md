# 长期记忆

## 用户偏好

- **文件默认输出目录**：`D:\软件安装\`（用户于2026-05-12指定）

## 项目背景

- 用户正在开发「AI攻防靶场管理系统」毕业设计
- 技术栈：Flask + Docker SDK + JWT
- 后端路径：`D:/0503/AI_range/`
- 论文文档路径：`D:/毕设/`

## 双模型测试结果（2026-05-14）

通过50轮×5任务的实测，发现原论文数据有偏差，已调整模型分配：

| 任务类型 | 原配置 | 实测Chat成功率 | 实测Reasoner成功率 | 调整后 |
|---------|-------|--------------|-----------------|-------|
| attack_planning | Reasoner | 100% | 92% | **Chat** |
| security_classification | Chat | 100% | 84% | **Chat** (不变) |
| attack_analysis | Reasoner | 100% | 100% | Reasoner (不变) |
| defense_decision | Reasoner | 100% | 100% | Reasoner (不变) |
| range_generation | Chat | 100% | 100% | Chat (不变) |

关键发现：Reasoner模型在**简单分类**和**结构化规划**任务上反而成功率更低。

## DefenseAgent LLM结构化建议（2026-05-15）

实现了论文中描述的LLM生成结构化防御建议功能：

### 新增文件
- `backend/models/defense_alert.py` - 防御警报模型
- `backend/services/database.py` - 添加 defense_alerts 表

### 修改文件
- `backend/agents/defense_agent.py` - 添加 `_generate_defense_suggestion()` 方法
- `backend/routes/defenses.py` - 添加 `/api/defense/alerts` 等API
- `frontend/src/views/DefensePanel.vue` - 展示LLM生成的建议

### 功能实现
- LLM调用（defense_decision任务，deepseek-reasoner模型，temp=0.05，max_tokens=800）
- 生成MITRE ATT&CK分类（tactic/technique）
- 生成影响评估
- 生成处置建议列表
- 生成规则建议（WAF/iptables片段）
- 存入defense_alerts表
- 实时推送到前端（5秒轮询）

### MITRE ATT&CK映射表
支持16种攻击类型的MITRE分类：SQL注入、XSS、CSRF、端口扫描、暴力破解等。

## 小红书MCP（2026-05-12接入）

- MCP 程序位置：`D:/软件安装/xiaohongshu-mcp-windows-amd64/`
- 关键发现：服务器使用 `Mcp-Session-Id` HTTP 头进行会话管理（每次 initialize 后从响应头获取，后续所有请求必须带上）
- Skill 位置：`C:/Users/王山而/.workbuddy/skills/xiaohongshu-mcp/`
- MCP URL：`http://localhost:18060/mcp`
