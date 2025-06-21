#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebSocket服务器适配器 - 用于接收浏览器扩展发送的标签页数据
"""

import asyncio
import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime

import websockets

logger = logging.getLogger(__name__)

# 存储所有连接的客户端
connected_clients = set()
# 存储最新的标签页数据
latest_tabs_data = {}
# 服务器实例
server_instance = None
# 服务器状态
server_status = {
    "running": False,
    "start_time": None,
    "host": "127.0.0.1",
    "port": 8765,
    "client_count": 0,
    "last_message_time": None
}

async def handle_client(websocket, path):
    """处理WebSocket客户端连接"""
    client_id = f"client_{len(connected_clients) + 1}"
    logger.info(f"客户端 {client_id} 已连接")
    
    # 添加到连接集合
    connected_clients.add(websocket)
    server_status["client_count"] = len(connected_clients)
    
    try:
        # 发送欢迎消息
        await websocket.send(json.dumps({
            "type": "welcome",
            "message": "已连接到Windows会话管理器标签页监控服务器",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        }))
        
        # 处理来自客户端的消息
        async for message in websocket:
            try:
                data = json.loads(message)
                logger.debug(f"收到来自 {client_id} 的消息: {data['type'] if 'type' in data else 'unknown'}")
                server_status["last_message_time"] = datetime.now().isoformat()
                
                # 处理不同类型的消息
                if data.get("type") == "tabs":
                    # 处理标签页数据
                    browser_id = data.get("browser_id", "unknown")
                    window_id = data.get("window_id", "unknown")
                    tabs = data.get("tabs", [])
                    
                    # 更新存储的标签页数据
                    if browser_id not in latest_tabs_data:
                        latest_tabs_data[browser_id] = {}
                    
                    latest_tabs_data[browser_id][window_id] = {
                        "tabs": tabs,
                        "timestamp": datetime.now().isoformat(),
                        "client_id": client_id
                    }
                    
                    logger.debug(f"已更新 {browser_id} 的 {len(tabs)} 个标签页")
                    
                    # 发送确认消息
                    await websocket.send(json.dumps({
                        "type": "tabs_received",
                        "count": len(tabs),
                        "timestamp": datetime.now().isoformat()
                    }))
                    
                elif data.get("type") == "heartbeat":
                    # 处理心跳消息
                    await websocket.send(json.dumps({
                        "type": "heartbeat_ack",
                        "timestamp": datetime.now().isoformat()
                    }))
                    
                else:
                    # 处理未知类型的消息
                    logger.warning(f"收到未知类型的消息: {data}")
                    
            except json.JSONDecodeError:
                logger.error(f"无法解析JSON消息: {message}")
            except Exception as e:
                logger.error(f"处理消息时出错: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"客户端 {client_id} 连接已关闭")
    except Exception as e:
        logger.error(f"处理客户端 {client_id} 时出错: {e}")
    finally:
        # 从连接集合中移除
        connected_clients.remove(websocket)
        server_status["client_count"] = len(connected_clients)
        logger.info(f"客户端 {client_id} 已断开连接")

def get_latest_tabs():
    """获取最新的标签页数据"""
    return latest_tabs_data

def get_server_status():
    """获取服务器状态"""
    return server_status

async def broadcast_message(message):
    """向所有连接的客户端广播消息"""
    if connected_clients:
        await asyncio.gather(
            *[client.send(json.dumps(message)) for client in connected_clients]
        )

async def start_server(host='127.0.0.1', port=8765):
    """启动WebSocket服务器"""
    global server_instance, server_status
    
    server_instance = await websockets.serve(handle_client, host, port)
    server_status["running"] = True
    server_status["start_time"] = datetime.now().isoformat()
    server_status["host"] = host
    server_status["port"] = port
    
    logger.info(f"WebSocket服务器已启动，监听 {host}:{port}")
    
    # 设置信号处理
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
        except NotImplementedError:
            # Windows不支持add_signal_handler
            pass
    
    await server_instance.wait_closed()

async def shutdown():
    """关闭服务器"""
    global server_instance, server_status
    
    if server_instance:
        logger.info("正在关闭WebSocket服务器...")
        server_instance.close()
        await server_instance.wait_closed()
        server_instance = None
        server_status["running"] = False
        logger.info("WebSocket服务器已关闭")

def run_server_in_thread(host='127.0.0.1', port=8765):
    """在后台线程中运行WebSocket服务器"""
    def _run_server():
        try:
            asyncio.run(start_server(host, port))
        except Exception as e:
            logger.error(f"运行WebSocket服务器时出错: {e}")
    
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()
    
    # 等待服务器启动
    for _ in range(10):  # 最多等待5秒
        if server_status["running"]:
            logger.info(f"WebSocket服务器已在后台启动 ({host}:{port})")
            return True
        time.sleep(0.5)
    
    logger.warning("WebSocket服务器可能未能正常启动")
    return server_status["running"]

def stop_server():
    """停止WebSocket服务器"""
    if not server_status["running"]:
        return
    
    try:
        # 创建一个新的事件循环来运行关闭任务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(shutdown())
        loop.close()
    except Exception as e:
        logger.error(f"停止WebSocket服务器时出错: {e}") 