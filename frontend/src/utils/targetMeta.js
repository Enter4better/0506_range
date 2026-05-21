/**
 * 综合漏洞靶场元数据 — 与 backend/agents/env_agent.py COMPREHENSIVE_TARGETS 保持同步
 * DVWA / WebGoat / bWAPP 是"刻意脆弱"的靶场，具有多种已知漏洞类型，
 * 与普通通用容器（ubuntu / nginx / mysql 等）有本质区别
 */
export const COMPREHENSIVE_TARGETS = {
  'vulnerables/web-dvwa': {
    label: 'DVWA综合靶场',
    short: 'DVWA',
    vulnTypes: ['SQL注入', 'XSS攻击', 'CSRF攻击', '文件包含', '命令执行', '暴力破解'],
    defaultPort: 80,
    difficulty: '低-中',
    owaspCoverage: 'OWASP Top 10',
    description: 'Damn Vulnerable Web Application — 经典 OWASP Top 10 多漏洞训练靶场',
    color: 'warning',
  },
  'webgoat/webgoat-8.0': {
    label: 'WebGoat综合靶场',
    short: 'WebGoat',
    vulnTypes: ['SQL注入', 'XSS攻击', 'CSRF攻击', 'XXE注入', 'SSRF攻击', '权限提升'],
    defaultPort: 8080,
    difficulty: '中',
    owaspCoverage: 'OWASP Top 10 + A06~A10',
    description: 'OWASP WebGoat — 面向开发者的教学型多漏洞靶场（默认端口 8080）',
    color: 'danger',
  },
  'bkimminich/juice-shop': {
    label: 'Juice Shop综合靶场',
    short: 'JuiceShop',
    vulnTypes: ['SQL注入', 'XSS攻击', 'CSRF攻击', 'XXE注入', 'SSRF攻击', '认证缺陷', '权限提升', '敏感数据泄露'],
    defaultPort: 3000,
    difficulty: '中-高',
    owaspCoverage: 'OWASP Top 10 全覆盖',
    description: 'OWASP Juice Shop — 现代全栈刻意脆弱应用，覆盖 OWASP Top 10 全部类别',
    color: 'danger',
  },
}

/** 根据镜像名称获取元数据，未命中返回 null（支持 Docker tag 后缀） */
export function getTargetMeta(image) {
  if (!image) return null
  // 精确匹配
  if (COMPREHENSIVE_TARGETS[image]) return COMPREHENSIVE_TARGETS[image]
  // 去掉 :tag 后缀后匹配（Docker 可能追加 :latest）
  const baseName = image.replace(/:[^:]+$/, '')
  return COMPREHENSIVE_TARGETS[baseName] || null
}

// ============================================================
// 沙箱攻击-靶场兼容性匹配
// ============================================================

/**
 * 沙箱模式支持的攻击类型（对应 backend sandbox_executor._ALIASES）
 * 不在该列表中的类型沙箱执行时会降级为仿真模式
 */
export const SANDBOX_ATTACK_TYPES = [
  '端口扫描', '服务识别', 'Web目录枚举',
  'SQL注入', 'XSS攻击', 'SSRF攻击',
  '暴力破解', '横向移动', '数据外传', '命令执行'
]

/**
 * 需要 HTTP 服务的攻击类型（沙箱模式下需要目标有 Web 服务）
 * 端口扫描、横向移动 不需要 HTTP，其余都需要
 */
const HTTP_DEPENDENT_ATTACKS = [
  'SQL注入', 'XSS攻击', 'SSRF攻击', 'Web目录枚举',
  '暴力破解', '数据外传', '命令执行', '服务识别',
  'CSRF攻击', '文件包含', 'XXE注入'  // 预留，虽暂无沙箱脚本但逻辑上需要 HTTP
]

/**
 * 有 Web 服务的镜像（沙箱模式下可响应 HTTP 请求）
 */
const WEB_SERVICE_IMAGES = [
  // 综合漏洞靶场
  'vulnerables/web-dvwa',
  'webgoat/webgoat-8.0',
  'bkimminich/juice-shop',
  // 基础 Web 服务
  'nginx:alpine',
  'httpd:alpine',
  'php:8.1-apache',
]

/**
 * 判断攻击类型是否需要 HTTP 服务
 */
export function attackNeedsHttp(attackType) {
  return HTTP_DEPENDENT_ATTACKS.includes(attackType)
}

/**
 * 判断靶场镜像是否有 Web 服务
 * Docker SDK 返回的 image 可能带 tag 后缀（如 vulnerables/web-dvwa:latest），
 * 需要做前缀匹配而非精确匹配
 */
export function targetHasWebService(image) {
  if (!image) return false
  // 精确匹配
  if (WEB_SERVICE_IMAGES.includes(image)) return true
  // 去掉 :tag 后缀后匹配（处理 Docker 自动追加的 :latest 等情况）
  const baseName = image.replace(/:[^:]+$/, '')
  if (WEB_SERVICE_IMAGES.includes(baseName)) return true
  // 反过来：如果镜像本身带 tag 但列表中的基础名是像 nginx:alpine 这样带 tag 的
  for (const ws of WEB_SERVICE_IMAGES) {
    if (image === ws || baseName === ws || image.startsWith(ws + ':')) return true
  }
  return false
}

