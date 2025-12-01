import os
import json
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QCheckBox, QGroupBox, QComboBox, QSpinBox, 
                             QGridLayout, QFileDialog)
from ui.message_box import BilibiliMessageBox
from PyQt5.QtCore import Qt

logger = logging.getLogger('bilibili_desktop')

class SettingsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.crawler = main_window.crawler
        self.init_ui()
        self.load_config_from_file()
        
    def init_ui(self):
        # 使用主垂直布局，增加边距和间距
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # --- 1. 基本设置分组 ---
        basic_group = QGroupBox("基本设置")
        basic_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 28px; 
                margin-top: 12px; 
            } 
            QGroupBox::title { 
                subcontrol-origin: margin; 
                subcontrol-position: top left; 
                padding: 0 5px; 
            }
            QLabel, QLineEdit, QSpinBox, QCheckBox, QComboBox {
                font-size: 24px;
            }
        """)
        basic_layout = QGridLayout(basic_group)
        basic_layout.setVerticalSpacing(15)
        basic_layout.setHorizontalSpacing(15)
        basic_layout.setContentsMargins(20, 25, 20, 20)
        
        # 数据存储目录
        basic_layout.addWidget(QLabel("数据存储目录:"), 0, 0)
        self.data_dir_input = QLineEdit(os.path.abspath(self.crawler.data_dir))
        self.data_dir_input.setMinimumWidth(400)
        basic_layout.addWidget(self.data_dir_input, 0, 1)
        browse_btn = QPushButton("浏览...")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self.browse_data_dir)
        basic_layout.addWidget(browse_btn, 0, 2)

        # 最大重试次数
        basic_layout.addWidget(QLabel("最大重试次数:"), 1, 0)
        self.retry_count = QSpinBox()
        self.retry_count.setRange(1, 10)
        self.retry_count.setValue(3)
        self.retry_count.setFixedWidth(100)
        basic_layout.addWidget(self.retry_count, 1, 1)
        
        main_layout.addWidget(basic_group)
        
        # --- 2. 下载设置分组 ---
        download_group = QGroupBox("下载设置")
        download_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 28px; 
                margin-top: 12px; 
            } 
            QGroupBox::title { 
                subcontrol-origin: margin; 
                subcontrol-position: top left; 
                padding: 0 5px; 
            }
            QLabel, QCheckBox, QComboBox {
                font-size: 24px;
            }
        """)
        download_layout = QGridLayout(download_group)
        download_layout.setVerticalSpacing(15)
        download_layout.setHorizontalSpacing(15)
        download_layout.setContentsMargins(20, 25, 20, 20)
        
        # 画质选择
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("首选画质:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["720p", "480p", "360p"])
        self.quality_combo.setCurrentText("720p")
        self.quality_combo.setFixedWidth(200)
        quality_layout.addWidget(self.quality_combo)
        tips_label = QLabel("（登录解锁1080P/4K）")
        tips_label.setStyleSheet("color: #888;")
        quality_layout.addWidget(tips_label)
        quality_layout.addStretch()
        download_layout.addLayout(quality_layout, 0, 0, 1, 3)

        # 复选框选项 - 使用网格布局排列
        # 第一行复选框
        self.merge_check = QCheckBox("合并视频和音频")
        self.merge_check.setChecked(True)
        self.merge_check.setToolTip("推荐勾选，否则视频和音频将分离开")
        download_layout.addWidget(self.merge_check, 1, 0, 1, 3)
        
        self.delete_original_check = QCheckBox("合并后删除原始文件")
        self.delete_original_check.setChecked(True)
        download_layout.addWidget(self.delete_original_check, 2, 0, 1, 3)

        # 第二行复选框
        self.remove_watermark_check = QCheckBox("尝试去除水印 (实验性)")
        self.remove_watermark_check.setChecked(False)
        download_layout.addWidget(self.remove_watermark_check, 3, 0, 1, 3)
        
        # 额外下载选项
        extra_container = QHBoxLayout()
        self.download_danmaku_check = QCheckBox("下载弹幕")
        extra_container.addWidget(self.download_danmaku_check)
        
        self.download_comments_check = QCheckBox("下载评论")
        extra_container.addWidget(self.download_comments_check)
        extra_container.addStretch()
        
        download_layout.addLayout(extra_container, 4, 0, 1, 3)
        
        # 下载完成后操作
        complete_layout = QHBoxLayout()
        complete_layout.addWidget(QLabel("下载完成后:"))
        self.complete_action = QComboBox()
        self.complete_action.addItems(["无操作", "打开文件夹", "播放视频", "关闭程序"])
        self.complete_action.setCurrentIndex(1)
        self.complete_action.setFixedWidth(200)
        complete_layout.addWidget(self.complete_action)
        complete_layout.addStretch()
        download_layout.addLayout(complete_layout, 5, 0, 1, 3)
        
        main_layout.addWidget(download_group)
        
        # 底部保存按钮
        main_layout.addStretch()
        save_btn = QPushButton("保存设置")
        save_btn.setMinimumHeight(45)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                font-weight: bold; 
                font-size: 30px; 
                background-color: #fb7299; 
                color: white; 
                border-radius: 6px;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
            QPushButton:pressed {
                background-color: #e45c84;
            }
        """)
        save_btn.clicked.connect(self.save_settings)
        
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(save_btn)
        btn_container.addStretch()
        
        main_layout.addLayout(btn_container)
        main_layout.addSpacing(20)

    def browse_data_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择数据存储目录", os.path.abspath(self.crawler.data_dir))
        if dir_path:
            self.data_dir_input.setText(dir_path)

    def save_settings(self):
        new_data_dir = self.data_dir_input.text().strip()
        if new_data_dir and os.path.exists(new_data_dir):
            self.crawler.data_dir = new_data_dir
            self.crawler.download_dir = os.path.join(new_data_dir, 'downloads')
            if not os.path.exists(self.crawler.download_dir):
                os.makedirs(self.crawler.download_dir)
        
        # 移除代理设置的保存逻辑
        self.crawler.use_proxy = False
        self.crawler.proxies = {}
        
        self.save_config_to_file()
        BilibiliMessageBox.information(self, "设置保存", "设置已保存")

    def save_config_to_file(self):
        config = {
            'data_dir': self.data_dir_input.text().strip(),
            'max_retries': self.retry_count.value(),
            'merge_video': self.merge_check.isChecked(),
            'delete_original': self.delete_original_check.isChecked(),
            'remove_watermark': self.remove_watermark_check.isChecked(),
            'download_danmaku': self.download_danmaku_check.isChecked(),
            'download_comments': self.download_comments_check.isChecked(),
            'complete_action': self.complete_action.currentIndex(),
            'video_quality': self.quality_combo.currentText()
        }
        try:
            config_dir = os.path.join(self.crawler.data_dir, 'config')
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            config_path = os.path.join(config_dir, 'settings.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"配置已保存到 {config_path}")
        except Exception as e:
            logger.error(f"保存配置文件时出错: {e}")

    def load_config_from_file(self):
        config_path = os.path.join(self.crawler.data_dir, 'config', 'settings.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                if 'data_dir' in config and os.path.exists(config['data_dir']):
                    self.data_dir_input.setText(config['data_dir'])
                    self.crawler.data_dir = config['data_dir']
                    self.crawler.download_dir = os.path.join(config['data_dir'], 'downloads')
                if 'max_retries' in config:
                    self.retry_count.setValue(config['max_retries'])
                if 'merge_video' in config:
                    self.merge_check.setChecked(config['merge_video'])
                if 'delete_original' in config:
                    self.delete_original_check.setChecked(config['delete_original'])
                if 'remove_watermark' in config:
                    self.remove_watermark_check.setChecked(config['remove_watermark'])
                if 'download_danmaku' in config:
                    self.download_danmaku_check.setChecked(config['download_danmaku'])
                if 'download_comments' in config:
                    self.download_comments_check.setChecked(config['download_comments'])
                if 'complete_action' in config:
                    self.complete_action.setCurrentIndex(config['complete_action'])
                if 'video_quality' in config:
                    self.quality_combo.setCurrentText(config['video_quality'])
            except Exception as e:
                logger.error(f"加载配置文件时出错: {e}")
