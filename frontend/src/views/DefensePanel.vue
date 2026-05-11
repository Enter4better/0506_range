<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon>
          <Umbrella />
        </el-icon>
        AI 自适应防御中心
      </h2>
      <p class="page-desc">AI Agent 根据攻击类型、强度、轮次自动选择防御策略</p>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="12" :sm="6">
        <StatCard :icon="Warning" :value="stats.total_attacks" label="检测攻击总数" type="danger" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard :icon="Lock" :value="activeBlocksCount" label="活跃封禁类型" type="warning" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard :icon="DataLine" :value="attackTypesCount" label="攻击类型" type="info" />
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard :icon="Timer" :value="defenseLogsCount" label="防御日志" type="success" />
      </el-col>
    </el-row>

    <!-- 防御策略表 -->
    <el-card class="tech-card">
      <template #header>
        <div class="card-header">
          <span><el-icon>
              <List />
            </el-icon> 自适应防御策略</span>
          <span class="tip">攻击强度越高、轮次越多 → 防御等级越高</span>
        </div>
      </template>
      <el-table :data="defenseTableData" stripe size="small">
        <el-table-column prop="attack_type" label="攻击类型" width="120" />
        <el-table-column prop="level_1" label="轻度防御(强度1-2)" />
        <el-table-column prop="level_2" label="基础防御(强度3-4)" />
        <el-table-column prop="level_3" label="中级防御(强度5-6)" />
        <el-table-column prop="level_4" label="高级防御(强度7-8)" />
        <el-table-column prop="level_5" label="极致防御(强度9-10)" />
      </el-table>
    </el-card>

    <!-- 防御规则管理（从数据库加载，在攻防演练中实际生效） -->
    <el-card class="tech-card" style="margin-top: 16px;">
      <template #header>
        <div class="card-header">
          <span><el-icon>
              <Umbrella />
            </el-icon> 防御规则管理（{{ enabledRulesCount }}/{{ defenseRules.length }} 已启用）</span>
          <div>
            <el-button size="small" :icon="Refresh" @click="loadDefenseRules" :loading="loadingRules">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table :data="defenseRules" stripe size="small" v-loading="loadingRules">
        <el-table-column prop="name" label="规则名称" min-width="140" />
        <el-table-column prop="defense_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.defense_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="160" />
        <el-table-column prop="coverage" label="覆盖率" width="80">
          <template #default="{ row }">
            <span>{{ row.coverage }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="toggleRule(row)" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" type="danger" :icon="Delete" circle @click="deleteRule(row)" />
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!defenseRules.length && !loadingRules" class="empty-tip" style="padding: 20px;">
        暂无防御规则，请在环境管理页面添加
      </div>
      <div style="margin-top: 8px; font-size: 12px; color: var(--text-muted);">
        <el-tag size="small" type="success" style="margin-right: 4px;">💡</el-tag>
        启用的规则会在攻防演练中自动生效，匹配攻击类型时提升拦截率
      </div>
    </el-card>

    <!-- 防御日志 -->
    <el-card class="tech-card" style="margin-top: 16px;">
      <template #header>
        <div class="card-header">
          <span><el-icon>
              <Document />
            </el-icon> 防御执行日志（共 {{ defenseTotal }} 条）</span>
          <el-button size="small" @click="loadDefenseLogs(1)">刷新</el-button>
        </div>
      </template>
      <div class="log-list">
        <div v-for="log in defenseLogs" :key="log.timestamp" class="log-item" :class="'level-' + log.defense_level">
          <div class="log-time">{{ formatTime(log.timestamp) }}</div>
          <div class="log-content">
            <el-tag size="small" type="danger">{{ log.attack_type }}</el-tag>
            <el-tag size="small" :type="getLevelType(log.defense_level)">
              等级 {{ log.defense_level }}
            </el-tag>
            <span class="log-action">{{ log.actions?.join(' → ') }}</span>
          </div>
        </div>
        <div v-if="!defenseLogs.length" class="empty-tip">暂无防御日志，执行攻击后将自动记录</div>
      </div>
      <div v-if="defenseTotal > defensePageSize" style="margin-top: 12px; display: flex; justify-content: flex-end;">
        <el-pagination
          v-model:current-page="defensePage"
          :page-size="defensePageSize"
          :total="defenseTotal"
          layout="total, prev, pager, next"
          small
          @current-change="loadDefenseLogs"
        />
      </div>
    </el-card>

    <!-- 活跃封禁 -->
    <el-card class="tech-card" style="margin-top: 16px;" v-if="Object.keys(activeBlocks).length">
      <template #header>
        <div class="card-header">
          <span><el-icon>
              <Lock />
            </el-icon> 活跃封禁列表</span>
        </div>
      </template>
      <div class="block-list">
        <div v-for="(block, type) in activeBlocks" :key="type" class="block-item">
          <span class="block-type">{{ type }}</span>
          <span class="block-level">封禁等级: {{ block.level }}</span>
          <span class="block-ips">封禁IP: {{ block.ips?.join(', ') || '无' }}</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Umbrella, Warning, Lock, DataLine, Timer, List, Document, Plus, Delete, Refresh } from '@element-plus/icons-vue'
