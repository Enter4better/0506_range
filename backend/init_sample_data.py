#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化示例数据脚本
为新系统创建一些演示数据
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# 添加backend目录到路径
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.database import db_service

def init_sample_data():
    """初始化示例数据"""
    print("=" * 60)
    print("AI攻防靶场 - 示例数据初始化")
    print("=" * 60)
    
    # 确保数据库已初始化
    db_service.init_database()
    print("\n[1/5] 数据库连接成功")
    
    # 获取默认用户ID（admin）
    connection = db_service.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT user_id, username FROM users WHERE username = ?", ('admin',))
    user = cursor.fetchone()
    if not user:
        print("未找到admin用户，请先启动系统并登录一次")
        return False
    user_id = user['user_id']
    username = user['username']
    cursor.close()
    connection.close()
    print(f"[2/5] 使用用户: {username} (ID: {user_id})")
    
    # 1. 创建示例靶场环境
    print("\n[3/5] 创建靶场环境...")
    
    # 检查是否已有靶场
    connection = db_service.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM targets")
    target_count = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    
    if target_count > 0:
        print(f"   已存在 {target_count} 个靶场环境，跳过创建")
    else:
        target_templates = [
            {
                'name': 'DVWA靶场',
                'type': 'container',
                'ip': '127.0.0.1',
                'port': 8080,
                'os': 'Linux',
                'status': 'offline'
            },
            {
                'name': 'Metasploit测试环境',
                'type': 'container',
                'ip': '127.0.0.1',
                'port': 8081,
                'os': 'Linux',
                'status': 'offline'
            },
            {
                'name': 'WordPress漏洞环境',
                'type': 'vm',
                'ip': '127.0.0.1',
                'port': 8082,
                'os': 'Linux',
                'status': 'offline'
            }
        ]
        
        connection = db_service.get_connection()
        cursor = connection.cursor()
        for template in target_templates:
            cursor.execute("""
                INSERT INTO targets (name, type, ip, port, os, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template['name'],
                template['type'],
                template['ip'],
                template['port'],
                template['os'],
                template['status'],
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            print(f"   创建靶场环境: {template['name']}")
        connection.commit()
        cursor.close()
        connection.close()
    
    # 2. 创建示例防御规则
    print("\n[4/5] 创建防御规则...")
    
    # 检查是否已有防御规则
    connection = db_service.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM defenses")
    defense_count = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    
    if defense_count > 0:
        print(f"   已存在 {defense_count} 个防御规则，跳过创建")
    else:
        defense_templates = [
            {
                'name': 'SQL注入防护',
                'defense_type': 'WAF',
                'description': '检测并阻止SQL注入攻击，使用正则表达式匹配恶意SQL语句',
                'coverage': 92
            },
            {
                'name': 'XSS攻击拦截',
                'defense_type': 'WAF',
                'description': '检测并阻止跨站脚本攻击，过滤恶意JavaScript代码',
                'coverage': 88
            },
            {
                'name': 'CSRF防护',
                'defense_type': 'WAF',
                'description': '防止跨站请求伪造，验证请求来源的合法性',
                'coverage': 85
            },
            {
                'name': '端口扫描检测',
                'defense_type': 'IDS',
                'description': '检测端口扫描行为，识别潜在的攻击者',
                'coverage': 95
            },
            {
                'name': '暴力破解阻断',
                'defense_type': 'IPS',
                'description': '阻止暴力破解攻击，限制登录尝试次数',
                'coverage': 78
            },
            {
                'name': '防火墙规则',
                'defense_type': 'Firewall',
                'description': '控制网络流量，阻止未授权的访问',
                'coverage': 90
            },
            {
                'name': '文件上传检测',
                'defense_type': 'WAF',
                'description': '检测并阻止恶意文件上传，验证文件类型和内容',
                'coverage': 86
            },
            {
                'name': '命令注入防护',
                'defense_type': 'IPS',
                'description': '检测并阻止命令注入攻击，过滤系统命令执行',
                'coverage': 82
            },
            {
                'name': 'SSRF防护',
                'defense_type': 'WAF',
                'description': '防止服务端请求伪造，限制内网请求',
                'coverage': 80
            },
            {
                'name': '路径遍历检测',
                'defense_type': 'IDS',
                'description': '检测目录遍历攻击，监控异常文件访问模式',
                'coverage': 88
            },
            {
                'name': '反序列化防护',
                'defense_type': 'WAF',
                'description': '检测并阻止反序列化攻击，过滤恶意序列化数据',
                'coverage': 75
            },
            {
                'name': '容器逃逸检测',
                'defense_type': 'EDR',
                'description': '检测容器逃逸行为，监控容器内异常系统调用',
                'coverage': 70
            },
            {
                'name': '横向移动检测',
                'defense_type': 'IDS',
                'description': '检测内网横向移动行为，识别异常网络连接',
                'coverage': 76
            },
            {
                'name': '权限提升防护',
                'defense_type': 'EDR',
                'description': '检测并阻止权限提升攻击，监控特权操作',
                'coverage': 72
            },
            {
                'name': '数据泄露防护',
                'defense_type': 'DLP',
                'description': '防止敏感数据外泄，监控出站流量中的敏感信息',
                'coverage': 68
            },
            {
                'name': '蜜罐诱捕系统',
                'defense_type': 'Honeypot',
                'description': '部署蜜罐诱捕攻击者，收集攻击手法和工具信息',
                'coverage': 60
            },
            {
                'name': '身份认证审计',
                'defense_type': 'IAM',
                'description': '审计用户身份认证行为，检测异常登录和权限滥用',
                'coverage': 84
            },
            {
                'name': '漏洞扫描预警',
                'defense_type': 'Vulnerability Scanner',
                'description': '定期扫描系统漏洞，及时发现并预警安全风险',
                'coverage': 90
            },
            {
                'name': 'SIEM日志分析',
                'defense_type': 'SIEM',
                'description': '集中分析安全日志，关联多源告警发现高级威胁',
                'coverage': 74
            },
            {
                'name': '网络准入控制',
                'defense_type': 'NAC',
                'description': '控制设备接入网络，确保终端符合安全基线',
                'coverage': 66
            }
        ]
        
        connection = db_service.get_connection()
        cursor = connection.cursor()
        for template in defense_templates:
            cursor.execute("""
                INSERT INTO defenses (name, defense_type, description, enabled, coverage, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                template['name'],
                template['defense_type'],
                template['description'],
                1,  # enabled
                template['coverage'],
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            print(f"   创建防御规则: {template['name']}")
        connection.commit()
        cursor.close()
        connection.close()
        
        # 为防御创建日志
        connection = db_service.get_connection()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO logs (level, source, message, user_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'success',
            'defense',
            '初始化防御规则模板',
            user_id,
            datetime.now().isoformat()
        ))
        connection.commit()
        cursor.close()
        connection.close()
    
    # 3. 创建示例日志
    print("\n[5/5] 创建示例日志...")
    
    # 检查是否已有日志
    connection = db_service.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM logs")
    log_count = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    
    if log_count > 10:
        print(f"   已存在 {log_count} 条日志，跳过创建")
    else:
        # 生成过去7天的日志
        log_templates = [
            {'level': 'success', 'source': 'system', 'message': '系统启动成功'},
            {'level': 'info', 'source': 'auth', 'message': '用户登录成功'},
            {'level': 'info', 'source': 'defense', 'message': '防御规则已启用'},
            {'level': 'warning', 'source': 'attack', 'message': '检测到可疑活动'},
            {'level': 'success', 'source': 'defense', 'message': '成功阻断攻击尝试'},
            {'level': 'info', 'source': 'target', 'message': '靶场环境检查完成'},
            {'level': 'success', 'source': 'system', 'message': '数据库连接正常'},
            {'level': 'info', 'source': 'ai', 'message': 'AI分析任务完成'},
        ]
        
        # 生成50条日志，分布在过去7天
        base_time = datetime.now() - timedelta(days=7)
        connection = db_service.get_connection()
        cursor = connection.cursor()
        
        for i in range(50):
            # 随机选择日志模板
            template = random.choice(log_templates)
            
            # 随机时间（过去7天内）
            random_seconds = random.randint(0, 7 * 24 * 3600)
            log_time = base_time + timedelta(seconds=random_seconds)
            
            cursor.execute("""
                INSERT INTO logs (level, source, message, user_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                template['level'],
                template['source'],
                template['message'],
                user_id,
                log_time.isoformat()
            ))
        
        connection.commit()
        cursor.close()
        connection.close()
        print(f"   创建了 50 条示例日志")
    
    print("\n" + "=" * 60)
    print("示例数据初始化完成！")
    print("=" * 60)
    print("\n现在可以刷新浏览器查看：")
    print("  - 防御规则面板：已创建6个示例防御规则")
    print("  - 日志面板：已创建50条示例日志")
    print("  - 靶场环境：需要先启动Docker并手动创建")
    print("\n提示：靶场环境需要Docker支持，请确保Docker Desktop已启动")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    try:
        init_sample_data()
    except Exception as e:
        print(f"\n初始化失败: {e}")
        import traceback
        traceback.print_exc()