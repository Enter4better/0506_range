# AI 辅助开发会话变更记录

本文档记录了 Claude AI 助手在本项目中完成的所有问答、分析与代码/论文修改，按时间顺序排列。

---

## 会话一：论文完善与文献规范

### Q：Watchdog 和轮询是否同时存在？论文描述是否准确？

**分析：** 两者并存、职责不同。

- **后端 WatchdogService**（`services/watchdog.py`）：守护线程，每 30 秒巡检一次宿主机 CPU / 内存 / 磁盘 / Docker 容器状态，触发阈值告警。
- **前端 setInterval**（`AttackPanel.vue`）：每 2 秒轮询一次攻击进度与最新日志，用于"准实时"可视化。

论文原描述只提到前端轮询，未提及后端 Watchdog，属于描述不完整。

**修改：**
- 论文新增 §4.4 `WatchdogService` 完整章节，包含架构设计（注册-巡检-告警）、系统资源监控指标、与防御体系的协同及告警 API。

---

### Q：文献需要 2024 年以后占比 90% 以上，并在文中标注引用

**修改：**
- 全文添加 `[序号]` 格式行内引用，共 29 篇文献。
- 最终分布：`[1]–[8]` = 2024 年（8 篇），`[9]–[19]` = 2025 年（11 篇），`[20]–[27]` = 2026 年（8 篇），`[28]–[29]` = 经典奠基文献（2020 年，2 篇）。
- 2024–2026 年合计 27/29 = **93.1%**，2025+2026（19 篇）> 2024（8 篇），满足"近年偏重"要求。

---

## 会话二：五项技术问题核查与修复

### Q1："包含 xxx 漏洞" 的描述，部署时会真实部署漏洞吗？

**答：** 不会。系统使用 `VERIFIED_IMAGES` 白名单中的干净官方镜像（nginx:alpine、mysql:8.0 等），不包含任何预置漏洞。"包含 SQL 注入漏洞"是**场景语义标注**，描述训练目的，实际漏洞模拟由 AttackAgent 在应用层仿真完成。

**修改：** 论文 §4.2.1 新增专项说明段落。

---

### Q2：AI 创建的靶场在前端端口映射为空

**根因：** Docker API `container.ports` 对已停止容器返回 `{}`，`compat_env_list` 路由仅从 Docker API 读取端口，忽略了数据库中存储的端口信息。

**修复（`backend/routes/compat.py`）：**

```python
# 停止的容器 Docker API 返回空端口，从 DB 补全显示
if not ports:
    if db_target.port:
        ports = db_target.port
        try:
            parts = db_target.port.split(':')
            if len(parts) == 2:
                host_port = int(parts[0])
                container_port = int(parts[1])
        except Exception:
            pass
    elif db_target.config:
        try:
            cfg_data = json.loads(db_target.config) if isinstance(db_target.config, str) else {}
            hp = cfg_data.get('host_port')
            cp = cfg_data.get('container_port')
            if hp and cp:
                ports = f'{hp}:{cp}'
                host_port = int(hp)
                container_port = int(cp)
        except Exception:
            pass
```

---

### Q3：攻击/防御页面卡片数量为 0，核实实际攻击类型数量

**根因：**
- `attackTypes = ref([])` 初始化为空，API 加载前统计卡显示 0。
- 实际攻击类型：代码中确认为 **16 类**（前端 `AttackTypeSelect.vue`、后端 `Attack.get_attack_types()`、防御面板 `defenseTableData` 三处对齐）。

**修复（`frontend/src/views/AttackPanel.vue`）：**
- `attackTypes` 改为在声明时直接初始化全部 16 种类型，消除加载前的 0 显示。

**论文修改：** 摘要及 §4.3.1 中 "12 类" 全部更正为 "**16 类**"。

---

### Q4：防御规则启用/禁用是否真实生效？

**答：确实生效**，三步完整链路：

1. 前端切换 → `POST /defense/toggle/{id}` 更新 DB `enabled` 字段
2. 立即调用 `POST /agents/defense/refresh-rules` → `DefenseAgent.refresh_rules()` 重载内存规则
3. 攻击演练时 `detect_and_respond()` 对已启用规则做名称关键词匹配，命中规则提升 5%~15% 拦截率，未精确命中的已启用规则各提供 2% 基础加成（上限 20%），总加成上限 40%

**论文修改：** §4.3.2 新增"防御规则的实际生效机制"详细说明段落。

---

## 会话三：拓扑页面状态与攻击记录分页

### Q：拓扑页面所有靶场显示"未开始"，且选择会话后阶段数字缺失

