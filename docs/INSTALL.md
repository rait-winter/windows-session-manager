# 安装说明（INSTALL.md）

## 环境要求
- Windows 10 或更高版本
- Python 3.7 及以上

## 依赖包说明
- pygetwindow
- pyinstaller（可选，打包用）
- tkinter（Python自带）
- 其它依赖见 requirements.txt

## 安装依赖
在命令行中运行：

```bash
pip install -r requirements.txt
```

如需打包为独立 exe：
```bash
pip install pyinstaller
```

## 运行程序

```bash
python get_windows.py
```

## 打包为可执行文件

```bash
pyinstaller -F -w get_windows.py -n SessionManager
```

> 打包后请将 resources 目录下的 config.json、图标等资源文件一并复制到 dist 目录。

## 常见安装问题
- pip 安装慢：可使用国内镜像源，如 `-i https://pypi.tuna.tsinghua.edu.cn/simple`
- 权限不足：请用管理员权限运行命令行。
- 缺少 tkinter：部分精简 Python 发行版需手动安装 tkinter。

## 目录结构建议
请参考项目根目录下的 README.md。 