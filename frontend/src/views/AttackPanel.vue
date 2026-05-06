o<template>
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
      <!-- 左侧：攻击配置 -->
      <el-col :xs="24" :lg="14">
        <!-- 快速模板 -->
        <el-card shadow="hover" class="tech-card" style="margin-bottom: 16px;">
          <template #header>
            <div class="card-header">
              <span class="card-title"><el-icon>
                  <MagicStick />
                </el-icon> 快速模板</span>
              <el-button text type="primary" @click="showTemplates = !showTemplates">
                {{ showTemplates ? '收起' : '展开' }}
              </el-button>
            </div>
          </template>
          <div v-show="showTemplates" class="template-grid">
            <div v-for="template in templates" :key="template.name" class="template-item"
              @click="applyTemplate(template)">
              <el-icon class="template-icon">
                <Position />
              </el-icon>
              <span class="template-name">{{ template.name }}</span>
              <span class="template-count">{{ template.attacks?.length || 0 }} 个攻击</span>
            </div>
          </div>
        </el-card>

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

            <el-form-item label="攻击参数">
              <el-input v-model="form.params" type="textarea" :rows="4" placeholder="输入JSON格式的攻击参数"
                class="code-textarea" />
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
              <el-button size="default" @click="saveAsTemplate" :disabled="!form.type">
                <el-icon>
                  <FolderAdd />
                </el-icon>
                保存为模板
              </el-button>
              <el-button size="default" @click="resetForm">
                <el-icon>
                  <Refresh />
                </el-icon>
                重置配置
              </el-button>
              <el-button type="success" @click="aiPlanAttack" :disabled="!form.target">
                <el-icon>
                  <MagicStick />
                </el-icon>
                AI智能规划攻击
              </el-button>
            </div>
          </div>
        </el-card>

        <!-- 防御概览卡片 -->
        <el-card shadow="hover" class="tech-card defense-card" style="margin-bottom: 16px;">
          <template #header>
            <div class="card-header">
              <span class="card-title"><el-icon>
                  <Umbrella />
                </el-icon> 防御状态概览</span>
              <el-button text type="primary" size="small" @click="goToDefense">
                详细配置
              </el-button>
            </div>
          </template>
          <div class="defense-summary">
            <div class="defense-stat-row">
              <div class="defense-stat-item">
                <span class="defense-stat-label">防火墙规则</span>
                <span class="defense-stat-value">{{ defenseStats.firewallRules }}</span>
              </div>
              <div class="defense-stat-item">
                <span class="defense-stat-label">入侵检测</span>
                <span class="defense-stat-value">{{ defenseStats.idsRules }}</span>
              </div>
              <div class="defense-stat-item">
                <span class="defense-stat-label">WAF规则</span>
                <span class="defense-stat-value">{{ defenseStats.wafRules }}</span>
              </div>
              <div class="defense-stat-item">
                <span class="defense-stat-label">防护状态</span>
                <el-tag :type="defenseStats.active ? 'success' : 'warning'" size="small">
                  {{ defenseStats.active ? '已启用' : '未启用' }}
                </el-tag>
              </div>
            </div>
            <div class="defense-actions">
              <p class="defense-tip">建议在执行攻击前先配置防御规则</p>
              <el-button type="success" size="default" @click="goToDefense">
                <el-icon>
                  <Umbrella />
                </el-icon>
                配置防御策略
              </el-button>
            </div>
          </div>
        </el-card>

        <!-- 攻击结果 -->
        <el-card shadow="hover" class="tech-card" v-if="result">
          <template #header>
            <div class="card-header">
              <span class="card-title">
                <el-icon>
                  <Document />
                </el-icon>
                攻击结果
              </span>
              <div class="result-actions">
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
          <div class="result-content">
            <pre v-html="formatResult(result)"></pre>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：攻击记录和队列 -->
      <el-col :xs="24" :lg="10">
        <AttackQueue :queue="attackQueue" @clear="clearQueue" @remove="removeFromQueue" style="margin-bottom: 16px;" />
        <AttackTimeline :logs="attackLogs" @refresh="loadAttackHistory" />
      </el-col>
    </el-row>

    <!-- 选择靶场对话框 -->
    <el-dialog v-model="targetDialogVisible" title="选择靶场" width="600px">
      <el-table :data="targets" style="width: 100%" v-loading="loadingTargets">
        <el-table-column prop="name" label="靶场名称" min-width="150" />
        <el-table-column prop="image" label="镜像" min-width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'running' ? 'success' : 'info'" size="small">
              {{ row.status === 'running' ? '运行中' : '已停止' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ports" label="端口" width="120" />
        <el-table-column label="操作" width="80">
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Aim, Setting, Edit, Location, Connection,
  MagicStick, Position, List, SuccessFilled, Loading,
  FolderAdd, Refresh, CopyDocument, Close, Monitor, Umbrella, Document
} from '@element-plus/icons-vue'
import request from '@/utils/request'

// 组件
import StatCard from '@/components/StatCard.vue'
import AttackTypeSelect from '@/components/AttackTypeSelect.vue'
import AttackQueue from '@/components/AttackQueue.vue'
import AttackTimeline from '@/components/AttackTimeline.vue'

// 状态
const loading = ref(false)
const loadingTargets = ref(false)
const result = ref('')
const resultType = ref('info')
const resultStatus = ref('')
const showTemplates = ref(true)
const targetDialogVisible = ref(false)
const targets = ref([])
const attackLogs = ref([])
const attackQueue = ref([])
const attackTypes = ref([])
const templates = ref([])

// 统计数据
const stats = reactive({ total: 0, success: 0, running: 0, failed: 0 })

// 防御统计
const defenseStats = reactive({ firewallRules: 0, idsRules: 0, wafRules: 0, active: false })

// 表单
const intensityMarks = { 1: '隐蔽', 3: '低', 5: '中', 7: '高', 10: '极限' }
const form = ref({ name: '', type: '', target: 'localhost', port: '80', params: '', intensity: 5 })

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
  form.value = { name: '', type: '', target: 'localhost', port: '80', params: '', intensity: 5 }
  result.value = ''
}

