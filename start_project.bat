@echo off
echo ===== 启动Windows会话管理器 =====
echo.
echo 功能说明：
echo 1. 已优化会话恢复功能，只恢复不存在的浏览器和应用程序
echo 2. 自动跳过已存在的浏览器和应用程序，避免重复打开
echo.

REM 启动WebSocket标签页服务器
echo 正在启动WebSocket标签页服务器...
start "WebSocket标签页服务器" cmd /c "python start_tabs_server.py --port 8765"

echo 等待服务器启动...
timeout /t 3 > nul

echo 正在检查服务器状态...
python test_server_status.py

echo.
echo 正在启动主程序...
python get_windows.py

echo.
echo 程序已退出，按任意键关闭此窗口...
pause > nul 