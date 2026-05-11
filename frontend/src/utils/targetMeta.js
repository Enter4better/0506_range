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
  'webgoat/webgoat': {
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

/** 根据镜像名称获取元数据，未命中返回 null */
export function getTargetMeta(image) {
  if (!image) return null
  return COMPREHENSIVE_TARGETS[image] || null
}

/** 端口建议映射（创建靶场时自动填充） */
export const IMAGE_PORT_HINTS = {
  'vulnerables/web-dvwa': '80:80',
  'webgoat/webgoat':      '8080:8080',
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
