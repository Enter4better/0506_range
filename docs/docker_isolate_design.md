# Docker 容器网络隔离功能设计文档

## 1. 背景与动机

原防御模块（`DefenseAgent`）在触发"封禁级"防御动作时，执行的实际操作是：

```python
actions.append(f"🔒 IP封禁: {source_ip}已加入黑名单")   # 只是字符串
session['blocked_ips'].append(source_ip)               # 只是内存列表
```

即所有"封禁"行为均为文本仿真，不产生任何真实的网络层效果。

本次改动在防御等级升至 **封禁级（level ≥ 4）** 时，调用 Docker SDK 真实断开靶场容器的网络连接，使"服务隔离"动作从日志描述变为可验证的 Docker 操作。

---

## 2. 整体流程

```
用户发起攻击
     │
     ▼
AttackAgent.execute_attack()          ← 概率模型计算成功/失败，LLM 生成分析
     │  attack_phase, attack_type
     ▼
attacks.py: _execute_dynamic_attack_async()
     │  构造 attack_data（新增 port 字段）
     ▼
DefenseAgent.detect_and_respond()
     │  根据攻击阶段确定目标 defense_level
     │  level >= 4 时 ──────────────────────────────────────┐
     ▼                                                       │
_execute_defense_actions(attack_port=port)                  │
     │                                                       │
     ▼                                                       ▼
docker_isolate.block_container_by_port(port)        ← 真实 Docker API
     │
     ├── 查数据库 targets 表，匹配 container_port == port
     ├── docker.networks.get(net).disconnect(container)
     ├── 记录隔离状态到 _blocked 字典
     └── 启动 60s 后自动恢复的 threading.Timer
```

---

## 3. 新增文件

### `backend/services/docker_isolate.py`

核心隔离服务，对外暴露三个函数：

| 函数 | 说明 |
|---|---|
| `block_container_by_port(port, attack_type)` | 通过容器内部端口定位容器，断开所有 bridge 网络 |
| `unblock_container(container_name)` | 恢复被隔离容器的网络连接 |
| `get_blocked_containers()` | 返回当前所有隔离容器的状态列表 |

**容器定位逻辑**：查询 `targets` 表，匹配 `config.container_port == attack_port` 且 `status = 'running'` 的记录，取其 `container_name` 字段。

**降级保护**：若 Docker 客户端不可用（环境未安装 docker-py、Docker 未启动），函数返回 `success=False`，`DefenseAgent` 自动回退到原有的文本记录行为，演练流程不中断。

**自动恢复**：封禁后启动一个 `threading.Timer`（守护线程，默认 60 秒），到期后自动调用 `unblock_container` 重连网络。

---

## 4. 修改文件

### `backend/agents/defense_agent.py`

**`_execute_defense_actions` 新增参数**：
```python
def _execute_defense_actions(self, attack_type, defense_level,
                              source_ip, session,
                              attack_port: int = 80)   # ← 新增
```

**level >= 4 时的新逻辑**：
```python
from services.docker_isolate import block_container_by_port, AUTO_UNBLOCK_SECONDS
iso_result = block_container_by_port(attack_port, attack_type)
if iso_result['success']:
    actions.append(f"🔒 容器网络已隔离: {iso_result['container_name']} ...")
else:
    # 降级：回退到文本记录
    actions.append(f"🔒 IP封禁记录: {source_ip}（{iso_result['message']}）")
```

**`detect_and_respond` 读取 port**：
```python
attack_port = int(attack_data.get('port', 80) or 80)
actions = self._execute_defense_actions(..., attack_port=attack_port)
```

---

### `backend/routes/attacks.py`

`_execute_dynamic_attack_async` 的 `attack_data` 新增 `port` 字段：

```python
try:
    attack_port = int(attack.port) if attack.port else 80
except (ValueError, TypeError):
    attack_port = 80

defense_result = defense_agent.detect_and_respond(
    session_id=session_id,
    attack_data={
        ...
        'port': attack_port,   # ← 新增，供 docker_isolate 定位容器
        ...
    }
)
```

---

### `backend/routes/defenses.py`

新增两个 API 端点：

#### `GET /api/defense/blocked`

查询当前所有处于网络隔离状态的容器。

**响应示例**：
```json
{
  "status": "success",
  "count": 1,
  "blocked": [
    {
      "container_name": "cyber_range_web-server_20260513_171050",
      "networks": ["bridge"],
      "blocked_at": "2026-05-20T14:30:00.123456",
      "port": 80,
      "attack_type": "SQL注入"
    }
  ]
}
```

#### `POST /api/defense/unblock/<container_name>`

手动提前解除指定容器的网络隔离（无需等待 60s 自动恢复）。

**响应示例**：
```json
{
  "status": "success",
  "message": "容器 cyber_range_web-server_20260513_171050 网络已恢复: ['bridge']"
}
```

---

## 5. 触发条件

防御等级与 Kill Chain 攻击阶段的映射如下（已有逻辑，未变更）：

| 攻击阶段 | 防御等级 | 是否触发 Docker 隔离 |
|---|---|---|
| 1 侦察 | 1 监控级 | 否 |
| 2 武器化与投递 | 2 过滤级 | 否 |
| 3 漏洞利用 | 3 阻断级 | 否 |
| 4 持久化与提权 | 4 **封禁级** | **是** |
| 5 横向移动 | 5 极限级 | **是** |
| 6 目标行动 | 5 极限级 | **是** |

攻击强度 ≥ 8 时防御等级额外 +1，因此强度较高的漏洞利用（阶段3）也可能触发隔离。

