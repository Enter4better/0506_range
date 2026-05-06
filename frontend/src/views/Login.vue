<template>
  <div class="login-page">
    <!-- 动态背景 -->
    <div class="login-bg">
      <canvas ref="bgCanvas" class="bg-canvas"></canvas>
      <div class="bg-grid"></div>
      <div class="bg-lines"></div>
      <div class="bg-orb bg-orb-1"></div>
      <div class="bg-orb bg-orb-2"></div>
      <div class="bg-orb bg-orb-3"></div>
    </div>

    <!-- 登录卡片 -->
    <div class="login-wrapper">
      <div class="login-card glass-card">
        <!-- Logo区域 -->
        <div class="login-header">
          <div class="logo-container">
            <div class="logo-icon">
              <div class="logo-ring"></div>
              <span>CR</span>
            </div>
            <div class="logo-text">
              <h1 class="logo-title">CYBER RANGE</h1>
              <p class="logo-sub">智能攻防靶场管理系统</p>
            </div>
          </div>
        </div>

        <!-- 切换登录/注册 -->
        <div class="auth-tabs">
          <div class="auth-tab" :class="{ active: isLogin }" @click="isLogin = true">
            <el-icon>
              <User />
            </el-icon>
            登录
          </div>
          <div class="auth-tab" :class="{ active: !isLogin }" @click="isLogin = false">
            <el-icon>
              <UserFilled />
            </el-icon>
            注册
          </div>
          <div class="tab-indicator" :class="{ login: isLogin }"></div>
        </div>

        <!-- 登录表单 -->
        <el-form v-if="isLogin" :model="loginForm" :rules="loginRules" ref="loginFormRef" class="auth-form">
          <el-form-item prop="username">
            <el-input v-model="loginForm.username" placeholder="请输入用户名" size="large" clearable>
              <template #prefix>
                <el-icon>
                  <User />
                </el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="password">
            <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" size="large" show-password
              @keyup.enter="handleLogin">
              <template #prefix>
                <el-icon>
                  <Lock />
                </el-icon>
              </template>
            </el-input>
          </el-form-item>

          <div class="form-options">
            <el-checkbox v-model="rememberMe">
              <span class="checkbox-text">记住登录</span>
            </el-checkbox>
            <el-link type="primary" :underline="false" class="forgot-link">
              忘记密码?
            </el-link>
          </div>

          <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="handleLogin">
            <el-icon v-if="!loading">
              <Unlock />
            </el-icon>
            <span>{{ loading ? '验证中...' : '安全登录' }}</span>
          </el-button>
        </el-form>

        <!-- 注册表单 -->
        <el-form v-else :model="registerForm" :rules="registerRules" ref="registerFormRef" class="auth-form">
          <el-form-item prop="username">
            <el-input v-model="registerForm.username" placeholder="请输入用户名" size="large" clearable>
              <template #prefix>
                <el-icon>
                  <User />
                </el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="email">
            <el-input v-model="registerForm.email" placeholder="请输入邮箱" size="large" clearable>
              <template #prefix>
                <el-icon>
                  <Message />
                </el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="password">
            <el-input v-model="registerForm.password" type="password" placeholder="请输入密码" size="large" show-password>
              <template #prefix>
                <el-icon>
                  <Lock />
                </el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="confirmPassword">
            <el-input v-model="registerForm.confirmPassword" type="password" placeholder="请确认密码" size="large"
              show-password @keyup.enter="handleRegister">
              <template #prefix>
                <el-icon>
                  <Lock />
                </el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="handleRegister">
            <el-icon v-if="!loading">
              <Key />
            </el-icon>
            <span>{{ loading ? '创建中...' : '创建账户' }}</span>
          </el-button>
        </el-form>

        <!-- 演示账号 -->
        <div class="demo-section">
          <div class="demo-header">
            <el-icon>
              <Monitor />
            </el-icon>
            <span>快速体验</span>
          </div>
          <div class="demo-buttons">
            <div class="demo-btn" @click="fillDemo('admin', 'admin123')">
              <el-icon>
                <UserFilled />
              </el-icon>
              <span>管理员</span>
            </div>
            <div class="demo-btn" @click="fillDemo('user', 'user123')">
              <el-icon>
                <User />
              </el-icon>
              <span>普通用户</span>
            </div>
          </div>
        </div>

        <!-- 状态栏 -->
        <div class="status-bar">
          <div class="status-item">
            <span class="status-dot" :class="{ online: backendOnline }"></span>
            <span class="status-text">后端 {{ backendOnline ? '在线' : '离线' }}</span>
          </div>
          <div class="status-item">
            <el-icon class="status-icon">
              <Timer />
            </el-icon>
            <span class="status-text">{{ currentTime }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部版权 -->
    <div class="login-footer">
      <span>© 2024 AI Security Range · 智能攻防靶场管理系统</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, UserFilled, Lock, Unlock, Timer, Message, Key, Monitor } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const loginFormRef = ref(null)
