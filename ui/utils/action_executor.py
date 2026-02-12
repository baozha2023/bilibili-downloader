import os
import re
from PyQt5.QtWidgets import QMessageBox
from ui.message_box import BilibiliMessageBox

class ActionExecutor:
    """
    负责执行下载完成后的操作
    """
    
    ACTION_NONE = 0
    ACTION_OPEN_FOLDER = 1
    ACTION_PLAY_VIDEO = 2
    ACTION_CLOSE_APP = 3
    ACTION_SHUTDOWN = 4
    
    @staticmethod
    def execute_completion_action(main_window, download_dir=None, merged_file=None):
        """
        执行下载完成后的操作
        :param main_window: 主窗口实例，用于访问设置和控制窗口
        :param download_dir: 下载目录（用于"打开文件夹"）
        :param merged_file: 合并后的文件路径（用于"播放视频"）
        """
        try:
            settings_tab = main_window.settings_tab
            action_index = settings_tab.complete_action.currentIndex()
            
            if action_index == ActionExecutor.ACTION_OPEN_FOLDER: # 打开文件夹
                if download_dir and os.path.exists(download_dir):
                    os.startfile(download_dir)
                else:
                    # 如果未提供具体目录，打开默认下载目录
                    base_dir = settings_tab.data_dir_input.text().strip()
                    if os.path.exists(base_dir):
                         os.startfile(base_dir)
                         
            elif action_index == ActionExecutor.ACTION_PLAY_VIDEO: # 播放视频
                if merged_file and os.path.exists(merged_file):
                    os.startfile(merged_file)
                # 批量下载场景下，通常忽略此选项或只播放最后一个，这里选择忽略或仅在有具体文件时播放
                    
            elif action_index == ActionExecutor.ACTION_CLOSE_APP: # 关闭程序
                main_window.close()
                
            elif action_index == ActionExecutor.ACTION_SHUTDOWN: # 关闭电脑
                import platform
                if platform.system() == "Windows":
                    os.system("shutdown /s /t 60")
                    BilibiliMessageBox.information(main_window, "提示", "电脑将在60秒后关机")
                else:
                    main_window.log_to_console("自动关机仅支持Windows系统", "warning")
                    
        except Exception as e:
            print(f"执行完成后操作失败: {e}")
            if hasattr(main_window, 'log_to_console'):
                main_window.log_to_console(f"执行完成后操作失败: {str(e)}", "error")
