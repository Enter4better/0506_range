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

            <!-- 选中综合靶场时显示漏洞匹配提示 -->
            <el-form-item v-if="selectedTargetMeta" label=" ">
              <div class="target-meta-hint">
                <el-tag size="small" :type="selectedTargetMeta.color" style="margin-right: 8px;">
                  {{ selectedTargetMeta.short }}
                </el-tag>
                <span style="font-size: 12px; color: var(--text-secondary);">
                  {{ selectedTargetMeta.label }} — 推荐攻击类型：
                </span>
                <el-tag v-for="v in selectedTargetMeta.vulnTypes" :key="v"
                  size="small"
                  :type="form.type === v ? 'success' : 'info'"
                  style="margin: 2px; cursor: pointer;"
                  @click="form.type = v">
                  {{ v }}{{ form.type === v ? ' ✓' : '' }}
                </el-tag>
              </div>
            </el-form-item>

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
        <AttackTimeline
          :logs="attackLogs"
          :total="attackTotal"
          :current-page="attackLogPage"
          :page-size="attackLogPageSize"
          @refresh="loadAttackHistory(1)"
          @page-change="loadAttackHistory"
        />
      </el-col>
    </el-row>

    <!-- 选择靶场对话框：点击行高亮，Enter 确认选中 -->
    <el-dialog v-model="targetDialogVisible" title="选择靶场（点击行高亮后按 Enter 确认）" width="1200px" class="tech-dialog"
      @keyup.enter="tableCurrentRow ? selectTargetConfirm(tableCurrentRow) : undefined">
      <el-table :data="targets" stripe style="width: 100%;" size="small" v-loading="loadingTargets" max-height="380"
        highlight-current-row @current-change="(row) => tableCurrentRow = row" @row-dblclick="selectTargetConfirm">
        <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="color: var(--cyan); font-weight: 500;">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="image" label="镜像" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.image }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="靶场类型 / 已知漏洞" min-width="280">
          <template #default="{ row }">
            <template v-if="getTargetMeta(row.image)">
              <el-tag size="small" :type="getTargetMeta(row.image).color" style="margin-right: 4px;">
                {{ getTargetMeta(row.image).short }} · 综合靶场
              </el-tag>
              <el-tag v-for="v in getTargetMeta(row.image).vulnTypes.slice(0, 3)" :key="v"
                size="small" type="warning" style="margin-right: 2px; font-size: 10px;">{{ v }}</el-tag>
              <span v-if="getTargetMeta(row.image).vulnTypes.length > 3"
                style="font-size: 10px; color: var(--text-muted);">+{{ getTargetMeta(row.image).vulnTypes.length - 3 }}种</span>
            </template>
            <span v-else style="font-size: 11px; color: var(--text-muted);">通用容器</span>
          </template>
        </el-table-column>
        <el-table-column prop="ports" label="端口" width="110">
          <template #default="{ row }">
            <span style="color: var(--purple); font-family: monospace;">{{ row.ports || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'running' ? 'success' : 'danger'" size="small">
              {{ row.status === 'running' ? '运行中' : '已停止' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="selectTargetConfirm(row)">选择</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 综合靶场推荐面板：选中行时实时显示 -->
      <div v-if="tableCurrentRow && getTargetMeta(tableCurrentRow.image)" class="vuln-recommend-panel">
        <div class="vrp-title">
          🎯 {{ getTargetMeta(tableCurrentRow.image).label }} — 推荐攻击类型
          <el-tag size="small" type="info" style="margin-left: 8px;">
            {{ getTargetMeta(tableCurrentRow.image).owaspCoverage }}
          </el-tag>
          <el-tag size="small" style="margin-left: 4px;">
            难度 {{ getTargetMeta(tableCurrentRow.image).difficulty }}
          </el-tag>
        </div>
        <div class="vrp-desc">{{ getTargetMeta(tableCurrentRow.image).description }}</div>
        <div class="vrp-tags">
          <el-tag v-for="v in getTargetMeta(tableCurrentRow.image).vulnTypes" :key="v"
            size="small" type="warning" style="margin: 3px; cursor: pointer;"
            @click="applyVulnType(v)">
            {{ v }} ↗
          </el-tag>
        </div>
        <div class="vrp-hint">点击漏洞类型标签可直接设置为攻击类型</div>
      </div>
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
import { getTargetMeta } from '@/utils/targetMeta'

// 组件
import StatCard from '@/components/StatCard.vue'
import AttackTypeSelect from '@/components/AttackTypeSelect.vue'
import AttackTimeline from '@/components/AttackTimeline.vue'

// 状态
const loading = ref(false)
const loadingTargets = ref(false)
const tableCurrentRow = ref(null)
const result = ref('')
const resultType = ref('info')
const resultStatus = ref('')
const targetDialogVisible = ref(false)
const targets = ref([])
const selectedTargetStatus = ref(null)
const selectedTargetImage = ref('')
const selectedTargetMeta = ref(null)
const attackLogs = ref([])
const attackLogPage = ref(1)
const attackLogPageSize = ref(10)
// 与 AttackTypeSelect.vue 和后端 Attack.get_attack_types() 保持一致，共 16 种
const attackTypes = ref([
  { type: 'SQL注入', category: 'Web攻击' }, { type: 'XSS攻击', category: 'Web攻击' },
  { type: 'CSRF攻击', category: 'Web攻击' }, { type: '文件包含', category: 'Web攻击' },
  { type: '命令执行', category: 'Web攻击' }, { type: 'SSRF攻击', category: 'Web攻击' },
  { type: 'XXE注入', category: 'Web攻击' }, { type: '权限提升', category: '系统攻击' },
  { type: '容器逃逸', category: '系统攻击' }, { type: '反弹Shell', category: '系统攻击' },
  { type: '端口扫描', category: '网络攻击' }, { type: '暴力破解', category: '网络攻击' },
  { type: '中间人攻击', category: '网络攻击' }, { type: '后门植入', category: 'APT攻击' },
  { type: '横向移动', category: 'APT攻击' }, { type: '数据外传', category: 'APT攻击' }
])
const attackTotal = ref(0)

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
let statsTimer = null

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
  1: '侦察', 2: '武器化与投递', 3: '漏洞利用',
  4: '持久化与提权', 5: '横向移动', 6: '目标行动'
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
      stats.total++
      const attackId = createRes.attack?.attack_id || Date.now()
      const execRes = await request.post(`/attack/execute/${attackId}`, {
          target_image: selectedTargetImage.value
        })

      if (execRes.status === 'success') {
        stats.running++
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
    loadStats()
  }
}

async function loadAttackHistory(page = attackLogPage.value) {
  attackLogPage.value = page
  try {
    const res = await request.get('/attack/list', {
      params: { page: attackLogPage.value, limit: attackLogPageSize.value }
    })
    if (res.status === 'success') {
      attackLogs.value = res.attacks || []
      attackTotal.value = res.total || 0
    }
  } catch (e) {
    console.error('加载攻击历史失败', e)
  }
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
  // 从端口映射中提取主机端口
  if (target.ports && target.ports !== '-') {
    const portStr = String(target.ports)
    const portMatch = portStr.match(/(\d+)/)
    if (portMatch) {
      form.value.port = portMatch[1]
    }
  }
  form.value.target = target.ip || 'localhost'
  selectedTargetStatus.value = target.status
  selectedTargetImage.value = target.image || ''
  selectedTargetMeta.value = getTargetMeta(target.image)
  targetDialogVisible.value = false

  const metaInfo = selectedTargetMeta.value ? ` (${selectedTargetMeta.value.label})` : ''
  ElMessage.success(`已选择靶场: ${target.name}${metaInfo}，端口: ${form.value.port}`)
}

function applyVulnType(vulnType) {
  form.value.type = vulnType
  tableCurrentRow.value = null
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
  statsTimer = setInterval(loadStats, 5000)
})

onUnmounted(() => {
  if (progressTimer) clearInterval(progressTimer)
  if (statsTimer) clearInterval(statsTimer)
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

/* 综合靶场漏洞匹配提示（攻击表单内） */
.target-meta-hint {
  padding: 10px 12px;
  background: rgba(103, 194, 58, 0.06);
  border: 1px solid rgba(103, 194, 58, 0.25);
  border-radius: 6px;
  width: 100%;
  line-height: 2;
}

/* 靶场选择弹窗中的推荐面板 */
.vuln-recommend-panel {
  margin-top: 12px;
  padding: 14px 16px;
  background: rgba(230, 162, 60, 0.07);
  border: 1px solid rgba(230, 162, 60, 0.3);
  border-radius: 8px;
}

.vrp-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--el-color-warning);
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.vrp-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.vrp-tags {
  display: flex;
  flex-wrap: wrap;
}

.vrp-hint {
  margin-top: 6px;
  font-size: 11px;
  color: var(--text-muted);
}
</style>
