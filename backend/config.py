# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件
load_dotenv()

# 获取backend目录路径
BACKEND_DIR = Path(__file__).parent

# 数据库配置 - 使用SQLite
DB_CONFIG = {
    'type': 'sqlite',
    'path': os.getenv('DB_PATH', str(BACKEND_DIR / 'data' / 'ai_security_range.db')),
    # MySQL配置（备用）
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_DATABASE', 'ai_security_range'),
}

# 日志配置
LOG_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'file_path': os.getenv('LOG_FILE', 'logs/system.log'),
    'max_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5
}

# Docker配置
DOCKER_CONFIG = {
    'base_image': os.getenv('DOCKER_BASE_IMAGE', 'nginx'),
    'container_prefix': os.getenv('DOCKER_PREFIX', 'cyber_range_'),
    'port_range_start': 8080,
    'port_range_end': 8999
}

# AI配置（DeepSeek）
AI_CONFIG = {
    'api_key': os.getenv('DEEPSEEK_API_KEY', ''),
    'model': os.getenv('AI_MODEL', 'deepseek-chat'),
    'max_tokens': int(os.getenv('AI_MAX_TOKENS', 1024)),
    'temperature': float(os.getenv('AI_TEMPERATURE', 0.7))
}

# 异步队列配置
ASYNC_CONFIG = {
    'max_queue_size': int(os.getenv('ASYNC_QUEUE_SIZE', 100)),
    'worker_count': int(os.getenv('ASYNC_WORKERS', 4)),
    'timeout': int(os.getenv('ASYNC_TIMEOUT', 30))
}

# Watchdog配置
WATCHDOG_CONFIG = {
    'watch_paths': [
        os.getenv('WATCHDOG_PATH_1', '/var/log/docker'),
        os.getenv('WATCHDOG_PATH_2', 'logs')
    ],
    'file_patterns': ['*.log', '*.txt'],
    'recursive': True,
    'ignore_patterns': ['*.pyc', '__pycache__', '.git']
}

# 安全配置
SECURITY_CONFIG = {
    'secret_key': os.getenv('SECRET_KEY', 'bb1dbf7f91a3c5cb43da2e2092e4627db420dbac185108213682a194df9d581'),
    'token_expire': int(os.getenv('TOKEN_EXPIRE', 3600)),
    'password_hash': os.getenv('PASSWORD_HASH', 'pbkdf2:sha256:260000')
}