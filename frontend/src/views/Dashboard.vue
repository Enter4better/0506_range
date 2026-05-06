<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title"><el-icon>
          <DataLine />
        </el-icon> 攻防控制台</h2>
      <p class="page-desc">
        实时监控 | 后端{{ backendStatus ? '在线' : '离线' }} | 最后更新: {{ lastUpdate }}
      </p>
    </div>

    <div v-if="!backendStatus" class="backend-warning">
      <el-icon>
        <Warning />
      </el-icon>
      后端服务未启动，请先运行：
      <code>cd backend && python app.py</code>
    </div>

    <!-- 统计卡片 - 使用自定义 StatCard 组件 -->
    <el-row :gutter="14" style="margin-bottom: 14px;">
      <el-col :xs="24" :sm="12" :md="6">
        <StatCard :icon="CircleCheck" :value="stats.health" label="靶场健康度" type="success" />
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <StatCard :icon="Warning" :value="stats.danger" label="危险等级" type="danger" />
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <StatCard :icon="Monitor" :value="stats.coverage" label="防御覆盖率" type="cyan" />
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <StatCard :icon="Timer" :value="stats.runtime" label="运行时间" type="info" />
      </el-col>
    </el-row>

    <el-row :gutter="14">
      <!-- 快速攻击面板 -->
      <el-col :xs="24" :lg="6">
        <el-card shadow="hover" class="tech-card" style="margin-bottom: 14px;">
          <template #header>
            <div class="card-title">
              <el-icon>
                <Aim />
              </el-icon> 快速攻击
              <el-tag type="danger" size="small" style="margin-left: 8px;">LIVE</el-tag>
            </div>
          </template>
          <el-form label-width="72px" size="small">
            <el-form-item label="攻击类型">
              <el-select v-model="attackType" style="width: 100%;" filterable>
                <el-option-group label="Web漏洞攻击">
                  <el-option label="SQL注入" value="SQL注入">
                    <span style="float: left;">SQL注入</span>
                    <span style="float: right; color: #ff4466; font-size: 11px;">高危</span>
                  </el-option>
                  <el-option label="XSS跨站脚本" value="XSS攻击">
                    <span style="float: left;">XSS跨站脚本</span>
                    <span style="float: right; color: #ffd740; font-size: 11px;">中危</span>
                  </el-option>
                  <el-option label="CSRF跨站请求伪造" value="CSRF攻击">
                    <span style="float: left;">CSRF攻击</span>
                    <span style="float: right; color: #ffd740; font-size: 11px;">中危</span>
                  </el-option>
                  <el-option label="文件包含漏洞" value="文件包含">
                    <span style="float: left;">文件包含</span>
                    <span style="float: right; color: #ff4466; font-size: 11px;">高危</span>
                  </el-option>
                  <el-option label="命令执行" value="命令执行">
                    <span style="float: left;">命令执行</span>
                    <span style="float: right; color: #ff4466; font-size: 11px;">高危</span>
                  </el-option>
                  <el-option label="SSRF服务端请求伪造" value="SSRF攻击">
                    <span style="float: left;">SSRF攻击</span>
                    <span style="float: right; color: #ffd740; font-size: 11px;">中危</span>
                  </el-option>
                  <el-option label="XXE外部实体注入" value="XXE注入">
                    <span style="float: left;">XXE注入</span>
                    <span style="float: right; color: #ff4466; font-size: 11px;">高危</span>
                  </el-option>
                </el-option-group>
                <el-option-group label="系统层攻击">
                  <el-option label="权限提升" value="权限提升">
                    <span style="float: left;">权限提升</span>
                    <span style="float: right; color: #ff4466; font-size: 11px;">高危</span>
                  </el-option>
                  <el-option label="容器逃逸" value="容器逃逸">
                    <span style="float: left;">容器逃逸</span>
                    <span style="float: right; color: #ff4466; font-size: 11px;">高危</span>
                  </el-option>
                </el-option-group>
                <el-option-group label="网络攻击">
                  <el-option label="端口扫描" value="端口扫描">
                    <span style="float: left;">端口扫描</span>
                    <span style="float: right; color: #00e5ff; font-size: 11px;">探测</span>
                  </el-option>
                  <el-option label="暴力破解" value="暴力破解">
                    <span style="float: left;">暴力破解</span>
                    <span style="float: right; color: #ffd740; font-size: 11px;">中危</span>
                  </el-option>
                </el-option-group>
              </el-select>
            </el-form-item>
            <el-form-item label="目标端口">
              <el-input v-model="targetPort" placeholder="8080">
                <template #prepend>PORT</template>
              </el-input>
            </el-form-item>
            <el-form-item label="攻击强度">
              <el-slider v-model="attackIntensity" :min="1" :max="10" :marks="intensityMarks" />
            </el-form-item>
          </el-form>
          <el-button type="danger" style="width: 100%;" @click="startAttack" :loading="attackLoading"
            :disabled="!backendStatus">
            <el-icon>
              <Aim />
            </el-icon> 发起攻击
          </el-button>

          <!-- 最近攻击记录 -->
          <div v-if="recentAttacks.length > 0" style="margin-top: 14px;">
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">最近攻击</div>
            <el-timeline>
              <el-timeline-item v-for="attack in recentAttacks.slice(0, 3)" :key="attack.id"
                :type="attack.success ? 'success' : 'danger'" size="small">
                <span style="font-size: 12px;">{{ attack.type }}</span>
                <span style="font-size: 11px; color: var(--text-muted); margin-left: 8px;">{{ attack.time }}</span>
              </el-timeline-item>
            </el-timeline>
          </div>
        </el-card>
      </el-col>

      <!-- 快速防御面板 -->
      <el-col :xs="24" :lg="6">
        <el-card shadow="hover" class="tech-card" style="margin-bottom: 14px;">
          <template #header>
            <div class="card-title">
              <el-icon>
                <Umbrella />
              </el-icon> 快速防御
              <el-tag type="success" size="small" style="margin-left: 8px;">ACTIVE</el-tag>
            </div>
          </template>
          <el-form label-width="72px" size="small">
            <el-form-item label="防御类型">
              <el-select v-model="defenseType" style="width: 100%;">
                <el-option-group label="网络防御">
                  <el-option label="防火墙规则" value="firewall">
                    <span style="float: left;">防火墙</span>
                    <span style="float: right; color: #8b2ce6; font-size: 11px;">网络层</span>
                  </el-option>
                  <el-option label="入侵检测IDS" value="ids">
                    <span style="float: left;">入侵检测</span>
                    <span style="float: right; color: #00e676; font-size: 11px;">分析层</span>
                  </el-option>
                  <el-option label="WAF防护" value="waf">
                    <span style="float: left;">WAF</span>
                    <span style="float: right; color: #00e5ff; font-size: 11px;">应用层</span>
                  </el-option>
                </el-option-group>
                <el-option-group label="系统防御">
                  <el-option label="端口封锁" value="port_block">
                    <span style="float: left;">端口封锁</span>
                    <span style="float: right; color: #ff4466; font-size: 11px;">高危</span>
                  </el-option>
                  <el-option label="IP黑名单" value="ip_blacklist">
                    <span style="float: left;">IP黑名单</span>
                    <span style="float: right; color: #ffd740; font-size: 11px;">拦截</span>
                  </el-option>
                </el-option-group>
              </el-select>
            </el-form-item>
            <el-form-item label="防护端口">
              <el-input v-model="defensePort" placeholder="8080">
                <template #prepend>PORT</template>
              </el-input>
            </el-form-item>
            <el-form-item label="防御强度">
              <el-slider v-model="defenseIntensity" :min="1" :max="10" :marks="intensityMarks" />
            </el-form-item>
          </el-form>
          <el-button type="success" style="width: 100%;" @click="startDefense" :loading="defenseLoading"
            :disabled="!backendStatus">
            <el-icon>
              <Umbrella />
            </el-icon> 启用防御
          </el-button>

          <!-- 防御状态 -->
          <div style="margin-top: 14px;">
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">当前防御</div>
            <el-space wrap>
              <el-tag type="success" size="small" effect="dark">防火墙 ✓</el-tag>
              <el-tag type="success" size="small" effect="dark">IDS ✓</el-tag>
              <el-tag type="warning" size="small" effect="plain">WAF</el-tag>
            </el-space>
          </div>
        </el-card>
      </el-col>

      <!-- AI 决策中心 -->
      <el-col :xs="24" :lg="6">
        <el-card shadow="hover" class="tech-card" style="margin-bottom: 14px;">
          <template #header>
            <div class="card-title">
              <el-icon>
                <Cpu />
              </el-icon> AI 决策中心
              <el-tag type="success" size="small" style="margin-left: 8px;">GLM-4</el-tag>
            </div>
          </template>
          <el-button type="primary" style="width: 100%;" @click="aiAnalyze" :loading="aiLoading"
            :disabled="!backendStatus">
            <el-icon>
              <Cpu />
            </el-icon> 启动 AI 分析
          </el-button>

          <div v-if="aiLoading" style="margin-top: 14px; text-align: center; padding: 20px;">
            <el-icon :size="32" style="color: var(--purple); animation: spin 1.5s linear infinite;">
              <Loading />
            </el-icon>
            <p style="color: var(--text-muted); margin-top: 8px; font-size: 12px;">AI 正在分析安全态势...</p>
          </div>

          <div v-else-if="aiResult"
            style="margin-top: 14px; color: var(--text-secondary); line-height: 1.7; font-size: 13px;"
            v-html="aiResult"></div>

          <div v-else style="margin-top: 14px; text-align: center; padding: 20px; color: var(--text-muted);">
            <el-icon :size="32">
              <Cpu />
            </el-icon>
            <p style="font-size: 12px; margin-top: 8px;">点击启动 AI 安全分析</p>
          </div>

          <!-- AI 建议快速操作 -->
          <div v-if="aiSuggestions.length > 0" style="margin-top: 14px;">
            <el-divider style="margin: 10px 0;" />
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">AI 建议</div>
            <el-space wrap>
              <el-button v-for="sug in aiSuggestions" :key="sug" size="small" type="warning" plain>
                {{ sug }}
              </el-button>
            </el-space>
          </div>
        </el-card>
      </el-col>

      <!-- 实时状态 -->
      <el-col :xs="24" :lg="6">
        <el-card shadow="hover" class="tech-card" style="margin-bottom: 14px;">
          <template #header>
            <div class="card-title">
              <el-icon>
                <Monitor />
              </el-icon> 实时状态
              <el-tag :type="backendStatus ? 'success' : 'danger'" size="small" style="margin-left: 8px;">
                {{ backendStatus ? '正常' : '异常' }}
              </el-tag>
            </div>
          </template>

          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="靶场引擎">
              <el-tag type="success" size="small">运行中</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="活跃靶场">
              <span style="color: var(--cyan);">{{ activeTargets }}</span> 个
            </el-descriptions-item>
            <el-descriptions-item label="防御规则">
              <span style="color: var(--purple);">{{ activeRules }}</span> 条
            </el-descriptions-item>
            <el-descriptions-item label="今日攻击">
              <span style="color: var(--danger);">{{ todayAttacks }}</span> 次
            </el-descriptions-item>
            <el-descriptions-item label="拦截次数">
              <span style="color: var(--success);">{{ blockedCount }}</span> 次
            </el-descriptions-item>
          </el-descriptions>

          <div style="margin-top: 14px;">
            <el-button type="primary" style="width: 100%;" @click="goToEnv">
              <el-icon>
                <Setting />
              </el-icon> 管理靶场
            </el-button>
          </div>

          <!-- 系统资源监控 -->
          <div style="margin-top: 14px;">
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">系统资源</div>
            <div style="display: flex; gap: 14px;">
              <div style="flex: 1;">
                <div style="font-size: 11px; color: var(--text-muted);">CPU</div>
                <el-progress :percentage="cpuUsage" :color="cpuUsage > 80 ? '#ff4466' : '#00e676'" :stroke-width="6" />
              </div>
              <div style="flex: 1;">
                <div style="font-size: 11px; color: var(--text-muted);">内存</div>
                <el-progress :percentage="memUsage" :color="memUsage > 80 ? '#ff4466' : '#8b2ce6'" :stroke-width="6" />
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 网络拓扑 -->
    <el-card shadow="hover" class="tech-card" style="margin-top: 14px;">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div class="card-title"><el-icon>
              <Connection />
            </el-icon> 网络拓扑</div>
          <div style="display: flex; gap: 8px;">
            <el-button-group>
              <el-button size="small" :type="topoView === 'svg' ? 'primary' : ''"
                @click="topoView = 'svg'">SVG</el-button>
              <el-button size="small" :type="topoView === 'canvas' ? 'primary' : ''"
                @click="topoView = 'canvas'">Canvas</el-button>
            </el-button-group>
            <el-button size="small" @click="loadTopo" :loading="topoLoading">
              <el-icon>
                <Refresh />
              </el-icon> 刷新
            </el-button>
          </div>
        </div>
      </template>
      <div ref="topoRef" class="topo-box" style="height: 360px;"></div>

      <!-- 拓扑节点信息 -->
      <div v-if="selectedNode"
        style="margin-top: 14px; padding: 12px; background: rgba(8,10,20,0.5); border-radius: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <span style="color: var(--cyan); font-weight: 600;">{{ selectedNode.name }}</span>
            <el-tag size="small" style="margin-left: 8px;">{{ selectedNode.type }}</el-tag>
          </div>
          <el-button size="small" type="primary" plain @click="selectedNode = null">关闭</el-button>
        </div>
        <div style="font-size: 12px; color: var(--text-muted); margin-top: 8px;">
          状态: {{ selectedNode.status || '正常' }} | IP: {{ selectedNode.ip || 'N/A' }}
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataLine, Aim, Cpu, Connection, Monitor, Warning, CircleCheck, Timer, Refresh, Setting, Loading, Umbrella } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const backendStatus = ref(false)
const lastUpdate = ref('--')
const topoRef = ref(null)
const topoLoading = ref(false)
const attackLoading = ref(false)
const defenseLoading = ref(false)
const aiLoading = ref(false)
const aiResult = ref('')
const aiSuggestions = ref([])
const attackType = ref('SQL注入')
const targetPort = ref('8080')
const attackIntensity = ref(5)
const defenseType = ref('firewall')
const defensePort = ref('8080')
const defenseIntensity = ref(5)
const topoView = ref('svg')
const selectedNode = ref(null)
const recentAttacks = ref([])
const activeTargets = ref(0)
const activeRules = ref(0)
const todayAttacks = ref(0)
const blockedCount = ref(0)
const cpuUsage = ref(35)
const memUsage = ref(42)

