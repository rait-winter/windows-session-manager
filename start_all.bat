@echo off
echo ===== Windows会话管理器启动脚本 =====
echo.

echo 正在启动WebSocket标签页服务器...
start "WebSocket标签页服务器" cmd /c "python start_tabs_server.py --port 8765"

echo 等待服务器启动...
timeout /t 3 > nul

echo 正在检查服务器状态...
python test_server_status.py

echo.
echo WebSocket服务器已启动，现在可以启动会话管理器了
echo 按任意键继续...
pause > nul

echo 正在启动会话管理器...
start "Windows会话管理器" python main.py

echo.
echo 所有服务已启动，可以关闭此窗口
echo 按任意键退出...
pause > nul 