<template>
  <div class="app-wrapper">
    <!-- 全局动态背景 -->
    <div class="global-bg">
      <canvas ref="bgCanvas" class="bg-canvas"></canvas>
      <div class="bg-grid"></div>
      <div class="bg-orb bg-orb-1"></div>
      <div class="bg-orb bg-orb-2"></div>
      <div class="bg-orb bg-orb-3"></div>
      <div class="bg-scanline"></div>
    </div>

    <nav class="navbar glass-nav" v-if="route.path !== '/login'">
      <router-link to="/" class="navbar-logo">
        <div class="navbar-logo-icon">CR</div>
        <div>
          <div class="navbar-logo-text">CYBER RANGE</div>
          <div class="navbar-logo-sub">智能攻防靶场</div>
        </div>
      </router-link>

      <div class="navbar-center">
        <router-link
          v-for="link in visibleNavLinks"
          :key="link.path"
          :to="link.path"
          class="nav-item glass-item"
          :class="{ active: route.path === link.path }"
        >
          <el-icon><component :is="link.icon" /></el-icon>
          {{ link.name }}
        </router-link>
      </div>

      <div class="navbar-right">
        <span class="navbar-time">{{ currentTime }}</span>
        <div class="navbar-status glass-status">
          <span class="status-dot" :class="{ offline: !backendOnline }"></span>
          <span>{{ backendOnline ? '在线' : '离线' }}</span>
        </div>
        <router-link v-if="!user" to="/login" class="navbar-user glass-btn">
          <el-icon><User /></el-icon> 登录
        </router-link>
        <el-popover v-else trigger="click" placement="bottom" :width="180">
          <template #reference>
            <div class="navbar-user glass-btn"><el-icon><User /></el-icon> {{ user.username }}</div>
          </template>
          <div style="padding: 6px 0;">
            <div style="font-weight: 600; color: var(--purple);">{{ user.username }}</div>
            <div style="font-size: 11px; color: var(--text-muted);">{{ user.role || '用户' }}</div>
            <el-divider style="margin: 10px 0;" />
            <el-button size="small" type="danger" plain style="width: 100%;" @click="logout">退出登录</el-button>
          </div>
        </el-popover>
      </div>
    </nav>

    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <keep-alive :max="8">
            <component :is="Component" />
          </keep-alive>
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { User } from '@element-plus/icons-vue'
import { navLinks } from './router/index.js'
import axios from 'axios'

const route = useRoute()
const router = useRouter()

const user = ref(null)
const isAdmin = computed(() => user.value?.role === 'admin')
const visibleNavLinks = computed(() =>
  navLinks.filter(link => !link.adminOnly || isAdmin.value)
)
const currentTime = ref('')
const backendOnline = ref(false)
const bgCanvas = ref(null)
let timeInterval = null
let bgAnimId = null

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

async function checkBackend() {
  try {
    const res = await axios.get('/api/health', { timeout: 3000 })
    backendOnline.value = res && res.data && res.data.status === 'ok'
  } catch (e) {
    backendOnline.value = false
  }
}

function checkLogin() {
  const stored = localStorage.getItem('cyber_user')
  if (stored) {
    try { user.value = JSON.parse(stored) } catch { user.value = null }
  }
}

function logout() {
  localStorage.removeItem('cyber_user')
  user.value = null
  router.push('/login')
}

// 背景动画
function initBgAnimation() {
  const canvas = bgCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight

  const particles = []
  for (let i = 0; i < 80; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      size: Math.random() * 2 + 1,
      hue: Math.random() > 0.5 ? 270 : 190
    })
  }

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    particles.forEach(p => {
      p.x += p.vx
      p.y += p.vy
      if (p.x < 0 || p.x > canvas.width) p.vx *= -1
      if (p.y < 0 || p.y > canvas.height) p.vy *= -1

      const color = p.hue === 270 ? 'rgba(139,44,230,0.6)' : 'rgba(0,229,255,0.6)'
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
      ctx.fillStyle = color
      ctx.shadowBlur = 10
      ctx.shadowColor = color
      ctx.fill()
    })
    bgAnimId = requestAnimationFrame(animate)
  }
  animate()
}

function handleResize() {
  if (bgCanvas.value) {
    bgCanvas.value.width = window.innerWidth
    bgCanvas.value.height = window.innerHeight
  }
}

onMounted(() => {
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
  checkLogin()
  checkBackend()
  setInterval(checkBackend, 15000)
  initBgAnimation()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
  if (bgAnimId) cancelAnimationFrame(bgAnimId)
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
/* 全局动态背景 */
.global-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}

.bg-canvas {
  position: absolute;
  inset: 0;
  opacity: 0.4;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(139, 44, 230, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(139, 44, 230, 0.06) 1px, transparent 1px);
  background-size: 60px 60px;
  animation: grid-move 20s linear infinite;
}

@keyframes grid-move {
  from { background-position: 0 0; }
  to { background-position: 60px 60px; }
}

.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.3;
  animation: orb-float 18s ease-in-out infinite;
}

.bg-orb-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(139, 44, 230, 0.5), transparent 70%);
  top: -200px;
  right: -150px;
}

.bg-orb-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(0, 229, 255, 0.4), transparent 70%);
  bottom: -150px;
  left: -100px;
  animation-delay: -6s;
}

.bg-orb-3 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(180, 100, 255, 0.3), transparent 70%);
  top: 40%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: -12s;
}

@keyframes orb-float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(50px, -40px) scale(1.1); }
  66% { transform: translate(-30px, 50px) scale(0.95); }
}

.bg-scanline {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.3), rgba(139, 44, 230, 0.3), transparent);
  animation: scan 10s linear infinite;
}

@keyframes scan {
  0% { top: -2px; opacity: 0; }
  5% { opacity: 1; }
  95% { opacity: 1; }
  100% { top: 100%; opacity: 0; }
}

/* 玻璃质感导航栏 */
.glass-nav {
  background: rgba(8, 10, 20, 0.75) !important;
  backdrop-filter: blur(24px) saturate(1.5);
  border-bottom: 1px solid rgba(139, 44, 230, 0.2);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.glass-item {
  background: transparent;
  border: 1px solid transparent;
  transition: all 0.25s ease;
}

.glass-item:hover {
  background: rgba(139, 44, 230, 0.1);
  border-color: rgba(139, 44, 230, 0.2);
}

.glass-item.active {
  background: rgba(0, 229, 255, 0.1);
  border-color: rgba(0, 229, 255, 0.3);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
}

.glass-status {
  background: rgba(8, 10, 20, 0.6);
  border: 1px solid rgba(139, 44, 230, 0.2);
  border-radius: 20px;
  padding: 4px 12px;
  backdrop-filter: blur(10px);
}

.glass-btn {
  background: rgba(139, 44, 230, 0.1);
  border: 1px solid rgba(139, 44, 230, 0.3);
  backdrop-filter: blur(10px);
  transition: all 0.25s ease;
}

.glass-btn:hover {
  background: rgba(139, 44, 230, 0.2);
  border-color: rgba(139, 44, 230, 0.5);
  box-shadow: 0 0 20px rgba(139, 44, 230, 0.3);
}
</style>
