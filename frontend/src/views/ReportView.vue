<template>
    <div class="page-container">
        <div class="page-header">
            <h2 class="page-title">
                <el-icon><DataAnalysis /></el-icon>
                攻防演练报告
            </h2>
            <p class="page-desc">演练结束后自动生成：攻击路径、防御效果、漏洞分布、AI安全建议</p>
        </div>

        <!-- 会话选择 & 操作栏 -->
        <el-card shadow="hover" class="tech-card toolbar-card">
            <div class="toolbar-row">
                <div class="toolbar-left">
                    <el-select v-model="selectedSession" placeholder="选择演练会话" style="width:280px"
                        @change="generateReport" clearable>
                        <el-option v-for="s in sessions" :key="s.session_id"
                            :label="`${s.environment?.name || '未知靶场'}  (${s.session_id.slice(-8)})`"
                            :value="s.session_id" />
                    </el-select>
                    <el-button type="primary" @click="generateReport" :loading="loading" style="margin-left:10px">
                        <el-icon><Refresh /></el-icon> 生成报告
                    </el-button>
                </div>
                <div class="toolbar-right" v-if="report">
                    <el-button type="success" plain @click="downloadReport">
                        <el-icon><Download /></el-icon> 下载JSON
                    </el-button>
                </div>
            </div>
        </el-card>

        <!-- 报告主体 -->
        <div v-if="report" class="report-body">

            <!-- 总览卡片 -->
            <div class="overview-grid">
                <div class="score-card tech-card">
                    <div class="score-ring" :class="scoreClass">{{ report.overall_score?.score }}</div>
                    <div class="score-info">
                        <div class="score-grade">{{ report.overall_score?.grade }}级 · {{ report.overall_score?.label }}</div>
                        <div class="score-meta">{{ report.range_name }}</div>
                        <div class="score-meta">历时 {{ report.duration_desc }}</div>
                    </div>
                </div>
                <div class="stat-item tech-card">
                    <div class="stat-num cyan">{{ report.total_attacks }}</div>
                    <div class="stat-label">攻击总次数</div>
                </div>
                <div class="stat-item tech-card">
                    <div class="stat-num warning">{{ (report.defense_stats?.intercept_avg * 100).toFixed(0) }}%</div>
                    <div class="stat-label">平均拦截率</div>
                </div>
                <div class="stat-item tech-card">
                    <div class="stat-num danger">{{ report.defense_stats?.max_level }}</div>
                    <div class="stat-label">最高防御等级</div>
                </div>
                <div class="stat-item tech-card">
                    <div class="stat-num purple">{{ report.defense_stats?.blocked_ips }}</div>
                    <div class="stat-label">封禁IP数</div>
                </div>
            </div>

            <!-- 摘要 -->
            <el-card shadow="hover" class="tech-card section-card">
                <template #header>
                    <div class="card-title"><el-icon><InfoFilled /></el-icon> 演练摘要</div>
                </template>
                <div class="summary-text">{{ report.summary }}</div>
            </el-card>

            <!-- 攻击路径 + 漏洞分布 -->
            <div class="two-col">
                <!-- 攻击路径时间线 -->
                <el-card shadow="hover" class="tech-card section-card">
                    <template #header>
                        <div class="card-title"><el-icon><Aim /></el-icon> 攻击路径时间线</div>
                    </template>
                    <div class="path-scroll">
                        <el-timeline>
                            <el-timeline-item
                                v-for="step in report.attack_path"
                                :key="step.step"
                                :type="step.success ? 'danger' : 'success'"
                                :hollow="!step.success"
                                size="large">
                                <div class="path-item">
                                    <span class="path-step">Step {{ step.step }}</span>
                                    <el-tag :type="step.success ? 'danger' : 'success'" size="small" style="margin: 0 6px">
                                        {{ step.attack_type }}
                                    </el-tag>
                                    <el-tag type="info" size="small">阶段{{ step.phase }}/{{ step.phase_name }}</el-tag>
                                    <span v-if="step.combo_chain?.length > 1" class="combo-badge">
                                        组合{{ step.combo_chain.length }}连击
                                    </span>
                                    <div class="path-reasoning">{{ step.reasoning }}</div>
                                </div>
                            </el-timeline-item>
                            <el-empty v-if="!report.attack_path?.length" description="暂无攻击记录" :image-size="60" />
                        </el-timeline>
                    </div>
                </el-card>

                <!-- 漏洞分布饼图 -->
                <el-card shadow="hover" class="tech-card section-card">
                    <template #header>
                        <div class="card-title"><el-icon><PieChart /></el-icon> 漏洞分布</div>
                    </template>
                    <div ref="vulnChartRef" class="chart-container" />
                    <div class="vuln-list">
                        <div v-for="v in report.vuln_distribution" :key="v.name" class="vuln-row">
                            <span class="vuln-name">{{ v.name }}</span>
                            <el-progress :percentage="v.percent" :stroke-width="6"
                                color="#a04050" style="flex:1;margin:0 10px" />
                            <span class="vuln-count">{{ v.count }}次</span>
                        </div>
                    </div>
                </el-card>
            </div>

            <!-- 防御拦截率趋势 -->
            <el-card shadow="hover" class="tech-card section-card">
                <template #header>
                    <div class="card-title"><el-icon><TrendCharts /></el-icon> 防御拦截率趋势</div>
                </template>
                <div ref="trendChartRef" class="chart-container-wide" />
            </el-card>

            <!-- 决策日志（可解释性） -->
            <el-card shadow="hover" class="tech-card section-card">
                <template #header>
                    <div class="card-title">
                        <el-icon><ChatDotRound /></el-icon> 可解释决策链
                        <el-tag size="small" type="info" style="margin-left:8px">每步动作的推理依据</el-tag>
                    </div>
                </template>
                <div class="decision-list">
                    <div v-for="(d, i) in report.decision_log" :key="i" class="decision-item">
                        <span class="decision-time">{{ formatTime(d.time) }}</span>
                        <span class="decision-reasoning">{{ d.reasoning }}</span>
                        <el-tag v-if="d.env_action && d.env_action !== '无需环境干预'"
                            size="small" type="warning" style="margin-left:8px">
                            {{ d.env_action }}
                        </el-tag>
                        <el-tag v-if="d.adapt_msg" size="small" type="primary"
                            style="margin-left:4px; max-width:260px; white-space:normal; height:auto">
                            {{ d.adapt_msg }}
                        </el-tag>
                    </div>
                    <el-empty v-if="!report.decision_log?.length" description="暂无决策记录" :image-size="60" />
                </div>
            </el-card>

            <!-- AI 安全建议 -->
            <el-card shadow="hover" class="tech-card section-card">
                <template #header>
                    <div class="card-title"><el-icon><MagicStick /></el-icon> AI安全建议</div>
                </template>
                <div class="rec-list">
                    <div v-for="(rec, i) in report.ai_recommendations" :key="i" class="rec-item">
                        <span class="rec-index">{{ i + 1 }}</span>
                        <span class="rec-text">{{ rec }}</span>
                    </div>
                    <el-empty v-if="!report.ai_recommendations?.length" description="暂无建议" :image-size="60" />
                </div>
            </el-card>

            <!-- 环境调整记录 -->
            <el-card v-if="report.env_adjustments?.length" shadow="hover" class="tech-card section-card">
                <template #header>
                    <div class="card-title"><el-icon><Monitor /></el-icon> 环境Agent动态调整记录</div>
                </template>
                <el-table :data="report.env_adjustments" stripe size="small">
                    <el-table-column prop="time" label="时间" width="180">
                        <template #default="{ row }">{{ formatTime(row.time) }}</template>
                    </el-table-column>
                    <el-table-column prop="type" label="操作类型" width="130">
                        <template #default="{ row }">
                            <el-tag :type="row.type === 'isolate' ? 'danger' : 'warning'" size="small">
                                {{ { isolate: '组件隔离', scale_monitor: '扩容监控', rebuild_hint: '重建建议' }[row.type] || row.type }}
                            </el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column prop="reason" label="原因" />
                </el-table>
            </el-card>

        </div>

        <!-- 空状态 -->
        <el-card v-if="!report && !loading" shadow="hover" class="tech-card empty-card">
            <el-empty description="请选择演练会话并点击「生成报告」" :image-size="80">
                <el-button type="primary" @click="loadSessions">
                    <el-icon><Refresh /></el-icon> 刷新会话列表
                </el-button>
            </el-empty>
        </el-card>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
    DataAnalysis, Aim, Refresh, Download, InfoFilled,
    TrendCharts, ChatDotRound, MagicStick, Monitor, PieChart
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import request from '../utils/request'

