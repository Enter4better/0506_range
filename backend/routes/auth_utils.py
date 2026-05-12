# -*- coding: utf-8 -*-
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def require_admin(fn):
    """仅管理员可访问。包含 JWT 验证，无需再叠加 @jwt_required()。"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'status': 'error', 'msg': '需要管理员权限'}), 403
        return fn(*args, **kwargs)
    return wrapper