import StatCard from '@/components/StatCard.vue'
import request from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'

const defenseLogs = ref([])
const defensePage = ref(1)
const defensePageSize = ref(10)
const defenseTotal = ref(0)
const activeBlocks = ref({})
const stats = ref({ total_attacks: 0, defense_logs_count: 0 })
const defenseRules = ref([])  // 从数据库加载的防御规则
const loadingRules = ref(false)
let refreshTimer = null

// 防御策略表数据（与攻击类型完全同步，共16种）
const defenseTableData = [
  // Web漏洞攻击
  { attack_type: 'SQL注入', level_1: '参数化查询', level_2: 'WAF规则', level_3: 'SQL审计', level_4: '数据库隔离', level_5: '只读模式' },
  { attack_type: 'XSS攻击', level_1: '输入过滤', level_2: '输出编码', level_3: 'CSP策略', level_4: 'DOM净化', level_5: '沙箱隔离' },
  { attack_type: 'CSRF攻击', level_1: 'Token验证', level_2: 'Referer检查', level_3: 'SameSite Cookie', level_4: '请求签名', level_5: '二次确认' },
  { attack_type: '文件包含', level_1: '路径过滤', level_2: '白名单校验', level_3: '文件隔离', level_4: '沙箱执行', level_5: '禁用包含' },
  { attack_type: '命令执行', level_1: '命令过滤', level_2: '禁用函数', level_3: '容器隔离', level_4: '审计', level_5: '沙箱' },
  { attack_type: 'SSRF攻击', level_1: 'URL校验', level_2: '内网IP过滤', level_3: 'DNS解析检查', level_4: '请求代理', level_5: '网络隔离' },
  { attack_type: 'XXE注入', level_1: '禁用DTD', level_2: 'XML过滤', level_3: '输入验证', level_4: 'WAF规则', level_5: '沙箱解析' },
  // 系统层攻击
  { attack_type: '权限提升', level_1: '最小权限', level_2: 'SELinux', level_3: '内核加固', level_4: '审计追踪', level_5: '容器隔离' },
  { attack_type: '容器逃逸', level_1: '只读根fs', level_2: 'Capabilities限制', level_3: 'Seccomp', level_4: 'AppArmor', level_5: '沙箱嵌套' },
  { attack_type: '反弹Shell', level_1: '出站过滤', level_2: '端口限制', level_3: '行为检测', level_4: '进程隔离', level_5: '网络阻断' },
  // 网络攻击
  { attack_type: '端口扫描', level_1: '记录日志', level_2: '减速响应', level_3: '临时封禁', level_4: '永久封禁', level_5: '蜜罐启动' },
  { attack_type: '暴力破解', level_1: '延迟响应', level_2: '验证码', level_3: '临时封禁', level_4: '永久封禁', level_5: '全域封锁' },
  { attack_type: '中间人攻击', level_1: 'HSTS', level_2: '证书固定', level_3: '双向TLS', level_4: '流量加密', level_5: '网络隔离' },
  // 高级持续性威胁
  { attack_type: '后门植入', level_1: '文件监控', level_2: '进程审计', level_3: '行为分析', level_4: 'Rootkit检测', level_5: '系统还原' },
  { attack_type: '横向移动', level_1: '网络分段', level_2: '零信任', level_3: '微隔离', level_4: '行为基线', level_5: '自动响应' },
  { attack_type: '数据外传', level_1: '流量监控', level_2: 'DLP策略', level_3: '数据脱敏', level_4: '出口过滤', level_5: '网络阻断' }
]

