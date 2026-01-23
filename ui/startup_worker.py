from PyQt5.QtCore import QThread, pyqtSignal
import time
import logging

# 延迟导入，避免在主线程加载过重
# from core.crawler import BilibiliCrawler
# from core.version_manager import VersionManager
# from core.config import ConfigManager

class StartupWorker(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        
    def run(self):
        context = {}
        
        try:
            # 1. 加载核心模块 (10-30%)
            self.progress_signal.emit(10, "正在加载核心模块...")
            from core.crawler import BilibiliCrawler
            from core.version_manager import VersionManager
            from core.config import ConfigManager
            import os
            import json
            
            time.sleep(0.1)
            
            # 2. 初始化配置和爬虫 (30-50%)
            self.progress_signal.emit(30, "初始化配置...")
            config_manager = ConfigManager()
            crawler = BilibiliCrawler()
            context['crawler'] = crawler
            context['config_manager'] = config_manager
            
            # 3. 检查登录状态 (50-70%)
            self.progress_signal.emit(50, "检查登录状态...")
            
            # 尝试读取本地 cookies
            login_info = {"is_login": False, "data": None}
            try:
                config_file = os.path.join(crawler.data_dir, "config", "login_config.json")
                if os.path.exists(config_file):
                    from core.utils import decrypt_data
                    
                    with open(config_file, 'r', encoding='utf-8') as f:
                        saved_data = json.load(f)
                    
                    config = None
                    if isinstance(saved_data, dict) and "data" in saved_data:
                        decrypted_str = decrypt_data(saved_data["data"])
                        if decrypted_str:
                            config = json.loads(decrypted_str)
                    
                    if config:
                        cookies = config.get("cookies", {})
                        if cookies and "SESSDATA" in cookies:
                            # 验证登录
                            crawler.cookies = cookies
                            nav_info = crawler.api.get_nav_info()
                            if nav_info and nav_info.get('code') == 0 and nav_info.get('data', {}).get('isLogin'):
                                # 登录成功
                                user_data = nav_info.get('data', {})
                                # 简单获取收藏夹和历史记录 (为了完整性)
                                try:
                                    fav_resp = crawler.api.get_fav_folder_list(user_data.get('mid'))
                                    user_data['favorites'] = fav_resp.get('data', {}).get('list', []) if fav_resp else []
                                except:
                                    user_data['favorites'] = []
                                
                                try:
                                    history_resp = crawler.api.get_history()
                                    user_data['history'] = history_resp if history_resp else []
                                except:
                                    user_data['history'] = []
                                
                                login_info = {
                                    "is_login": True, 
                                    "data": user_data,
                                    "cookies": cookies
                                }
            except Exception as e:
                logging.warning(f"Startup login check failed: {e}")
            
            context['login_info'] = login_info
            time.sleep(0.2)
            
            # 4. 检查版本更新 (70-90%)
            self.progress_signal.emit(70, "正在检查 Gitee 版本更新...")
            update_info = {"has_update": False, "version": None, "checked": False, "error": None}
            try:
                vm = VersionManager()
                # 限制超时，避免启动过久
                # 这里我们只获取列表，不阻塞太久
                # 在实际应用中，网络请求可能会慢，所以这是必要的异步步骤
                versions = vm.get_versions(source="gitee")
                if versions:
                    update_info["checked"] = True
                    latest = versions[0]
                    from core.config import APP_VERSION
                    # Use compare_versions to check if latest > current
                    if VersionManager.compare_versions(latest['tag'], APP_VERSION) > 0:
                        update_info["has_update"] = True
                        update_info["version"] = latest
                        self.progress_signal.emit(80, f"发现新版本: {latest['tag']}")
                    else:
                        self.progress_signal.emit(80, "当前已是最新版本")
                else:
                    update_info["error"] = "未获取到版本信息"
                    self.progress_signal.emit(80, "版本检测失败: 未获取到数据")
            except Exception as e:
                update_info["error"] = str(e)
                logging.warning(f"Startup update check failed: {e}")
                self.progress_signal.emit(80, "版本检测失败: 网络或其他错误")
                
            context['update_info'] = update_info
            time.sleep(0.5)  # 稍微停留以便用户看清状态

            
            # 5. 完成 (90-100%)
            self.progress_signal.emit(90, "准备启动界面...")
            time.sleep(0.2)
            self.progress_signal.emit(100, "加载完成")
            
        except Exception as e:
            logging.error(f"Startup error: {e}")
            context['error'] = str(e)
            
        self.finished_signal.emit(context)
