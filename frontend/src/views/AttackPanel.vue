<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <h2 class="page-title">
        <el-icon>
          <Aim />
        </el-icon>
        攻击模拟面板
      </h2>
      <p class="page-desc">配置并执行各类安全攻击场景，支持多种攻击类型和自定义参数</p>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="12" :sm="6">
        <StatCard :icon="Aim" :value="stats.total" label="总攻击数" type="danger" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard :icon="SuccessFilled" :value="stats.success" label="成功攻击" type="success" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard :icon="Loading" :value="stats.running" label="执行中" type="warning" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard :icon="List" :value="attackTypes.length" label="攻击类型" type="info" />
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 左侧：攻击配置 + 攻击结果 -->
      <el-col :xs="24" :lg="14">
        <!-- 攻击配置表单 -->
        <el-card shadow="hover" class="tech-card" style="margin-bottom: 16px;">
          <template #header>
            <div class="card-header">
              <span class="card-title"><el-icon>
                  <Setting />
                </el-icon> 攻击配置</span>
              <el-tag v-if="form.type" :type="getAttackTypeTag(form.type)" size="small">
                {{ form.type }}
              </el-tag>
            </div>
          </template>

          <el-form :model="form" label-width="100px" size="default" class="attack-form">
            <el-form-item label="攻击名称">
              <el-input v-model="form.name" placeholder="给攻击起个名字（可选）" clearable>
                <template #prefix>
                  <el-icon>
                    <Edit />
                  </el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item label="攻击类型" required>
              <AttackTypeSelect v-model="form.type" @change="onAttackTypeChange" />
            </el-form-item>

            <el-row :gutter="20">
              <el-col :span="16">
                <el-form-item label="目标地址" required>
                  <el-input v-model="form.target" placeholder="192.168.1.100 或 localhost">
                    <template #prefix>
                      <el-icon>
                        <Location />
                      </el-icon>
                    </template>
                    <template #append>
                      <el-button @click="selectTarget" :icon="Monitor">选择靶场</el-button>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="端口">
                  <el-input v-model="form.port" placeholder="8080">
                    <template #prefix>
                      <el-icon>
                        <Connection />
                      </el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="攻击强度">
              <div class="intensity-wrapper">
                <el-slider v-model="form.intensity" :min="1" :max="10" :marks="intensityMarks"
                  :format-tooltip="formatIntensity" show-stops class="intensity-slider" />
              </div>
              <div class="intensity-footer">
                <el-tag :type="getIntensityType(form.intensity)" size="small" class="intensity-tag">
                  强度 {{ form.intensity }} - {{ formatIntensity(form.intensity) }}
                </el-tag>
              </div>
              <!-- 强度效果预览 -->
              <div class="intensity-preview">
                <div class="preview-row">
                  <span class="preview-label">攻击成功率</span>
                  <el-progress :percentage="intensityPreview.successRate" :color="intensityPreview.successColor"
                    :stroke-width="12" :format="() => intensityPreview.successRate + '%'" />
                </div>
                <div class="preview-row">
                  <span class="preview-label">防御拦截率</span>
                  <el-progress :percentage="intensityPreview.blockRate" :color="intensityPreview.blockColor"
                    :stroke-width="12" :format="() => intensityPreview.blockRate + '%'" />
                </div>
                <div class="preview-row">
                  <span class="preview-label">防御升级速度</span>
                  <el-tag :type="intensityPreview.defenseTagType" size="small">
                    {{ intensityPreview.defenseSpeed }}
                  </el-tag>
                </div>
                <div class="preview-desc">{{ intensityPreview.description }}</div>
              </div>
            </el-form-item>

          </el-form>

          <!-- 操作按钮区域 -->
          <div class="form-actions-wrapper">
            <p class="form-actions-tip">配置完成后点击下方按钮执行攻击操作</p>
            <div class="form-actions">
              <el-button type="danger" size="default" :loading="loading" @click="launch"
                :disabled="!form.type || !form.target">
                <el-icon>
                  <Aim />
                </el-icon>
                发起攻击
              </el-button>
              <el-button size="default" @click="resetForm">
                <el-icon>
                  <Refresh />
                </el-icon>
                重置配置
              </el-button>
            </div>
          </div>
        </el-card>

        <!-- 攻击结果（常态显示） -->
        <el-card shadow="hover" class="tech-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">
                <el-icon>
                  <Document />
                </el-icon>
                攻击结果
              </span>
              <div class="result-actions" v-if="result">
                <el-tag :type="resultType" size="small">{{ resultStatus }}</el-tag>
                <el-button text size="small" @click="copyResult">
                  <el-icon>
                    <CopyDocument />
                  </el-icon>
                  复制
                </el-button>
                <el-button text size="small" @click="result = ''">
                  <el-icon>
                    <Close />
                  </el-icon>
                  关闭
                </el-button>
              </div>
            </div>
          </template>
          <div v-if="result" class="result-content">
            <pre v-html="formatResult(result)"></pre>
          </div>
          <div v-else class="empty-progress">
            <el-icon :size="32" style="color: var(--text-muted);">
              <Document />
            </el-icon>
            <p>暂无攻击结果，请发起攻击</p>
          </div>
        </el-card>

      </el-col>

      <!-- 右侧：动态攻防进度 + 攻击记录 -->
      <el-col :xs="24" :lg="10">
        <!-- 动态攻防进度 -->
        <el-card shadow="hover" class="tech-card" style="margin-bottom: 16px;">
          <template #header>
            <div class="card-header">
              <span class="card-title">
                <el-icon>
                  <DataLine />
                </el-icon>
                动态攻防进度
              </span>
              <el-tag v-if="showProgress" :type="progressStatus.type" size="small">{{ progressStatus.text }}</el-tag>
              <el-tag v-else type="info" size="small">等待中</el-tag>
            </div>
          </template>
          <div v-if="showProgress" class="progress-content">
            <!-- 攻击阶段进度 -->
            <div class="progress-section">
              <div class="progress-label">
                <span>攻击阶段</span>
                <span class="progress-value">{{ attackPhaseName }}</span>
              </div>
              <el-progress :percentage="attackPhasePercent" :color="attackPhaseColor" :stroke-width="16"
                :format="attackPhaseFormat" />
            </div>
            <!-- 防御等级进度 -->
            <div class="progress-section">
              <div class="progress-label">
                <span>防御等级</span>
                <span class="progress-value">{{ defenseLevelName }}</span>
              </div>
              <el-progress :percentage="defenseLevelPercent" :color="defenseLevelColor" :stroke-width="16"
                :format="defenseLevelFormat" />
            </div>
            <!-- 攻防状态信息 -->
            <div class="progress-info" v-if="progressMessage">
              <el-alert :title="progressMessage" :type="progressAlertType" :closable="false" show-icon />
            </div>
          </div>
          <div v-else class="empty-progress">
            <el-icon :size="32" style="color: var(--text-muted);">
              <DataLine />
            </el-icon>
            <p>暂无攻防数据，请发起攻击</p>
          </div>
        </el-card>

        <!-- 攻击记录 -->
        <AttackTimeline :logs="attackLogs" :total="attackTotal" @refresh="loadAttackHistory"
          @page-change="onAttackPageChange" />
      </el-col>
    </el-row>

    <!-- 选择靶场对话框 -->
    <el-dialog v-model="targetDialogVisible" title="选择靶场" width="1100px" class="tech-dialog">
      <el-table :data="targets" stripe style="width: 100%;" size="small" v-loading="loadingTargets" max-height="400">
        <el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="color: var(--cyan); font-weight: 500;">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="image" label="镜像" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.image }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ports" label="端口映射" min-width="120">
          <template #default="{ row }">
            <span style="color: var(--purple); font-family: monospace;">{{ row.ports || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'running' ? 'success' : 'danger'" size="small">
              {{ row.status === 'running' ? '运行中' : '已停止' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created" label="创建时间" width="160">
          <template #default="{ row }">
            <span style="color: var(--text-muted); font-size: 12px;">{{ row.created || row.created_at || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="selectTargetConfirm(row)">
              选择
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'

import { ElMessage } from 'element-plus'
import {
  Aim, Setting, Edit, Location, Connection,
  MagicStick, Position, List, SuccessFilled, Loading,
  Refresh, CopyDocument, Close, Monitor, Document, DataLine
} from '@element-plus/icons-vue'
import request from '@/utils/request'

// 组件
import StatCard from '@/components/StatCard.vue'
import AttackTypeSelect from '@/components/AttackTypeSelect.vue'
import AttackTimeline from '@/components/AttackTimeline.vue'

// 状态
const loading = ref(false)
const loadingTargets = ref(false)
const result = ref('')
const resultType = ref('info')
const resultStatus = ref('')
const targetDialogVisible = ref(false)
const targets = ref([])
const selectedTargetStatus = ref(null)
const attackLogs = ref([])
const attackTypes = ref([])
const attackTotal = ref(0)
const attackPage = ref(1)

// 攻防进度状态
const showProgress = ref(false)
const attackPhasePercent = ref(0)
const attackPhaseName = ref('信息收集')
const defenseLevelPercent = ref(20)
const defenseLevelName = ref('监控级')
const progressMessage = ref('')
const progressAlertType = ref('info')
const progressStatus = ref({ type: 'warning', text: '执行中' })
const currentSessionId = ref('')
let progressTimer = null

// 统计数据
const stats = reactive({ total: 0, success: 0, running: 0, failed: 0 })

// 表单
const intensityMarks = { 1: '隐蔽', 3: '低', 5: '中', 7: '高', 10: '极限' }
const form = ref({ name: '', type: '', target: 'localhost', port: '80', intensity: 5 })

// 攻击阶段颜色映射
const phaseColors = {
  1: '#909399', 2: '#409eff', 3: '#e6a23c',
  4: '#f56c6c', 5: '#f56c6c', 6: '#909399'
}
const phaseNames = {
  1: '信息收集', 2: '漏洞探测', 3: '漏洞利用',
  4: '权限维持', 5: '横向移动', 6: '痕迹清理'
}
const defenseLevelNames = {
  1: '监控级', 2: '过滤级', 3: '阻断级',
  4: '封禁级', 5: '极限级'
}
const defenseLevelColors = {
  1: '#909399', 2: '#409eff', 3: '#e6a23c',
  4: '#f56c6c', 5: '#f56c6c'
}

// 攻防概率计算函数（与后端公式保持一致）
function calcAttackSuccessRate(attackPhase, intensity, defenseLevel) {
  // 攻击成功率 = 基础成功率 × 强度因子 × (1 - 防御等级因子)
  const baseRates = { 1: 0.75, 2: 0.65, 3: 0.50, 4: 0.40, 5: 0.35, 6: 0.30 }
  const baseRate = baseRates[attackPhase] || 0.50
  const intensityFactor = 0.8 + (intensity / 10) * 0.7
  const defenseFactor = defenseLevel / 6
  return Math.round(baseRate * intensityFactor * (1 - defenseFactor) * 100)
}

function calcDefenseInterceptRate(attackPhase, intensity, defenseLevel, coverage) {
  // 防御拦截率 = (防御等级因子 + 覆盖率因子) × 阶段因子 × 强度惩罚
  const levelFactor = defenseLevel / 8
  const coverageFactor = (coverage / 100) * 0.35
  const phaseFactors = { 1: 0.95, 2: 0.90, 3: 0.70, 4: 0.50, 5: 0.35, 6: 0.20 }
  const phaseFactor = phaseFactors[attackPhase] || 0.70
  const intensityPenalty = 1.0 - (intensity / 10) * 0.15
  let rate = (levelFactor + coverageFactor) * phaseFactor * intensityPenalty
  rate = Math.min(0.95, Math.max(0.05, rate))
  return Math.round(rate * 100)
}

// 强度效果预览 - 使用新的攻防概率模型
const intensityPreview = computed(() => {
  const i = form.value.intensity
  // 使用阶段1（信息收集）和默认防御等级1、覆盖率50%作为预览
  const attackPhase = 1
  const defenseLevel = 1
  const coverage = 50

  const successRate = calcAttackSuccessRate(attackPhase, i, defenseLevel)
  const blockRate = calcDefenseInterceptRate(attackPhase, i, defenseLevel, coverage)

  // 防御升级速度
  let defenseSpeed, defenseTagType
  if (i < 5) {
    defenseSpeed = '缓慢（强度<5，防御不易升级）'
    defenseTagType = 'success'
  } else if (i < 8) {
    defenseSpeed = '中等（强度5-7，防御会逐步升级）'
    defenseTagType = 'warning'
  } else {
    defenseSpeed = '快速（强度8-10，防御会迅速升级）'
    defenseTagType = 'danger'
  }
  // 描述
  let description
  if (i <= 3) {
    description = '🌱 低强度攻击：隐蔽性强，不易触发高级防御，但成功率较低'
  } else if (i <= 6) {
    description = '⚖️ 中等强度攻击：攻防平衡，适合常规测试场景'
  } else {
    description = '🔥 高强度攻击：成功率高，但会迅速触发高级防御，对抗更激烈'
  }
  // 颜色
  const successColor = successRate >= 70 ? '#f56c6c' : successRate >= 50 ? '#e6a23c' : '#67c23a'
  const blockColor = blockRate >= 50 ? '#e6a23c' : '#67c23a'
  return { successRate, blockRate, defenseSpeed, defenseTagType, description, successColor, blockColor }
})

// 工具函数
function getAttackTypeTag(type) {

  const typeMap = { 'SQL注入': 'danger', 'XSS攻击': 'warning', 'CSRF攻击': 'warning', '文件包含': 'danger', '命令执行': 'danger', 'SSRF攻击': 'warning', 'XXE注入': 'danger', '权限提升': 'danger', '容器逃逸': 'danger', '反弹Shell': 'danger', '端口扫描': 'info', '暴力破解': 'danger', '中间人攻击': 'danger', '后门植入': 'danger', '横向移动': 'danger', '数据外传': 'danger' }
  return typeMap[type] || 'info'
}

function formatIntensity(val) {
  const labels = { 1: '隐蔽', 2: '很低', 3: '低', 4: '中低', 5: '中等', 6: '中高', 7: '高', 8: '很高', 9: '极高', 10: '极限' }
  return labels[val] || val
}

function getIntensityType(val) {
  if (val <= 3) return 'success'
  if (val <= 6) return 'warning'
  return 'danger'
}

function onAttackTypeChange(type, port) {
  form.value.port = port
}

function resetForm() {
  form.value = { name: '', type: '', target: 'localhost', port: '80', intensity: 5 }
  result.value = ''
  showProgress.value = false
}

// 攻防进度动画
function startProgressAnimation(sessionId) {
  currentSessionId.value = sessionId
  showProgress.value = true
  attackPhasePercent.value = 16
  defenseLevelPercent.value = 20
  progressMessage.value = '动态攻防已启动，防御已激活...'
  progressAlertType.value = 'info'
  progressStatus.value = { type: 'warning', text: '执行中' }

  // 轮询获取攻防状态
  if (progressTimer) clearInterval(progressTimer)
  progressTimer = setInterval(async () => {
    try {
      const res = await request.get(`/attack/session/${sessionId}`)
      if (res.status === 'success') {
        const session = res.session || {}
        const attackStatus = res.attack_status || {}
        const defenseStatus = res.defense_status || {}

        const phase = attackStatus.current_phase || session.current_phase || 1
        const defLevel = defenseStatus.current_level || session.defense_level || 1

        // 更新攻击阶段进度
        attackPhasePercent.value = Math.round((phase / 6) * 100)
        attackPhaseName.value = phaseNames[phase] || `阶段${phase}`

        // 更新防御等级进度
        defenseLevelPercent.value = Math.round((defLevel / 5) * 100)
        defenseLevelName.value = defenseLevelNames[defLevel] || `等级${defLevel}`

        // 更新状态信息
        if (session.status === 'active') {
          progressMessage.value = `攻击阶段${phase}(${attackPhaseName.value}) | 防御等级${defLevel}(${defenseLevelName.value})`
          progressAlertType.value = defLevel >= 3 ? 'warning' : 'info'
        }

        // 如果攻击完成
        if (session.attacks_count > 0 && session.status === 'active') {
          progressStatus.value = { type: 'success', text: '已完成' }
          progressMessage.value = `攻防演练完成！攻击阶段${phase}，防御等级${defLevel}`
          progressAlertType.value = 'success'
          clearInterval(progressTimer)
          progressTimer = null
        }

        // 每次轮询都刷新统计，确保统计卡片实时更新
        loadStats()
      }
    } catch (e) {
      // 会话可能已结束
    }
  }, 2000)
}

function attackPhaseFormat(percentage) {
  return attackPhaseName.value
}

function defenseLevelFormat(percentage) {
  return defenseLevelName.value
}

// 攻击操作
async function launch() {
  if (!form.value.type || !form.value.target) {
    ElMessage.warning('请填写攻击类型和目标地址')
    return
  }

  // 检查靶场状态（如果是从弹窗选择的靶场）
  if (selectedTargetStatus.value) {
    if (selectedTargetStatus.value !== 'running') {
      ElMessage.warning('所选靶场已停止，请先启动靶场后再发起攻击')
      loading.value = false
      return
    }
  }

  loading.value = true
  result.value = ''
  showProgress.value = false

  try {
    const createRes = await request.post('/attack/create', {
      name: form.value.name || form.value.type,
      attack_type: form.value.type,
      target: form.value.target + ':' + form.value.port,
      port: form.value.port,
      intensity: form.value.intensity
    })

    if (createRes.status === 'success') {
      const attackId = createRes.attack?.attack_id || Date.now()
      const execRes = await request.post(`/attack/execute/${attackId}`)

      if (execRes.status === 'success') {
        const sessionId = execRes.session_id || ''

        // 启动攻防进度动画
        startProgressAnimation(sessionId)

        result.value = JSON.stringify({
          status: 'success',
          attack_id: attackId,
          session_id: sessionId,
          message: '动态攻防已启动，防御已激活'
        }, null, 2)
        resultType.value = 'success'
        resultStatus.value = '攻防进行中'
        ElMessage.success('动态攻防已启动')

        loadAttackHistory()
        loadStats()
      } else {
        throw new Error(execRes.msg || '攻击执行失败')
      }
    } else {
      throw new Error(createRes.msg || '创建攻击失败')
    }
  } catch (e) {
    result.value = `攻击执行失败: ${e.response?.data?.msg || e.message}`
    resultType.value = 'danger'
    resultStatus.value = '失败'
    ElMessage.error('攻击执行失败')
  } finally {
    loading.value = false
  }
}

// 数据加载（支持分页）
async function loadAttackHistory() {
  try {
    const res = await request.get('/attack/list', {
      params: { page: attackPage.value, limit: 10 }
    })
    if (res.status === 'success') {
      attackLogs.value = res.attacks || []
      attackTotal.value = res.total || 0
    }
  } catch (e) {
    console.error('加载攻击历史失败', e)
  }
}

function onAttackPageChange(page) {
  attackPage.value = page
  loadAttackHistory()
}

async function loadStats() {
  try {
    const res = await request.get('/attack/stats')
    if (res.status === 'success') {
      const userStats = res.user_stats || {}
      stats.total = userStats.total || 0
      stats.success = userStats.success || 0
      stats.running = userStats.running || 0
      stats.failed = userStats.failed || 0
    }
  } catch (e) {
    console.error('加载统计失败', e)
  }
}

async function selectTarget() {
  targetDialogVisible.value = true
  loadingTargets.value = true
  try {
    const res = await request.get('/env/list')
    if (res.status === 'success') {
      // 格式化数据，确保所有字段都正确显示（与EnvManage.vue保持一致）
      targets.value = (res.containers || res.data || []).map(t => ({
        ...t,
        name: t.name || '未命名靶场',
        image: t.image || t.os || 'unknown',
        ports: t.ports || t.port || '-',
        created: t.created || t.created_at || '-'
      }))
    }
  } catch (e) { ElMessage.error('获取靶场列表失败') }
  finally { loadingTargets.value = false }
}

function selectTargetConfirm(target) {
  if (target.ports) {
    const portMatch = target.ports.match(/(\d+):/)
    if (portMatch) form.value.port = portMatch[1]
  }
  form.value.target = 'localhost'
  selectedTargetStatus.value = target.status
  targetDialogVisible.value = false
  ElMessage.success(`已选择靶场: ${target.name}`)
}

function formatResult(text) {
  if (!text) return ''
  return text.replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>')
    .replace(/"成功"/g, '<span style="color: #67c23a;">"成功"</span>')
    .replace(/"失败"/g, '<span style="color: #f56c6c;">"失败"</span>')
}

function copyResult() {
  navigator.clipboard.writeText(result.value)
  ElMessage.success('已复制到剪贴板')
}

// 加载攻击类型
async function loadAttackTypes() {
  try {
    const res = await request.get('/attack/types')
    if (res.status === 'success' && res.types) {
      attackTypes.value = res.types
    }
  } catch (e) {
    console.error('加载攻击类型失败', e)
  }
}

onMounted(() => {
  loadAttackTypes()
  loadAttackHistory()
  loadStats()
})

onUnmounted(() => {
  if (progressTimer) clearInterval(progressTimer)
})
</script>

<style scoped>
.stats-row {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-display) !important;
}

.attack-form {
  padding: 8px 0;
}

.code-textarea {
  font-family: var(--font-mono);
}

.intensity-wrapper {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 8px 0;
}

.intensity-slider {
  flex: 1;
}

.intensity-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.intensity-tag {
  min-width: 100px;
  text-align: center;
  padding: 4px 12px;
}

/* 强度效果预览 */
.intensity-preview {
  margin-top: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.15);
  border-radius: 8px;
  border: 1px solid var(--border-dim);
}

.preview-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.preview-row:last-child {
  margin-bottom: 0;
}

.preview-label {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 80px;
  flex-shrink: 0;
}

.preview-row .el-progress {
  flex: 1;
}

.preview-desc {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border-dim);
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}


.form-actions-wrapper {
  padding: 16px;
  background: rgba(139, 44, 230, 0.05);
  border-radius: 8px;
  margin-top: 16px;
}

.form-actions-tip {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 12px;
  text-align: center;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.result-content {
  background: rgba(0, 0, 0, 0.2);
  padding: 16px;
  border-radius: 8px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
}

/* 攻防进度条样式 */
.progress-content {
  padding: 8px 0;
}

.progress-section {
  margin-bottom: 16px;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.progress-value {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 12px;
}

.progress-info {
  margin-top: 12px;
}

.empty-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: var(--text-muted);
  gap: 12px;
}

@media (max-width: 768px) {
  .form-actions {
    flex-wrap: wrap;
  }
}
</style>