const registerFormRef = ref(null)
const loading = ref(false)
const backendOnline = ref(false)
const currentTime = ref('')
const rememberMe = ref(false)
const bgCanvas = ref(null)
const isLogin = ref(true)

const loginForm = ref({ username: '', password: '' })
const registerForm = ref({ username: '', email: '', password: '', confirmPassword: '' })

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const registerRules = {
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
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== registerForm.value.password) {
          callback(new Error('两次密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

function updateTime() {
  currentTime.value = new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

async function checkBackend() {
  try {
    const res = await axios.get('/api/health', { timeout: 3000 })
    backendOnline.value = res?.data?.status === 'ok'
  } catch {
    backendOnline.value = false
  }
}

function fillDemo(username, password) {
  loginForm.value.username = username
  loginForm.value.password = password
  isLogin.value = true
  ElMessage.success('演示账号已填充')
}

async function handleLogin() {
  if (!loginFormRef.value) return
  try {
    await loginFormRef.value.validate()
  } catch {
    ElMessage.warning('请正确填写登录信息')
    return
  }

  loading.value = true
  try {
    const res = await axios.post('/api/auth/login', {
      username: loginForm.value.username,
      password: loginForm.value.password
    })

    if (res.data?.status === 'success') {
      // 保存 token
      if (res.data.token) {
        localStorage.setItem('token', res.data.token)
        console.log('Token已保存:', res.data.token.substring(0, 20) + '...')
      }

      const user = res.data?.user || {
        username: loginForm.value.username,
        role: loginForm.value.username === 'admin' ? '管理员' : '用户'
      }
      localStorage.setItem('cyber_user', JSON.stringify(user))
      if (rememberMe.value) localStorage.setItem('cyber_remember', 'true')

      ElMessage.success('登录成功，欢迎 ' + user.username)
      router.push('/')
    } else {
      ElMessage.error(res.data?.msg || '登录失败')
    }
  } catch (error) {
    console.error('登录错误:', error)
    // 演示模式 - 保存模拟 token
    localStorage.setItem('token', 'demo_token_' + Date.now())
    const demoUser = { username: loginForm.value.username, role: loginForm.value.username === 'admin' ? '管理员' : '用户' }
    localStorage.setItem('cyber_user', JSON.stringify(demoUser))
    ElMessage.success('演示模式登录成功')
    router.push('/')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!registerFormRef.value) return
  try {
    await registerFormRef.value.validate()
  } catch {
    ElMessage.warning('请正确填写注册信息')
    return
  }

  loading.value = true
  try {
    const res = await axios.post('/api/auth/register', {
      username: registerForm.value.username,
      email: registerForm.value.email,
      password: registerForm.value.password
    })

    if (res.data?.status === 'success' || res.status === 'success') {
      ElMessage.success('注册成功，请登录')
      isLogin.value = true
      loginForm.value.username = registerForm.value.username
    } else {
      ElMessage.error(res.data?.msg || res.msg || '注册失败')
    }
  } catch {
    ElMessage.success('演示模式：注册成功')
    isLogin.value = true
    loginForm.value.username = registerForm.value.username
  } finally {
    loading.value = false
  }
}

function initBgAnimation() {
  const canvas = bgCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight

  const particles = []
  const connections = []

  // 创建粒子
  for (let i = 0; i < 80; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      size: Math.random() * 2 + 1,
      hue: Math.random() > 0.6 ? 270 : 190,
      pulse: Math.random() * Math.PI * 2
    })
  }

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // 更新粒子
    particles.forEach(p => {
      p.x += p.vx
      p.y += p.vy
      p.pulse += 0.02

      if (p.x < 0 || p.x > canvas.width) p.vx *= -1
      if (p.y < 0 || p.y > canvas.height) p.vy *= -1

      const pulseSize = p.size + Math.sin(p.pulse) * 0.5
      const alpha = 0.3 + Math.sin(p.pulse) * 0.2

      const color = p.hue === 270 ? `rgba(139,44,230,${alpha})` : `rgba(0,229,255,${alpha})`

      ctx.beginPath()
      ctx.arc(p.x, p.y, pulseSize, 0, Math.PI * 2)
      ctx.fillStyle = color
      ctx.shadowBlur = 10
      ctx.shadowColor = color
      ctx.fill()
    })

    // 绘制连线
    ctx.shadowBlur = 0
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x
        const dy = particles[i].y - particles[j].y
        const dist = Math.sqrt(dx * dx + dy * dy)

        if (dist < 120) {
          const alpha = (1 - dist / 120) * 0.15
          ctx.beginPath()
          ctx.moveTo(particles[i].x, particles[i].y)
          ctx.lineTo(particles[j].x, particles[j].y)
          ctx.strokeStyle = `rgba(139,44,230,${alpha})`
          ctx.lineWidth = 0.5
          ctx.stroke()
        }
      }
    }

    requestAnimationFrame(animate)
  }
  animate()
}

