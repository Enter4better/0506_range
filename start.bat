@echo off
chcp 65001 >nul
echo ========================================
echo   AI攻防靶场管理系统 - 启动脚本
echo ========================================
echo.

:: 设置Python路径
:: 优先使用 PATH 中的 python，若不存在则用默认路径
where python >nul 2>&1 && (set PYTHON_PATH=python) || (set PYTHON_PATH=C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe)

echo [1/3] 检查Python环境...
%PYTHON_PATH% --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python未找到，请确认已将 Python 加入 PATH 或修改脚本中的 PYTHON_PATH
    pause
    exit /b 1
)
echo [OK] Python环境正常

echo.
echo [2/3] 启动后端服务...
cd backend
start "Backend - AI攻防靶场" cmd /k "%PYTHON_PATH% run.py"
cd ..
echo [OK] 后端服务启动中...

echo.
echo [3/3] 启动前端服务...
cd frontend
start "Frontend - AI攻防靶场" cmd /k "npm run dev"
cd ..
echo [OK] 前端服务启动中...

echo.
timeout /t 3 /nobreak >nul
echo ========================================
echo   服务启动完成!
echo ========================================
echo   前端地址: http://localhost:3000
echo   后端地址: http://localhost:5000
echo   默认账户: admin / 123456  （user / 123456）
echo ========================================
echo.
echo 按任意键打开浏览器访问系统...
pause >nul
start http://localhost:3000