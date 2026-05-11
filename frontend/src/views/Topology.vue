<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon>
          <Connection />
        </el-icon>
        攻防动态拓扑
      </h2>
      <p class="page-desc">实时显示攻击阶段和防御等级的动态对抗态势</p>
    </div>

    <!-- 控制栏 -->
    <el-card class="tech-card" style="margin-bottom: 16px;">
      <div class="control-bar">
        <el-select v-model="selectedTargetId" placeholder="选择靶场" filterable style="width: 250px"
          @change="onTargetChange">
          <el-option v-for="target in targets" :key="target.id" :label="target.name" :value="target.id" />
        </el-select>

        <el-tooltip content="演练会话是一次完整的攻防演练，包含从开始到结束的所有攻击和防御记录" placement="top">
          <el-select v-model="selectedSessionId" placeholder="选择演练会话" filterable style="width: 250px"
            @change="onSessionChange">
            <el-option v-for="session in sessions" :key="session.session_id" :label="session.session_id"
              :value="session.session_id" />
          </el-select>
        </el-tooltip>

        <el-button type="primary" @click="loadTopology" :loading="loading">
          <el-icon>
            <Refresh />
          </el-icon>
          刷新
        </el-button>
        <el-button type="warning" @click="exportTopology" :disabled="!selectedTargetId">
          <el-icon>
            <Download />
          </el-icon>
          导出拓扑
        </el-button>
      </div>

    </el-card>

    <!-- 攻防态势卡片 -->
    <el-row :gutter="16" style="margin-bottom: 16px;" v-if="attackStatus">
      <el-col :xs="12" :sm="6">
        <div class="status-card attack">
          <div class="status-label">攻击阶段</div>
          <div class="status-value">{{ attackStatus.phase_name }}</div>
          <div class="status-progress">
            <el-progress
              :percentage="attackStatus.phase_name === '已结束' ? 100 : attackStatus.phase_name === '未开始' ? 0 : Math.round(attackStatus.current_phase / (attackStatus.total_phases || 6) * 100)"
              :show-text="false" color="#f56c6c" />
          </div>
          <div class="status-sub">
            <template v-if="attackStatus.phase_name === '未开始'">等待攻击启动</template>
            <template v-else-if="attackStatus.phase_name === '已结束'">演练已结束</template>
            <template v-else>第 {{ attackStatus.current_phase }} / {{ attackStatus.total_phases || 6 }} 阶段</template>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="status-card defense">
          <div class="status-label">防御等级</div>
          <div class="status-value">{{ defenseStatus.level_name }}</div>
          <div class="status-progress">
            <el-progress :percentage="defenseStatus.current_level * 20" :show-text="false" color="#67c23a" />
          </div>
          <div class="status-sub">等级 {{ defenseStatus.current_level }} / 5</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="status-card">
          <div class="status-label">攻击成功</div>
          <div class="status-value">{{ attackStatus.successes || 0 }}</div>
          <div class="status-sub">次成功尝试</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="status-card">
          <div class="status-label">封禁IP</div>
          <div class="status-value">{{ defenseStatus.blocked_ips?.length || 0 }}</div>
          <div class="status-sub">个IP已封禁</div>
        </div>
      </el-col>
    </el-row>

    <!-- 拓扑图 -->
    <el-card class="tech-card" v-if="selectedTarget">
      <template #header>
        <div class="card-header">
          <span><el-icon>
              <Connection />
            </el-icon> {{ selectedTarget.name }} - 攻防拓扑</span>
          <div class="header-tags">
            <el-tag size="small" type="danger">攻击阶段: {{ attackStatus?.phase_name || '未开始' }}</el-tag>
            <el-tag size="small" type="success">防御等级: {{ defenseStatus?.level_name || '监控级' }}</el-tag>
          </div>
        </div>
      </template>

      <div ref="topoRef" class="topo-container">
        <div v-if="loading" class="loading-tip">
          <el-icon class="is-loading">
            <Loading />
          </el-icon>
          加载拓扑数据...
        </div>
        <div v-else-if="!topology.nodes?.length" class="empty-tip">
          <el-icon :size="48">
            <Connection />
          </el-icon>
          <p>暂无拓扑数据</p>
        </div>
      </div>

      <!-- 图例 -->
      <div class="legend">
        <div class="legend-item"><span class="dot attacker"></span> 攻击机</div>
        <div class="legend-item"><span class="dot web"></span> Web服务器</div>
        <div class="legend-item"><span class="dot database"></span> 数据库</div>
        <div class="legend-item"><span class="dot waf"></span> WAF</div>
        <div class="legend-item"><span class="dot firewall"></span> 防火墙</div>
        <div class="legend-item"><span class="dot monitor"></span> 监控系统</div>
        <div class="legend-item"><span class="dot target-node"></span> 靶场目标</div>
        <div class="legend-item"><span class="dot threat-high"></span> 高危节点</div>
        <div class="legend-item"><span class="dot threat-critical"></span> 严重威胁</div>
      </div>
    </el-card>

    <!-- 未选择时的提示 -->
    <el-card class="tech-card" v-else>
      <div class="empty-state">
        <el-icon :size="48">
          <Connection />
        </el-icon>
        <p>请选择靶场和演练会话查看攻防动态拓扑</p>
        <p class="sub-text">拓扑将显示攻击阶段和防御等级的变化</p>
      </div>
    </el-card>

    <!-- 节点详情弹窗 -->
    <el-dialog v-model="nodeDialogVisible" :title="nodeDetail?.name || '节点详情'" width="500px" class="tech-dialog">
      <div v-if="nodeDetail" class="node-detail-content">
        <div class="detail-row">
          <span class="detail-label">节点名称</span>
          <span class="detail-value">{{ nodeDetail.name }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">节点类型</span>
          <el-tag size="small" :color="getNodeColor(nodeDetail.type)">{{ nodeLabels[nodeDetail.type] || nodeDetail.type
          }}</el-tag>
        </div>
        <div class="detail-row">
          <span class="detail-label">IP 地址</span>
          <span class="detail-value mono">{{ nodeDetail.ip || 'N/A' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">端口</span>
          <span class="detail-value mono">{{ nodeDetail.port || 'N/A' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">威胁等级</span>
          <el-tag v-if="nodeDetail.threat === 'critical'" type="danger" size="small">严重威胁</el-tag>
          <el-tag v-else-if="nodeDetail.threat === 'high'" type="warning" size="small">高危</el-tag>
          <el-tag v-else-if="nodeDetail.threat === 'medium'" type="warning" size="small">中危</el-tag>
          <el-tag v-else type="info" size="small">正常</el-tag>
        </div>
        <div class="detail-row">
          <span class="detail-label">防御状态</span>
          <el-tag v-if="nodeDetail.defense === 'active'" type="success" size="small">已激活</el-tag>
          <el-tag v-else type="info" size="small">待命中</el-tag>
        </div>
        <div class="detail-row" v-if="nodeDetail.is_attacker">
          <span class="detail-label">攻击源</span>
          <el-tag type="danger" size="small">⚠ 攻击源</el-tag>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Refresh, Loading, Download } from '@element-plus/icons-vue'

import request from '../utils/request'


const targets = ref([])
const sessions = ref([])
const selectedTargetId = ref('')
const selectedSessionId = ref('')
const selectedTarget = ref(null)
const attackStatus = ref(null)
const defenseStatus = ref(null)
const topology = ref({ nodes: [], edges: [] })
const loading = ref(false)
const topoRef = ref(null)
const nodeDialogVisible = ref(false)
const nodeDetail = ref(null)

// 节点颜色（每种节点类型使用不同颜色，避免混淆）
const nodeColors = {
  attacker: '#f56c6c',   // 红色：攻击机
  web: '#409eff',        // 蓝色：Web服务器
  database: '#67c23a',   // 绿色：数据库
  waf: '#e6a23c',        // 橙色：WAF
  firewall: '#9b59b6',   // 紫色：防火墙（与WAF橙色区分）
  monitor: '#909399',    // 灰色：监控系统
  app: '#409eff',        // 蓝色：应用服务器
  backup: '#67c23a',     // 绿色：备份服务器
  target: '#00bcd4'      // 青色：靶场目标
}

const nodeLabels = {
  attacker: '攻击者',
  web: 'Web服务器',
  database: '数据库',
  waf: 'WAF',
  firewall: '防火墙',
  monitor: '监控系统',
  app: '应用服务器',
  backup: '备份服务器',
  target: '靶场'
}

async function loadTargets() {
  try {
    const res = await request.get('/topology')
    if (res.status === 'success') {
      targets.value = res.targets || []
    }
  } catch (e) {
    console.error('加载靶场列表失败', e)
  }
}

async function loadSessions(targetId) {
  try {
    const params = {}
    if (targetId) {
      params.target_id = targetId
    }
    const res = await request.get('/agents/sessions', { params })
    if (res.status === 'success') {
      sessions.value = (res.sessions || []).map(s => ({
        session_id: s.session_id,
        attack_type: s.environment?.name || s.status || '未知',
        target: s.environment?.components?.join(', ') || '',
        current_phase: 1,
        defense_level: 1,
        attacks_count: 0,
        status: s.status || 'active',
        created_at: s.created_at || '',
        last_activity: s.created_at || ''
      }))
    }
  } catch (e) {
    console.error('加载会话列表失败', e)
  }
}


async function loadTopology() {
  if (!selectedTargetId.value) {
    return
  }

  loading.value = true
  try {
    const params = { target_id: selectedTargetId.value }
    if (selectedSessionId.value) {
      params.session_id = selectedSessionId.value
    }

    const res = await request.get('/topology', { params })

    if (res.status === 'success') {
      selectedTarget.value = res.target
      attackStatus.value = res.attack_status
      defenseStatus.value = res.defense_status
      topology.value = res.topology || { nodes: [], edges: [] }
      await nextTick()
      drawTopology()
    }
  } catch (e) {
    console.error('加载拓扑失败', e)
  } finally {
    loading.value = false
  }
}

function drawTopology() {
  if (!topoRef.value || !topology.value.nodes?.length) return

  const el = topoRef.value
  const w = el.clientWidth || 800
  const h = 450

  const nodes = topology.value.nodes
  const edges = topology.value.edges
  const nodeCount = nodes.length
  const centerX = w / 2
  const centerY = h / 2
  const radius = Math.min(w, h) * 0.35

  nodes.forEach((node, i) => {
    const angle = (i / nodeCount) * Math.PI * 2 - Math.PI / 2
    node.x = centerX + radius * Math.cos(angle)
    node.y = centerY + radius * Math.sin(angle)
  })

  let svg = `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="background: #0a0a14; border-radius: 8px;">`

  // 绘制连接线
  edges.forEach(edge => {
    const source = nodes.find(n => n.id === edge.source)
    const target = nodes.find(n => n.id === edge.target)
    if (source && target) {
      svg += `<line x1="${source.x}" y1="${source.y}" x2="${target.x}" y2="${target.y}" 
                    stroke="#5090a0" stroke-width="1.5" stroke-dasharray="5,3"
                    class="topo-edge"/>
              <text x="${(source.x + target.x) / 2}" y="${(source.y + target.y) / 2 - 5}" 
                    text-anchor="middle" fill="#606888" font-size="9" font-family="monospace">
                ${edge.protocol || '连接'} ${edge.port || ''}
              </text>`
    }
  })

  // 绘制节点
  nodes.forEach(node => {
    const color = node.is_attacker ? '#f56c6c' : (nodeColors[node.type] || '#67c23a')
    const label = nodeLabels[node.type] || node.name
    const threat = node.threat
    const defense = node.defense

    let glowFilter = ''
    let borderWidth = 2

    if (threat === 'critical') {
      glowFilter = 'filter="url(#glow-danger)"'
      borderWidth = 3
    } else if (threat === 'high') {
      glowFilter = 'filter="url(#glow-warning)"'
      borderWidth = 2.5
    }

    if (defense === 'active') {
      glowFilter = 'filter="url(#glow-success)"'
    }

    svg += `
      <g class="topo-node" data-id="${node.id}" data-type="${node.type}">
        <circle cx="${node.x}" cy="${node.y}" r="24" fill="#1a1a2e" stroke="${color}" stroke-width="${borderWidth}" ${glowFilter}/>
        <circle cx="${node.x}" cy="${node.y}" r="5" fill="${color}">
          ${node.is_attacker ? '<animate attributeName="r" values="5;8;5" dur="1.5s" repeatCount="indefinite"/>' : ''}
        </circle>
        <text x="${node.x}" y="${node.y - 10}" text-anchor="middle" fill="${color}" font-size="11" font-weight="bold">
          ${node.name}
        </text>
        <text x="${node.x}" y="${node.y + 4}" text-anchor="middle" fill="#606888" font-size="9">
          ${label}
        </text>
        ${node.port ? `<text x="${node.x}" y="${node.y + 13}" text-anchor="middle" fill="#606888" font-size="8">
          端口: ${node.port}
        </text>` : ''}
        ${threat === 'critical' ? `<text x="${node.x}" y="${node.y - 18}" text-anchor="middle" fill="#f56c6c" font-size="8">
          ⚠ 严重威胁
        </text>` : threat === 'high' ? `<text x="${node.x}" y="${node.y - 18}" text-anchor="middle" fill="#e6a23c" font-size="8">
          ⚠ 高危
        </text>` : ''}
      </g>
    `
  })

  svg += `
    <defs>
      <filter id="glow-danger">
        <feGaussianBlur stdDeviation="3" result="blur"/>
        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <filter id="glow-warning">
        <feGaussianBlur stdDeviation="2" result="blur"/>
        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <filter id="glow-success">
        <feGaussianBlur stdDeviation="2" result="blur"/>
        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>
  </svg>
  `

  el.innerHTML = svg

  // 添加节点点击事件
  el.querySelectorAll('.topo-node').forEach(nodeEl => {
    nodeEl.addEventListener('click', () => {
      const nodeId = nodeEl.getAttribute('data-id')
      const node = nodes.find(n => n.id === nodeId)
      if (node) {
        showNodeDetail(node)
      }
    })
  })
}

function showNodeDetail(node) {
  nodeDetail.value = node
  nodeDialogVisible.value = true
}

function getNodeColor(type) {
  return nodeColors[type] || '#67c23a'
}

// 导出拓扑
async function exportTopology() {
  if (!selectedTargetId.value) return
  try {
    const params = { target_id: selectedTargetId.value, format: 'json' }
    if (selectedSessionId.value) {
      params.session_id = selectedSessionId.value
    }
    const response = await request.get('/topology/export', {
      params,
      responseType: 'blob'
    })
    const blob = new Blob([response.data], { type: 'application/json;charset=utf-8' })

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const now = new Date()
    const ts = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
    a.download = `topology_export_${ts}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('拓扑数据已导出')
  } catch (e) {
    ElMessage.error('导出失败: ' + (e.message || '未知错误'))
  }
}

function onTargetChange() {
  selectedSessionId.value = ''
  // 选择靶场后加载该靶场关联的演练会话
  loadSessions(selectedTargetId.value)
  loadTopology()
}


function onSessionChange() {
  loadTopology()
}

onMounted(() => {
  loadTargets()
  loadSessions()
  window.addEventListener('resize', () => {
    if (topology.value.nodes?.length) drawTopology()
  })
})
</script>

<style scoped>
.control-bar {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.status-card {
  background: rgba(16, 18, 32, 0.8);
  border: 1px solid var(--border-mid);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.status-card.attack {
  border-left: 4px solid #f56c6c;
}

.status-card.defense {
  border-left: 4px solid #67c23a;
}

.status-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.status-value {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
}

.status-card.attack .status-value {
  color: #f56c6c;
}

.status-card.defense .status-value {
  color: #67c23a;
}

.status-progress {
  margin: 8px 0;
}

.status-sub {
  font-size: 11px;
  color: var(--text-muted);
}

.topo-container {
  height: 450px;
  overflow: hidden;
}

.header-tags {
  display: flex;
  gap: 8px;
}

.legend {
  display: flex;
  gap: 16px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-dim);
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.dot.attacker {
  background: #f56c6c;
}

.dot.web {
  background: #409eff;
}

.dot.database {
  background: #67c23a;
}

.dot.waf {
  background: #e6a23c;
}

.dot.firewall {
  background: #9b59b6;
}

.dot.monitor {
  background: #909399;
}

.dot.target-node {
  background: #00bcd4;
}

.dot.threat-high {
  background: #e6a23c;
  box-shadow: 0 0 4px #e6a23c;
}

.dot.threat-critical {
  background: #f56c6c;
  box-shadow: 0 0 6px #f56c6c;
}

.loading-tip,
.empty-tip,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  gap: 12px;
}

.sub-text {
  font-size: 12px;
  margin-top: 4px;
}

/* 节点详情弹窗样式 */
.node-detail-content {
  padding: 8px 0;
}

.detail-row {
  display: flex;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  width: 100px;
  font-size: 13px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.detail-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.detail-value.mono {
  font-family: var(--font-mono);
  color: var(--cyan);
}
</style>
