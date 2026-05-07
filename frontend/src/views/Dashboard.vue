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

    <!-- 实时状态统计卡片（与攻击/防御页面风格一致） -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="12" :sm="6">
        <StatCard :icon="Monitor" :value="activeTargets" label="活跃靶场" type="cyan" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard :icon="Umbrella" :value="activeRules" label="防御规则" type="success" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard :icon="Aim" :value="todayAttacks" label="今日攻击" type="danger" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard :icon="Warning" :value="blockedCount" label="拦截次数" type="warning" />
      </el-col>
    </el-row>

    <!-- 横向切换栏（与上方卡片风格一致） -->
    <div class="tab-bar">
      <div class="tab-item" :class="{ active: activeSection === 'ai' }" @click="activeSection = 'ai'">
        <el-icon>
          <MagicStick />
        </el-icon>
        <span>AI自动生成</span>
      </div>
      <div class="tab-item" :class="{ active: activeSection === 'manual' }" @click="activeSection = 'manual'">
        <el-icon>
          <Setting />
        </el-icon>
        <span>手动配置靶场</span>
      </div>
    </div>

    <!-- ========== AI自动生成板块 ========== -->
    <div v-show="activeSection === 'ai'" class="section-content">
      <div class="section-header">
        <h3><el-icon>
            <MagicStick />
          </el-icon> AI自动靶场生成</h3>
        <p>通过自然语言描述，AI自动分析并构建高度仿真的网络靶场环境</p>
      </div>

      <el-row :gutter="14">
        <el-col :xs="24" :lg="12">
          <el-card shadow="hover" class="tech-card">
            <template #header>
              <div class="card-title">
                <el-icon>
                  <Cpu />
                </el-icon> AI场景描述
                <el-tag type="success" size="small" style="margin-left: 8px;">智能</el-tag>
              </div>
            </template>
            <el-input v-model="aiRangeDesc" type="textarea" :rows="6"
              placeholder="例如：我需要一个包含Web服务器和MySQL数据库的Web安全靶场，包含SQL注入和XSS漏洞..." maxlength="500" show-word-limit
              style="margin-bottom: 16px;" />
            <div style="display: flex; gap: 12px;">
              <el-button type="primary" style="flex: 1;" @click="aiGenerateAndDeploy" :loading="aiLoading"
                :disabled="!backendStatus || !aiRangeDesc.trim()">
                <el-icon>
                  <Cpu />
                </el-icon> AI分析并生成
              </el-button>
              <el-button @click="goToAIRange">
                <el-icon>
                  <MagicStick />
                </el-icon> 进入AI靶场
              </el-button>
            </div>

            <!-- AI生成结果展示 -->
            <div v-if="aiResult" style="margin-top: 16px;">
              <el-alert :title="aiResult.message" :type="aiResult.success ? 'success' : 'error'" show-icon
                :closable="false" size="small" />
              <div v-if="aiResult.success && aiResult.config" style="margin-top: 12px;">
                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">生成配置摘要</div>
                <div class="config-summary">
                  <div class="config-item">
                    <span class="config-label">靶场名称</span>
                    <span class="config-value">{{ aiResult.config.name || '--' }}</span>
                  </div>
                  <div class="config-item">
                    <span class="config-label">组件数量</span>
                    <span class="config-value">{{ aiResult.config.components?.length || 0 }} 个</span>
                  </div>
                  <div class="config-item">
                    <span class="config-label">网络拓扑</span>
                    <span class="config-value">{{ aiResult.config.network?.type || '--' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="12">
          <el-card shadow="hover" class="tech-card">
            <template #header>
              <div class="card-title">
                <el-icon>
                  <Connection />
                </el-icon> 场景模板
                <el-tag type="warning" size="small" style="margin-left: 8px;">推荐</el-tag>
              </div>
            </template>
            <div class="template-list">
              <div class="template-item" @click="selectTemplate('web')">
                <div class="template-icon" style="color: #409eff;">🌐</div>
                <div class="template-info">
                  <div class="template-name">Web安全靶场</div>
                  <div class="template-desc">包含SQL注入、XSS、CSRF等Web漏洞</div>
                </div>
              </div>
              <div class="template-item" @click="selectTemplate('network')">
                <div class="template-icon" style="color: #00e676;">🌍</div>
                <div class="template-info">
                  <div class="template-name">网络安全靶场</div>
                  <div class="template-desc">包含端口扫描、中间人攻击等网络攻防</div>
                </div>
              </div>
              <div class="template-item" @click="selectTemplate('system')">
                <div class="template-icon" style="color: #ffd740;">💻</div>
                <div class="template-info">
                  <div class="template-name">系统安全靶场</div>
                  <div class="template-desc">包含权限提升、容器逃逸等系统攻防</div>
                </div>
              </div>
              <div class="template-item" @click="selectTemplate('full')">
                <div class="template-icon" style="color: #8b2ce6;">🔬</div>
                <div class="template-info">
                  <div class="template-name">综合演练靶场</div>
                  <div class="template-desc">多层网络架构，包含完整攻防链</div>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- ========== 手动配置靶场板块 ========== -->
    <div v-show="activeSection === 'manual'" class="section-content">
      <div class="section-header">
        <h3><el-icon>
            <Setting />
          </el-icon> 手动配置靶场</h3>
        <p>手动选择镜像、配置端口映射和环境变量，创建自定义靶场环境并进行攻防演练</p>
      </div>

      <el-row :gutter="14">
        <!-- 靶场管理 -->
        <el-col :xs="24" :lg="8">
          <el-card shadow="hover" class="tech-card" style="margin-bottom: 14px;">
            <template #header>
              <div class="card-title">
                <el-icon>
                  <Monitor />
                </el-icon> 靶场管理
                <el-tag type="warning" size="small" style="margin-left: 8px;">自定义</el-tag>
              </div>
            </template>
            <div style="padding: 8px 0;">
              <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 16px; line-height: 1.6;">
                创建、启动、停止和管理您的靶场环境。支持自定义镜像、端口映射和环境变量配置。
              </p>
              <div class="feature-grid">
                <div class="feature-item">
                  <el-icon :size="24" style="color: var(--cyan);">
                    <Plus />
                  </el-icon>
                  <span>创建靶场</span>
                </div>
                <div class="feature-item">
                  <el-icon :size="24" style="color: var(--success);">
                    <VideoPlay />
                  </el-icon>
                  <span>启动环境</span>
                </div>
                <div class="feature-item">
                  <el-icon :size="24" style="color: var(--danger);">
                    <VideoPause />
                  </el-icon>
                  <span>停止环境</span>
                </div>
                <div class="feature-item">
                  <el-icon :size="24" style="color: var(--purple);">
                    <Refresh />
                  </el-icon>
                  <span>重置环境</span>
                </div>
              </div>
              <el-button type="warning" style="width: 100%; margin-top: 12px;" @click="goToEnv"
                :disabled="!backendStatus">
                <el-icon>
                  <Setting />
                </el-icon> 管理靶场
              </el-button>
            </div>
          </el-card>
        </el-col>

        <!-- 攻击模拟 -->
        <el-col :xs="24" :lg="8">
          <el-card shadow="hover" class="tech-card" style="margin-bottom: 14px;">
            <template #header>
              <div class="card-title">
                <el-icon>
                  <Aim />
                </el-icon> 攻击模拟
                <el-tag type="danger" size="small" style="margin-left: 8px;">LIVE</el-tag>
              </div>
            </template>
            <div style="padding: 8px 0;">
              <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 16px; line-height: 1.6;">
                选择攻击类型和目标，对靶场环境发起模拟攻击，测试安全防护能力。
              </p>
              <el-form label-width="72px" size="small">
                <el-form-item label="攻击类型">
                  <el-select v-model="attackType" style="width: 100%;" filterable>
                    <el-option-group label="Web漏洞攻击">
                      <el-option label="SQL注入" value="SQL注入" />
                      <el-option label="XSS跨站脚本" value="XSS攻击" />
                      <el-option label="CSRF跨站请求伪造" value="CSRF攻击" />
                      <el-option label="文件包含漏洞" value="文件包含" />
                      <el-option label="命令执行" value="命令执行" />
                      <el-option label="SSRF服务端请求伪造" value="SSRF攻击" />
                      <el-option label="XXE外部实体注入" value="XXE注入" />
                    </el-option-group>
                    <el-option-group label="系统层攻击">
                      <el-option label="权限提升" value="权限提升" />
                      <el-option label="容器逃逸" value="容器逃逸" />
                    </el-option-group>
                    <el-option-group label="网络攻击">
                      <el-option label="端口扫描" value="端口扫描" />
                      <el-option label="暴力破解" value="暴力破解" />
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

              <!-- 攻防进度 -->
              <div v-if="showProgress" style="margin-top: 14px;">
                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">
                  攻防进度
                  <el-tag :type="progressStatus.type" size="small" style="margin-left: 6px;">{{ progressStatus.text
                  }}</el-tag>
                </div>
                <div style="margin-bottom: 8px;">
                  <div
                    style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); margin-bottom: 2px;">
                    <span>攻击: {{ attackPhaseName }}</span>
                    <span>{{ attackPhasePercent }}%</span>
                  </div>
                  <el-progress :percentage="attackPhasePercent" :color="attackPhaseColor" :stroke-width="10"
                    :format="() => ''" />
                </div>
                <div>
                  <div
                    style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); margin-bottom: 2px;">
                    <span>防御: {{ defenseLevelName }}</span>
                    <span>{{ defenseLevelPercent }}%</span>
                  </div>
                  <el-progress :percentage="defenseLevelPercent" :color="defenseLevelColor" :stroke-width="10"
                    :format="() => ''" />
                </div>
                <div v-if="progressMessage" style="margin-top: 8px;">
                  <el-alert :title="progressMessage" :type="progressAlertType" :closable="false" show-icon
                    size="small" />
                </div>
              </div>

              <!-- 最近攻击记录 -->
              <div v-if="recentAttacks.length > 0" style="margin-top: 14px;">
                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">最近攻击</div>
                <el-timeline>
                  <el-timeline-item v-for="attack in recentAttacks.slice(0, 3)" :key="attack.id"
                    :type="attack.success ? 'success' : 'danger'" size="small">
                    <span style="font-size: 12px;">{{ attack.type }}</span>
                    <span style="font-size: 11px; color: var(--text-muted); margin-left: 8px;">{{ attack.time
                    }}</span>
                  </el-timeline-item>
                </el-timeline>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 防御配置 -->
        <el-col :xs="24" :lg="8">
          <el-card shadow="hover" class="tech-card" style="margin-bottom: 14px;">
            <template #header>
              <div class="card-title">
                <el-icon>
                  <Umbrella />
                </el-icon> 防御配置
                <el-tag type="success" size="small" style="margin-left: 8px;">ACTIVE</el-tag>
              </div>
            </template>
            <div style="padding: 8px 0;">
              <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 16px; line-height: 1.6;">
                配置防火墙、入侵检测、WAF等防御规则，保护靶场环境免受攻击。
              </p>
              <el-form label-width="72px" size="small">
                <el-form-item label="防御类型">
                  <el-select v-model="defenseType" style="width: 100%;">
                    <el-option-group label="网络防御">
                      <el-option label="防火墙规则" value="firewall" />
                      <el-option label="入侵检测IDS" value="ids" />
                      <el-option label="WAF防护" value="waf" />
                    </el-option-group>
                    <el-option-group label="系统防御">
                      <el-option label="端口封锁" value="port_block" />
                      <el-option label="IP黑名单" value="ip_blacklist" />
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
              <div style="margin-top: 14px;">
                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">当前防御</div>
                <el-space wrap>
                  <el-tag type="success" size="small" effect="dark">防火墙 ✓</el-tag>
                  <el-tag type="success" size="small" effect="dark">IDS ✓</el-tag>
                  <el-tag type="warning" size="small" effect="plain">WAF</el-tag>
                </el-space>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  DataLine, Aim, Cpu, Connection, Monitor, Warning,
  Timer, Refresh, Setting, Loading, Umbrella, MagicStick,
  Plus, VideoPlay, VideoPause
} from '@element-plus/icons-vue'
import StatCard from '@/components/StatCard.vue'
import request from '@/utils/request'

