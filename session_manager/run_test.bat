@echo off
chcp 65001 > nul
echo 开始运行session_manager测试...
echo.

echo 测试browser_tabs.py模块...
python -m test_browser_tabs
echo.

echo 测试整个项目功能...
python -m test_all
echo.

echo 测试完成!
pause 