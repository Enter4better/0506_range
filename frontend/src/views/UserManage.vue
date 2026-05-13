<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon><User /></el-icon> 用户管理
      </h2>
      <p class="page-desc">
        管理系统用户 | 共 {{ users.length }} 个用户
      </p>
    </div>

    <!-- 用户列表 -->
    <el-card shadow="hover" class="tech-card">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 600;">用户列表</span>
          <div style="display: flex; gap: 8px;">
            <el-button type="primary" size="small" @click="showAddDialog">
              <el-icon><Plus /></el-icon> 增加用户
            </el-button>
            <el-button type="default" size="small" @click="fetchUsers" :loading="loading">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="users" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="user_id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" min-width="120">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px;">
              <el-avatar :size="28" style="background: var(--purple); color: #fff; font-size: 12px;">
                {{ row.username?.charAt(0)?.toUpperCase() }}
              </el-avatar>
              <span style="font-weight: 500;">{{ row.username }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180">
          <template #default="{ row }">
            <span style="color: var(--text-muted); font-size: 12px;">
              {{ formatTime(row.created_at) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="last_login" label="最后登录" width="180">
          <template #default="{ row }">
            <span v-if="row.last_login" style="color: var(--text-muted); font-size: 12px;">
              {{ formatTime(row.last_login) }}
            </span>
            <span v-else style="color: var(--text-muted); font-size: 12px;">从未登录</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" type="primary" @click="showEditDialog(row)">
                <el-icon><Edit /></el-icon> 编辑
              </el-button>
              <el-button size="small" type="warning" @click="showPasswordDialog(row)">
                <el-icon><Lock /></el-icon> 改密
              </el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)" :disabled="row.user_id === currentUserId">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑用户对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑用户" width="450px" class="tech-dialog">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role" style="width: 100%;">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 增加用户对话框 -->
    <el-dialog v-model="addDialogVisible" title="增加用户" width="450px" class="tech-dialog">
      <el-form :model="addForm" :rules="addRules" ref="addFormRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="addForm.username" placeholder="请输入用户名（3-20字符）" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="addForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="addForm.password" type="password" placeholder="请输入密码（至少8位，含大写、小写、数字）" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="addForm.confirmPassword" type="password" placeholder="请再次输入密码" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="addForm.role" style="width: 100%;">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdd" :loading="saving">创建</el-button>
      </template>
    </el-dialog>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="450px" class="tech-dialog">
      <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="passwordForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="password">
          <el-input v-model="passwordForm.password" type="password" placeholder="请输入新密码（至少8位，含大写、小写、数字）" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="passwordForm.confirmPassword" type="password" placeholder="请再次输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleChangePassword" :loading="saving">修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Refresh, Edit, Delete, Plus, Lock } from '@element-plus/icons-vue'
import request from '@/utils/request'

const users = ref([])
const loading = ref(false)
const editDialogVisible = ref(false)
const addDialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const saving = ref(false)
const addFormRef = ref(null)
const passwordFormRef = ref(null)
const editForm = ref({
  user_id: null,
  username: '',
  email: '',
  role: 'user'
})
const addForm = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  role: 'user'
})
const passwordForm = ref({
  user_id: null,
  username: '',
  password: '',
  confirmPassword: ''
})

// 增加用户表单验证规则
const addRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度 3-20 字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少8位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== addForm.value.password) {
          callback(new Error('两次密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 修改密码表单验证规则
const passwordRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少8位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.value.password) {
          callback(new Error('两次密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 获取当前用户ID
const currentUserId = computed(() => {
  try {
    const u = JSON.parse(localStorage.getItem('cyber_user') || '{}')
    return u.user_id
  } catch { return null }
})

// 获取用户列表
async function fetchUsers() {
  loading.value = true
  try {
    const res = await request.get('/auth/users')
    if (res.status === 'success') {
      users.value = res.users || []
    } else {
      ElMessage.error(res.msg || '获取用户列表失败')
    }
  } catch (err) {
    console.error('获取用户列表失败:', err)
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

// 显示编辑对话框
function showEditDialog(user) {
  editForm.value = {
    user_id: user.user_id,
    username: user.username,
    email: user.email || '',
    role: user.role || 'user'
  }
  editDialogVisible.value = true
}

// 保存修改
async function handleSave() {
  if (!editForm.value.email) {
    ElMessage.warning('请输入邮箱')
    return
  }

  saving.value = true
  try {
    const res = await request.put(`/auth/users/${editForm.value.user_id}`, {
      username: editForm.value.username,
      email: editForm.value.email,
      role: editForm.value.role
    })
    if (res.status === 'success') {
      ElMessage.success('用户信息已更新')
      editDialogVisible.value = false
      await fetchUsers()
    } else {
      ElMessage.error(res.msg || '更新失败')
    }
  } catch (err) {
    console.error('更新用户失败:', err)
    ElMessage.error('更新失败')
  } finally {
    saving.value = false
  }
}

// 删除用户
async function handleDelete(user) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户 "${user.username}" 吗？此操作不可恢复！`,
      '确认删除',
      { type: 'warning' }
    )

    const res = await request.delete(`/auth/users/${user.user_id}`)
    if (res.status === 'success') {
      ElMessage.success(`用户 ${user.username} 已删除`)
      await fetchUsers()
    } else {
      ElMessage.error(res.msg || '删除失败')
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 显示增加用户对话框
function showAddDialog() {
  addForm.value = {
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    role: 'user'
  }
  addDialogVisible.value = true
}

// 增加用户
async function handleAdd() {
  if (!addFormRef.value) return
  try {
    await addFormRef.value.validate()
  } catch {
    ElMessage.warning('请正确填写信息')
    return
  }

  saving.value = true
  try {
    const res = await request.post('/auth/register', {
      username: addForm.value.username,
      email: addForm.value.email,
      password: addForm.value.password,
      role: addForm.value.role
    })
    if (res.status === 'success') {
      ElMessage.success('用户创建成功')
      addDialogVisible.value = false
      await fetchUsers()
    } else {
      ElMessage.error(res.msg || '创建失败')
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || '创建失败')
  } finally {
    saving.value = false
  }
}

// 显示修改密码对话框
function showPasswordDialog(user) {
  passwordForm.value = {
    user_id: user.user_id,
    username: user.username,
    password: '',
    confirmPassword: ''
  }
  passwordDialogVisible.value = true
}

// 修改密码
async function handleChangePassword() {
  if (!passwordFormRef.value) return
  try {
    await passwordFormRef.value.validate()
  } catch {
    ElMessage.warning('请正确填写信息')
    return
  }

  saving.value = true
  try {
    const res = await request.put(`/auth/users/${passwordForm.value.user_id}`, {
      password: passwordForm.value.password
    })
    if (res.status === 'success') {
      ElMessage.success('密码修改成功')
      passwordDialogVisible.value = false
    } else {
      ElMessage.error(res.msg || '修改失败')
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || '修改失败')
  } finally {
    saving.value = false
  }
}

// 格式化时间
function formatTime(timeStr) {
  if (!timeStr) return '--'
  try {
    const date = new Date(timeStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return timeStr
  }
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.page-header {
  margin-bottom: 20px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.page-desc {
  color: var(--text-muted);
  font-size: 14px;
  margin: 0;
}

:deep(.el-table) {
  --el-table-border-color: rgba(139, 44, 230, 0.15);
  --el-table-header-bg-color: rgba(139, 44, 230, 0.08);
}

:deep(.tech-dialog) {
  --el-dialog-bg-color: rgba(10, 12, 20, 0.95);
}
</style>