const router = useRouter()
const activeSection = ref('ai')
const backendStatus = ref(false)
const lastUpdate = ref('--')
const attackLoading = ref(false)
const defenseLoading = ref(false)
const aiLoading = ref(false)
const attackType = ref('SQL注入')
const targetPort = ref('8080')
const attackIntensity = ref(5)
const defenseType = ref('firewall')
const defensePort = ref('8080')
const defenseIntensity = ref(5)
const recentAttacks = ref([])
const activeTargets = ref(0)
const activeRules = ref(0)
const todayAttacks = ref(0)
const blockedCount = ref(0)
const aiRangeDesc = ref('')
const aiResult = ref(null)

// 攻防进度状态
const showProgress = ref(false)
const attackPhasePercent = ref(0)
const attackPhaseName = ref('信息收集')
const attackPhaseColor = ref('#909399')
const defenseLevelPercent = ref(20)
const defenseLevelName = ref('监控级')
const defenseLevelColor = ref('#909399')
const progressMessage = ref('')
const progressAlertType = ref('info')
const progressStatus = ref({ type: 'warning', text: '执行中' })
let progressTimer = null

const intensityMarks = { 1: '低', 3: '轻', 5: '中', 7: '强', 10: '极高' }

const phaseNames = {
  1: '信息收集', 2: '漏洞探测', 3: '漏洞利用',
  4: '权限维持', 5: '横向移动', 6: '痕迹清理'
}
const phaseColors = {
  1: '#909399', 2: '#409eff', 3: '#e6a23c',
  4: '#f56c6c', 5: '#f56c6c', 6: '#909399'
}
const defenseLevelNames = {
  1: '监控级', 2: '过滤级', 3: '阻断级',
  4: '封禁级', 5: '极限级'
}
const defenseLevelColors = {
  1: '#909399', 2: '#409eff', 3: '#e6a23c',
  4: '#f56c6c', 5: '#f56c6c'
}