const intensityMarks = { 1: '低', 3: '轻', 5: '中', 7: '强', 10: '极高' }

const stats = ref([
  { key: 'health', title: '靶场健康度', value: '--', icon: 'CircleCheck', color: '#00e676', class: '', trend: 5 },
  { key: 'danger', title: '危险等级', value: '--', icon: 'Warning', color: '#ffd740', class: '', trend: -2 },
  { key: 'coverage', title: '防御覆盖率', value: '--', icon: 'Monitor', color: '#8b2ce6', class: '', trend: 8 },
  { key: 'runtime', title: '运行时间', value: '--', icon: 'Timer', color: '#00e5ff', class: '', trend: 0 },
])

async function loadStats() {
  try {
    const res = await axios.get('/api/stats/overview')
    backendStatus.value = true
    const data = res.data || {}
    const statsData = data.stats || {}

    // 使用真实数据
    stats.value[0].value = (statsData.health || 95) + '%'
    stats.value[0].class = 'stat-active'
    stats.value[1].value = statsData.alerts > 5 ? '中' : '低'
    stats.value[2].value = '0%'
    stats.value[3].value = '运行中'

    activeTargets.value = statsData.environments || 0
    activeRules.value = statsData.defenses || 0
    todayAttacks.value = statsData.attacks || 0
    blockedCount.value = statsData.alerts || 0
    cpuUsage.value = 35
    memUsage.value = 42
    lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
  } catch {
    backendStatus.value = false
    stats.value[0].value = '--'
    stats.value[1].value = '--'
    stats.value[2].value = '--'
    stats.value[3].value = '--'
  }
}