---

## 6. 触发条件详解

### 6.1 触发门槛计算

防御等级由攻击阶段基础值加强度加成共同决定，只要最终等级 ≥ 4 即触发 Docker 隔离：

| 攻击阶段 | 基础防御等级 | 强度 <5 | 强度 5–7 | 强度 ≥8 |
|---|---|---|---|---|
| 1 侦察 | 1 | 1 | 2 | 3 |
| 2 武器化与投递 | 2 | 2 | 3 | **4 ← 触发** |
| 3 漏洞利用 | 3 | 3 | **4 ← 触发** | **5** |
| 4 持久化与提权 | 4 | **4 ← 触发** | **5** | **5** |
| 5 横向移动 | 5 | **5** | **5** | **5** |
| 6 目标行动 | 5 | **5** | **5** | **5** |

强度加成规则（`defense_agent.py:125`）：强度 < 5 加 0，强度 5–7 加 1，强度 ≥ 8 加 2，上限 5。

### 6.2 触发后的三个可见位置

**位置 1：攻击结果 `actions_taken` 字段（最直接）**

前端攻击面板轮询 `GET /api/attack/result/<id>`，返回的 `defense.actions_taken` 数组中会包含：

```
🔒 容器网络已隔离: cyber_range_web-server_20260513_171050 （port=80，60s 后自动恢复）
```

Docker 不可用或找不到对应容器时降级为：

```
🔒 IP封禁记录: 192.168.1.xxx（未找到 container_port=80 对应的运行中靶场容器）
```

**位置 2：`GET /api/defense/blocked` 接口**

触发后 60 秒内调用，可查询当前处于隔离状态的所有容器：

```bash
curl http://localhost:5001/api/defense/blocked
```

```json
{
  "status": "success",
  "count": 1,
  "blocked": [
    {
      "container_name": "cyber_range_web-server_20260513_171050",
      "networks": ["bridge"],
      "blocked_at": "2026-05-20T14:30:00.123456",
      "port": 80,
      "attack_type": "SQL注入"
    }
  ]
}
```

**位置 3：Docker 本身**

```bash
docker inspect <container_name> --format '{{json .NetworkSettings.Networks}}'
# 隔离期间：{} （空，网络已断开）
# 60s 后恢复：{"bridge": {...}}
```

### 6.3 "IP封禁"与"容器隔离"的区别

系统中存在两个概念，需区分：

| 概念 | 实现方式 | 是否真实 |
|---|---|---|
| IP 封禁 | 将随机生成的 `192.168.1.x` 写入 `session['blocked_ips']` 内存列表 | **仅仿真**，无实际网络效果 |
| 容器网络隔离 | 通过 Docker SDK 断开容器的所有 bridge 网络 | **真实 Docker 操作**，可通过 `docker inspect` 验证 |

`source_ip` 是攻击仿真层随机生成的假 IP（`attacks.py:73`），不对应任何真实主机，因此"IP封禁"仅作为演练日志展示用。真正产生网络层效果的是容器隔离操作。

---

## 7. 验证方法

### 7.1 功能验证（需 Docker 运行中且有 running 状态的靶场容器）

1. 部署一个靶场（例如含 nginx:alpine，container_port=80）
2. 创建一个攻击任务，port 设为 80，intensity 设为 8 以上
3. 执行攻击，观察防御面板的 `actions_taken` 字段

**预期结果**：
```
🔒 容器网络已隔离: cyber_range_web-server_XXXXXX（port=80，60s 后自动恢复）
```

4. 在 60s 内调用 `GET /api/defense/blocked`，应返回该容器的隔离记录
5. 调用 Docker Desktop 或 `docker inspect <container_name>`，确认 `Networks` 为空
6. 60s 后再次 inspect，确认网络已恢复

### 7.2 降级验证（模拟 Docker 不可用）

停止 Docker Desktop，重新发起攻击，防御面板应显示：
```
🔒 IP封禁记录: 192.168.1.xxx（Docker 客户端不可用，降级为文本记录）
```
演练流程正常继续，不报错。

---

## 7. 限制与注意事项

1. **仅隔离 bridge 网络**：host/none 类型网络不会被断开，避免容器因失去必要进程通信而崩溃。

2. **隔离针对目标容器而非攻击者容器**：由于本系统的攻击是在 Flask 进程内仿真（非真实网络流量），不存在真实的"攻击者容器"，因此隔离对象为攻击指向的靶场容器（`attack.port` 对应的容器），语义上对应"服务隔离/断网处置"。

3. **source_ip 仍为随机值**：`f'192.168.1.{random.randint(1,255)}'` 这一行未修改，因为它只用于日志展示。如需真实 IP，需要改造攻击仿真层，超出本次改动范围。

4. **自动恢复依赖守护线程**：若 Flask 进程在 60s 内重启，Timer 会随进程销毁，容器需手动通过 `/api/defense/unblock` 或 `docker network connect` 恢复网络。

5. **单机 Docker 限制**：当前实现仅适用于单机 Docker Engine。若未来迁移至 Kubernetes，需替换为 NetworkPolicy API。

---

## 8. 改动文件汇总

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `backend/services/docker_isolate.py` | **新增** | 隔离服务核心逻辑 |
| `backend/agents/defense_agent.py` | 修改 | `_execute_defense_actions` 接入隔离，`detect_and_respond` 传 port |
| `backend/routes/attacks.py` | 修改 | `attack_data` 新增 port 字段 |
| `backend/routes/defenses.py` | 修改 | 新增 `/blocked` 和 `/unblock/<name>` 两个端点 |
