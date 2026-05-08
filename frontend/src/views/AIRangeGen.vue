<template>
    <div class="page-container">
        <div class="page-header">
            <h2 class="page-title">
                <el-icon>
                    <MagicStick />
                </el-icon>
                AI靶场自动生成
            </h2>
            <p class="page-desc">通过自然语言描述，AI自动构建高度仿真的网络靶场环境</p>
        </div>

        <!-- 步骤条 -->
        <el-steps :active="currentStep" align-center class="gen-steps">
            <el-step title="场景描述" description="用自然语言描述靶场需求" />
            <el-step title="AI分析" description="AI自动分析并生成配置" />
            <el-step title="配置预览" description="确认并调整靶场配置" />
            <el-step title="部署完成" description="靶场部署并启动演练" />
        </el-steps>

        <!-- 步骤1: 场景描述 -->
        <el-card v-show="currentStep === 0" shadow="hover" class="tech-card step-card">
            <template #header>
                <div class="card-title">
                    <el-icon>
                        <Edit />
                    </el-icon> 描述你的靶场需求
                </div>
            </template>

            <div class="desc-section">
                <el-input v-model="scenarioDesc" type="textarea" :rows="6"
                    placeholder="例如：我需要一个包含Web服务器和MySQL数据库的Web安全靶场，包含SQL注入和XSS漏洞，用于测试Web应用防火墙的效果..." maxlength="2000"
                    show-word-limit class="desc-input" />

                <div class="quick-templates">
                    <div class="template-label">快速模板：</div>
                    <div class="template-tags">
                        <el-tag v-for="(tmpl, idx) in templates" :key="idx"
                            :type="idx === 0 ? 'primary' : idx === 1 ? 'danger' : 'warning'" class="template-tag"
                            @click="applyTemplate(tmpl)">
                            {{ tmpl.name }}
                        </el-tag>
                    </div>
                </div>

                <div class="desc-actions">
                    <el-button type="primary" size="large" @click="analyzeScenario" :loading="analyzing"
                        :disabled="!scenarioDesc.trim()">
                        <el-icon>
                            <Cpu />
                        </el-icon> AI分析场景
                    </el-button>
                </div>
            </div>
        </el-card>

        <!-- 步骤2: AI分析中 -->
        <el-card v-show="currentStep === 1" shadow="hover" class="tech-card step-card">
            <template #header>
                <div class="card-title">
                    <el-icon>
                        <Cpu />
                    </el-icon> AI正在分析场景...
                </div>
            </template>

            <div class="analyzing-section">
                <div class="analyzing-animation">
                    <el-icon :size="48" class="analyzing-icon">
                        <Loading />
                    </el-icon>
                    <div class="analyzing-text">
                        <p>环境管理Agent正在分析您的场景描述...</p>
                        <p class="analyzing-sub">正在匹配场景模板、规划组件配置、设计网络拓扑</p>
                    </div>
                </div>
                <el-progress :percentage="analyzeProgress" :stroke-width="6" striped striped-flow
                    class="analyze-progress" />
            </div>
        </el-card>

        <!-- 步骤3: 配置预览 -->
        <el-card v-show="currentStep === 2" shadow="hover" class="tech-card step-card">
            <template #header>
                <div class="card-title">
                    <el-icon>
                        <View />
                    </el-icon> 靶场配置预览
                    <el-tag size="small" type="success" style="margin-left: 8px;">AI已生成</el-tag>
                </div>
            </template>

            <div v-if="generatedConfig && generatedConfig.components" class="preview-section">
                <!-- 基本信息 -->
                <el-descriptions title="基本信息" :column="2" border size="small" class="config-descriptions">
                    <el-descriptions-item label="靶场名称" label-class-name="desc-label">
                        <el-input v-model="generatedConfig.name" size="small" />
                    </el-descriptions-item>
                    <el-descriptions-item label="场景描述" label-class-name="desc-label">
                        <el-input v-model="generatedConfig.description" size="small" />
                    </el-descriptions-item>
                    <el-descriptions-item label="网络类型" label-class-name="desc-label">
                        <el-tag size="small">{{ generatedConfig.network?.type || 'bridge' }}</el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="子网" label-class-name="desc-label">
                        <code>{{ generatedConfig.network?.subnet || 'N/A' }}</code>
                    </el-descriptions-item>
                </el-descriptions>

                <!-- 组件列表 -->
                <div class="section-title">
                    <el-icon>
                        <Monitor />
                    </el-icon> 组件列表 ({{ generatedConfig.components?.length || 0 }})
                </div>
                <el-table :data="generatedConfig.components || []" stripe size="small" class="comp-table">
                    <el-table-column prop="name" label="组件名称" min-width="120" />
                    <el-table-column prop="type" label="类型" width="100">
                        <template #default="{ row }">
                            <el-tag size="small" type="info">{{ row.type }}</el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column prop="image" label="镜像" min-width="150" />
                    <el-table-column label="端口映射" min-width="150">
                        <template #default="{ row }">
                            <span v-if="row.ports?.length" class="port-list">
                                <el-tag v-for="p in row.ports" :key="p" size="small" type="warning"
                                    style="margin-right: 4px;">
                                    :{{ p }}
                                </el-tag>
                            </span>
                            <span v-else class="text-muted">-</span>
                        </template>
                    </el-table-column>
                </el-table>

                <!-- 场景变种扩展 -->
                <div class="section-title" style="margin-top: 16px;">
                    <el-icon>
                        <MagicStick />
                    </el-icon> 场景变种扩展
                    <el-tooltip content="从当前场景一键派生多种变种配置，快速切换不同攻防场景" placement="top">
                        <el-icon style="margin-left: 4px; color: var(--text-muted); cursor: help;">
                            <InfoFilled />
                        </el-icon>
                    </el-tooltip>
                </div>
                <div class="variant-buttons">
                    <el-button v-for="(variant, idx) in variants" :key="idx" size="small"
                        :type="selectedVariantIdx === idx ? 'primary' : 'default'" :icon="MagicStick"
                        @click="applyVariant(variant, idx)" :loading="loadingVariant === idx">
                        {{ variant.variant_label || variant.name }}
                    </el-button>
                    <el-button v-if="!variants.length && !loadingVariants" size="small" plain @click="loadVariants">
                        <el-icon>
                            <MagicStick />
                        </el-icon> 加载变种
                    </el-button>
                    <el-button v-if="variants.length" size="small" plain @click="loadVariants"
                        :loading="loadingVariants">
                        <el-icon>
                            <Refresh />
                        </el-icon> 刷新
                    </el-button>
                </div>
                <div v-if="selectedVariantDesc" class="variant-desc">
                    <el-alert :title="selectedVariantDesc" type="info" :closable="false" show-icon size="small" />
                </div>

                <!-- 漏洞类型（可编辑） -->
                <div class="section-title" style="margin-top: 16px;">
                    <el-icon>
                        <Warning />
                    </el-icon> 漏洞类型
                    <el-button size="small" type="danger" plain style="margin-left: 8px;" @click="openVulnDialog">
                        <el-icon>
                            <Plus />
                        </el-icon> 添加
                    </el-button>
                </div>
                <div class="vuln-tags">
                    <template v-for="(v, idx) in generatedConfig.vulnerabilities || []" :key="idx">
                        <el-tag type="danger" closable :disable-transitions="false" style="margin: 4px;"
                            @close="removeVuln(idx)">
                            {{ v }}
                        </el-tag>
                    </template>
                    <span v-if="!generatedConfig.vulnerabilities?.length" class="text-muted">无预设漏洞</span>
                </div>

                <!-- 操作按钮 -->
                <div class="preview-actions">
                    <el-button size="large" @click="currentStep = 0">
                        <el-icon>
                            <Back />
                        </el-icon> 修改配置
                    </el-button>
                    <el-button type="primary" size="large" @click="deployRange" :loading="deploying">
                        <el-icon>
                            <Upload />
                        </el-icon> 确认部署
                    </el-button>
                </div>

            </div>

            <!-- 生成失败兜底 -->
            <div v-else class="gen-failed-section">
                <el-empty description="配置生成失败，请返回重新描述靶场需求" :image-size="80">
                    <el-button type="primary" @click="currentStep = 0; generatedConfig = null">
                        <el-icon>
                            <Back />
                        </el-icon> 返回重新生成
                    </el-button>
                </el-empty>
            </div>
        </el-card>

        <!-- 步骤4: 部署完成 -->
        <el-card v-show="currentStep === 3" shadow="hover" class="tech-card step-card">
            <template #header>
                <div class="card-title">
                    <el-icon>
                        <CircleCheck />
                    </el-icon> 部署结果
                </div>
            </template>

            <div v-if="deployResult" class="result-section">
                <el-result :icon="deploySuccess ? 'success' : 'error'" :title="deploySuccess ? '靶场部署成功！' : '部署失败'"
                    :sub-title="deploySuccess ? 'AI靶场已自动构建完成，攻防演练已就绪' : deployError">
                    <template #extra>
                        <div v-if="deploySuccess" class="result-info">
                            <el-descriptions :column="1" border size="small">
                                <el-descriptions-item label="环境ID">
                                    <code>{{ deployResult.result?.environment_id || 'N/A' }}</code>
                                </el-descriptions-item>
                                <el-descriptions-item label="靶场名称">
                                    {{ deployResult.result?.name || generatedConfig?.name }}
                                </el-descriptions-item>
                                <el-descriptions-item label="组件数量">
                                    {{ deployResult.result?.components?.length || 0 }} 个
                                </el-descriptions-item>
                                <el-descriptions-item label="会话ID" v-if="deployResult.session?.session_id">
                                    <code>{{ deployResult.session.session_id }}</code>
                                </el-descriptions-item>
                            </el-descriptions>
                        </div>
                        <div class="result-actions">
                            <el-button @click="resetAll">
                                <el-icon>
                                    <Refresh />
                                </el-icon> 重新生成
                            </el-button>
                            <el-button type="primary" @click="goToEnv">
                                <el-icon>
                                    <Monitor />
                                </el-icon> 查看靶场
                            </el-button>
                            <el-button type="success" @click="goToAttack">
                                <el-icon>
                                    <Aim />
                                </el-icon> 进入攻防演练
                            </el-button>
                        </div>
                    </template>
                </el-result>
            </div>
        </el-card>
    </div>

    <!-- 添加漏洞弹窗 -->
    <el-dialog v-model="vulnDialogVisible" title="选择漏洞类型" width="520px" class="tech-dialog"
        :close-on-click-modal="false" align-center>
        <div class="vuln-dialog-body">
            <div class="preset-label">
                点击选择（已选 <span class="select-count">{{ pendingVulns.length }}</span> 项），再次点击取消选择
            </div>
            <div class="preset-grid">
                <div v-for="preset in vulnPresets" :key="preset" class="preset-tag"
                    :class="{ selected: pendingVulns.includes(preset), disabled: alreadyHasVuln(preset) }"
                    @click="togglePendingVuln(preset)">
                    <el-icon v-if="pendingVulns.includes(preset)" class="check-icon">
                        <Check />
                    </el-icon>
                    <el-icon v-else-if="alreadyHasVuln(preset)" class="check-icon added-icon"><Select /></el-icon>
                    {{ preset }}
                </div>
            </div>
        </div>
        <template #footer>
            <div class="dialog-footer">
                <el-button @click="vulnDialogVisible = false">取消</el-button>
                <el-button type="danger" @click="confirmAddVuln" :disabled="pendingVulns.length === 0">
                    <el-icon>
                        <Plus />
                    </el-icon> 添加已选 ({{ pendingVulns.length }})
                </el-button>
            </div>
        </template>
    </el-dialog>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
    MagicStick, Edit, Cpu, View, Monitor, Warning,
    CircleCheck, Upload, Back, Refresh, Aim, Loading, Plus, Check, Select, InfoFilled
} from '@element-plus/icons-vue'

