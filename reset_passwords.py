#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重置默认账号密码脚本（纯标准库，无需 werkzeug）
用法：在项目根目录运行  python reset_passwords.py
"""
import hashlib
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / 'backend' / 'data' / 'ai_security_range.db'

ACCOUNTS = [
    ('admin', '123456', 'admin@example.com', 'admin'),
    ('user',  '123456', 'user@example.com',  'user'),
]

def make_pbkdf2_hash(password: str, salt: str, iterations: int = 260000) -> str:
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), iterations)
    return f'pbkdf2:sha256:{iterations}${salt}${dk.hex()}'

def main():
    if not DB_PATH.exists():
        print(f'[ERROR] 数据库不存在: {DB_PATH}')
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for username, password, email, role in ACCOUNTS:
        salt = f'CyberRange{username}2026'
        hashed = make_pbkdf2_hash(password, salt)

        cur.execute('SELECT user_id FROM users WHERE username = ?', (username,))
        row = cur.fetchone()
        if row:
            cur.execute(
                'UPDATE users SET password = ?, role = ? WHERE username = ?',
                (hashed, role, username)
            )
            print(f'[OK] {username} 密码已重置为 {password}')
        else:
            cur.execute(
                'INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)',
                (username, hashed, email, role)
            )
            print(f'[OK] {username} 账号已创建，密码 {password}')

    conn.commit()
    conn.close()
    print('\n完成！请重启后端后使用以下账号登录：')
    print('  admin / 123456  （管理员）')
    print('  user  / 123456  （普通用户）')

if __name__ == '__main__':
    main()