const activeBlocksCount = computed(() => Object.keys(activeBlocks.value).length)
const attackTypesCount = computed(() => defenseTableData.length)
const defenseLogsCount = computed(() => defenseLogs.value.length)
const enabledRulesCount = computed(() => defenseRules.value.filter(r => r.enabled).length)

// 从数据库加载防御规则
async function loadDefenseRules() {
  loadingRules.value = true
  try {
    const res = await request.get('/defense/list')
    if (res.status === 'success') {
      defenseRules.value = res.defenses || res.data || []
    }
  } catch (e) {
    console.error('加载防御规则失败', e)
  } finally {
    loadingRules.value = false
  }
}

// 切换防御规则启用/禁用
async function toggleRule(rule) {
  try {
    const res = await request.post(`/defense/toggle/${rule.defense_id}`)
    if (res.status === 'success') {
      rule.enabled = !rule.enabled
      ElMessage.success(res.message || `规则已${rule.enabled ? '启用' : '禁用'}`)
      // 通知后端刷新防御Agent的规则缓存
      await request.post('/agents/defense/refresh-rules')
    }
  } catch (e) {
    ElMessage.error('切换失败')
  }
}

// 删除防御规则
async function deleteRule(rule) {
  try {
    await ElMessageBox.confirm(`确定要删除规则 "${rule.name}" 吗？`, '确认删除', { type: 'warning' })
    const res = await request.delete(`/defense/delete/${rule.defense_id}`)
    if (res.status === 'success') {
      defenseRules.value = defenseRules.value.filter(r => r.defense_id !== rule.defense_id)
      ElMessage.success('规则已删除')
      await request.post('/agents/defense/refresh-rules')
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

async function loadDefenseStatus() {
  try {
    const res = await request.get('/agents/defense/status')
    if (res.status === 'success') {
      stats.value = res.data
      activeBlocks.value = res.data.active_blocks || {}
    }
  } catch (e) {
    console.error('加载防御状态失败', e)
  }
}

async function loadDefenseLogs(page = defensePage.value) {
  defensePage.value = page
  try {
    const res = await request.get('/agents/defense/logs', {
      params: { page: defensePage.value, limit: defensePageSize.value }
    })
    if (res.status === 'success') {
      defenseLogs.value = res.logs || []
      defenseTotal.value = res.total || 0
    }
  } catch (e) {
    console.error('加载防御日志失败', e)
  }
}


function getLevelType(level) {
  if (level >= 4) return 'danger'
  if (level >= 3) return 'warning'
  return 'info'
}

function formatTime(time) {
  if (!time) return ''
  return new Date(time).toLocaleTimeString()
}

onMounted(() => {
  loadDefenseStatus()
  loadDefenseLogs()
  loadDefenseRules()
  // 每5秒自动刷新防御状态（保持当前页）
  refreshTimer = setInterval(() => {
    loadDefenseStatus()
    loadDefenseLogs(defensePage.value)
  }, 5000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.log-list {
  max-height: 400px;
  overflow-y: auto;
}

.log-item {
  display: flex;
  gap: 16px;
  padding: 12px;
  border-bottom: 1px solid var(--border-dim);
}

.log-item.level-4,
.log-item.level-5 {
  background: rgba(245, 108, 108, 0.1);
}

.log-time {
  font-size: 12px;
  color: var(--text-muted);
  min-width: 100px;
}

.log-action {
  color: var(--text-secondary);
  font-size: 13px;
  flex: 1;
}

.block-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.block-item {
  display: flex;
  gap: 20px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.block-type {
  font-weight: 600;
  color: var(--danger);
  min-width: 100px;
}

.block-level {
  color: var(--warning);
}

.block-ips {
  color: var(--text-muted);
  font-family: monospace;
}

.tip {
  font-size: 12px;
  color: var(--text-muted);
}

.empty-tip {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}
</style>