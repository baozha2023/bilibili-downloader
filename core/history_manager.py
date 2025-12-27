# -*- coding: utf-8 -*-
import json
import os
import time

class HistoryManager:
    """管理下载历史"""
    
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.history_file = os.path.join(data_dir, "download_history.json")
        self.history = self._load_history()
        
    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存下载历史失败: {e}")

    def add_history(self, bvid, title, status):
        history_item = {
            "bvid": bvid,
            "title": title,
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "status": status
        }
        self.history.insert(0, history_item)
        if len(self.history) > 100:
            self.history = self.history[:100]
        self.save_history()

    def clear_history(self):
        self.history = []
        self.save_history()
        
    def get_history(self):
        return self.history
