#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
启动WebSocket标签页服务器的脚本
"""

import os
import sys
import asyncio
import argparse
import logging
import json
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("start_tabs_server")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='启动WebSocket标签页服务器')
    parser.add_argument('--host', default='127.0.0.1', help='WebSocket服务器主机地址')
    parser.add_argument('--port', type=int, default=8765, help='WebSocket服务器端口')
    parser.add_argument('--data-dir', help='数据存储目录')
    parser.add_argument('--config', help='配置文件路径')
    return parser.parse_args()

def load_config(config_path=None):
    """加载配置文件"""
    config = {}
    
    # 默认配置文件路径
    if not config_path:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                 "session_manager", "config.json")
    
    # 尝试加载配置文件
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"已从 {config_path} 加载配置")
    except Exception as e:
        logger.error(f"加载配置文件时出错: {e}")
    
    return config

async def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 加载配置
    config = load_config(args.config)
    
    # 更新WebSocket配置
    if "websocket" not in config:
        config["websocket"] = {}
    
    config["websocket"]["host"] = args.host
    config["websocket"]["port"] = args.port
    config["websocket"]["enabled"] = True
    config["websocket"]["auto_start"] = True
    
    if args.data_dir:
        config["data_dir"] = args.data_dir
    
    # 导入模块
    try:
        from session_manager.hybrid_tabs.websocket_server import start_server
        
        # 启动WebSocket服务器
        logger.info(f"正在启动WebSocket服务器，监听 {args.host}:{args.port}")
        await start_server(host=args.host, port=args.port)
    except ImportError:
        logger.error("无法导入WebSocket服务器模块，请确保安装了所有依赖")
        sys.exit(1)
    except Exception as e:
        logger.error(f"启动WebSocket服务器时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在退出...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"运行WebSocket服务器时出错: {e}")
        sys.exit(1) 