async function loadStats() {
  try {
    const res = await request.get('/stats/overview')
    backendStatus.value = true
    const data = res || {}
    const statsData = data.stats || {}

    activeTargets.value = statsData.environments || 0
    activeRules.value = statsData.defenses || 0
    todayAttacks.value = statsData.attacks || 0
    blockedCount.value = statsData.alerts || 0
    lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
  } catch {
    backendStatus.value = false
    activeTargets.value = 0
    activeRules.value = 0
    todayAttacks.value = 0
    blockedCount.value = 0
  }
}

// AI分析并直接生成靶场
async function aiGenerateAndDeploy() {
  if (!aiRangeDesc.value.trim()) {
    ElMessage.warning('请先输入场景描述或选择一个模板')
    return
  }
  aiLoading.value = true
  aiResult.value = null
  try {
    // 1. 调用AI分析场景
    const generateRes = await request.post('/agents/ai-range/generate', {
      description: aiRangeDesc.value
    })

    if (generateRes.status !== 'success') {
      throw new Error(generateRes.msg || 'AI场景分析失败')
    }

    const config = generateRes.config

    // 2. 自动部署靶场
    const deployRes = await request.post('/agents/ai-range/deploy', {
      config: config
    })

    if (deployRes.status === 'success') {
      aiResult.value = {
        success: true,
        message: `✅ 靶场「${config.name || '自定义靶场'}」生成并部署成功！`,
        config: config,
        result: deployRes.result,
        session: deployRes.session
      }
      ElMessage.success('AI靶场生成并部署成功！')
      await loadStats()
    } else {
      throw new Error(deployRes.msg || '靶场部署失败')
    }
  } catch (e) {
    aiResult.value = {
      success: false,
      message: '❌ ' + (e.response?.data?.msg || e.message)
    }
    ElMessage.error('AI靶场生成失败: ' + (e.response?.data?.msg || e.message))
  } finally {
    aiLoading.value = false
  }
}