async function loadTopo() {
  if (!topoRef.value) return
  topoLoading.value = true
  try {
    const res = await axios.get('/api/topology/')
    const data = res.data || {}
    // 使用后端返回的真实节点和边数据
    if (data.status === 'success' && data.nodes && data.nodes.length > 0) {
      // 将后端数据转换为绘图格式
      const nodes = data.nodes.map((n, i) => ({
        id: n.id,
        name: n.label || n.name || n.id,
        type: n.type || 'target',
        x: 20 + (i % 4) * 20,
        y: 20 + Math.floor(i / 4) * 25
      }))
      const links = data.edges.map(e => ({
        source: e.source,
        target: e.target
      }))
      drawTopoFromData(nodes, links)
    } else {
      // 无数据时显示空拓扑
      drawTopoFromData([{ id: 'server', name: '靶场服务器', type: 'server', x: 50, y: 50 }], [])
    }
  } catch {
    drawTopoFromData([{ id: 'server', name: '靶场服务器', type: 'server', x: 50, y: 50 }], [])
  } finally { topoLoading.value = false }
}

function drawTopoFromData(nodes, links) {
  if (!topoRef.value) return
  const el = topoRef.value
  const w = el.clientWidth || 800
  const h = 360

  const typeColors = {
    router: '#00e5ff',
    firewall: '#8b2ce6',
    ids: '#8b2ce6',
    switch: '#00e5ff',
    attacker: '#ff4466',
    target: '#00e676',
    dmz: '#ffd740',
    logserver: '#00e676',
    range: '#00e676',
  }

  const typeLabels = {
    router: '路由器', firewall: '防火墙', ids: '入侵检测',
    switch: '交换机', attacker: '攻击机', target: '靶机',
    dmz: '隔离区', logserver: '分析服务', range: '靶场核心',
  }

  const nodesToDraw = nodes || [
    { id: 'core', name: '核心路由器', type: 'router', x: 50, y: 12 },
    { id: 'fw', name: '防火墙', type: 'firewall', x: 25, y: 30 },
    { id: 'ids', name: '入侵检测', type: 'ids', x: 75, y: 30 },
    { id: 'sw', name: '核心交换机', type: 'switch', x: 50, y: 45 },
    { id: 'attacker', name: '攻击机', type: 'attacker', x: 15, y: 65 },
    { id: 'target-a', name: '靶机A', type: 'target', x: 40, y: 75 },
    { id: 'target-b', name: '靶机B', type: 'target', x: 60, y: 75 },
    { id: 'dmz', name: 'DMZ区', type: 'dmz', x: 85, y: 65 },
    { id: 'range', name: '靶场核心', type: 'range', x: 50, y: 88 },
  ]

  const linksToDraw = links || [
    { source: 'core', target: 'fw' },
    { source: 'core', target: 'ids' },
    { source: 'fw', target: 'sw' },
    { source: 'ids', target: 'sw' },
    { source: 'sw', target: 'attacker' },
    { source: 'sw', target: 'target-a' },
    { source: 'sw', target: 'target-b' },
    { source: 'sw', target: 'dmz' },
    { source: 'target-a', target: 'range' },
    { source: 'target-b', target: 'range' },
  ]

  const nodeMap = {}
  nodesToDraw.forEach(n => { nodeMap[n.id] = n })

  // 绘制连接线（带动画效果）
  const lineElements = linksToDraw.map((l, i) => {
    const s = nodeMap[l.source]
    const t = nodeMap[l.target]
    if (!s || !t) return ''
    const x1 = s.x * w / 100
    const y1 = s.y * h / 100
    const x2 = t.x * w / 100
    const y2 = t.y * h / 100
    const color = typeColors[s.type] || '#00e5ff'
    return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" 
      stroke="${color}" stroke-width="1.5" stroke-opacity="0.4" stroke-dasharray="5,3"
      class="topo-line topo-line-${i}"/>`
  }).join('')

  // 绘制节点
  const nodeElements = nodesToDraw.map(n => {
    const cx = n.x * w / 100
    const cy = n.y * h / 100
    const color = typeColors[n.type] || '#00e5ff'
    const label = typeLabels[n.type] || n.name
    const isAttacker = n.type === 'attacker'
    const isTarget = n.type === 'target' || n.type === 'range'

    return `
      <g class="topo-node" data-id="${n.id}" data-type="${n.type}">
        <circle cx="${cx}" cy="${cy}" r="22" fill="#0a0a14" stroke="${color}" stroke-width="2" 
          filter="url(#glow)" class="node-circle"/>
        <circle cx="${cx}" cy="${cy}" r="4" fill="${color}" class="node-dot">
          <animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite"/>
        </circle>
        <text x="${cx}" y="${cy - 6}" text-anchor="middle" fill="${color}" font-size="10" 
          font-family="var(--font-display)" font-weight="600">${n.name}</text>
        <text x="${cx}" y="${cy + 8}" text-anchor="middle" fill="#606888" font-size="8" 
          font-family="var(--font-mono)">${label}</text>
        ${isAttacker ? `<text x="${cx}" y="${cy + 18}" text-anchor="middle" fill="#ff4466" font-size="7">⚠ 攻击源</text>` : ''}
        ${isTarget ? `<text x="${cx}" y="${cy + 18}" text-anchor="middle" fill="#00e676" font-size="7">● 运行中</text>` : ''}
      </g>`
  }).join('')

  const svg = `<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg" 
    style="background: radial-gradient(ellipse at center, #1a1a2e 0%, #0a0a14 100%); border-radius: 10px;">
    <defs>
      <filter id="glow">
        <feGaussianBlur stdDeviation="3" result="blur"/>
        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <style>
        .topo-line { animation: dash 20s linear infinite; }
        @keyframes dash { to { stroke-dashoffset: -100; } }
        .topo-node:hover .node-circle { stroke-width: 3; stroke-opacity: 1; }
        .topo-node { cursor: pointer; transition: all 0.2s; }
      </style>
    </defs>
    ${lineElements}
    ${nodeElements}
    <text x="${w - 10}" y="${h - 10}" text-anchor="end" fill="#606888" font-size="9" 
      font-family="var(--font-mono)">实时拓扑 · AI-SEC-RANGE</text>
  </svg>`

  el.innerHTML = svg

  // 添加节点点击事件
  el.querySelectorAll('.topo-node').forEach(nodeEl => {
    nodeEl.addEventListener('click', () => {
      const nodeId = nodeEl.getAttribute('data-id')
      const nodeType = nodeEl.getAttribute('data-type')
      const nodeData = nodesToDraw.find(n => n.id === nodeId)
      if (nodeData) {
        selectedNode.value = { ...nodeData, status: '正常', ip: '192.168.1.' + Math.floor(Math.random() * 255) }
      }
    })
  })
}

async function startAttack() {
  attackLoading.value = true
  try {
    const res = await axios.post('/api/attack/create', {
      name: attackType.value + '测试',
      attack_type: attackType.value,
      target: 'localhost:' + targetPort.value,
      port: targetPort.value,
      intensity: attackIntensity.value
    })
    ElMessage.success('攻击已启动')

    // 添加到最近攻击记录
    recentAttacks.value.unshift({
      id: Date.now(),
      type: attackType.value,
      time: new Date().toLocaleTimeString('zh-CN'),
      success: true
    })

    await loadStats()
  } catch (e) {
    recentAttacks.value.unshift({
      id: Date.now(),
      type: attackType.value,
      time: new Date().toLocaleTimeString('zh-CN'),
      success: false
    })
    ElMessage.error('攻击启动失败: ' + (e.response?.data?.msg || e.message))
  } finally { attackLoading.value = false }
}

async function aiAnalyze() {
  aiLoading.value = true
  aiResult.value = ''
  aiSuggestions.value = []
  try {
    const res = await axios.post('/api/ai/analyze', {})
    const data = res.data?.data || {}
    aiResult.value = data.analysis || '分析完成：系统运行正常，未发现明显安全威胁。'

    // 提取建议
    const suggestions = []
    if (aiResult.value.includes('建议')) {
      const lines = aiResult.value.split('\n')
      lines.forEach(line => {
        if (line.includes('建议') || line.includes('优化') || line.includes('修复')) {
          const clean = line.replace(/^[-*#\s]+/, '').trim()
          if (clean.length > 5 && clean.length < 50) {
            suggestions.push(clean)
          }
        }
      })
    }
    aiSuggestions.value = suggestions.slice(0, 3)

    ElMessage.success('AI 分析完成')
  } catch {
    ElMessage.error('AI 分析失败')
    aiResult.value = '<div style="color: var(--danger);">分析失败，请检查后端服务</div>'
  }
  finally { aiLoading.value = false }
}

async function startDefense() {
  defenseLoading.value = true
  try {
    const res = await axios.post('/api/defense/create', {
      name: defenseType.value + '防御规则',
      defense_type: defenseType.value,
      description: '快速防御规则',
      enabled: true,
      coverage: defenseIntensity.value * 10
    })
    ElMessage.success('防御规则已启用')
    activeRules.value++
    await loadStats()
  } catch (e) {
    ElMessage.error('防御启用失败: ' + (e.response?.data?.msg || e.message))
  } finally { defenseLoading.value = false }
}

function goToEnv() {
  router.push('/env')
}

let refreshInterval = null
onMounted(async () => {
  lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
  await loadStats()
  await loadTopo()
  refreshInterval = setInterval(async () => {
    await loadStats()
    lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
  }, 8000)
  window.addEventListener('resize', loadTopo)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
  window.removeEventListener('resize', loadTopo)
})
</script>

<style scoped>
.backend-warning {
  background: rgba(255, 68, 102, 0.1);
  border: 1px solid rgba(255, 68, 102, 0.35);
  border-radius: 8px;
  padding: 12px 18px;
  color: #ff7088;
  font-size: 13px;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.backend-warning code {
  font-family: var(--font-mono);
  background: rgba(255, 68, 102, 0.15);
  padding: 2px 8px;
  border-radius: 4px;
}

.stat-footer {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  font-size: 12px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-display) !important;
  font-weight: 700 !important;
  letter-spacing: 0.5px !important;
}

/* 统计卡片标题使用科技风字体 */
:deep(.el-statistic__title) {
  font-family: var(--font-display) !important;
  font-weight: 600 !important;
  letter-spacing: 0.3px !important;
}

:deep(.el-statistic__number) {
  font-family: var(--font-display) !important;
  font-weight: 700 !important;
}

/* 描述列表标签 */
:deep(.el-descriptions__label) {
  font-family: var(--font-mono) !important;
}

/* 时间线文字 */
:deep(.el-timeline-item__timestamp) {
  font-family: var(--font-mono) !important;
}

:deep(.el-timeline-item__content) {
  font-family: var(--font-ui) !important;
}

.topo-box {
  border-radius: 10px;
  overflow: hidden;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