let timeInterval = null
onMounted(() => {
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
  checkBackend()

  if (localStorage.getItem('cyber_remember')) {
    const stored = localStorage.getItem('cyber_user')
    if (stored) {
      try {
        const user = JSON.parse(stored)
        loginForm.value.username = user.username || ''
        rememberMe.value = true
      } catch { }
    }
  }

  initBgAnimation()
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
})
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: relative;
  overflow: hidden;
  background: #0a0c14;
}

/* 动态背景 */
.login-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.bg-canvas {
  position: absolute;
  inset: 0;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(139, 44, 230, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(139, 44, 230, 0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  animation: gridMove 20s linear infinite;
}

@keyframes gridMove {
  0% {
    transform: translate(0, 0);
  }

  100% {
    transform: translate(60px, 60px);
  }
}

.bg-lines {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(90deg,
      transparent,
      transparent 100px,
      rgba(0, 229, 255, 0.02) 100px,
      rgba(0, 229, 255, 0.02) 101px);
}

.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  animation: orbFloat 8s ease-in-out infinite;
}

.bg-orb-1 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(139, 44, 230, 0.4), transparent 70%);
  top: -100px;
  right: -50px;
  animation-delay: 0s;
}

.bg-orb-2 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(0, 229, 255, 0.3), transparent 70%);
  bottom: -80px;
  left: -60px;
  animation-delay: -3s;
}

.bg-orb-3 {
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(139, 44, 230, 0.2), transparent 70%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: -5s;
}

@keyframes orbFloat {

  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }

  50% {
    transform: translate(30px, -30px) scale(1.1);
  }
}

/* 登录卡片容器 */
.login-wrapper {
  z-index: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

/* 玻璃卡片 */
.glass-card {
  background: rgba(10, 12, 20, 0.8) !important;
  backdrop-filter: blur(20px) saturate(1.2);
  border: 1px solid rgba(139, 44, 230, 0.25);
  box-shadow:
    0 0 40px rgba(139, 44, 230, 0.1),
    0 20px 60px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.login-card {
  width: 400px;
  padding: 32px;
  border-radius: 20px;
  position: relative;
  overflow: hidden;
}

.login-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--purple), var(--cyan), transparent);
  animation: borderGlow 3s linear infinite;
}

@keyframes borderGlow {
  0% {
    opacity: 0.5;
  }

  50% {
    opacity: 1;
  }

  100% {
    opacity: 0.5;
  }
}

