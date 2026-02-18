import os
import json
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QCheckBox, QComboBox, QSpinBox, 
                             QGridLayout, QFileDialog, QScrollArea, QFrame,
                             QDialog, QTextBrowser)
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import Qt, QUrl
import sys
import re
from ui.message_box import BilibiliMessageBox
from ui.widgets.card_widget import CardWidget
from PyQt5.QtCore import Qt

logger = logging.getLogger('bilibili_desktop')

from ui.widgets.custom_combobox import NoScrollComboBox
from ui.about_module import AboutDialog
from ui.version_dialog import VersionDialog
from core.version_manager import VersionManager
from core.constants import VideoQuality, VideoCodec, AudioQuality

class SettingsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.crawler = main_window.crawler
        self.init_ui()
        self.load_config_from_file()
        
    def init_ui(self):
        # 主布局使用垂直布局，包含滚动区域
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #ffffff;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #ccc;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # 滚动内容容器
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #ffffff;")
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(25)
        self.content_layout.setContentsMargins(30, 30, 30, 30)
        
        # --- 1. 基本设置卡片 ---
        basic_card = CardWidget("基本设置")
        basic_layout = QGridLayout()
        basic_layout.setVerticalSpacing(20)
        basic_layout.setHorizontalSpacing(15)
        
        # 数据存储目录
        dir_label = QLabel("数据存储目录:")
        dir_label.setStyleSheet("font-size: 20px; color: #555;")
        basic_layout.addWidget(dir_label, 0, 0)
        
        self.data_dir_input = QLineEdit(os.path.abspath(self.crawler.data_dir))
        self.data_dir_input.setMinimumWidth(400)
        self.data_dir_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 19px;
                background-color: #fafafa;
            }
            QLineEdit:focus {
                border-color: #fb7299;
                background-color: white;
            }
        """)
        basic_layout.addWidget(self.data_dir_input, 0, 1)
        
        browse_btn = QPushButton("浏览")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                padding: 8px 20px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 6px;
                color: #555;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #ccc;
                color: #fb7299;
            }
        """)
        browse_btn.clicked.connect(self.browse_data_dir)
        basic_layout.addWidget(browse_btn, 0, 2)

        # 最大重试次数
        retry_label = QLabel("最大重试次数:")
        retry_label.setStyleSheet("font-size: 20px; color: #555;")
        basic_layout.addWidget(retry_label, 1, 0)
        
        self.retry_count = QSpinBox()
        self.retry_count.setRange(1, 10)
        self.retry_count.setValue(3)
        self.retry_count.setFixedWidth(120)
        self.retry_count.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 19px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
            }
        """)
        basic_layout.addWidget(self.retry_count, 1, 1)

        # 超时时间 (秒)
        timeout_label = QLabel("超时时间 (秒):")
        timeout_label.setStyleSheet("font-size: 20px; color: #555;")
        basic_layout.addWidget(timeout_label, 2, 0)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setFixedWidth(120)
        self.timeout_spin.setStyleSheet(self.retry_count.styleSheet())
        basic_layout.addWidget(self.timeout_spin, 2, 1)

        # 重试间隔 (秒)
        interval_label = QLabel("重试间隔 (秒):")
        interval_label.setStyleSheet("font-size: 20px; color: #555;")
        basic_layout.addWidget(interval_label, 3, 0)

        self.retry_interval_spin = QSpinBox()
        self.retry_interval_spin.setRange(1, 60)
        self.retry_interval_spin.setValue(2)
        self.retry_interval_spin.setFixedWidth(120)
        self.retry_interval_spin.setStyleSheet(self.retry_count.styleSheet())
        basic_layout.addWidget(self.retry_interval_spin, 3, 1)

        basic_card.add_layout(basic_layout)
        self.content_layout.addWidget(basic_card)
        
        # --- 2. 下载偏好卡片 ---
        pref_card = CardWidget("下载偏好")
        pref_layout = QGridLayout()
        pref_layout.setVerticalSpacing(20)
        pref_layout.setHorizontalSpacing(15)
        
        # 通用下拉框样式
        combo_style = """
            QComboBox {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 19px;
                background-color: #fafafa;
                min-width: 200px;
            }
            QComboBox:hover {
                border-color: #fb7299;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #666;
                margin-right: 10px;
            }
        """

        # 1. 视频编码
        codec_label = QLabel("优先视频编码:")
        codec_label.setStyleSheet("font-size: 20px; color: #555;")
        pref_layout.addWidget(codec_label, 0, 0)
        
        self.codec_combo = NoScrollComboBox()
        self.codec_combo.addItems([VideoCodec.AVC, VideoCodec.HEVC, VideoCodec.AV1])
        self.codec_combo.setCurrentText(VideoCodec.AVC)
        self.codec_combo.setStyleSheet(combo_style)
        pref_layout.addWidget(self.codec_combo, 0, 1)
        
        # 2. 视频画质
        quality_label = QLabel("优先视频画质:")
        quality_label.setStyleSheet("font-size: 20px; color: #555;")
        pref_layout.addWidget(quality_label, 1, 0)
        
        self.quality_combo = NoScrollComboBox()
        # 默认只显示非登录用户的画质选项，登录后会自动更新
        self.quality_combo.addItems([VideoQuality.Q_720P, VideoQuality.Q_480P, VideoQuality.Q_360P])
        self.quality_combo.setCurrentText(VideoQuality.Q_720P)
        self.quality_combo.setStyleSheet(combo_style)
        pref_layout.addWidget(self.quality_combo, 1, 1)
        
        # 3. 视频音质
        audio_label = QLabel("优先视频音质:")
        audio_label.setStyleSheet("font-size: 20px; color: #555;")
        pref_layout.addWidget(audio_label, 2, 0)
        
        self.audio_quality_combo = NoScrollComboBox()
        self.audio_quality_combo.addItems(AudioQuality.ALL_QUALITIES)
        self.audio_quality_combo.setCurrentText(AudioQuality.HI_RES)
        self.audio_quality_combo.setStyleSheet(combo_style)
        pref_layout.addWidget(self.audio_quality_combo, 2, 1)

        tips_label = QLabel("💡 提示：实际下载画质取决于视频源和账号权限，登录大会员可解锁最高画质")
        tips_label.setStyleSheet("color: #999; font-size: 18px; margin-top: 10px; font-style: italic;")
        pref_layout.addWidget(tips_label, 3, 0, 1, 2)
        
        pref_card.add_layout(pref_layout)
        self.content_layout.addWidget(pref_card)
        
        # --- 3. 下载选项卡片 ---
        download_card = CardWidget("下载选项")
        
        # 通用复选框样式
        checkbox_style = """
            QCheckBox {
                font-size: 20px;
                color: #555;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: white;
            }
            QCheckBox::indicator:checked {
                background-color: #fb7299;
                border-color: #fb7299;
                image: url(resource/check.png); /* 这里可以放一个勾选图标，或者用纯色 */
            }
            QCheckBox:hover {
                color: #333;
            }
        """
        
        # 复选框容器
        checkbox_layout = QGridLayout()
        checkbox_layout.setVerticalSpacing(15)
        checkbox_layout.setHorizontalSpacing(30)
        
        self.merge_check = QCheckBox("合并视频和音频")
        self.merge_check.setChecked(True)
        self.merge_check.setStyleSheet(checkbox_style)
        self.merge_check.setCursor(Qt.PointingHandCursor)
        checkbox_layout.addWidget(self.merge_check, 0, 0)
        
        self.delete_original_check = QCheckBox("合并后删除原始文件")
        self.delete_original_check.setChecked(True)
        self.delete_original_check.setStyleSheet(checkbox_style)
        self.delete_original_check.setCursor(Qt.PointingHandCursor)
        checkbox_layout.addWidget(self.delete_original_check, 0, 1)

        self.download_danmaku_check = QCheckBox("下载弹幕")
        self.download_danmaku_check.setStyleSheet(checkbox_style)
        self.download_danmaku_check.setCursor(Qt.PointingHandCursor)
        checkbox_layout.addWidget(self.download_danmaku_check, 1, 0)
        
        self.download_comments_check = QCheckBox("下载评论")
        self.download_comments_check.setStyleSheet(checkbox_style)
        self.download_comments_check.setCursor(Qt.PointingHandCursor)
        checkbox_layout.addWidget(self.download_comments_check, 1, 1)
        
        self.floating_window_check = QCheckBox("显示桌面悬浮窗")
        self.floating_window_check.setStyleSheet(checkbox_style)
        self.floating_window_check.setCursor(Qt.PointingHandCursor)
        self.floating_window_check.stateChanged.connect(self.toggle_floating_window)
        self.floating_window_check.setChecked(True) # 默认开启
        checkbox_layout.addWidget(self.floating_window_check, 2, 0)
        
        self.hardware_acceleration_check = QCheckBox("启用 NVIDIA 硬件加速 (NVDEC)")
        self.hardware_acceleration_check.setStyleSheet(checkbox_style)
        self.hardware_acceleration_check.setCursor(Qt.PointingHandCursor)
        self.hardware_acceleration_check.setToolTip("需要 NVIDIA 显卡支持，可加速视频处理")
        checkbox_layout.addWidget(self.hardware_acceleration_check, 2, 1)
        
        download_card.add_layout(checkbox_layout)
        
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #eee; margin: 15px 0;")
        download_card.add_widget(line)
        
        # 完成后操作
        action_layout = QHBoxLayout()
        action_label = QLabel("下载完成后:")
        action_label.setStyleSheet("font-size: 20px; color: #555;")
        action_layout.addWidget(action_label)
        
        self.complete_action = NoScrollComboBox()
        self.complete_action.addItems(["无操作", "打开文件夹", "播放视频", "关闭程序", "关闭电脑"])
        self.complete_action.setCurrentIndex(1)
        self.complete_action.setStyleSheet(combo_style)
        self.complete_action.setFixedWidth(200)
        action_layout.addWidget(self.complete_action)
        action_layout.addStretch()
        
        download_card.add_layout(action_layout)
        self.content_layout.addWidget(download_card)
        
        # --- 4. 隐私与安全卡片 ---
        privacy_card = CardWidget("隐私与安全")
        privacy_layout = QGridLayout()
        privacy_layout.setVerticalSpacing(20)
        
        self.always_lock_check = QCheckBox("每次进入'我的账号'都需要点击解锁")
        self.always_lock_check.setChecked(False) # 默认不开启
        self.always_lock_check.setStyleSheet(checkbox_style)
        self.always_lock_check.setCursor(Qt.PointingHandCursor)
        self.always_lock_check.setToolTip("开启后，每次切换到'我的账号'页面时，收藏夹和历史记录都会被隐藏，直到点击解锁")
        privacy_layout.addWidget(self.always_lock_check, 0, 0)
        
        privacy_card.add_layout(privacy_layout)
        self.content_layout.addWidget(privacy_card)
        
        self.content_layout.addStretch()
        
        # 设置滚动区域内容
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # 底部保存按钮栏
        bottom_bar = QWidget()
        bottom_bar.setStyleSheet("""
            QWidget {
                background-color: white;
                border-top: 1px solid #e0e0e0;
            }
        """)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(30, 15, 30, 15)
        
        status_label = QLabel("修改设置后请记得保存")
        status_label.setStyleSheet("color: #999; font-size: 14px;")
        bottom_layout.addWidget(status_label)
        
        bottom_layout.addStretch()
        
        # 作者声明按钮
        credits_btn = QPushButton("作者声明")
        credits_btn.setCursor(Qt.PointingHandCursor)
        credits_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                background-color: #f6f7f8;
                color: #666;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 10px 20px;
                margin-right: 15px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                color: #333;
            }
        """)
        credits_btn.clicked.connect(self.show_credits)
        bottom_layout.addWidget(credits_btn)
        
        # 版本管理按钮
        version_btn = QPushButton("版本管理")
        version_btn.setCursor(Qt.PointingHandCursor)
        version_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                background-color: #f6f7f8;
                color: #666;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 10px 20px;
                margin-right: 15px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                color: #333;
            }
        """)
        version_btn.clicked.connect(self.show_version_manager)
        bottom_layout.addWidget(version_btn)
        
        save_btn = QPushButton("保存设置")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                background-color: #fb7299;
                color: white;
                border-radius: 6px;
                padding: 10px 35px;
                border: none;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
            QPushButton:pressed {
                background-color: #e45c84;
            }
        """)
        save_btn.clicked.connect(self.save_settings)
        bottom_layout.addWidget(save_btn)
        
        main_layout.addWidget(bottom_bar)

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
        
        # Apply hardware acceleration setting immediately
        self.crawler.processor.set_hardware_acceleration(self.hardware_acceleration_check.isChecked())
        
        self.save_config_to_file()
        self.main_window.log_to_console("系统设置已保存", "success")
        BilibiliMessageBox.information(self, "设置保存", "设置已保存")

    def toggle_floating_window(self, state):
        visible = state == Qt.Checked
        if hasattr(self.main_window, 'floating_window'):
            self.main_window.floating_window.set_visibility(visible)

    def save_config_to_file(self):
        if not hasattr(self.main_window, 'config_manager'):
            return

        # Collect UI settings
        ui_config = {
            'data_dir': self.data_dir_input.text().strip(),
            'max_retries': self.retry_count.value(),
            'timeout': self.timeout_spin.value(),
            'retry_interval': self.retry_interval_spin.value(),
            'merge_video': self.merge_check.isChecked(),
            'delete_original': self.delete_original_check.isChecked(),
            'download_danmaku': self.download_danmaku_check.isChecked(),
            'download_comments': self.download_comments_check.isChecked(),
            'floating_window': self.floating_window_check.isChecked(),
            'complete_action': self.complete_action.currentIndex(),
            'video_quality': self.quality_combo.currentText(),
            'video_codec': self.codec_combo.currentText(),
            'audio_quality': self.audio_quality_combo.currentText(),
            'always_lock_account': self.always_lock_check.isChecked(),
            'hardware_acceleration': self.hardware_acceleration_check.isChecked()
        }
        
        try:
            # Update ConfigManager and save
            self.main_window.config_manager.update(ui_config)
            self.main_window.config_manager.save()
            
            config_path = self.main_window.config_manager.config_path
            logger.info(f"配置已保存到 {config_path}")
            self.main_window.log_to_console(f"配置文件已更新: {config_path}", "system")
        except Exception as e:
            logger.error(f"保存配置文件时出错: {e}")
            self.main_window.log_to_console(f"保存配置文件失败: {e}", "error")

    def load_config_from_file(self):
        if not hasattr(self.main_window, 'config_manager'):
            return

        config = self.main_window.config_manager.config
        
        try:
            if 'data_dir' in config and os.path.exists(config['data_dir']):
                self.data_dir_input.setText(config['data_dir'])
                self.crawler.data_dir = config['data_dir']
                self.crawler.download_dir = os.path.join(config['data_dir'], 'downloads')
            if 'max_retries' in config:
                self.retry_count.setValue(config['max_retries'])
            if 'timeout' in config:
                self.timeout_spin.setValue(config['timeout'])
            if 'retry_interval' in config:
                self.retry_interval_spin.setValue(config['retry_interval'])
            if 'merge_video' in config:
                self.merge_check.setChecked(config['merge_video'])
            if 'delete_original' in config:
                self.delete_original_check.setChecked(config['delete_original'])
            if 'download_danmaku' in config:
                self.download_danmaku_check.setChecked(config['download_danmaku'])
            if 'download_comments' in config:
                self.download_comments_check.setChecked(config['download_comments'])
            if 'floating_window' in config:
                self.floating_window_check.setChecked(config['floating_window'])
                # 触发状态更新
                self.toggle_floating_window(Qt.Checked if config['floating_window'] else Qt.Unchecked)
            if 'complete_action' in config:
                self.complete_action.setCurrentIndex(config['complete_action'])
            if 'video_quality' in config:
                self.quality_combo.setCurrentText(config['video_quality'])
            if 'video_codec' in config:
                self.codec_combo.setCurrentText(config['video_codec'])
            if 'audio_quality' in config:
                self.audio_quality_combo.setCurrentText(config['audio_quality'])
            if 'always_lock_account' in config:
                self.always_lock_check.setChecked(config['always_lock_account'])
            if 'hardware_acceleration' in config:
                self.hardware_acceleration_check.setChecked(config['hardware_acceleration'])
                self.crawler.processor.set_hardware_acceleration(config['hardware_acceleration'])
        except Exception as e:
            logger.error(f"加载配置文件时出错: {e}")

    def show_credits(self):
        """显示作者声明对话框"""
        dialog = AboutDialog(self)
        dialog.exec_()

    def show_version_manager(self):
        """显示版本管理对话框"""
        dialog = VersionDialog(self.main_window, self)
        dialog.exec_()

    def get_download_params(self):
        """获取当前下载参数配置"""
        return {
            "should_merge": self.merge_check.isChecked(),
            "delete_original": self.delete_original_check.isChecked(),
            "download_danmaku": self.download_danmaku_check.isChecked(),
            "download_comments": self.download_comments_check.isChecked(),
            "video_quality": self.quality_combo.currentText(),
            "video_codec": self.codec_combo.currentText(),
            "audio_quality": self.audio_quality_combo.currentText()
        }
