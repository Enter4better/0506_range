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
            <el-tag :type="getLogType(log.status || log.type)" size="small" effect="dark">
              {{ getStatusText(log.status || log.type) }}
            </el-tag>
          </div>
          <div class="timeline-detail">
            <span v-if="log.target"><el-icon>
                <Location />
              </el-icon> {{ log.target }}:{{ log.port }}</span>
            <span v-if="log.attack_type"><el-icon>
                <Aim />
              </el-icon> {{ log.attack_type }}</span>
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
import { Timer, Refresh, Document, Location, Aim } from '@element-plus/icons-vue'

const props = defineProps({
  logs: { type: Array, default: () => [] },
  total: { type: Number, default: 0 },
  currentPage: { type: Number, default: 1 },
  pageSize: { type: Number, default: 10 }
})

const emit = defineEmits(['refresh', 'page-change'])

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

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 12px 0 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
</style>