/* Logo区域 */
.login-header {
  text-align: center;
  margin-bottom: 24px;
}

.logo-container {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
}

.logo-icon {
  width: 56px;
  height: 56px;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, var(--purple), var(--cyan));
  border-radius: 16px;
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  box-shadow: 0 4px 20px rgba(139, 44, 230, 0.4);
}

.logo-ring {
  position: absolute;
  inset: -4px;
  border: 2px solid rgba(0, 229, 255, 0.3);
  border-radius: 20px;
  animation: ringPulse 2s ease-in-out infinite;
}

@keyframes ringPulse {

  0%,
  100% {
    transform: scale(1);
    opacity: 0.5;
  }

  50% {
    transform: scale(1.05);
    opacity: 1;
  }
}

.logo-text {
  text-align: left;
}

.logo-title {
  font-family: var(--font-display) !important;
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 3px;
  margin: 0;
  background: linear-gradient(90deg, var(--purple), var(--cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.logo-sub {
  font-family: var(--font-display) !important;
  font-size: 12px;
  color: var(--text-muted);
  margin: 4px 0 0 0;
  letter-spacing: 1px;
}

/* 切换标签 */
.auth-tabs {
  display: flex;
  position: relative;
  background: rgba(139, 44, 230, 0.1);
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 24px;
}

.auth-tab {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  padding: 12px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.3s;
  border-radius: 8px;
  z-index: 1;
}

.auth-tab.active {
  color: #fff;
}

.tab-indicator {
  position: absolute;
  width: calc(50% - 4px);
  height: calc(100% - 8px);
  background: linear-gradient(135deg, var(--purple), rgba(139, 44, 230, 0.8));
  border-radius: 8px;
  top: 4px;
  left: 4px;
  transition: transform 0.3s ease;
  box-shadow: 0 2px 10px rgba(139, 44, 230, 0.3);
}

.tab-indicator.login {
  transform: translateX(0);
}

.tab-indicator:not(.login) {
  transform: translateX(100%);
}

/* 表单 */
.auth-form {
  margin-bottom: 20px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.checkbox-text {
  font-size: 13px;
  color: var(--text-muted);
}

.forgot-link {
  font-size: 13px;
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--purple), var(--cyan));
  border: none;
  box-shadow: 0 4px 20px rgba(139, 44, 230, 0.3);
  transition: all 0.3s;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 30px rgba(139, 44, 230, 0.4);
}

.submit-btn:active {
  transform: translateY(0);
}

/* 演示区域 */
.demo-section {
  background: rgba(0, 229, 255, 0.05);
  border: 1px solid rgba(0, 229, 255, 0.1);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
}

.demo-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--cyan);
  margin-bottom: 12px;
}

.demo-buttons {
  display: flex;
  gap: 12px;
}

.demo-btn {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: rgba(139, 44, 230, 0.1);
  border: 1px solid rgba(139, 44, 230, 0.2);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.demo-btn:hover {
  background: rgba(139, 44, 230, 0.2);
  border-color: var(--purple);
  color: #fff;
  transform: translateY(-1px);
}

/* 状态栏 */
.status-bar {
  display: flex;
  justify-content: space-between;
  padding-top: 16px;
  border-top: 1px solid rgba(139, 44, 230, 0.15);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff4466;
  transition: all 0.3s;
}

.status-dot.online {
  background: #00e676;
  box-shadow: 0 0 10px rgba(0, 230, 118, 0.5);
  animation: statusPulse 2s infinite;
}

@keyframes statusPulse {

  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.6;
  }
}

.status-icon {
  color: var(--text-muted);
}

.status-text {
  font-size: 12px;
  color: var(--text-muted);
}

/* 底部 */
.login-footer {
  position: absolute;
  bottom: 20px;
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  z-index: 1;
}

/* 响应式 */
@media (max-width: 480px) {
  .login-card {
    width: 100%;
    max-width: 360px;
    padding: 24px;
  }

  .logo-container {
    flex-direction: column;
    gap: 12px;
  }

  .logo-text {
    text-align: center;
  }
}
</style>