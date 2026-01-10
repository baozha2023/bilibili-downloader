import os
import json
import logging

logger = logging.getLogger('bilibili_core')

APP_VERSION = 'v5.7.3'

class ConfigManager:
    _instance = None
    
    DEFAULT_CONFIG = {
       "max_retries": 3,
       "merge_video": True,
       "delete_original": True,
       "download_danmaku": False,
       "download_comments": False,
       "complete_action": 1,
       "video_quality": "1080P 高清",
       "video_codec": "H.264/AVC",
       "audio_quality": "高音质 (Hi-Res/Dolby)",
       "always_lock_account": False,
       "hardware_acceleration": True,
       "tab_order": [
         "视频下载",
         "合集下载",
         "热门视频",
         "视频分析",
         "我的账号",
         "视频编辑",
         "设置",
         "用户查询"
       ],
       "tab_visibility": {
         "设置": True,
         "视频编辑": True,
         "我的账号": True,
         "热门视频": True,
         "合集下载": True,
         "视频分析": True,
         "视频下载": True,
         "用户查询": True
       },
       "timeout": 30,
       "retry_interval": 2,
       "floating_window": True
    }

    def __new__(cls, data_dir=None):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.init(data_dir)
        return cls._instance

    def init(self, data_dir):
        # Default to bilibili_data if not provided to avoid creating config in root
        self.data_dir = data_dir or os.path.join(os.getcwd(), 'bilibili_data')
        self.config_dir = os.path.join(self.data_dir, 'config')
        self.config_path = os.path.join(self.config_dir, 'settings.json')
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
                    # Update data_dir if present
                    if 'data_dir' in loaded:
                        self.data_dir = loaded['data_dir']
            except Exception as e:
                logger.error(f"Failed to load config: {e}")

    def save(self):
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)
            
            # Ensure data_dir is saved
            self.config['data_dir'] = self.data_dir
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value

    def update(self, new_config):
        self.config.update(new_config)
