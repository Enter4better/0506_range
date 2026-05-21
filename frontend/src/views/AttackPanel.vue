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
      <el-col :xs="12" :sm="8">
        <StatCard :icon="Aim" :value="stats.total" label="总攻击数" type="danger" />
      </el-col>
      <el-col :xs="12" :sm="8">
        <StatCard :icon="SuccessFilled" :value="stats.success" label="成功攻击" type="success" />
      </el-col>
      <el-col :xs="24" :sm="8">
        <StatCard :icon="List" :value="attackTypes.length" label="攻击类型" type="info" />
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 左侧：攻击配置 -->
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
                  <el-input v-model="form.port" placeholder="8080"
                    :readonly="!!selectedTargetPorts"
                    :style="selectedTargetPorts ? { backgroundColor: 'var(--bg-input-disabled)', cursor: 'not-allowed' } : {}">
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

            <!-- 端口自动填充提示 -->
            <el-form-item v-if="selectedTargetPorts" label=" ">
              <span style="font-size: 12px; color: var(--text-muted);">
                <el-icon><InfoFilled /></el-icon> 端口由靶场自动填充（选择靶场后固定），如需更换靶场请先清除选择
              </span>
            </el-form-item>

            <!-- 沙箱模式端口不兼容警告 -->
            <el-form-item v-if="sandboxCompatWarn" label=" ">
              <el-alert :title="sandboxCompatWarn" type="warning" :closable="false" show-icon />
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

          <!-- 沙箱模式开关 -->
          <div class="sandbox-mode-section" :class="{ 'is-sandbox': sandboxMode }">
            <div class="sandbox-mode-top">
              <div class="sandbox-mode-label">
                <el-icon><Monitor /></el-icon>
                <span>执行模式</span>
              </div>
              <div class="sandbox-mode-cards">
                <div class="mode-card" :class="{ active: !sandboxMode }" @click="sandboxMode = false">
                  <el-icon><MagicStick /></el-icon>
                  <span class="mode-card-name">仿真模式</span>
                  <span class="mode-card-desc">LLM 生成分析</span>
                </div>
                <div class="mode-card sandbox" :class="{ active: sandboxMode }" @click="sandboxMode = true">
                  <el-icon><Connection /></el-icon>
                  <span class="mode-card-name">🔥 沙箱模式</span>
                  <span class="mode-card-desc">真实容器执行</span>
                </div>
              </div>
            </div>
            <div v-if="sandboxMode" class="sandbox-mode-tip">
              <el-icon><Warning /></el-icon>
              将在 Docker 容器内执行真实命令，需目标靶场处于运行状态，支持端口扫描、SQL注入等 10 类攻击
            </div>
            <div v-else class="sandbox-mode-tip sim">
              <el-icon><MagicStick /></el-icon>
              由 DeepSeek 生成攻击分析与步骤，不产生真实网络请求，适合演练展示
            </div>
          </div>

          <!-- 操作按钮区域 -->
          <div class="form-actions-wrapper" :class="{ 'sandbox-btn-area': sandboxMode }">
            <p class="form-actions-tip">配置完成后点击下方按钮执行攻击操作</p>
            <div class="form-actions">
              <el-button :type="sandboxMode ? 'warning' : 'danger'" size="default" :loading="loading"
                @click="launch" :disabled="!form.type || !form.target">
                <el-icon><Aim /></el-icon>
                {{ sandboxMode ? '🔥 沙箱攻击' : '发起攻击' }}
              </el-button>
              <el-button size="default" @click="resetForm">
                <el-icon><Refresh /></el-icon>
                重置配置
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：攻击结果 + 动态攻防进度 -->
      <el-col :xs="24" :lg="10">
        <!-- 攻击结果 -->
        <el-card shadow="hover" class="tech-card" style="margin-bottom: 16px;">
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

        <!-- 沙箱真实输出 -->
        <el-card v-if="sandboxMode" shadow="hover" class="tech-card sandbox-output-card" style="margin-bottom: 16px;">
          <template #header>
            <div class="card-header">
              <span class="card-title sandbox-output-title">
                <el-icon><Connection /></el-icon>
                沙箱真实输出
              </span>
              <el-tag v-if="sandboxPolling" type="warning" size="small" effect="plain">
                <el-icon class="is-loading"><Loading /></el-icon> 等待容器执行
              </el-tag>
              <el-tag v-else-if="sandboxOutput" :type="sandboxIsReal ? 'success' : 'warning'" size="small">
                {{ sandboxIsReal ? '真实执行' : '已降级' }}
              </el-tag>
              <el-tag v-else type="info" size="small">等待攻击</el-tag>
            </div>
          </template>
          <div v-if="sandboxOutput" class="sandbox-terminal">
            <pre>{{ sandboxOutput }}</pre>
          </div>
          <div v-else-if="sandboxPolling" class="empty-progress">
            <el-icon :size="28" class="is-loading" style="color: var(--el-color-warning);">
              <Loading />
            </el-icon>
            <p style="color: var(--el-color-warning);">容器执行中，请稍候...</p>
          </div>
          <div v-else class="empty-progress">
            <el-icon :size="28" style="color: var(--text-muted);"><Connection /></el-icon>
            <p>发起沙箱攻击后，真实命令输出将显示在这里</p>
          </div>
        </el-card>

        <!-- 动态攻防进度 -->
        <el-card shadow="hover" class="tech-card">
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
      </el-col>
    </el-row>

    <!-- 攻击记录（底部） -->
    <el-card shadow="hover" class="tech-card" style="margin-top: 16px;">
      <AttackTimeline
        :logs="attackLogs"
        :total="attackTotal"
        :current-page="attackLogPage"
        :page-size="attackLogPageSize"
        @refresh="loadAttackHistory(1)"
        @page-change="loadAttackHistory"
      />
    </el-card>

    <!-- 选择靶场对话框 -->
    <el-dialog v-model="targetDialogVisible" title="选择靶场（Enter 确认选中行）" width="1200px" class="tech-dialog"
      @keyup.enter="tableCurrentRow ? selectTargetConfirm(tableCurrentRow) : undefined">
      <!-- 沙箱过滤提示 -->
      <el-alert v-if="sandboxMode && form.type && incompatibleTargets.length > 0"
        title="沙箱模式：已自动过滤不兼容靶场"
        type="info" :closable="false" show-icon style="margin-bottom: 8px;">
        <template #default>
          当前攻击类型 <el-tag size="small" type="warning">{{ form.type }}</el-tag> 需要靶场具备 Web 服务，
          已隐藏 {{ incompatibleTargets.length }} 个不兼容靶场
          <el-button text size="small" type="primary" @click="showIncompatibleTargets = !showIncompatibleTargets">
            {{ showIncompatibleTargets ? '隐藏不兼容' : '显示全部' }}
          </el-button>
        </template>
      </el-alert>
      <el-alert v-if="sandboxMode && form.type && incompatibleTargets.length > 0 && targets.length === 0 && !loadingTargets"
        title="无兼容靶场" type="warning" :closable="false" show-icon style="margin-bottom: 8px;">
        <template #default>
          请先在「环境管理」中创建综合漏洞靶场（DVWA/WebGoat/Juice Shop）或启动 Web 服务容器
        </template>
      </el-alert>
      <el-table :data="displayTargets" stripe style="width: 100%;" size="small" v-loading="loadingTargets" max-height="380"
        highlight-current-row @current-change="(row) => tableCurrentRow = row" @row-dblclick="selectTargetConfirm">
        <el-table-column v-if="sandboxMode && form.type" label="兼容" width="70" align="center">
          <template #default="{ row }">
            <el-tooltip :content="getTargetCompatTooltip(row)" placement="right">
              <el-icon v-if="getTargetCompatCheck(row)" style="color: #67c23a;"><CircleCheck /></el-icon>
              <el-icon v-else style="color: #f56c6c;"><WarningFilled /></el-icon>
            </el-tooltip>
          </template>
        </el-table-column>
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
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'