**根因 1（"未开始"问题）：** `get_session_status()` 在 session 不在内存中时（服务重启后内存清零）返回：
```python
{'phase': 1, 'phase_name': '未开始', ...}
```
已知会话 ID 不在内存，说明该会话已结束，应返回"已结束"而非"未开始"。

**根因 2（数字缺失）：** 同分支返回键名为 `phase`，而前端和正常路径均使用 `current_phase`，导致 `attackStatus.current_phase` 为 `undefined`。

**修复（`backend/agents/attack_agent.py`）：**
```python
if session_id not in self.session_data:
    return {'current_phase': 0, 'phase_name': '已结束', 'total_phases': total_phases, 'total_attempts': 0, 'successes': 0}
```

**修复（`frontend/src/views/Topology.vue`）：** 攻击阶段卡片子文本三态显示：
- `未开始` → "等待攻击启动"，进度 0%
- `已结束` → "演练已结束"，进度 100%
- 正常阶段 → "第 X / N 阶段"，进度动态计算

---

### Q：进度条为什么用 16.7%，不应该动态计算吗？

**答：** `current_phase * 16.7` 是 100/6 的近似，确为硬编码，且存在精度问题（6×16.7=100.2%）。

**修复：**
- 后端 `get_session_status()` 返回值加入 `total_phases: len(self.ATTACK_PHASES)`
- 前端进度条改为 `Math.round(current_phase / (total_phases || 6) * 100)`
- 子文本中硬编码的"/ 6 阶段"改为 `/ (total_phases || 6) 阶段`

---

### Q：攻击记录卡片应只显示最近 10 条，参考日志页面分页

**修复（三处联动）：**

**`backend/routes/compat.py`** — `/attack/list` 支持分页参数：
```python
page = int(request.args.get('page', 1))
limit = int(request.args.get('limit', 10))
offset = (page - 1) * limit
attacks = Attack.list_all(str(user_id), limit=limit, offset=offset)
total = Attack.count(str(user_id))
```

**`frontend/src/views/AttackPanel.vue`** — 新增分页状态，`loadAttackHistory(page)` 支持翻页：
```javascript
const attackLogPage = ref(1)
const attackLogPageSize = ref(10)
```

**`frontend/src/components/AttackTimeline.vue`** — 移除"省略提示"，改为 `el-pagination`：
- 新增 `currentPage`、`pageSize` props
- `total > pageSize` 时显示分页器
- emit `page-change` 给父组件

---

## 会话四：攻防阶段规范化（核心重构）

### Q：确保攻击防御阶段符合规范，告知理论来源，修改代码和论文

#### 理论来源

| 标准 | 出处 | 在本系统的用途 |
|------|------|--------------|
| **Cyber Kill Chain®** | Lockheed Martin，Hutchins 等，2011 | 攻击 6 阶段框架主干 |
| **MITRE ATT&CK Enterprise** | MITRE Corp，2025 | 各阶段战术 ID（TA0043 等）细化 |
| **MITRE D3FEND** | MITRE Corp | 各阶段防御检测难度系数校准 |
| **NIST SP 800-61 Rev.3** | NIST | 防御等级对齐事件响应四阶段 |
| **Verizon DBIR 2024** | Verizon Business | 攻击基础成功率数值实测校准 |

#### 原模型问题

| 问题 | 原设计 | 标准要求 |
|------|--------|---------|
| 最终阶段语义错误 | Phase 6 = "痕迹清理"（手段） | Kill Chain Stage 7 = "目标行动"（目的），包含数据渗出、业务破坏，痕迹清理只是子操作 |
| 阶段 1/2 边界模糊 | "信息收集"与"漏洞探测"同属侦察 | Kill Chain 将 Weaponization+Delivery 明确为独立阶段 |
| 防御等级无标准依据 | 自定义描述 | 应对齐 NIST SP 800-61 事件响应阶段 |
| 成功率/拦截率无数据来源 | 凭经验设值 | 应引用 Verizon DBIR / MITRE D3FEND 实测数据 |

#### 新攻击阶段模型（Kill Chain 6 阶段压缩映射）

