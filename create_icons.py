#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建Windows会话管理器的图标文件
"""

import os
from PIL import Image, ImageDraw, ImageFont

ICONS_DIR = 'resources'
os.makedirs(ICONS_DIR, exist_ok=True)

def create_icon(size, color='#2271b3'):
    """创建简单的图标"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制四个窗口的图标
    margin = size // 10
    window_size = (size - 3 * margin) // 2
    
    # 四个窗口位置
    positions = [
        (margin, margin),
        (margin * 2 + window_size, margin),
        (margin, margin * 2 + window_size),
        (margin * 2 + window_size, margin * 2 + window_size)
    ]
    
    # 窗口颜色
    colors = [
        '#4285F4',  # 蓝色
        '#34A853',  # 绿色
        '#FBBC05',  # 黄色
        '#EA4335'   # 红色
    ]
    
    # 绘制窗口
    for i, (x, y) in enumerate(positions):
        # 窗口背景
        draw.rectangle(
            [x, y, x + window_size, y + window_size],
            fill=colors[i]
        )
        
        # 窗口顶部栏
        bar_height = window_size // 5
        draw.rectangle(
            [x, y, x + window_size, y + bar_height],
            fill='#FFFFFF33'
        )
        
        # 窗口控制按钮
        btn_size = bar_height // 2
        btn_margin = btn_size // 2
        btn_y = y + (bar_height - btn_size) // 2
        
        # 绘制关闭按钮
        draw.ellipse(
            [x + window_size - btn_margin - btn_size, btn_y, 
             x + window_size - btn_margin, btn_y + btn_size],
            fill='#FFFFFF66'
        )
    
    return img

def create_all_icons():
    """创建各种尺寸的图标"""
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = []
    
    for size in sizes:
        icon = create_icon(size)
        icon_path = os.path.join(ICONS_DIR, f'icon_{size}.png')
        icon.save(icon_path)
        icons.append((size, icon))
        print(f"已创建 {size}x{size} 图标")
    
    # 创建ICO文件
    # 使用第一个图标尺寸作为基础，保存多尺寸ICO
    icons[0][1].save(
        os.path.join(ICONS_DIR, 'icon.ico'),
        format='ICO', 
        sizes=[(size, size) for size, _ in icons]
    )
    print("已创建 ICO 文件")

if __name__ == "__main__":
    create_all_icons()
    print(f"所有图标已保存到 {os.path.abspath(ICONS_DIR)} 目录") 