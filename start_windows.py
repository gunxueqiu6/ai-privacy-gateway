"""
Windows 启动脚本 - 双击运行 + 自动打开管理页 + 托盘图标
"""
import os
import sys
import time
import threading
import webbrowser
import subprocess
import logging

# 托盘图标（需要 pystray）
try:
    from pystray import Icon, Menu, MenuItem
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


def create_icon_image():
    """创建托盘图标"""
    # 创建一个简单的图标
    width = 64
    height = 64
    color1 = (0, 128, 255)  # 蓝色
    color2 = (255, 255, 255)  # 白色

    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 16, 48, 48), fill=color2)
    dc.text((20, 24), "AI", fill=color1)

    return image


def open_admin_page():
    """打开管理后台"""
    time.sleep(2)  # 等待服务启动
    webbrowser.open('http://localhost:9999/admin')


def start_server():
    """启动服务器"""
    os.environ['LISTEN_PORT'] = '9999'

    # 启动 main.py
    proc = subprocess.Popen([sys.executable, 'main.py'])
    _active_processes.append(proc)
    return proc


# 活跃子进程列表
_active_processes = []


def _monitor_process(proc):
    """监控子进程，退出时记录日志"""
    try:
        exit_code = proc.wait()
        logger = logging.getLogger(__name__)
        if exit_code != 0:
            logger.error(f"主服务进程异常退出，退出码: {exit_code}")
            print(f"\n!!! 主服务进程异常退出，退出码: {exit_code} !!!\n")
        else:
            logger.info("主服务进程正常退出")
    except Exception as e:
        logging.getLogger(__name__).error(f"监控子进程时发生异常: {e}")


def quit_app(icon=None):
    """退出应用"""
    if icon:
        icon.stop()
    sys.exit(0)


def run_tray_icon():
    """运行托盘图标"""
    if not HAS_TRAY:
        print("pystray 未安装，无托盘图标")
        return

    icon_image = create_icon_image()

    menu = Menu(
        MenuItem('打开管理后台', lambda: webbrowser.open('http://localhost:9999/admin')),
        MenuItem('查看状态', lambda: webbrowser.open('http://localhost:9999/')),
        MenuItem('退出', quit_app)
    )

    icon = Icon("AI Privacy Gateway", icon_image, "AI Privacy Gateway", menu)
    icon.run()


def main():
    """主入口"""
    print("=" * 50)
    print("AI Privacy Gateway - Lite 个人版")
    print("=" * 50)
    print()
    print("正在启动服务...")
    print("API 地址: http://localhost:9999")
    print("管理后台: http://localhost:9999/admin")
    print()
    print("将你的 AI 客户端 API 地址改为 http://localhost:9999")
    print()

    # 启动服务器并监控子进程
    proc = start_server()
    threading.Thread(target=_monitor_process, args=(proc,), daemon=True).start()

    # 自动打开管理页
    threading.Thread(target=open_admin_page, daemon=True).start()

    # 运行托盘图标
    if HAS_TRAY:
        run_tray_icon()
    else:
        # 无托盘时，保持运行
        print("按 Ctrl+C 退出")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("正在退出...")
            sys.exit(0)


if __name__ == "__main__":
    main()