import request from '../utils/request'

const router = useRouter()

const currentStep = ref(0)
const scenarioDesc = ref('')
const analyzing = ref(false)
const analyzeProgress = ref(0)
const generatedConfig = ref(null)
const deploying = ref(false)
const deployResult = ref(null)
const deploySuccess = ref(false)
const deployError = ref('')
const templates = ref([])

// 漏洞弹窗
const vulnDialogVisible = ref(false)
const pendingVulns = ref([])   // 本次弹窗中待添加的选中项
const vulnPresets = [
    'SQL注入', 'XSS跨站脚本', 'CSRF', 'XXE',
    'SSRF', '文件上传', '命令注入', '目录遍历',
    '反序列化', '弱口令', '越权访问', '缓冲区溢出',
    '容器逃逸', '暴力破解', '中间人攻击', 'IDOR',
    '路径遍历', '业务逻辑漏洞', 'JWT伪造', 'DNS重绑定'
]

// 加载场景模板
async function loadTemplates() {
    try {
        const res = await request.get('/agents/ai-range/scenarios')
        if (res.status === 'success') {
            templates.value = res.scenarios || []
        }
    } catch (e) {
        console.error('加载模板失败:', e)
    }
}

// 应用模板
function applyTemplate(tmpl) {
    scenarioDesc.value = `我需要一个${tmpl.name}：${tmpl.description}，包含${tmpl.vulnerabilities?.join('、') || '多种'}漏洞`
}