// 攻防进度轮询
function startProgressAnimation(sessionId) {
  showProgress.value = true
  attackPhasePercent.value = 16
  defenseLevelPercent.value = 20
  progressMessage.value = '动态攻防已启动...'
  progressAlertType.value = 'info'
  progressStatus.value = { type: 'warning', text: '执行中' }

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

        attackPhasePercent.value = Math.round((phase / 6) * 100)
        attackPhaseName.value = phaseNames[phase] || `阶段${phase}`
        attackPhaseColor.value = phaseColors[phase] || '#909399'

        defenseLevelPercent.value = Math.round((defLevel / 5) * 100)
        defenseLevelName.value = defenseLevelNames[defLevel] || `等级${defLevel}`
        defenseLevelColor.value = defenseLevelColors[defLevel] || '#909399'

        if (session.status === 'active') {
          progressMessage.value = `攻击阶段${phase} | 防御等级${defLevel}`
          progressAlertType.value = defLevel >= 3 ? 'warning' : 'info'
        }

        if (session.attacks_count > 0) {
          progressStatus.value = { type: 'success', text: '已完成' }
          progressMessage.value = `攻防完成！阶段${phase}，防御等级${defLevel}`
          progressAlertType.value = 'success'
          clearInterval(progressTimer)
          progressTimer = null
        }
      }
    } catch (e) {
      // 会话可能已结束
    }
  }, 2000)
}

