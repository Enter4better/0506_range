<template>
  <el-card shadow="hover" class="tech-card">
    <template #header>
      <div class="card-header">
        <span class="card-title"><el-icon>
            <Timer />
          </el-icon> 攻击记录</span>
        <div class="header-actions">
          <span class="log-count" v-if="total > 0">共 {{ total }} 条</span>
          <el-button text type="primary" size="small" @click="$emit('refresh')">
            <el-icon>
              <Refresh />
            </el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </template>
    <div v-if="logs.length === 0" class="empty-logs">
      <el-icon>
        <Document />
      </el-icon>
      <p>暂无攻击记录</p>
    </div>
    <el-timeline v-else class="attack-timeline">
      <el-timeline-item v-for="log in logs" :key="log.id || log.attack_id"
        :timestamp="formatTime(log.created_at || log.time)" :type="getLogType(log.status || log.type)"
        :hollow="log.status !== 'completed'" placement="top">
        <div class="timeline-content">
          <div class="timeline-header">
            <span class="timeline-title">{{ log.name || log.attack_type }}</span>
            <div class="header-right">
              <el-tag :type="getLogType(log.status || log.type)" size="small" effect="dark">
                {{ getStatusText(log.status || log.type) }}
              </el-tag>
              <el-button
                v-if="hasDetail(log)"
                text
                size="small"
                type="primary"
                @click.stop="toggleDetail(log.attack_id || log.id)"
              >
                <el-icon>
                  <component :is="expandedIds.has(String(log.attack_id || log.id)) ? 'ArrowUp' : 'ArrowDown'" />
                </el-icon>
                {{ expandedIds.has(String(log.attack_id || log.id)) ? '收起' : '详情' }}
              </el-button>
            </div>
          </div>
          <div class="timeline-detail">
            <span v-if="log.target"><el-icon>
                <Location />
              </el-icon> {{ log.target }}:{{ log.port }}</span>
            <span v-if="log.attack_type"><el-icon>
                <Aim />
              </el-icon> {{ log.attack_type }}</span>
          </div>

          <!-- 展开详情：终端风格 -->
          <div v-if="hasDetail(log) && expandedIds.has(String(log.attack_id || log.id))" class="attack-detail">
            <!-- 阶段与AI分析 -->
            <div class="detail-meta" v-if="getDetailMeta(log)">
              <div class="meta-item">
                <span class="meta-label">攻击阶段</span>
                <span class="meta-value">
                  <el-tag size="small" type="warning">{{ getDetailMeta(log).phase_name }}</el-tag>
                  <span class="phase-hint">Kill Chain {{ getDetailMeta(log).attack_phase }}/6</span>
                </span>
              </div>
              <div class="meta-item" v-if="getDetailMeta(log).ai_analysis">
                <span class="meta-label">AI分析</span>
                <span class="meta-value ai-analysis">{{ getDetailMeta(log).ai_analysis }}</span>
              </div>
            </div>

            <!-- 终端命令步骤 - Windows风格 -->
            <div class="terminal-block" v-if="getSteps(log).length > 0">
              <div class="terminal-title">
                <span class="terminal-label">攻击步骤 · 终端输出</span>
                <span class="win-controls">
                  <span class="win-btn minimize">─</span>
                  <span class="win-btn maximize">□</span>
                  <span class="win-btn close">✕</span>
                </span>
              </div>
              <div class="terminal-body">
                <div
                  v-for="step in getSteps(log)"
                  :key="step.step"
                  class="terminal-step"
                >
                  <div class="step-cmd">
                    <span class="step-prompt">$</span>
                    <span class="step-command">{{ step.command }}</span>
                  </div>
                  <div
                    class="step-output"
                    :class="step.status"
                  >{{ step.output }}</div>
                </div>
              </div>
            </div>

            <!-- 防御响应 -->
            <div class="defense-block" v-if="getDefenseInfo(log)">
              <div class="defense-title">
                <el-icon><Lock /></el-icon>
                防御响应
              </div>
              <div class="defense-content">
                <el-tag size="small" type="info" style="margin-right: 8px;">
                  等级 {{ getDefenseInfo(log).defense_level }} · {{ getDefenseInfo(log).level_name }}
                </el-tag>
                <span class="actions-text" v-if="getDefenseInfo(log).actions_taken?.length">
                  {{ getDefenseInfo(log).actions_taken.join(' | ') }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </el-timeline-item>
    </el-timeline>
    <div class="pagination-wrapper" v-if="total > pageSize">
      <el-pagination
        :current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        small
        background
        @current-change="(p) => $emit('page-change', p)"
      />
    </div>
  </el-card>
</template>

<script setup>
import { Timer, Refresh, Document, Location, Aim, ArrowUp, ArrowDown, Lock } from '@element-plus/icons-vue'
import { ref } from 'vue'

const props = defineProps({
  logs: { type: Array, default: () => [] },
  total: { type: Number, default: 0 },
  currentPage: { type: Number, default: 1 },
  pageSize: { type: Number, default: 10 }
})

const emit = defineEmits(['refresh', 'page-change'])

const expandedIds = ref(new Set())

function toggleDetail(id) {
  const key = String(id)
  if (expandedIds.value.has(key)) {
    expandedIds.value.delete(key)
  } else {
    expandedIds.value.add(key)
  }
}

function hasDetail(log) {
  const r = log.result
  if (!r) return false
  if (typeof r === 'string') {
    try { return JSON.parse(r).attack?.steps?.length > 0 } catch(e) { return false }
  }
  return r.attack?.steps?.length > 0 || r.attack?.ai_analysis
}

function getDetailMeta(log) {
  const r = log.result
  if (!r) return null
  let obj = typeof r === 'string' ? JSON.parse(r) : r
  const attack = obj.attack || obj
  return {
    phase_name: attack.phase_name || (attack.attack_phase ? `阶段${attack.attack_phase}` : ''),
    attack_phase: attack.attack_phase || 1,
    ai_analysis: attack.ai_analysis || ''
  }
}

function getSteps(log) {
  const r = log.result
  if (!r) return []
  let obj = typeof r === 'string' ? JSON.parse(r) : r
  const steps = obj.attack?.steps || []
  return Array.isArray(steps) ? steps : []
}

function getDefenseInfo(log) {
  const r = log.result
  if (!r) return null
  let obj = typeof r === 'string' ? JSON.parse(r) : r
  return obj.defense || null
}

function getLogType(status) {
  const typeMap = {
    'completed': 'success',
    'success': 'success',
    'running': 'primary',
    'pending': 'info',
    'failed': 'danger',
    'fail': 'danger'
  }
  return typeMap[status] || 'info'
}

function getStatusText(status) {
  const textMap = {
    'completed': '成功',
    'success': '成功',
    'running': '执行中',
    'pending': '等待中',
    'failed': '失败',
    'fail': '失败'
  }
  return textMap[status] || status
}

function formatTime(time) {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.log-count {
  font-size: 12px;
  color: var(--text-muted);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-display) !important;
}

.empty-logs {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: var(--text-muted);
}

.empty-logs .el-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.attack-timeline {
  padding: 8px;
}

.timeline-content {
  padding: 4px 0;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.timeline-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  font-family: var(--font-ui) !important;
}

.timeline-detail {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-muted);
}