// AI分析场景
async function analyzeScenario() {
    if (!scenarioDesc.value.trim()) {
        ElMessage.warning('请先描述靶场需求')
        return
    }

    analyzing.value = true
    currentStep.value = 1
    analyzeProgress.value = 0

    // 模拟进度动画
    const progressInterval = setInterval(() => {
        if (analyzeProgress.value < 90) {
            analyzeProgress.value += Math.random() * 15
        }
    }, 500)

    try {
        const res = await request.post('/agents/ai-range/generate', {
            description: scenarioDesc.value
        })

        clearInterval(progressInterval)
        analyzeProgress.value = 100

        if (res.status === 'success') {
            generatedConfig.value = res.config
            ElMessage.success('场景分析完成')
            setTimeout(() => {
                currentStep.value = 2
            }, 500)
        } else {
            ElMessage.error(res.msg || '分析失败')
            currentStep.value = 0
        }
    } catch (e) {
        clearInterval(progressInterval)
        ElMessage.error('AI分析失败: ' + (e.response?.data?.msg || e.message))
        currentStep.value = 0
    } finally {
        analyzing.value = false
    }
}

// 部署靶场
async function deployRange() {
    if (!generatedConfig.value) return

    deploying.value = true

    try {
        const res = await request.post('/agents/ai-range/deploy', {
            config: generatedConfig.value
        })

        if (res.status === 'success') {
            deployResult.value = res
            deploySuccess.value = true
            currentStep.value = 3
            ElMessage.success('靶场部署成功！')
        } else {
            deploySuccess.value = false
            deployError.value = res.msg || '部署失败'
            currentStep.value = 3
            ElMessage.error('部署失败')
        }
    } catch (e) {
        deploySuccess.value = false
        deployError.value = e.response?.data?.msg || e.message
        currentStep.value = 3
        ElMessage.error('部署失败: ' + deployError.value)
    } finally {
        deploying.value = false
    }
}

