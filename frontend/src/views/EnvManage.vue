<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon>
          <Setting />
        </el-icon>
        靶场环境管理
      </h2>
      <p class="page-desc">
        Docker容器管理 | 运行中 {{ stats.running }} 个 | 总计 {{ stats.total }} 个
      </p>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="14" style="margin-bottom: 14px;">
      <el-col :xs="24" :sm="8" :md="8">
        <el-card shadow="hover" class="stat-card stat-success">
          <el-statistic title="运行中靶场" :value="stats.running">
            <template #prefix>
              <el-icon style="color: #00e676; font-size: 18px;">
                <CircleCheck />
              </el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8" :md="8">
        <el-card shadow="hover" class="stat-card stat-warning">
          <el-statistic title="已停止靶场" :value="stats.stopped">
            <template #prefix>
              <el-icon style="color: #ffd740; font-size: 18px;">
                <Warning />
              </el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8" :md="8">
        <el-card shadow="hover" class="stat-card stat-info">
          <el-statistic title="总靶场数" :value="stats.total">
            <template #prefix>
              <el-icon style="color: #00e5ff; font-size: 18px;">
                <DataLine />
              </el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <!-- 操作按钮 -->
    <el-card shadow="hover" class="tech-card" style="margin-bottom: 14px;">
      <div style="display: flex; gap: 12px; flex-wrap: wrap;">
        <el-button type="primary" @click="showCreateModal = true">
          <el-icon>
            <Plus />
          </el-icon> 创建靶场
        </el-button>
        <el-button @click="fetchTargets" :loading="loading">
          <el-icon>
            <Refresh />
          </el-icon> 刷新列表
        </el-button>
        <el-button type="danger" @click="cleanAllTargets" :disabled="targets.length === 0">
          <el-icon>
            <Delete />
          </el-icon> 清理全部
        </el-button>
        <el-button type="warning" @click="exportTargets" :disabled="targets.length === 0">
          <el-icon>
            <Download />
          </el-icon> 导出列表
        </el-button>
      </div>

    </el-card>

    <!-- 靶场列表 -->
    <el-card shadow="hover" class="tech-card">
      <template #header>
        <div class="card-title">
          <el-icon>
            <Monitor />
          </el-icon> 靶场列表
          <el-tag size="small" style="margin-left: 8px;">{{ targets.length }} 个</el-tag>
        </div>
      </template>

      <div v-if="loading" style="text-align: center; padding: 40px;">
        <el-icon :size="32" style="color: var(--cyan); animation: spin 1.5s linear infinite;">
          <Loading />
        </el-icon>
        <p style="color: var(--text-muted); margin-top: 8px;">正在加载靶场数据...</p>
      </div>

      <div v-else-if="targets.length === 0" style="text-align: center; padding: 40px; color: var(--text-muted);">
        <el-icon :size="48">
          <Box />
        </el-icon>
        <p style="margin-top: 12px;">暂无靶场环境</p>
        <p style="font-size: 12px; margin-top: 4px;">点击"创建靶场"按钮开始创建</p>
      </div>

      <el-table v-else :data="targets" stripe style="width: 100%;" size="small">
        <el-table-column prop="name" label="名称" min-width="150">
          <template #default="{ row }">
            <span style="color: var(--cyan); font-weight: 500;">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="image" label="镜像" min-width="150">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.image }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="靶场类型" min-width="200">
          <template #default="{ row }">
            <template v-if="getTargetMeta(row.image)">
              <el-tag size="small" :type="getTargetMeta(row.image).color" style="margin-right: 4px;">
                {{ getTargetMeta(row.image).short }}
              </el-tag>
              <el-tag v-for="v in getTargetMeta(row.image).vulnTypes.slice(0, 3)" :key="v"
                size="small" type="info" style="margin-right: 3px; font-size: 10px;">{{ v }}</el-tag>
              <span v-if="getTargetMeta(row.image).vulnTypes.length > 3"
                style="font-size: 10px; color: var(--text-muted);">+{{ getTargetMeta(row.image).vulnTypes.length - 3 }}</span>
            </template>
            <span v-else style="font-size: 11px; color: var(--text-muted);">通用容器</span>
          </template>
        </el-table-column>
        <el-table-column prop="ports" label="端口映射" min-width="100">
          <template #default="{ row }">
            <span style="color: var(--purple); font-family: monospace;">{{ row.ports || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'running' ? 'success' : 'danger'" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created" label="创建时间" width="150">
          <template #default="{ row }">
            <span style="color: var(--text-muted); font-size: 12px;">{{ row.created || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button v-if="row.status === 'running'" size="small" type="warning" @click="stopTarget(row)">
                停止
              </el-button>
              <el-button v-else size="small" type="success" @click="startTarget(row)">
                启动
              </el-button>
              <el-button size="small" type="danger" @click="deleteTarget(row)">
                删除
              </el-button>
              <el-button v-if="row.ports" size="small" type="primary" @click="accessTarget(row)">
                访问
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建靶场弹窗 -->
    <el-dialog v-model="showCreateModal" title="创建新靶场" width="500px" class="tech-dialog"
      @keyup.enter="createForm.image && createForm.port ? createTarget() : undefined">
      <el-form :model="createForm" label-width="100px" size="small">
        <el-form-item label="选择镜像" required>
          <el-select v-model="createForm.image" placeholder="请选择镜像" filterable style="width: 100%;">
            <el-option-group label="Web服务">
              <el-option label="Nginx Web服务器" value="nginx" />
              <el-option label="Apache HTTP" value="httpd:alpine" />
              <el-option label="PHP 8.1 + Apache" value="php:8.1-apache" />
            </el-option-group>
            <el-option-group label="数据库">
              <el-option label="MySQL 8.0" value="mysql:8.0" />
              <el-option label="Redis 缓存" value="redis:alpine" />
              <el-option label="PostgreSQL" value="postgres:15-alpine" />
            </el-option-group>
            <el-option-group label="漏洞靶场">
              <el-option label="DVWA (漏洞靶场)" value="vulnerables/web-dvwa" />
              <el-option label="WebGoat" value="webgoat/webgoat" />
              <el-option label="Juice Shop (漏洞靶场)" value="bkimminich/juice-shop" />
            </el-option-group>
            <el-option-group label="系统环境">
              <el-option label="Ubuntu 22.04" value="ubuntu:22.04" />
              <el-option label="Python 3.11" value="python:3.11-slim" />
              <el-option label="Node.js 18" value="node:18-alpine" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="端口映射" required>
          <el-input v-model="createForm.port" placeholder="例如: 8080:80">
            <template #prepend>PORT</template>
          </el-input>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">格式: 主机端口:容器端口</div>
        </el-form-item>

        <!-- 综合漏洞靶场说明（选中 DVWA / WebGoat / Juice Shop 时显示） -->
        <el-form-item v-if="getTargetMeta(createForm.image)" label=" ">
          <div class="vuln-hint-box">
            <div style="font-weight: 600; margin-bottom: 6px; color: var(--el-color-warning);">
              🎯 {{ getTargetMeta(createForm.image).label }}
            </div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">
              {{ getTargetMeta(createForm.image).description }}
            </div>
            <div style="margin-bottom: 4px; font-size: 11px; color: var(--text-muted);">已知漏洞类型（可直接发起对应攻击）：</div>
            <div>
              <el-tag v-for="v in getTargetMeta(createForm.image).vulnTypes" :key="v"
                size="small" type="warning" style="margin: 2px;">{{ v }}</el-tag>
            </div>
            <div style="margin-top: 8px; font-size: 11px; color: var(--text-muted);">
              覆盖范围：{{ getTargetMeta(createForm.image).owaspCoverage }} ·
              难度：{{ getTargetMeta(createForm.image).difficulty }}
            </div>
          </div>
        </el-form-item>

        <!-- 靶场名称自动生成，无需用户输入 -->

      </el-form>
      <template #footer>
        <el-button @click="showCreateModal = false">取消</el-button>
        <el-button type="primary" @click="createTarget" :disabled="!createForm.image || !createForm.port">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Setting, Plus, Refresh, Delete, Monitor, CircleCheck, Warning, DataLine, Box, Loading, Download } from '@element-plus/icons-vue'

import request from '../utils/request'
import { COMPREHENSIVE_TARGETS, getTargetMeta, IMAGE_PORT_HINTS } from '@/utils/targetMeta'

const targets = ref([])
const loading = ref(true)
const showCreateModal = ref(false)
const stats = reactive({ running: 0, stopped: 0, total: 0 })

const createForm = reactive({
  image: '',
  port: '8080:80',
  name: ''
})

let refreshInterval = null

// 选择镜像时自动更新端口建议（覆盖所有已知镜像）
watch(() => createForm.image, (img) => {
  createForm.port = IMAGE_PORT_HINTS[img] ?? '8080:80'
})

// 获取靶场列表
async function fetchTargets() {
  try {
    const res = await request.get('/env/list')
    if (res.status === 'success') {
      targets.value = res.containers || res.data || []
      // 格式化数据，确保所有字段都正确显示
      targets.value = targets.value.map(t => ({
        ...t,
        name: t.name || '未命名靶场',
        image: t.image || t.os || 'unknown',
        ports: t.ports || t.port || '-',
        created: t.created || t.created_at || '-'
      }))
      updateStats()
    }
  } catch (err) {
    console.error('获取靶场列表失败:', err)
    ElMessage.error('获取靶场列表失败')
    targets.value = []
    updateStats()
  } finally {
    loading.value = false
  }
}

// 更新统计
function updateStats() {
  stats.total = targets.value.length
  stats.running = targets.value.filter(t => t.status === 'running').length
  stats.stopped = stats.total - stats.running
}

// 创建靶场 - 修复：发送正确的数据格式
// 修改 createTarget 函数
async function createTarget() {
  if (!createForm.image || !createForm.port) {
    ElMessage.warning('请填写完整信息')
    return
  }

  try {
    const postData = {
      image: createForm.image,
      port: createForm.port
    }

    console.log('发送创建请求:', postData)

    const res = await request.post('/env/create', postData)


    if (res.status === 'success') {
      ElMessage.success(`靶场创建成功: ${res.name || createForm.image}`)
      showCreateModal.value = false
      // 重置表单
      createForm.image = ''
      createForm.port = '8080:80'
      createForm.name = ''
      // 重要：延迟一下再刷新，确保后端容器已完全创建
      setTimeout(() => {
        fetchTargets()
      }, 1000)
    } else {
      ElMessage.error(res.msg || '创建失败')
    }
  } catch (err) {
    console.error('创建失败:', err)
    ElMessage.error('创建靶场失败: ' + (err.response?.data?.msg || err.message))
  }
}
// 启动靶场
async function startTarget(target) {
  try {
    const id = target.target_id || target.id || target.name
    const res = await request.post(`/env/start/${id}`)
    if (res.status === 'success') {
      ElMessage.success(`靶场已启动: ${target.name}`)
      await fetchTargets()
    } else {
      ElMessage.error(res.msg || '启动失败')
    }
  } catch (err) {
    ElMessage.error('启动失败')
  }
}

// 停止靶场
async function stopTarget(target) {
  try {
    const id = target.target_id || target.id || target.name
    const res = await request.post(`/env/stop/${id}`)
    if (res.status === 'success') {
      ElMessage.success(`靶场已停止: ${target.name}`)
      await fetchTargets()
    } else {
      ElMessage.error(res.msg || '停止失败')
    }
  } catch (err) {
    ElMessage.error('停止失败')
  }
}

// 删除靶场
async function deleteTarget(target) {
  try {
    await ElMessageBox.confirm(`确定要删除靶场 "${target.name}" 吗？`, '确认删除', {
      type: 'warning'
    })

    const id = target.target_id || target.id || target.name
    const res = await request.post(`/env/delete/${id}`)
    if (res.status === 'success') {
      ElMessage.success(`靶场已删除: ${target.name}`)
      // 立即从本地列表中移除（使用多种匹配方式确保找到）
      const index = targets.value.findIndex(t => 
        (t.id || t.target_id) === (target.id || target.target_id) ||
        t.name === target.name ||
        t.container_name === target.container_name
      )
      if (index !== -1) {
        targets.value.splice(index, 1)
        updateStats()
      }
      // 延迟刷新后端数据确保完全同步
      setTimeout(() => {
        fetchTargets()
      }, 1000)
    } else {
      ElMessage.error(res.msg || '删除失败')
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('删除失败: ' + (err.message || '未知错误'))
    }
  }
}

// 清理全部
async function cleanAllTargets() {
  try {
    await ElMessageBox.confirm('确定要清理所有靶场吗？此操作不可恢复！', '确认清理', {
      type: 'warning'
    })

    const res = await request.post('/env/clean')
    if (res.status === 'success') {
      ElMessage.success(`已清理 ${res.cleaned} 个靶场`)
      await fetchTargets()
    } else {
      ElMessage.error(res.msg || '清理失败')
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('清理失败')
    }
  }
}

// 访问靶场
function accessTarget(target) {
  // 从端口映射中提取主机端口
  let port = null

  if (target.ports) {
    // 端口格式可能是 "8081:86/tcp" 或 "8080:80/tcp"
    const match = target.ports.match(/(\d+):/)
    if (match) {
      port = match[1]
    }
  }

  if (port) {
    const url = `http://localhost:${port}`
    console.log('访问地址:', url)
    window.open(url, '_blank')
  } else {
    ElMessage.warning('无法获取端口信息')
  }
}

// 获取状态文本
function getStatusText(status) {
  const statusMap = {
    'running': '运行中',
    'stopped': '已停止',
    'exited': '已停止',
    'created': '已创建',
    'pending': '等待中'
  }
  return statusMap[status] || status
}

// 导出靶场列表
function exportTargets() {
  try {
    const dataStr = JSON.stringify(targets.value, null, 2)
    const blob = new Blob([dataStr], { type: 'application/json;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const now = new Date()
    const ts = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
    a.download = `targets_export_${ts}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('靶场列表已导出')
  } catch (e) {
    ElMessage.error('导出失败: ' + (e.message || '未知错误'))
  }
}

onMounted(() => {
  fetchTargets()
  refreshInterval = setInterval(fetchTargets, 30000)
})


onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-display) !important;
  letter-spacing: 0.5px !important;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.stat-card {
  background: linear-gradient(135deg, var(--card-bg) 0%, rgba(255, 255, 255, 0.05) 100%);
  border-radius: 12px;
  border: 1px solid var(--border-color);
}

.stat-success .el-statistic__title {
  color: #67c23a;
}

.stat-warning .el-statistic__title {
  color: #e6a23c;
}

.stat-info .el-statistic__title {
  color: #409eff;
}

.vuln-hint-box {
  background: rgba(230, 162, 60, 0.08);
  border: 1px solid rgba(230, 162, 60, 0.3);
  border-radius: 8px;
  padding: 12px 14px;
  width: 100%;
}
</style>