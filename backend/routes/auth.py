# -*- coding: utf-8 -*-
"""
认证路由 - 用户注册、登录、权限管理
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import hashlib
import re
import sys
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.user import User
from services.database import db_service
from models.log import Log

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def validate_password(password: str) -> tuple:
    """验证密码强度"""
    if len(password) < 8:
        return False, "密码长度至少8位"
    if not re.search(r'[A-Z]', password):
        return False, "密码必须包含大写字母"
    if not re.search(r'[a-z]', password):
        return False, "密码必须包含小写字母"
    if not re.search(r'\d', password):
        return False, "密码必须包含数字"
    return True, "密码强度合格"

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['username', 'password', 'email']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'status': 'error', 'msg': f'{field} 是必填项'}), 400
        
        username = data['username'].strip()
        password = data['password']
        email = data['email'].strip()
        
        # 验证用户名格式
        if len(username) < 3 or len(username) > 20:
            return jsonify({'status': 'error', 'msg': '用户名长度必须在3-20位之间'}), 400
        
        # 验证密码强度
        is_valid, msg = validate_password(password)
        if not is_valid:
            return jsonify({'status': 'error', 'msg': msg}), 400
        
        # 验证邮箱格式
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({'status': 'error', 'msg': '邮箱格式不正确'}), 400
        
        # 检查用户名是否已存在
        if User.get_by_username(username):
            return jsonify({'status': 'error', 'msg': '用户名已存在'}), 400
        
        # 检查邮箱是否已存在
        if User.get_by_email(email):
            return jsonify({'status': 'error', 'msg': '邮箱已被注册'}), 400
        
        # 创建用户
        user = User.create(username, password, email, data.get('role', 'user'))
        if not user:
            return jsonify({'status': 'error', 'msg': '注册失败，请稍后重试'}), 500
        
        # 记录日志
        Log.create('info', 'auth', f'用户注册成功: {username}', user_id=user.user_id)
        
        return jsonify({
            'status': 'success',
            'msg': '注册成功',
            'user': {
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"注册失败: {e}")
        Log.create('danger', 'auth', f'用户注册异常: {str(e)}')
        return jsonify({'status': 'error', 'msg': '注册失败，请稍后重试'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('username') or not data.get('password'):
            return jsonify({'status': 'error', 'msg': '用户名和密码是必填项'}), 400
        
        username = data['username'].strip()
        password = data['password']
        
        # 查找用户
        user = User.get_by_username(username)
        if not user:
            Log.create('warning', 'auth', f'登录失败 - 用户不存在: {username}')
            return jsonify({'status': 'error', 'msg': '用户名或密码错误'}), 401
        
        # 验证密码
        if not user.check_password(password):
            Log.create('warning', 'auth', f'登录失败 - 密码错误: {username}')
            return jsonify({'status': 'error', 'msg': '用户名或密码错误'}), 401
        
        # 更新最后登录时间
        user.update_last_login()
        
        # 生成JWT令牌
        access_token = create_access_token(
            identity=user.user_id,
            additional_claims={
                'username': user.username,
                'role': user.role
            },
            expires_delta=timedelta(hours=24)
        )
        
        # 记录日志
        Log.create('success', 'auth', f'用户登录成功: {username}', user_id=user.user_id)
        
        return jsonify({
            'status': 'success',
            'msg': '登录成功',
            'token': access_token,
            'user': {
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'last_login': str(user.last_login) if user.last_login else None
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"登录失败: {e}")
        Log.create('danger', 'auth', f'用户登录异常: {str(e)}')
        return jsonify({'status': 'error', 'msg': '登录失败，请稍后重试'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """获取用户信息"""
    try:
        user_id = get_jwt_identity()
        user = User.get_by_id(user_id)
        
        if not user:
            return jsonify({'status': 'error', 'msg': '用户不存在'}), 404
        
        return jsonify({
            'status': 'success',
            'user': {
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'created_at': user.created_at.isoformat(),
                'last_login': str(user.last_login) if user.last_login else None
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取用户信息失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取用户信息失败'}), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """更新用户信息"""
    try:
        user_id = get_jwt_identity()
        user = User.get_by_id(user_id)
        
        if not user:
            return jsonify({'status': 'error', 'msg': '用户不存在'}), 404
        
        data = request.get_json()
        
        # 更新邮箱
        if 'email' in data:
            email = data['email'].strip()
            if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return jsonify({'status': 'error', 'msg': '邮箱格式不正确'}), 400
            user.email = email
        
        # 更新密码
        if 'password' in data:
            new_password = data['password']
            if not new_password:
                return jsonify({'status': 'error', 'msg': '密码不能为空'}), 400
            
            # 验证密码强度
            is_valid, msg = validate_password(new_password)
            if not is_valid:
                return jsonify({'status': 'error', 'msg': msg}), 400
            
            user.set_password(new_password)
        
        # 保存更新
        user.save()
        
        # 记录日志
        Log.create('info', 'auth', f'用户信息更新: {user.username}', user_id=user.user_id)
        
        return jsonify({
            'status': 'success',
            'msg': '更新成功',
            'user': {
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"更新用户信息失败: {e}")
        return jsonify({'status': 'error', 'msg': '更新用户信息失败'}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """用户登出"""
    try:
        user_id = get_jwt_identity()
        user = User.get_by_id(user_id)
        
        if user:
            Log.create('info', 'auth', f'用户登出: {user.username}', user_id=user.user_id)
        
        return jsonify({'status': 'success', 'msg': '登出成功'}), 200
        
    except Exception as e:
        current_app.logger.error(f"登出失败: {e}")
        return jsonify({'status': 'error', 'msg': '登出失败'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """修改密码"""
    try:
        user_id = get_jwt_identity()
        user = User.get_by_id(user_id)
        
        if not user:
            return jsonify({'status': 'error', 'msg': '用户不存在'}), 404
        
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('old_password') or not data.get('new_password'):
            return jsonify({'status': 'error', 'msg': '原密码和新密码是必填项'}), 400
        
        old_password = data['old_password']
        new_password = data['new_password']
        
        # 验证原密码
        if not user.check_password(old_password):
            Log.create('warning', 'auth', f'密码修改失败 - 原密码错误: {user.username}', user_id=user.user_id)
            return jsonify({'status': 'error', 'msg': '原密码错误'}), 400
        
        # 验证新密码强度
        is_valid, msg = validate_password(new_password)
        if not is_valid:
            return jsonify({'status': 'error', 'msg': msg}), 400
        
        # 更新密码
        user.set_password(new_password)
        user.save()
        
        # 记录日志
        Log.create('info', 'auth', f'密码修改成功: {user.username}', user_id=user.user_id)
        
        return jsonify({'status': 'success', 'msg': '密码修改成功'}), 200
        
    except Exception as e:
        current_app.logger.error(f"修改密码失败: {e}")
        Log.create('danger', 'auth', f'密码修改异常: {str(e)}')
        return jsonify({'status': 'error', 'msg': '修改密码失败'}), 500

@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    """获取用户列表（管理员功能）"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.get_by_id(current_user_id)
        
        if not current_user or current_user.role != 'admin':
            return jsonify({'status': 'error', 'msg': '权限不足'}), 403
        
        # 获取所有用户
        users = User.list_all()
        
        return jsonify({
            'status': 'success',
            'users': [u.to_dict() for u in users]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取用户列表失败: {e}")
        return jsonify({'status': 'error', 'msg': '获取用户列表失败'}), 500