// 重置
function resetAll() {
    currentStep.value = 0
    scenarioDesc.value = ''
    generatedConfig.value = null
    deployResult.value = null
    deploySuccess.value = false
    deployError.value = ''
    analyzeProgress.value = 0
}

// 打开漏洞弹窗
function openVulnDialog() {
    if (!generatedConfig.value) return
    pendingVulns.value = []
    vulnDialogVisible.value = true
}

// 判断某漏洞是否已在配置中
function alreadyHasVuln(name) {
    return (generatedConfig.value?.vulnerabilities || []).includes(name)
}

// 切换待选状态
function togglePendingVuln(name) {
    if (alreadyHasVuln(name)) return  // 已有的不可重复选
    const idx = pendingVulns.value.indexOf(name)
    if (idx >= 0) {
        pendingVulns.value.splice(idx, 1)
    } else {
        pendingVulns.value.push(name)
    }
}

// 确认添加漏洞
function confirmAddVuln() {
    if (!generatedConfig.value) return
    if (!generatedConfig.value.vulnerabilities) {
        generatedConfig.value.vulnerabilities = []
    }
    for (const v of pendingVulns.value) {
        if (!generatedConfig.value.vulnerabilities.includes(v)) {
            generatedConfig.value.vulnerabilities.push(v)
        }
    }
    vulnDialogVisible.value = false
    pendingVulns.value = []
}

