#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
构建Windows会话管理器可执行文件的脚本
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# 版本号
VERSION = "1.0.0"
APP_NAME = "WindowsSessionManager"

def clean_build_dir():
    """清理构建目录"""
    print("清理构建目录...")
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    for file in Path('.').glob('*.spec'):
        file.unlink()

def run_pyinstaller():
    """运行PyInstaller构建可执行文件"""
    print("构建可执行文件...")
    
    # 确保PyInstaller已安装
    try:
        import PyInstaller
    except ImportError:
        print("正在安装PyInstaller...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
    
    # 图标路径
    icon_path = os.path.join('resources', 'icon.ico')
    if not os.path.exists(icon_path):
        print("警告：图标文件不存在，将使用默认图标")
        icon_path = None
    
    # 构建命令
    cmd = [
        'pyinstaller',
        '--name', APP_NAME,
        '--onefile',
        '--windowed',
        '--clean',
    ]
    
    if icon_path:
        cmd.extend(['--icon', icon_path])
    
    # 添加数据文件
    cmd.extend([
        '--add-data', f'resources{os.pathsep}resources',
    ])
    
    # 主脚本
    cmd.append('get_windows.py')
    
    # 执行构建
    subprocess.check_call(cmd)

def create_installer():
    """创建NSIS安装程序（可选，需要NSIS）"""
    # 此函数可以用来创建Windows安装程序
    # 需要安装NSIS并配置环境变量
    pass

def create_zip_package():
    """创建便携版ZIP包"""
    print("创建ZIP包...")
    import zipfile
    
    output_dir = 'dist'
    zip_name = f"{APP_NAME}-{VERSION}-portable.zip"
    zip_path = os.path.join(output_dir, zip_name)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 添加主程序
        exe_path = os.path.join(output_dir, f"{APP_NAME}.exe")
        zipf.write(exe_path, os.path.basename(exe_path))
        
        # 添加自述文件
        if os.path.exists('README.md'):
            zipf.write('README.md', 'README.md')
        
        # 添加变更日志
        if os.path.exists('CHANGELOG.md'):
            zipf.write('CHANGELOG.md', 'CHANGELOG.md')
        
        # 添加许可证
        if os.path.exists('LICENSE'):
            zipf.write('LICENSE', 'LICENSE')
    
    print(f"便携版打包完成: {zip_path}")

def main():
    """主函数"""
    print(f"开始构建 {APP_NAME} v{VERSION}...")
    
    clean_build_dir()
    run_pyinstaller()
    create_zip_package()
    
    print("构建完成!")

if __name__ == "__main__":
    main() 