const sessions = ref([])
const selectedSession = ref('')
const loading = ref(false)
const report = ref(null)
const vulnChartRef = ref(null)
const trendChartRef = ref(null)
let vulnChart = null
let trendChart = null

const scoreClass = computed(() => {
    const s = report.value?.overall_score?.score || 0
    if (s >= 80) return 'grade-a'
    if (s >= 60) return 'grade-b'
    if (s >= 40) return 'grade-c'
    return 'grade-d'
})

async function loadSessions() {
    try {
        const res = await request.get('/agents/sessions')
        sessions.value = res.sessions || []
        if (sessions.value.length && !selectedSession.value) {
            selectedSession.value = sessions.value[sessions.value.length - 1].session_id
        }
    } catch (e) {
        console.error('加载会话失败:', e)
    }
}

async function generateReport() {
    if (!selectedSession.value) {
        ElMessage.warning('请先选择演练会话')
        return
    }
    loading.value = true
    try {
        const res = await request.get(`/agents/report/generate?session_id=${selectedSession.value}&format=object`)
        if (res.status === 'success') {
            report.value = res.data
            await nextTick()
            renderCharts()
        } else {
            ElMessage.error(res.msg || '报告生成失败')
        }
    } catch (e) {
        ElMessage.error('生成失败: ' + (e.response?.data?.msg || e.message))
    } finally {
        loading.value = false
    }
}