async function startAttack() {
  attackLoading.value = true
  showProgress.value = false
  try {
    const createRes = await request.post('/attack/create', {
      name: attackType.value + '测试',
      attack_type: attackType.value,
      target: 'localhost:' + targetPort.value,
      port: targetPort.value,
      intensity: attackIntensity.value
    })

    if (createRes.status === 'success') {
      const attackId = createRes.attack?.attack_id || Date.now()
      const execRes = await request.post(`/attack/execute/${attackId}`)

      if (execRes.status === 'success') {
        const sessionId = execRes.session_id || ''
        startProgressAnimation(sessionId)

        recentAttacks.value.unshift({
          id: Date.now(),
          type: attackType.value,
          time: new Date().toLocaleTimeString('zh-CN'),
          success: true
        })
        ElMessage.success('动态攻防已启动')
      } else {
        throw new Error(execRes.msg || '攻击执行失败')
      }
    } else {
      throw new Error(createRes.msg || '创建攻击失败')
    }

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

async function startDefense() {
  defenseLoading.value = true
  try {
    const res = await request.post('/defense/create', {
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

function goToAttack() {
  router.push('/attack')
}

function goToAIRange() {
  if (aiRangeDesc.value.trim()) {
    sessionStorage.setItem('aiRangeDesc', aiRangeDesc.value)
  }
  router.push('/ai-range')
}

function selectTemplate(type) {
  const templates = {
    web: '我需要一个包含Web服务器和MySQL数据库的Web安全靶场，包含SQL注入、XSS、CSRF、文件包含等常见Web漏洞，攻击机使用Kali Linux，靶机运行Apache+PHP+MySQL。',
    network: '我需要一个企业级网络安全靶场，包含路由器、交换机、防火墙等网络设备，支持端口扫描、ARP欺骗、DNS劫持、中间人攻击等网络层攻防演练。',
    system: '我需要一个系统安全靶场，包含Windows和Linux服务器，支持权限提升、容器逃逸、内核漏洞利用、恶意软件分析等系统层攻防演练。',
    full: '我需要一个综合攻防演练靶场，包含Web服务器、数据库服务器、域控制器、终端设备等多层网络架构，支持从信息收集到权限维持的完整攻击链演练。'
  }
  aiRangeDesc.value = templates[type] || ''
}

let refreshInterval = null

onMounted(async () => {
  lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
  await loadStats()
  refreshInterval = setInterval(async () => {
    await loadStats()
    lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
  }, 8000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
  if (progressTimer) clearInterval(progressTimer)
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

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-display) !important;
  font-weight: 700 !important;
  letter-spacing: 0.5px !important;
}

/* 横向切换栏 */
.tab-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  transition: all 0.2s;
}

.tab-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.15);
  color: var(--text-primary);
}

.tab-item.active {
  background: rgba(64, 158, 255, 0.1);
  border-color: rgba(64, 158, 255, 0.3);
  color: #409eff;
}

.section-header {
  margin-bottom: 14px;
}

.section-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.section-header p {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
  line-height: 1.5;
}

/* 场景模板列表 */
.template-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.template-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid transparent;
}

.template-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--border-color);
}

.template-icon {
  font-size: 28px;
  width: 40px;
  text-align: center;
}

.template-info {
  flex: 1;
}

.template-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.template-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* 功能网格 */
.feature-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  font-size: 12px;
  color: var(--text-muted);
  transition: all 0.2s;
}

.feature-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
}

/* AI生成配置摘要 */
.config-summary {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
}

.config-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.config-label {
  color: var(--text-muted);
}

.config-value {
  color: var(--text-primary);
  font-weight: 600;
}
</style>
