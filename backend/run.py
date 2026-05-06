from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import os
import logging
from datetime import timedelta
from dotenv import load_dotenv


# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """创建Flask应用"""
    # 设置静态文件目录为前端构建后的dist目录
    static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
    app = Flask(__name__, static_folder=static_folder, static_url_path='')
    
    # 配置
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'cyber-range-secret-key-2024')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-2024')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    
    # 启用CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # 初始化JWT
    jwt = JWTManager(app)
    
    # JWT错误处理
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'status': 'error',
            'msg': '令牌已过期，请重新登录'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'status': 'error',
            'msg': '无效的令牌'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'status': 'error',
            'msg': '缺少认证令牌'
        }), 401
    
    # 注册所有路由蓝图
    from routes import all_blueprints
    for bp in all_blueprints:
        app.register_blueprint(bp)
        logger.info(f"注册路由蓝图: {bp.name}")
    
    # 前端入口路由
    @app.route('/')
    def index():
        """前端入口页面"""
        return app.send_static_file('index.html')
    
    # 健康检查接口
    @app.route('/api/health')
    def health_check():
        """健康检查接口"""
        from services.database import db_service
        db_status = 'connected' if db_service.test_connection() else 'disconnected'
        return jsonify({
            'status': 'ok',
            'database': db_status,
            'mode': 'production',
            'timestamp': __import__('datetime').datetime.now().isoformat()
        })
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        """处理404错误 - 对于非API路径返回前端index.html"""
        from flask import request
        path = request.path
        if not path.startswith('/api/'):
            return app.send_static_file('index.html')
        return jsonify({
            'status': 'error',
            'msg': '接口不存在'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"内部服务器错误: {error}")
        return jsonify({
            'status': 'error',
            'msg': '内部服务器错误'
        }), 500
    
    # 请求日志
    @app.before_request
    def before_request():
        from flask import request
        logger.info(f"请求: {request.method} {request.path}")
    
    return app


# 创建应用实例
app = create_app()


if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("AI攻防靶场管理系统 - 后端服务启动")
    logger.info("=" * 50)
    logger.info("服务地址: http://localhost:5000")
    
    # ========== 初始化所有服务 ==========
    
    # 1. 初始化数据库
    try:
        from services.database import db_service
        if db_service.init_database():
            logger.info("✅ 数据库初始化完成")
        else:
            logger.warning("⚠️ 数据库初始化失败，请检查配置")
    except Exception as e:
        logger.warning(f"⚠️ 数据库初始化异常: {e}")
    
    # 2. 初始化异步队列服务
    try:
        from services.async_queue import async_queue_service
        async_queue_service.start()
        logger.info("✅ 异步队列服务启动")
    except Exception as e:
        logger.warning(f"⚠️ 异步队列服务启动失败: {e}")
    
    # 3. 初始化监控服务 (Watchdog)
    try:
        from services.watchdog import init_watchdog
        init_watchdog()
        logger.info("✅ 监控服务启动")
    except Exception as e:
        logger.warning(f"⚠️ 监控服务启动失败: {e}")
    
    # 4. 初始化 AI Agent 模块
    try:
        from agents import get_env_agent, get_attack_agent, get_defense_agent
        get_env_agent()
        get_attack_agent()
        get_defense_agent()
        logger.info("✅ AI Agent 模块初始化完成")
    except Exception as e:
        logger.warning(f"⚠️ AI Agent 初始化失败: {e}")
    
    logger.info("=" * 50)
    
    # 启动 Flask 应用
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )