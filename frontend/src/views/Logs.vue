<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon>
          <Document />
        </el-icon>
        攻防演练日志
      </h2>
      <p class="page-desc">AI智能体自动生成的攻防演练实时日志</p>
    </div>

    <!-- Agent状态概览 -->
    <el-row :gutter="16" class="agent-status-row">
      <el-col :xs="24" :sm="8">
        <div class="agent-card env-card">
          <div class="agent-icon">
            <el-icon>
              <Monitor />
            </el-icon>
          </div>
          <div class="agent-info">
            <div class="agent-name">环境管理Agent</div>
            <div class="agent-desc">资源编排 · 靶场构建</div>
          </div>
          <el-tag :type="agentStats.env.running ? 'success' : 'info'" size="small">
            {{ agentStats.env.running ? '运行中' : '待命' }}
          </el-tag>
        </div>
      </el-col>
      <el-col :xs="24" :sm="8">
        <div class="agent-card attack-card">
          <div class="agent-icon">
            <el-icon>
              <Warning />
            </el-icon>
          </div>
          <div class="agent-info">
            <div class="agent-name">模拟攻击Agent</div>
            <div class="agent-desc">漏洞利用 · 渗透测试</div>
          </div>
          <el-tag :type="agentStats.attack.running ? 'danger' : 'info'" size="small">
            {{ agentStats.attack.running ? '攻击中' : '待命' }}
          </el-tag>
        </div>
      </el-col>
      <el-col :xs="24" :sm="8">
        <div class="agent-card defense-card">
          <div class="agent-icon">
            <el-icon>
              <CircleCheck />
            </el-icon>
          </div>
          <div class="agent-info">
            <div class="agent-name">模拟防御Agent</div>
            <div class="agent-desc">检测拦截 · 安全响应</div>
          </div>
          <el-tag :type="agentStats.defense.running ? 'success' : 'info'" size="small">
            {{ agentStats.defense.running ? '防御中' : '待命' }}
          </el-tag>
        </div>
      </el-col>
    </el-row>

    <!-- 日志流 -->
    <el-card shadow="hover" class="tech-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon>
              <DataLine />
            </el-icon>
            实时日志流
          </span>
          <div class="header-actions">
            <el-select v-model="sourceFilter" size="small" style="width: 130px;">
              <el-option label="全部来源" value="all" />
              <el-option label="环境管理" value="env" />
              <el-option label="模拟攻击" value="attack" />
              <el-option label="模拟防御" value="defense" />
            </el-select>
            <el-select v-model="levelFilter" size="small" style="width: 100px; margin-left: 8px;">
              <el-option label="全部级别" value="" />
              <el-option label="危险" value="danger" />
              <el-option label="警告" value="warning" />
              <el-option label="成功" value="success" />
              <el-option label="信息" value="info" />
            </el-select>
            <el-button size="small" @click="loadLogs" :loading="loading" :icon="Refresh">
              刷新
            </el-button>
            <el-button size="small" :type="autoRefresh ? 'primary' : ''" @click="toggleAutoRefresh">
              {{ autoRefresh ? '自动刷新中' : '手动刷新' }}
            </el-button>
            <el-dropdown trigger="click" @command="handleExport">
              <el-button size="small" type="warning">
                <el-icon>
                  <Download />
                </el-icon> 导出
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="json">导出 JSON</el-dropdown-item>
                  <el-dropdown-item command="csv">导出 CSV</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>

          </div>
        </div>
      </template>

      <div ref="logContainer" class="log-container">
        <div v-if="loading && logs.length === 0" class="empty-state">
          <el-icon class="loading-icon">
            <Loading />
          </el-icon>
          <p>加载日志中...</p>
        </div>
        <div v-else-if="filteredLogs.length === 0" class="empty-state">
          <el-icon>
            <Document />
          </el-icon>
          <p>暂无日志，启动攻防演练后将自动生成</p>
        </div>
        <div v-else class="log-list">
          <div v-for="(log, i) in filteredLogs" :key="log.id || i" class="log-row" :class="'log-level-' + log.level">
            <span class="log-time">{{ log.time }}</span>
            <el-tag :type="getLevelType(log.level)" size="small" effect="dark" class="log-tag">
              {{ log.levelText }}
            </el-tag>
            <el-tag :type="getSourceType(log.source)" size="small" class="log-tag">
              {{ log.sourceLabel }}
            </el-tag>
            <span class="log-msg">{{ log.msg }}</span>
          </div>
        </div>
      </div>

      <div class="pagination-wrapper" v-if="totalLogs > pageSize">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[50, 100, 200]"
          :total="totalLogs" layout="total, prev, pager, next" small background @change="loadLogs" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Refresh, Warning, CircleCheck, DataLine, Monitor, Loading, Download } from '@element-plus/icons-vue'

import request from '@/utils/request'

const loading = ref(false)
const logs = ref([])
const sourceFilter = ref('all')
const levelFilter = ref('')
const logContainer = ref(null)
const autoRefresh = ref(true)
const currentPage = ref(1)
const pageSize = ref(100)
const totalLogs = ref(0)

const agentStats = ref({
  env: { running: false, count: 0 },
  attack: { running: false, count: 0 },
  defense: { running: false, count: 0 }
})

const levelMap = { danger: '危险', warning: '警告', success: '成功', info: '信息', error: '错误' }
const sourceLabelMap = {
  env_agent: '环境管理', env_manager: '环境管理',
  attack: '模拟攻击',
  defense: '模拟防御',
  target: '环境管理', auth: '认证', docker: 'Docker', system: '系统'
}