// 删除漏洞
function removeVuln(idx) {
    if (!generatedConfig.value?.vulnerabilities) return
    generatedConfig.value.vulnerabilities.splice(idx, 1)
}

// 场景变种扩展
const variants = ref([])
const loadingVariants = ref(false)
const loadingVariant = ref(-1)
const selectedVariantIdx = ref(-1)
const selectedVariantDesc = ref('')

// 加载场景变种
async function loadVariants() {
    if (!generatedConfig.value) return
    loadingVariants.value = true
    try {
        // 从当前配置推断基础场景类型
        const comps = generatedConfig.value.components || []
        let baseKey = 'web_security'
        if (comps.some(c => c.name?.includes('firewall') || c.name?.includes('ids'))) {
            baseKey = 'network_security'
        } else if (comps.some(c => c.name?.includes('docker') || c.name?.includes('escape'))) {
            baseKey = 'container_escape'
        }
        const res = await request.get('/agents/ai-range/expand-variants', {
            params: { base: baseKey }
        })
        if (res.status === 'success') {
            variants.value = res.variants || []
            selectedVariantIdx.value = -1
            selectedVariantDesc.value = ''
            if (variants.value.length) {
                ElMessage.success(`已加载 ${variants.value.length} 个场景变种`)
            } else {
                ElMessage.info('暂无可用变种')
            }
        }
    } catch (e) {
        ElMessage.error('加载变种失败: ' + (e.response?.data?.msg || e.message))
    } finally {
        loadingVariants.value = false
    }
}

// 应用变种配置
function applyVariant(variant, idx) {
    if (!generatedConfig.value) return
    selectedVariantIdx.value = idx
    selectedVariantDesc.value = `已切换至「${variant.variant_label || variant.name}」- ${variant.description || ''}`
    // 将变种配置应用到当前预览
    generatedConfig.value = {
        ...variant,
        // 保留用户已编辑的漏洞（合并）
        vulnerabilities: [...new Set([
            ...(variant.vulnerabilities || []),
            ...(generatedConfig.value.vulnerabilities || [])
        ])]
    }
    ElMessage.success(`已应用变种: ${variant.variant_label || variant.name}`)
}

// 跳转
function goToEnv() {
    router.push('/env')
}

function goToAttack() {
    router.push('/attack')
}

onMounted(() => {
    loadTemplates()
})
</script>


<style scoped>
.gen-steps {
    margin-bottom: 24px;
    padding: 20px;
    background: rgba(8, 10, 20, 0.6);
    border-radius: 12px;
    border: 1px solid var(--border-color);
}

.step-card {
    min-height: 400px;
}

.card-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    color: var(--text-primary);
}

/* 场景描述 */
.desc-section {
    padding: 8px 0;
}

.desc-input {
    margin-bottom: 16px;
}

.desc-input :deep(.el-textarea__inner) {
    background: rgba(8, 10, 20, 0.6);
    color: var(--text-primary);
    border-color: var(--border-color);
    font-size: 14px;
    line-height: 1.6;
}

.desc-input :deep(.el-textarea__inner:focus) {
    border-color: var(--cyan);
}

.quick-templates {
    margin-bottom: 20px;
}

.template-label {
    font-size: 13px;
    color: var(--text-muted);
    margin-bottom: 8px;
}

.template-tags {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.template-tag {
    cursor: pointer;
    transition: all 0.2s;
}

.template-tag:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0, 229, 255, 0.2);
}

.desc-actions {
    text-align: center;
    margin-top: 24px;
}

/* AI分析 */
.analyzing-section {
    text-align: center;
    padding: 40px 20px;
}