import { ElMessage } from 'element-plus'
import {
  Aim, Setting, Edit, Location, Connection,
  MagicStick, Position, List, SuccessFilled,
  Refresh, CopyDocument, Close, Monitor, Document, DataLine,
  Loading, Warning, CircleCheck, WarningFilled, InfoFilled
} from '@element-plus/icons-vue'
import request from '@/utils/request'
import { getTargetMeta, isSandboxCompatible, filterSandboxTargets, attackNeedsHttp, SANDBOX_ATTACK_TYPES, isPortCompatible, extractHostPort } from '@/utils/targetMeta'

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
const incompatibleTargets = ref([])       // 沙箱不兼容的靶场
const showIncompatibleTargets = ref(false) // 是否显示不兼容靶场
const sandboxCompatWarn = ref('')         // 沙箱兼容性警告信息
const selectedTargetStatus = ref(null)
const selectedTargetImage = ref('')
const selectedTargetMeta = ref(null)
const selectedTargetPorts = ref('')   // 选中靶场的端口字段（如 "80:80"），用于端口自动填充和校验
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

// 沙箱模式
const sandboxMode = ref(false)
const sandboxOutput = ref('')
const sandboxIsReal = ref(false)
const sandboxPolling = ref(false)
let sandboxTimer = null

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