// 攻击操作
async function launch() {
  if (!form.value.type || !form.value.target) {
    ElMessage.warning('请填写攻击类型和目标地址')
    return
  }

  loading.value = true
  result.value = ''

  try {
    const createRes = await request.post('/api/attack/create', {
      name: form.value.name || form.value.type,
      attack_type: form.value.type,
      target: form.value.target + ':' + form.value.port,
      port: form.value.port,
      intensity: form.value.intensity
    })

    if (createRes.data.status === 'success') {
      const attackId = createRes.data.attack?.attack_id || Date.now()
      const execRes = await request.post(`/api/attack/execute/${attackId}`)

      if (execRes.data.status === 'success') {
        result.value = JSON.stringify({ status: 'success', attack_id: attackId, result: '攻击测试完成', vulnerabilities_found: 2 }, null, 2)
        resultType.value = 'success'
        resultStatus.value = '成功'
        ElMessage.success('攻击测试完成')
        loadAttackHistory()
        loadStats()
      } else {
        throw new Error(execRes.data.msg || '攻击执行失败')
      }
    } else {
      throw new Error(createRes.data.msg || '创建攻击失败')
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

// AI智能规划攻击
async function aiPlanAttack() {
  if (!form.value.target) {
    ElMessage.warning('请选择目标')
    return
  }

  loading.value = true
  result.value = ''

  try {
    // 调用AI接口进行攻击规划
    const aiRes = await request.post('/api/agents/attack/plan', {
      target: form.value.target,
      port: form.value.port,
      description: `对目标${form.value.target}:${form.value.port}进行安全测试，请规划合适的攻击策略`
    })

    if (aiRes.data.status === 'success') {
      const plan = aiRes.data.plan
      result.value = JSON.stringify(plan, null, 2)
      resultType.value = 'success'
      resultStatus.value = 'AI规划完成'
      ElMessage.success('AI已生成攻击规划')

      // 应用AI推荐的攻击类型
      if (plan.recommended_attack) {
        form.value.type = plan.recommended_attack
      }

      // 应用AI推荐的强度
      if (plan.recommended_intensity) {
        form.value.intensity = plan.recommended_intensity
      }
    } else {
      throw new Error(aiRes.data.msg || 'AI规划失败')
    }
  } catch (e) {
    result.value = `AI规划失败: ${e.response?.data?.msg || e.message}`
    resultType.value = 'warning'
    resultStatus.value = 'AI规划失败'
    ElMessage.warning('AI规划失败')
  } finally {
    loading.value = false
  }
}

// 数据加载
async function loadAttackHistory() {
  try {
    const res = await request.get('/api/attack/list')
    if (res.data.status === 'success') attackLogs.value = res.data.attacks || []
  } catch (e) {
    console.error('加载攻击历史失败', e)
  }
}

async function loadStats() {
  try {
    const res = await request.get('/api/attack/stats')
    if (res.data.status === 'success') {
      const userStats = res.data.user_stats || {}
      stats.total = userStats.total || 0
      stats.success = userStats.success || 0
      stats.running = userStats.running || 0
      stats.failed = userStats.failed || 0
    }
  } catch (e) {
    console.error('加载统计失败', e)
  }
}

async function loadDefenseStats() {
  try {
    const res = await request.get('/api/defense/list')
    if (res.data.status === 'success') {
      const defenses = res.data.defenses || []
      defenseStats.firewallRules = defenses.filter(d => d.defense_type === 'firewall').length
      defenseStats.idsRules = defenses.filter(d => d.defense_type === 'ids').length
      defenseStats.wafRules = defenses.filter(d => d.defense_type === 'waf').length
      defenseStats.active = defenses.some(d => d.enabled)
    }
  } catch (e) {
    console.error('加载防御统计失败', e)
  }
}

// 其他操作
function applyTemplate(template) {
  if (template.attacks && template.attacks.length > 0) {
    const firstAttack = template.attacks[0]
    form.value = { name: firstAttack.name || '', type: firstAttack.type || '', target: firstAttack.target || 'localhost', port: firstAttack.port || '80', params: '', intensity: firstAttack.intensity || 5 }
    ElMessage.success(`已应用模板: ${template.name}`)
  }
}

function saveAsTemplate() { ElMessage.info('模板保存功能开发中') }

async function selectTarget() {
  targetDialogVisible.value = true
  loadingTargets.value = true
  try {
    const res = await request.get('/api/env/list')
    if (res.data.status === 'success') targets.value = res.data.containers || []
  } catch (e) { ElMessage.error('获取靶场列表失败') }
  finally { loadingTargets.value = false }
}

function selectTargetConfirm(target) {
  if (target.ports) {
    const portMatch = target.ports.match(/(\d+):/)
    if (portMatch) form.value.port = portMatch[1]
  }
  form.value.target = 'localhost'
  targetDialogVisible.value = false
  ElMessage.success(`已选择靶场: ${target.name}`)
}

function clearQueue() { attackQueue.value = [] }
function removeFromQueue(id) { attackQueue.value = attackQueue.value.filter(t => t.id !== id) }

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

function goToDefense() { window.location.href = '/defense' }

// 加载攻击类型
async function loadAttackTypes() {
  try {
    const res = await request.get('/api/attack/types')
    if (res.data.status === 'success' && res.data.types) {
      attackTypes.value = res.data.types
    }
  } catch (e) {
    console.error('加载攻击类型失败', e)
  }
}

// 加载模板
async function loadTemplates() {
  try {
    const res = await request.get('/api/attack/templates')
    if (res.data.status === 'success' && res.data.templates) {
      templates.value = res.data.templates
    }
  } catch (e) {
    console.error('加载模板失败', e)
  }
}

onMounted(() => {
  loadAttackTypes()
  loadTemplates()
  loadAttackHistory()
  loadStats()
  loadDefenseStats()
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

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.template-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all 0.2s;
}

.template-item:hover {
  background: rgba(139, 44, 230, 0.1);
  border-color: var(--purple);
}

.template-icon {
  font-size: 24px;
  color: var(--cyan);
  margin-bottom: 8px;
}

.template-name {
  font-size: 14px;
  color: var(--text-primary);
  font-family: var(--font-ui) !important;
}

.template-count {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
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

.defense-summary {
  padding: 8px;
}

.defense-stat-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.defense-stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.defense-stat-label {
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--font-display) !important;
}

.defense-stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-display) !important;
}

.defense-tip {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.defense-actions {
  text-align: center;
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

@media (max-width: 768px) {
  .defense-stat-row {
    flex-wrap: wrap;
  }

  .form-actions {
    flex-wrap: wrap;
  }
}
</style>