function renderCharts() {
    renderVulnChart()
    renderTrendChart()
}

function renderVulnChart() {
    if (!vulnChartRef.value || !report.value?.vuln_distribution?.length) return
    if (vulnChart) vulnChart.dispose()
    vulnChart = echarts.init(vulnChartRef.value)
    const data = report.value.vuln_distribution.map(v => ({ name: v.name, value: v.count }))
    vulnChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}: {c}次 ({d}%)' },
        series: [{
            type: 'pie',
            radius: ['40%', '65%'],
            center: ['50%', '50%'],
            data,
            label: { color: '#b0b8c8', fontSize: 11 },
            itemStyle: {
                borderRadius: 6,
                borderColor: 'rgba(8,10,20,0.9)',
                borderWidth: 2,
            },
            emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } }
        }]
    })
}

function renderTrendChart() {
    if (!trendChartRef.value || !report.value?.defense_stats?.intercept_trend?.length) return
    if (trendChart) trendChart.dispose()
    trendChart = echarts.init(trendChartRef.value)
    const trend = report.value.defense_stats.intercept_trend
    trendChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis', formatter: params => `第${params[0].dataIndex + 1}次攻击: 拦截率${(params[0].value * 100).toFixed(0)}%` },
        xAxis: {
            type: 'category',
            data: trend.map((_, i) => `#${i + 1}`),
            axisLine: { lineStyle: { color: '#404860' } },
            axisLabel: { color: '#707888' }
        },
        yAxis: {
            type: 'value', min: 0, max: 1,
            axisLabel: { color: '#707888', formatter: v => `${(v * 100).toFixed(0)}%` },
            splitLine: { lineStyle: { color: '#1c1e30' } }
        },
        series: [{
            type: 'line', data: trend, smooth: true,
            lineStyle: { color: '#5090a0', width: 2 },
            areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(80,144,160,0.3)' }, { offset: 1, color: 'rgba(80,144,160,0.02)' }] } },
            itemStyle: { color: '#5090a0' },
            markLine: {
                silent: true,
                data: [{ yAxis: 0.7, name: '强防御线', lineStyle: { color: '#40a060', type: 'dashed' } },
                       { yAxis: 0.3, name: '弱防御线', lineStyle: { color: '#a04050', type: 'dashed' } }],
                label: { color: '#b0b8c8', fontSize: 10 }
            }
        }]
    })
}