/**
 * 判断沙箱模式下攻击类型与靶场是否兼容
 * @param {string} attackType 攻击类型（如 'XSS攻击'）
 * @param {string} targetImage 靶场镜像（如 'vulnerables/web-dvwa'）
 * @returns {{ compatible: boolean, reason: string }}
 */
export function isSandboxCompatible(attackType, targetImage) {
  // 未在沙箱支持列表中 → 会降级为仿真，理论上所有靶场都"兼容"（不会出错）
  if (!SANDBOX_ATTACK_TYPES.includes(attackType)) {
    return { compatible: true, reason: '该攻击类型沙箱暂不支持，将降级为仿真模式' }
  }
  // 不需要 HTTP 的攻击（端口扫描/横向移动）→ 任意靶场都可以
  if (!attackNeedsHttp(attackType)) {
    return { compatible: true, reason: '网络层攻击，无需 Web 服务' }
  }
  // 需要 HTTP 的攻击 → 必须有 Web 服务
  if (targetHasWebService(targetImage)) {
    return { compatible: true, reason: '靶场具备 Web 服务，兼容' }
  }
  return {
    compatible: false,
    reason: `"${attackType}" 需要 HTTP 服务，当前靶场无 Web 服务，请选择 Web 靶场`
  }
}

/**
 * 从靶场列表中筛选沙箱兼容的靶场
 * @param {Array} targets 靶场列表
 * @param {string} attackType 当前攻击类型
 * @returns {{ compatible: Array, incompatible: Array }}
 */
export function filterSandboxTargets(targets, attackType) {
  if (!attackType) return { compatible: targets, incompatible: [] }
  const compatible = []
  const incompatible = []
  for (const t of targets) {
    const result = isSandboxCompatible(attackType, t.image)
    if (result.compatible) {
      compatible.push(t)
    } else {
      incompatible.push(t)
    }
  }
  return { compatible, incompatible }
}

/** 端口建议映射（创建靶场时自动填充） */
export const IMAGE_PORT_HINTS = {
  'vulnerables/web-dvwa': '80:80',
  'webgoat/webgoat-8.0':      '8080:8080',
  'bkimminich/juice-shop': '3000:3000',
  'nginx:alpine':         '8080:80',
  'httpd:alpine':         '8080:80',
  'php:8.1-apache':       '8080:80',
  'mysql:8.0':            '3306:3306',
  'redis:alpine':         '6379:6379',
  'postgres:15-alpine':   '5432:5432',
  'ubuntu:22.04':         '2222:22',
  'python:3.11-slim':     '',
  'node:18-alpine':       '3000:3000',
  'alpine:latest':        '',
}

/**
 * 从靶场端口字符串提取主机端口（用于沙箱攻击端口匹配）
 * @param {string} ports 端口字符串，如 "80:80"、"8080:8080"、"0.0.0.0:80->80/tcp"
 * @returns {number|null} 主机端口数字，或 null（无端口映射，如纯内网容器）
 */
export function extractHostPort(ports) {
  if (!ports || ports === '-' || ports === '') return null
  const m = String(ports).match(/(?:0\.0\.0\.0:)?(\d+)/)
  return m ? parseInt(m[1], 10) : null
}

/**
 * 判断端口是否与靶场兼容（沙箱模式下，端口必须与靶场实际暴露的端口一致）
 * 端口扫描和横向移动不依赖具体端口，始终兼容
 * @param {number} port 攻击目标端口
 * @param {string} targetImage 靶场镜像
 * @param {string} targetPorts 靶场的 ports 字段（如 "80:80"）
 * @param {string} attackType 攻击类型（可选，用于判断是否端口无关的攻击）
 * @returns {{ compatible: boolean, reason: string }}
 */
export function isPortCompatible(port, targetImage, targetPorts, attackType = '') {
  if (!port || !targetImage) return { compatible: true, reason: '' }

  // 端口扫描 / 横向移动：端口无关，始终兼容
  const portIndependentAttacks = ['端口扫描', '横向移动']
  if (attackType && portIndependentAttacks.includes(attackType)) {
    return { compatible: true, reason: '' }
  }

  const hostPort = extractHostPort(targetPorts)

  // 无端口映射（纯内网容器，如 alpine）：只能做端口扫描/横向移动
  if (hostPort === null) {
    return {
      compatible: false,
      reason: `靶场 ${targetImage} 未暴露任何端口到主机，沙箱模式下仅支持"端口扫描"和"横向移动"攻击`
    }
  }

  if (port !== hostPort) {
    return {
      compatible: false,
      reason: `端口不匹配：靶场 ${targetImage} 暴露的是端口 ${hostPort}，而非 ${port}。沙箱将无法连接，已自动降级为仿真模式`
    }
  }

  return { compatible: true, reason: '' }
}