const filteredLogs = computed(() => {
  let result = logs.value
  if (levelFilter.value) {
    result = result.filter(l => l.level === levelFilter.value)
  }
  return result
})

function getLevelType(level) {
  const map = { danger: 'danger', warning: 'warning', success: 'success', info: 'info', error: 'danger' }
  return map[level] || 'info'
}

function getSourceType(source) {
  const map = { attack: 'danger', defense: 'success', env_agent: '', env_manager: '' }
  return map[source] || 'info'
}

function formatTime(time) {
  if (!time) return '--'
  const d = new Date(time)
  const pad = n => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function loadLogs() {
  loading.value = true
  try {
    // 构建source参数
    let sourceParam = ''
    if (sourceFilter.value === 'env') {
      // 环境管理相关的日志source可能是 target、env_agent、env_manager
      sourceParam = 'target'
    } else if (sourceFilter.value !== 'all') {
      sourceParam = sourceFilter.value
    }

    const res = await request.get('/logs/list', {
      params: {
        page: currentPage.value,
        size: pageSize.value,
        source: sourceParam,
        level: levelFilter.value || undefined
      }
    })

    if (res.status === 'success') {
      const raw = res.logs || res.data || []
      totalLogs.value = res.total || raw.length

      logs.value = raw.map(l => {
        const time = l.created_at || l.time || new Date().toISOString()
        return {
          id: l.log_id || l.id || Date.now() + Math.random(),
          time: formatTime(time),
          level: l.level || 'info',
          levelText: levelMap[l.level] || l.level || '信息',
          source: l.source || 'system',
          sourceLabel: sourceLabelMap[l.source] || l.source || '系统',
          msg: l.message || l.action || l.detail || '系统日志'
        }
      })

      // 更新Agent状态统计
      updateAgentStats(raw)
    }
  } catch (e) {
    console.error('加载日志失败:', e)
    ElMessage.error('日志加载失败')
  } finally {
    loading.value = false
  }

  await nextTick()
  if (logContainer.value) {
    logContainer.value.scrollTop = 0
  }
}

function updateAgentStats(rawLogs) {
  const recentLogs = rawLogs.slice(0, 50)
  agentStats.value.env.count = recentLogs.filter(l => l.source === 'env_agent' || l.source === 'env_manager' || l.source === 'target').length
  agentStats.value.attack.count = recentLogs.filter(l => l.source === 'attack').length
  agentStats.value.defense.count = recentLogs.filter(l => l.source === 'defense').length

  // 判断Agent是否活跃（最近50条中有相关日志则认为运行中）
  agentStats.value.env.running = agentStats.value.env.count > 0
  agentStats.value.attack.running = agentStats.value.attack.count > 0
  agentStats.value.defense.running = agentStats.value.defense.count > 0
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
}

// 导出日志
async function handleExport(format) {
  try {
    const params = { format }
    if (sourceFilter.value !== 'all') {
      params.source = sourceFilter.value === 'env' ? 'target' : sourceFilter.value
    }
    if (levelFilter.value) {
      params.level = levelFilter.value
    }

    const response = await request.get('/logs/export', {
      params,
      responseType: 'blob'
    })

    // 创建下载链接
    const blob = new Blob([response.data], { type: format === 'csv' ? 'text/csv;charset=utf-8' : 'application/json;charset=utf-8' })

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const now = new Date()
    const ts = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
    a.download = `logs_export_${ts}.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success(`日志已导出为 ${format.toUpperCase()} 格式`)
  } catch (e) {
    ElMessage.error('导出失败: ' + (e.message || '未知错误'))
  }
}


let interval = null
onMounted(() => {
  loadLogs()
  interval = setInterval(() => {
    if (autoRefresh.value) loadLogs()
  }, 5000)
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<style scoped>
.agent-status-row {
  margin-bottom: 16px;
}

.agent-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(8, 10, 20, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  transition: all 0.3s ease;
}

.agent-card:hover {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(8, 10, 20, 0.8);
}

.env-card {
  border-left: 3px solid #409eff;
}

.attack-card {
  border-left: 3px solid #f56c6c;
}

.defense-card {
  border-left: 3px solid #67c23a;
}

.agent-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.agent-info {
  flex: 1;
}

.agent-name {
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e0;
}

.agent-desc {
  font-size: 11px;
  color: #888;
  margin-top: 2px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #e0e0e0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.log-container {
  max-height: 500px;
  overflow-y: auto;
  background: rgba(8, 10, 20, 0.4);
  border-radius: 6px;
  padding: 8px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #666;
}

.empty-state .el-icon {
  font-size: 40px;
  margin-bottom: 12px;
  opacity: 0.4;
}

.loading-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.log-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-family: 'Consolas', 'Courier New', monospace;
  transition: background 0.15s;
}

.log-row:hover {
  background: rgba(255, 255, 255, 0.04);
}

.log-level-danger {
  border-left: 3px solid #f56c6c;
}

.log-level-warning {
  border-left: 3px solid #e6a23c;
}

.log-level-success {
  border-left: 3px solid #67c23a;
}

.log-level-info {
  border-left: 3px solid #909399;
}

.log-level-error {
  border-left: 3px solid #f56c6c;
}

.log-time {
  color: #666;
  white-space: nowrap;
  min-width: 95px;
  font-size: 11px;
}

.log-tag {
  flex-shrink: 0;
}

.log-msg {
  color: #bbb;
  flex: 1;
  word-break: break-all;
  line-height: 1.4;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
  margin-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

@media (max-width: 768px) {
  .agent-status-row .el-col {
    margin-bottom: 8px;
  }

  .header-actions {
    width: 100%;
  }
}
</style>