function downloadReport() {
    if (!report.value) return
    const blob = new Blob([JSON.stringify(report.value, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${selectedSession.value?.slice(-8)}_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
}

function formatTime(t) {
    if (!t) return ''
    try { return new Date(t).toLocaleString('zh-CN') } catch { return t }
}

onMounted(loadSessions)
</script>

<style scoped>
.toolbar-card { margin-bottom: 20px; }
.toolbar-row { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.toolbar-left, .toolbar-right { display: flex; align-items: center; gap: 8px; }

/* 总览 */
.overview-grid {
    display: grid;
    grid-template-columns: 220px repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 20px;
}
.score-card {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 20px;
}
.score-ring {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    font-weight: 700;
    border: 3px solid;
    flex-shrink: 0;
}
.grade-a { border-color: #40a060; color: #40a060; box-shadow: 0 0 12px rgba(64,160,96,0.3); }
.grade-b { border-color: #5090a0; color: #5090a0; box-shadow: 0 0 12px rgba(80,144,160,0.3); }
.grade-c { border-color: #a09020; color: #a09020; box-shadow: 0 0 12px rgba(160,144,32,0.3); }
.grade-d { border-color: #a04050; color: #a04050; box-shadow: 0 0 12px rgba(160,64,80,0.3); }
.score-info { display: flex; flex-direction: column; gap: 4px; }
.score-grade { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.score-meta { font-size: 12px; color: var(--text-muted); }

.stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 16px;
    gap: 6px;
}
.stat-num {
    font-size: 28px;
    font-weight: 700;
    font-family: var(--font-mono);
}
.stat-num.cyan { color: #5090a0; }
.stat-num.warning { color: #a09020; }
.stat-num.danger { color: #a04050; }
.stat-num.purple { color: #6050a0; }
.stat-label { font-size: 12px; color: var(--text-muted); }

/* 摘要 */
.summary-text {
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.8;
    padding: 4px 0;
}

/* 两列布局 */
.two-col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
}

/* Section 卡片 */
.section-card { margin-bottom: 16px; }

/* 攻击路径 */
.path-scroll { max-height: 420px; overflow-y: auto; padding-right: 4px; }
.path-item { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; }
.path-step { font-size: 12px; color: var(--text-muted); margin-right: 4px; }
.combo-badge {
    background: rgba(160, 64, 80, 0.2);
    border: 1px solid rgba(160, 64, 80, 0.4);
    color: #c05060;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 4px;
}
.path-reasoning {
    width: 100%;
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
    line-height: 1.5;
}

/* 漏洞分布 */
.chart-container { height: 200px; }
.chart-container-wide { height: 220px; }
.vuln-list { margin-top: 12px; }
.vuln-row { display: flex; align-items: center; margin-bottom: 8px; }
.vuln-name { width: 110px; font-size: 12px; color: var(--text-secondary); flex-shrink: 0; }
.vuln-count { font-size: 12px; color: var(--text-muted); width: 40px; text-align: right; }

/* 决策链 */
.decision-list { display: flex; flex-direction: column; gap: 10px; max-height: 360px; overflow-y: auto; }
.decision-item { display: flex; align-items: flex-start; flex-wrap: wrap; gap: 6px; padding: 8px 10px; background: rgba(8,10,20,0.4); border-radius: 8px; border-left: 3px solid rgba(80,144,160,0.4); }
.decision-time { font-size: 11px; color: var(--text-muted); white-space: nowrap; }
.decision-reasoning { font-size: 13px; color: var(--text-secondary); flex: 1; line-height: 1.5; }

/* AI建议 */
.rec-list { display: flex; flex-direction: column; gap: 10px; }
.rec-item { display: flex; align-items: flex-start; gap: 12px; padding: 10px 14px; background: rgba(8,10,20,0.4); border-radius: 8px; border-left: 3px solid rgba(96,80,160,0.5); }
.rec-index { width: 22px; height: 22px; border-radius: 50%; background: rgba(96,80,160,0.3); color: #a090d0; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.rec-text { font-size: 13px; color: var(--text-secondary); line-height: 1.6; }

/* 空状态 */
.empty-card { min-height: 300px; display: flex; align-items: center; justify-content: center; }
.empty-card :deep(.el-card__body) { width: 100%; }
</style>