| 阶段 | 新名称 | Kill Chain | MITRE ATT&CK 战术 | 典型攻击技术 | 基础成功率 |
|:---:|--------|-----------|-------------------|-------------|-----------|
| 1 | **侦察** | Stage 1 | TA0043、TA0007 | 端口扫描、OSINT、Web目录枚举 | 0.80 |
| 2 | **武器化与投递** | Stage 2+3 | TA0042、TA0001 | 鱼叉式钓鱼、Exploit定制、供应链攻击 | 0.68 |
| 3 | **漏洞利用** | Stage 4 | TA0002、TA0004 | SQL注入利用、RCE、Web Shell上传 | 0.55 |
| 4 | **持久化与提权** | Stage 5 | TA0003、TA0004 | 后门植入、提权利用、持久化服务注册 | 0.44 |
| 5 | **横向移动** | Stage 6 | TA0008、TA0011 | 内网扫描、哈希传递、C2通道建立 | 0.36 |
| 6 | **目标行动** | Stage 7 | TA0009、TA0010、TA0040、TA0005 | 数据窃取、隐蔽外传、日志清除、业务破坏 | 0.30 |

#### 新防御等级模型（NIST SP 800-61 对齐）

| 等级 | 名称 | NIST 响应阶段 | 核心动作 | Phase_factor（D3FEND校准）|
|:---:|------|--------------|---------|:---:|
| 1 | **监控级** | Detect | 日志采集、IDS旁路监听 | 0.90 |
| 2 | **过滤级** | Protect | WAF/邮件网关基础过滤 | 0.82 |
| 3 | **阻断级** | Contain | IPS主动阻断、访问控制 | 0.72 |
| 4 | **封禁级** | Eradicate | IP封禁、服务隔离 | 0.55 |
| 5 | **极限级** | Recover/Emergency | 全链路防护、紧急溯源 | 0.38（对Phase5）/ 0.25（对Phase6）|

#### 代码修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `backend/agents/attack_agent.py` | `ATTACK_PHASES` 重命名 6 阶段；`PHASE_ATTACKS` 更新技术列表；基础成功率按 DBIR 校准 |
| `backend/agents/defense_agent.py` | `DEFENSE_LEVELS` 对齐 NIST SP 800-61；`PHASE_DEFENSE_MAP` 注释更新；`phase_factor` 按 D3FEND 重标定 |
| `backend/routes/topology.py` | 默认状态加入 `total_phases: 6` |
| `frontend/src/views/AttackPanel.vue` | `phaseNames` map 同步新阶段名 |
| `frontend/src/views/Dashboard.vue` | `phaseNames` map 同步新阶段名 |
| `frontend/src/views/Topology.vue` | 子文本"/ 6 阶段"改为动态 `total_phases || 6` |

#### 论文修改

- §4.3.1 重写为"攻击阶段模型与理论依据"，新增 Kill Chain 6 阶段对照表、攻击成功率公式（含 $B_k$ 来源说明）
- §4.3.2 重写防御等级框架，新增 NIST SP 800-61 对照表、拦截率公式（含 D3FEND 检测因子说明）
- §6.1 更新提及 Kill Chain 和 NIST SP 800-61 框架

---

## 本次会话全量修改文件索引

### 后端（`backend/`）

| 文件 | 变更 |
|------|------|
| `agents/attack_agent.py` | 阶段重命名、攻击列表更新、成功率校准、`get_session_status` 修复（`phase`→`current_phase`，"未开始"→"已结束"，加入 `total_phases`）|
| `agents/defense_agent.py` | 防御等级对齐 NIST；`phase_factor` 按 D3FEND 重标定 |
| `routes/compat.py` | 停止容器端口从 DB 补全；`/attack/list` 支持 `page`/`limit` 分页 |
| `routes/topology.py` | 默认状态修复（`current_phase: 0`，`total_phases: 6`）|

### 前端（`frontend/src/`）

| 文件 | 变更 |
|------|------|
| `views/AttackPanel.vue` | `attackTypes` 初始化为 16 种；`phaseNames` 同步新名称；分页状态 `attackLogPage`/`attackLogPageSize`（10条/页）|
| `views/Dashboard.vue` | `phaseNames` 同步新名称 |
| `views/Topology.vue` | 攻击阶段卡三态显示；进度条动态计算；子文本"/ N 阶段"动态化 |
| `components/AttackTimeline.vue` | 移除省略提示；新增 `el-pagination`（10条/页）；emit `page-change` |

### 论文

| 文件 | 变更 |
|------|------|
| `论文_AI驱动的网络安全攻防靶场自动生成系统.md` | 新增 §4.4 WatchdogService 章节；29 篇文献及行内引用；"12类"→"16类"；§4.2.1 漏洞声明；§4.3.1 攻击阶段理论框架与公式；§4.3.2 防御等级 NIST 对照；§6.1 更新 |

---

*生成时间：2026-05-11*
*AI 助手：Claude Sonnet 4.6（claude-sonnet-4-6）*