// 沙箱模式：靶场列表展示（按 showIncompatibleTargets 决定是否合并不兼容靶场）
const displayTargets = computed(() => {
  if (showIncompatibleTargets.value && incompatibleTargets.value.length > 0) {
    return [...targets.value, ...incompatibleTargets.value]
  }
  return targets.value
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

// 沙箱靶场兼容性辅助函数（对话框表格用）
function getTargetCompatCheck(target) {
  if (!sandboxMode.value || !form.value.type) return true
  return isSandboxCompatible(form.value.type, target.image).compatible
}

function getTargetCompatTooltip(target) {
  if (!sandboxMode.value || !form.value.type) return ''
  const result = isSandboxCompatible(form.value.type, target.image)
  return result.compatible ? '✓ ' + result.reason : '✗ ' + result.reason
}

function onAttackTypeChange(type, port) {
  form.value.port = port
  // 沙箱模式：攻击类型变了，重置兼容性状态
  if (sandboxMode.value) {
    sandboxCompatWarn.value = ''
    // 如果新选择的攻击类型不在沙箱支持列表中，自动关闭沙箱
    if (type && !SANDBOX_ATTACK_TYPES.includes(type)) {
      sandboxMode.value = false
      ElMessage.warning(`「${type}」暂不支持沙箱模式，已自动切换为仿真模式`)
      return
    }
    // 如果当前选中的靶场不兼容，清除选择
    if (selectedTargetImage.value && form.value.type) {
      const compat = isSandboxCompatible(form.value.type, selectedTargetImage.value)
      if (!compat.compatible) {
        selectedTargetMeta.value = null
        selectedTargetImage.value = ''
        selectedTargetPorts.value = ''
        selectedTargetStatus.value = null
        sandboxCompatWarn.value = compat.reason
      }
    }
  }
}

function resetForm() {
  form.value = { name: '', type: '', target: 'localhost', port: '80', intensity: 5 }
  result.value = ''
  showProgress.value = false
  sandboxOutput.value = ''
  sandboxIsReal.value = false
  sandboxPolling.value = false
  sandboxCompatWarn.value = ''
  selectedTargetMeta.value = null
  selectedTargetImage.value = ''
  selectedTargetPorts.value = ''
  selectedTargetStatus.value = null
  if (sandboxTimer) { clearInterval(sandboxTimer); sandboxTimer = null }
}

async function pollSandboxResult(attackId) {
  sandboxPolling.value = true
  sandboxOutput.value = ''
  if (sandboxTimer) clearInterval(sandboxTimer)
  let tries = 0
  const MAX_TRIES = 90  // 3 分钟（90 × 2s），足够 Docker 容器创建 + 脚本执行 + AI 分析
  sandboxTimer = setInterval(async () => {
    tries++
    try {
      const res = await request.get(`/attack/result/${attackId}`)
      // 优先从内存结果读取，回退到数据库中的 attack.result（异步任务完成后写入）
      const memOut = res.result?.attack?.sandbox_output
      const dbOut = res.attack?.result?.attack?.sandbox_output
      const out = memOut || dbOut
      if (out) {
        sandboxOutput.value = out
        sandboxIsReal.value = !!(res.result?.attack?.sandbox_real || res.attack?.result?.attack?.sandbox_real)
        sandboxPolling.value = false
        clearInterval(sandboxTimer)
        sandboxTimer = null
        return
      }
      // 如果攻击已结束但沙箱输出仍为空，再等几次后停止
      const attackDone = res.attack?.status === 'completed' || res.attack?.status === 'failed'
      if (attackDone && tries >= 10) {
        sandboxPolling.value = false
        clearInterval(sandboxTimer)
        sandboxTimer = null
        return
      }
    } catch (e) { /* ignore */ }
    if (tries >= MAX_TRIES) {
      sandboxPolling.value = false
      clearInterval(sandboxTimer)
      sandboxTimer = null
    }
  }, 2000)
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

  // 检查靶场状态（沙箱模式下严格要求运行中）
  if (sandboxMode.value) {
    // 未从弹窗选择靶场（手动输入地址），无法验证状态，提示用户确认
    if (!selectedTargetStatus.value && !selectedTargetImage.value) {
      // 不阻止，后端会做最终验证
    } else if (selectedTargetStatus.value && selectedTargetStatus.value !== 'running') {
      ElMessage.warning('所选靶场已停止，请先启动靶场后再发起攻击')
      loading.value = false
      return
    }
  }

  // 沙箱模式：校验攻击类型与靶场兼容性
  if (sandboxMode.value && form.value.type) {
    // 1) 攻击类型必须在沙箱支持列表中
    if (!SANDBOX_ATTACK_TYPES.includes(form.value.type)) {
      ElMessage.warning(`「${form.value.type}」暂不支持沙箱模式，请切换攻击类型或使用仿真模式`)
      loading.value = false
      return
    }
    // 2) 如果已选靶场，校验靶场兼容性
    if (selectedTargetImage.value) {
      const compat = isSandboxCompatible(form.value.type, selectedTargetImage.value)
      if (!compat.compatible) {
        ElMessage.warning(compat.reason)
        loading.value = false
        return
      }
    }
  }

  loading.value = true
  result.value = ''
  showProgress.value = false
  sandboxOutput.value = ''
  sandboxIsReal.value = false
  sandboxPolling.value = false
  if (sandboxTimer) { clearInterval(sandboxTimer); sandboxTimer = null }

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
      const execRes = await request.post(`/attack/execute/${attackId}`, {
          target_image: selectedTargetImage.value,
          sandbox_mode: sandboxMode.value
        })

      if (execRes.status === 'success') {
        const sessionId = execRes.session_id || ''

        // 启动攻防进度动画
        startProgressAnimation(sessionId)

        // 沙箱模式：轮询等待真实执行结果
        if (sandboxMode.value) pollSandboxResult(attackId)

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
    const listRes = await request.get('/attack/list', { params: { page: 1, limit: 1000 } })
    if (listRes.status === 'success') {
      stats.total = listRes.total || 0
      const attacks = listRes.attacks || []
      stats.success = attacks.filter(a => a.status === 'completed').length
      stats.failed = attacks.filter(a => a.status === 'failed').length
      stats.running = attacks.filter(a => a.status === 'running').length
    }
  } catch (e) {
    console.error('加载攻击统计失败', e)
  }
}

async function selectTarget() {
  targetDialogVisible.value = true
  loadingTargets.value = true
  showIncompatibleTargets.value = false
  incompatibleTargets.value = []
  sandboxCompatWarn.value = ''
  try {
    const res = await request.get('/env/list')
    if (res.status === 'success') {
      const allTargets = (res.containers || res.data || []).map(t => ({
        ...t,
        name: t.name || '未命名靶场',
        image: t.image || t.os || 'unknown',
        ports: t.ports || t.port || '-',
        created: t.created || t.created_at || '-'
      }))
      // 沙箱模式 + 已选攻击类型 → 过滤不兼容靶场
      if (sandboxMode.value && form.value.type) {
        const filtered = filterSandboxTargets(allTargets, form.value.type)
        targets.value = filtered.compatible
        incompatibleTargets.value = filtered.incompatible
        if (filtered.compatible.length === 0) {
          sandboxCompatWarn.value = `沙箱模式下「${form.value.type}」需要 Web 服务靶场，当前无兼容靶场运行，请先在环境管理中创建综合靶场（DVWA/WebGoat/Juice Shop）或 Web 服务容器`
        }
      } else {
        targets.value = allTargets
      }
    }
  } catch (e) { ElMessage.error('获取靶场列表失败') }
  finally { loadingTargets.value = false }
}

function selectTargetConfirm(target) {
  // 保存靶场端口字段，用于端口自动填充和校验
  selectedTargetPorts.value = target.ports || ''

  // 从端口映射中提取主机端口并自动填充（禁止手动修改）
  const hostPort = extractHostPort(target.ports)
  if (hostPort !== null) {
    form.value.port = String(hostPort)
  } else {
    // 纯内网容器无端口映射，端口保持原值
    form.value.port = form.value.port || ''
  }
  form.value.target = target.ip || 'localhost'
  selectedTargetStatus.value = target.status
  selectedTargetImage.value = target.image || ''
  selectedTargetMeta.value = getTargetMeta(target.image)

  // 沙箱兼容性检查（靶场类型 + 端口双重校验）
  if (sandboxMode.value && form.value.type) {
    const compatType = isSandboxCompatible(form.value.type, target.image)
    const compatPort = isPortCompatible(hostPort, target.image, target.ports, form.value.type)
    if (!compatType.compatible) {
      sandboxCompatWarn.value = compatType.reason
      ElMessage.warning(compatType.reason)
    } else if (!compatPort.compatible) {
      sandboxCompatWarn.value = compatPort.reason
      ElMessage.warning(compatPort.reason)
    } else {
      sandboxCompatWarn.value = ''
    }
  }

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

// 切换沙箱模式时重新校验靶场兼容性
watch(sandboxMode, (on) => {
  if (!on) {
    sandboxCompatWarn.value = ''
    incompatibleTargets.value = []
    return
  }
  // 检查攻击类型是否在沙箱支持列表中
  if (form.value.type && !SANDBOX_ATTACK_TYPES.includes(form.value.type)) {
    sandboxCompatWarn.value = `「${form.value.type}」暂不支持沙箱模式，将自动降级为仿真模式执行`
    return
  }
  // 沙箱模式开启，检查当前选中靶场（类型 + 端口双重校验）
  if (form.value.type && selectedTargetImage.value) {
    const compatType = isSandboxCompatible(form.value.type, selectedTargetImage.value)
    const compatPort = isPortCompatible(
      parseInt(form.value.port) || null,
      selectedTargetImage.value,
      selectedTargetPorts.value,
      form.value.type
    )
    if (!compatType.compatible) {
      sandboxCompatWarn.value = compatType.reason
    } else if (!compatPort.compatible) {
      sandboxCompatWarn.value = compatPort.reason
    } else {
      sandboxCompatWarn.value = ''
    }
  }
})

onMounted(() => {
  loadAttackTypes()
  loadAttackHistory()
  loadStats()
  statsTimer = setInterval(loadStats, 5000)
})

onUnmounted(() => {
  if (progressTimer) clearInterval(progressTimer)
  if (statsTimer) clearInterval(statsTimer)
  if (sandboxTimer) clearInterval(sandboxTimer)
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

/* 沙箱模式开关区域 */
.sandbox-mode-section {
  margin: 0 0 14px;
  padding: 14px 16px;
  border: 2px solid var(--border-dim);
  border-radius: 10px;
  background: rgba(64, 158, 255, 0.04);
  transition: all 0.3s;
}

.sandbox-mode-section.is-sandbox {
  border-color: rgba(230, 162, 60, 0.55);
  background: rgba(230, 162, 60, 0.06);
  box-shadow: 0 0 18px rgba(230, 162, 60, 0.18);
}

.sandbox-mode-top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.sandbox-mode-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.sandbox-mode-cards {
  display: flex;
  gap: 8px;
  flex: 1;
}

.mode-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 10px 8px;
  border: 1px solid var(--border-dim);
  border-radius: 8px;
  cursor: pointer;
  background: rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
  text-align: center;
  user-select: none;
}

.mode-card:hover {
  border-color: var(--el-color-primary);
  background: rgba(64, 158, 255, 0.08);
}

.mode-card.active {
  border-color: var(--el-color-primary);
  background: rgba(64, 158, 255, 0.12);
  box-shadow: 0 0 8px rgba(64, 158, 255, 0.2);
}

.mode-card.sandbox:hover {
  border-color: var(--el-color-warning);
  background: rgba(230, 162, 60, 0.08);
}

.mode-card.sandbox.active {
  border-color: var(--el-color-warning);
  background: rgba(230, 162, 60, 0.12);
  box-shadow: 0 0 12px rgba(230, 162, 60, 0.3);
}

.mode-card-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.mode-card-desc {
  font-size: 10px;
  color: var(--text-muted);
}

.sandbox-mode-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--el-color-warning);
  padding: 6px 10px;
  background: rgba(230, 162, 60, 0.08);
  border-radius: 6px;
  border: 1px solid rgba(230, 162, 60, 0.2);
}

.sandbox-mode-tip.sim {
  color: var(--text-muted);
  background: rgba(0, 0, 0, 0.08);
  border-color: var(--border-dim);
}

/* 沙箱模式下发起攻击按钮区域强调 */
.sandbox-btn-area {
  border-color: rgba(230, 162, 60, 0.3) !important;
  background: rgba(230, 162, 60, 0.06) !important;
}

/* 沙箱输出卡片 */
.sandbox-output-card {
  border: 1px solid rgba(230, 162, 60, 0.35) !important;
}

.sandbox-output-title {
  color: var(--el-color-warning) !important;
}

.sandbox-terminal {
  background: #0d1117;
  padding: 14px 16px;
  border-radius: 8px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: #e6edf3;
  white-space: pre-wrap;
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid rgba(230, 162, 60, 0.2);
  line-height: 1.6;
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