.analyzing-animation {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 20px;
    margin-bottom: 30px;
}

.analyzing-icon {
    color: var(--cyan);
    animation: spin 1.5s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

.analyzing-text p {
    margin: 4px 0;
    font-size: 16px;
    color: var(--text-primary);
}

.analyzing-sub {
    font-size: 13px !important;
    color: var(--text-muted) !important;
}

.analyze-progress {
    max-width: 400px;
    margin: 0 auto;
}

/* 配置预览 */
.preview-section {
    padding: 8px 0;
}

.config-descriptions {
    margin-bottom: 20px;
}

.config-descriptions :deep(.el-descriptions__title) {
    color: var(--cyan);
    font-size: 14px;
}

.config-descriptions :deep(.el-descriptions__label) {
    background: rgba(8, 10, 20, 0.4);
    color: var(--text-muted);
}

.config-descriptions :deep(.el-descriptions__content) {
    background: rgba(8, 10, 20, 0.2);
    color: var(--text-primary);
}

.section-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 16px 0 8px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
}

.comp-table {
    margin-bottom: 16px;
}

.vuln-tags {
    margin-bottom: 20px;
}

.text-muted {
    color: var(--text-muted);
    font-size: 13px;
}

.port-list {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
}

.preview-actions {
    display: flex;
    justify-content: center;
    gap: 16px;
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid var(--border-color);
}

/* 部署结果 */
.result-section {
    padding: 20px;
}

.result-info {
    max-width: 500px;
    margin: 0 auto 20px;
}

.result-info :deep(.el-descriptions__label) {
    background: rgba(8, 10, 20, 0.4);
    color: var(--text-muted);
}

.result-info :deep(.el-descriptions__content) {
    background: rgba(8, 10, 20, 0.2);
    color: var(--text-primary);
}

.result-info code {
    color: var(--cyan);
    font-family: monospace;
}

.result-actions {
    display: flex;
    justify-content: center;
    gap: 12px;
    flex-wrap: wrap;
}

/* 漏洞弹窗 */
:global(.tech-dialog) {
    background: rgba(12, 14, 28, 0.96) !important;
    border: 1px solid rgba(80, 144, 160, 0.35) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(30px) !important;
}

:global(.tech-dialog .el-dialog__header) {
    border-bottom: 1px solid rgba(80, 70, 120, 0.2);
    padding-bottom: 14px;
}

:global(.tech-dialog .el-dialog__title) {
    color: #5090a0;
    font-weight: 700;
    letter-spacing: 0.04em;
}

:global(.tech-dialog .el-dialog__headerbtn .el-dialog__close) {
    color: var(--text-muted);
}

.vuln-dialog-body {
    padding: 4px 0;
}

.preset-label {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 12px;
    line-height: 1.5;
}

.select-count {
    color: #a04050;
    font-weight: 700;
}

.preset-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
}

.preset-tag {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 7px 4px;
    font-size: 12px;
    border-radius: 7px;
    border: 1px solid rgba(80, 70, 120, 0.25);
    background: rgba(8, 10, 20, 0.5);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s;
    user-select: none;
    text-align: center;
}

.preset-tag:hover:not(.disabled) {
    border-color: rgba(160, 64, 80, 0.5);
    background: rgba(160, 64, 80, 0.1);
    color: #d06070;
    transform: translateY(-1px);
}

.preset-tag.selected {
    border-color: #a04050;
    background: rgba(160, 64, 80, 0.2);
    color: #d06070;
    box-shadow: 0 0 8px rgba(160, 64, 80, 0.25);
}

.preset-tag.disabled {
    border-color: rgba(64, 160, 96, 0.3);
    background: rgba(64, 160, 96, 0.08);
    color: #50a070;
    cursor: not-allowed;
    opacity: 0.7;
}

.check-icon {
    font-size: 11px;
    flex-shrink: 0;
}

.added-icon {
    color: #50a070;
}

.dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
}

.gen-failed-section {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 300px;
}

/* 场景变种扩展 */
.variant-buttons {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 8px;
}

.variant-desc {
    margin-bottom: 8px;
}
</style>