.timeline-detail span {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 展开详情 */
.attack-detail {
  margin-top: 12px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  overflow: hidden;
}

.detail-meta {
  padding: 10px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.meta-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.meta-label {
  font-size: 11px;
  color: #8b949e;
  min-width: 52px;
  padding-top: 2px;
}

.meta-value {
  font-size: 12px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.phase-hint {
  color: #8b949e;
  font-size: 11px;
}

.ai-analysis {
  color: #c9d1d9;
  font-size: 12px;
  line-height: 1.5;
}

/* Windows风格终端样式 */
.terminal-block {
  background: #0d1117;
  border: 1px solid #3c3c3c;
  border-radius: 4px;
}

.terminal-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px 0 12px;
  background: #007acc;
  border-bottom: 1px solid #005a9e;
  border-radius: 4px 4px 0 0;
  height: 28px;
}

.terminal-label {
  font-size: 12px;
  color: #fff;
  font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
  text-shadow: 0 1px 1px rgba(0,0,0,0.3);
  white-space: nowrap;
}

.win-controls {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 100%;
}

.win-btn {
  width: 28px;
  height: 20px;
  border: none;
  border-radius: 0;
  background: transparent;
  color: #fff;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: default;
  user-select: none;
  line-height: 1;
  box-sizing: border-box;
}
.win-btn:hover {
  background: rgba(255,255,255,0.15);
}
.win-btn.close:hover {
  background: #e81123;
}

.terminal-body {
  padding: 10px 0;
  font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  max-height: 280px;
  overflow-y: auto;
}

.terminal-step {
  margin-bottom: 8px;
}

.step-cmd {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 14px;
}

.step-prompt {
  color: #3fb950;
  font-weight: bold;
  user-select: none;
}

.step-command {
  color: #e6edf3;
  word-break: break-all;
}

.step-output {
  padding: 4px 14px 4px 26px;
  color: #8b949e;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.5;
}

.step-output.success {
  color: #3fb950;
}

.step-output.failed {
  color: #f85149;
}

.defense-block {
  padding: 10px 14px;
  background: rgba(64, 158, 255, 0.06);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.defense-title {
  font-size: 12px;
  font-weight: 600;
  color: #58a6ff;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.defense-content {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 6px;
}

.actions-text {
  font-size: 12px;
  color: #8b949e;
  line-height: 1.5;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 12px 0 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
</style>
