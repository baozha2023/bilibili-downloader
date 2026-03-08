import os
import ctypes
import sys

# 防止 OpenMP / MKL 冲突（PyQt5 常见杀手）
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

def preload_torch_dlls():
    """预加载 Torch DLL 以避免在 Windows 上出现 ImportError"""
    torch_lib_path = None
    
    if getattr(sys, 'frozen', False):
        # 运行在 PyInstaller 打包环境中
        # 尝试从 _MEIPASS 或可执行文件目录寻找 torch/lib
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.argv[0])))
        possible_paths = [
            os.path.join(base_path, 'torch', 'lib'),
            os.path.join(base_path, 'torch'),
            os.path.join(base_path, 'lib'),
            base_path
        ]
        
        for p in possible_paths:
            if os.path.exists(os.path.join(p, 'torch_cpu.dll')) or os.path.exists(os.path.join(p, 'torch.dll')):
                torch_lib_path = p
                break
    else:
        # 开发环境：尝试动态获取 torch 路径
        try:
            import importlib.util
            spec = importlib.util.find_spec('torch')
            if spec and spec.submodule_search_locations:
                torch_root = spec.submodule_search_locations[0]
                torch_lib_path = os.path.join(torch_root, 'lib')
        except Exception as e:
            # 仅在找不到时回退到硬编码路径（如果确实需要）
            pass

    # 如果找到了路径，添加 DLL 目录并预加载
    if torch_lib_path and os.path.exists(torch_lib_path):
        try:
            if hasattr(os, 'add_dll_directory'):
                os.add_dll_directory(torch_lib_path)
                print(f"[INFO] Torch lib 已加入 DLL 搜索路径: {torch_lib_path}")
        except Exception as e:
            print(f"[WARN] 添加 DLL 目录失败: {e}")

        # 强制预加载核心 DLL（顺序很重要）
        dll_list = ["c10.dll", "torch_cpu.dll", "c10_cuda.dll", "torch_cuda.dll", "torch.dll"]
        for dll_name in dll_list:
            dll_full_path = os.path.join(torch_lib_path, dll_name)
            if os.path.exists(dll_full_path):
                try:
                    ctypes.CDLL(dll_full_path, mode=ctypes.RTLD_GLOBAL)
                    print(f"[INFO] 预加载成功: {dll_name}")
                except Exception as e:
                    print(f"[WARN] 预加载 {dll_name} 失败: {e}")

# 执行预加载
try:
    preload_torch_dlls()
except Exception as e:
    print(f"[ERROR] Torch DLL 预加载过程出错: {e}")
# =============================================================================
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bilibili_downloader')


def global_exception_handler(exctype, value, tb):
    logger.error("Uncaught exception", exc_info=(exctype, value, tb))
    import traceback
    traceback.print_exception(exctype, value, tb)


sys.excepthook = global_exception_handler


def start_gui():
    """启动图形用户界面"""
    # Imports for GUI
    import ctypes
    from PyQt5.QtWidgets import QApplication
    from ui.splash_screen import SplashScreen
    from ui.startup_worker import StartupWorker
    from core.config import APP_VERSION

    try:
        myappid = f'bilibili.downloader.gui.{APP_VERSION}'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        logger.warning(f"Failed to set AppUserModelID: {e}")

    app = QApplication(sys.argv)

    # 启动画面 / Splash Screen
    splash_img_path = "resource/logo.jpg"

    # PyInstaller path handling
    if hasattr(sys, '_MEIPASS'):
        splash_img_path = os.path.join(sys._MEIPASS, "resource", "logo.jpg")
    elif not os.path.exists(splash_img_path):
        # 如果 logo.jpg 不存在，尝试 png
        splash_img_path = "resource/logo.png"
        if hasattr(sys, '_MEIPASS'):
            splash_img_path = os.path.join(sys._MEIPASS, "resource", "logo.png")

    splash = SplashScreen(splash_img_path, APP_VERSION)
    splash.show()

    # 启动后台任务
    worker = StartupWorker()

    def on_startup_finished(context):
        try:
            # Main window module is likely already imported in worker
            from ui.main_window import BilibiliDesktop
            window = BilibiliDesktop(context=context)
            window.show()
            splash.close()
        except Exception as e:
            logger.error(f"Failed to start main window: {e}")
            sys.exit(1)

    worker.progress_signal.connect(splash.set_progress)
    worker.finished_signal.connect(on_startup_finished)
    worker.start()

    sys.exit(app.exec_())


def start_cli(args):
    """启动命令行界面"""
    from core.cli import CliHandler
    cli = CliHandler()
    cli.handle_args(args)


def main():
    """主函数"""
    # 检查是否为 LaMa 处理器模式 (用于多进程调用)
    # Check for LaMa processor mode (for multiprocessing)
    if len(sys.argv) > 1 and sys.argv[1] == '--lama-processor':
        try:
            from core.lama_processor import main as lama_main
            # 传递剩余参数 (去除 exe 和 --lama-processor)
            lama_main(sys.argv[2:])
        except Exception as e:
            print(f"Error starting lama processor: {e}")
            sys.exit(1)
        return

    import argparse
    try:
        from core.config import APP_VERSION
    except ImportError:
        APP_VERSION = "Unknown"

    parser = argparse.ArgumentParser(description=f'bilibiliDownloader {APP_VERSION}')
    parser.add_argument('-g', '--gui', action='store_true',
                        help='启动图形用户界面')
    parser.add_argument('-p', '--popular', action='store_true',
                        help='爬取热门视频')
    parser.add_argument('-v', '--video', type=str,
                        help='爬取指定BV号视频的详细信息')
    parser.add_argument('-d', '--download', type=str,
                        help='下载指定BV号的视频')
    parser.add_argument('--pages', type=int,
                        help='指定爬取的页数，用于热门视频')
    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {APP_VERSION}')

    parser.add_argument('--player-mode', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--player-url', help=argparse.SUPPRESS)
    parser.add_argument('--player-title', help=argparse.SUPPRESS)
    parser.add_argument('--player-cookies', help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args.player_mode:
        try:
            from core.player_loader import run_player
            run_player(args.player_url, args.player_title, args.player_cookies)
        except Exception as e:
            logger.error(f"Failed to start player: {e}")
        return

    if args.gui or len(sys.argv) == 1:
        start_gui()
    else:
        start_cli(args)


if __name__ == "__main__":
    main()
