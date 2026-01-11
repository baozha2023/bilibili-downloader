import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, 
                             QAbstractItemView, QComboBox, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from ui.message_box import BilibiliMessageBox
from core.version_manager import VersionManager

class VersionFetchWorker(QThread):
    """Worker thread for fetching version list"""
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, manager, source):
        super().__init__()
        self.manager = manager
        self.source = source

    def run(self):
        try:
            versions = self.manager.get_versions(self.source)
            self.finished_signal.emit(versions)
        except Exception as e:
            self.error_signal.emit(str(e))

class VersionUpdateWorker(QThread):
    """Worker thread for switching version"""
    progress_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, manager, tag, source, assets):
        super().__init__()
        self.manager = manager
        self.tag = tag
        self.source = source
        self.assets = assets

    def run(self):
        try:
            def callback(msg, percent):
                self.progress_signal.emit(msg, percent)
                
            success, msg = self.manager.switch_version(self.tag, self.source, self.assets, progress_callback=callback)
            self.finished_signal.emit(success, msg)
        except Exception as e:
            self.finished_signal.emit(False, str(e))

class VersionDialog(QDialog):
    """
    版本管理对话框
    """
    
    # Styles
    GROUP_BOX_STYLE = """
        QGroupBox {
            font-weight: bold;
            font-size: 16px;
            color: #fb7299;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-top: 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
    """
    
    COMBO_BOX_STYLE = """
        QComboBox {
            padding: 5px 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            min-width: 200px;
        }
    """
    
    TABLE_STYLE = """
        QTableWidget {
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: white;
            selection-background-color: #f0f5ff;
            selection-color: #333;
        }
        QHeaderView::section {
            background-color: #f6f7f8;
            padding: 8px;
            border: none;
            border-bottom: 1px solid #ddd;
            font-weight: bold;
            color: #666;
        }
    """
    
    SWITCH_BTN_STYLE = """
        QPushButton {
            background-color: #00a1d6;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px 20px;
            font-weight: bold;
            font-size: 16px;
        }
        QPushButton:hover {
            background-color: #00b5e5;
        }
        QPushButton:pressed {
            background-color: #0090cc;
        }
        QPushButton:disabled {
            background-color: #cccccc;
        }
    """
    
    CLOSE_BTN_STYLE = """
        QPushButton {
            background-color: #f5f5f5;
            color: #666;
            padding: 10px 30px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 16px;
            border: 1px solid #ddd;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
            color: #333;
        }
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.version_manager = VersionManager()
        self.current_versions = [] 
        self.setWindowTitle("版本管理")
        self.setMinimumSize(900, 600)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        version_group = self._create_version_group()
        layout.addWidget(version_group)
        
        # Initial Load
        QTimer.singleShot(100, self.load_version_info)

    def _create_version_group(self):
        group = QGroupBox("版本列表")
        group.setStyleSheet(self.GROUP_BOX_STYLE)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 30, 20, 20)
        layout.setSpacing(15)
        
        layout.addLayout(self._create_top_bar())
        layout.addWidget(self._create_table())
        layout.addLayout(self._create_progress_area())
        layout.addLayout(self._create_action_buttons())
        
        return group

    def _create_top_bar(self):
        layout = QHBoxLayout()
        
        # Current Version
        title_ver = self.main_window.windowTitle().split(' ')[-1] if ' ' in self.main_window.windowTitle() else "未知"
        curr_ver_label = QLabel(f"当前版本: {title_ver}")
        curr_ver_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(curr_ver_label)
        
        layout.addStretch()
        
        # Source Selection
        source_label = QLabel("代码源:")
        source_label.setStyleSheet("font-size: 14px; color: #555;")
        layout.addWidget(source_label)
        
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Gitee (需本地Python编译)", "GitHub (推荐, 免Python)"])
        self.source_combo.setStyleSheet(self.COMBO_BOX_STYLE)
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        layout.addWidget(self.source_combo)
        
        return layout

    def _create_table(self):
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["版本号", "更新内容"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(self.TABLE_STYLE)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        return self.table

    def _create_progress_area(self):
        layout = QVBoxLayout()
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 14px;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 5px;
                text-align: center;
                background-color: #f0f0f0;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #fb7299;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        return layout

    def _create_action_buttons(self):
        layout = QHBoxLayout()
        
        self.switch_btn = QPushButton("切换至选中版本")
        self.switch_btn.setCursor(Qt.PointingHandCursor)
        self.switch_btn.setStyleSheet(self.SWITCH_BTN_STYLE)
        self.switch_btn.clicked.connect(self.switch_version)
        self.switch_btn.setEnabled(False)
        layout.addWidget(self.switch_btn)
        
        layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet(self.CLOSE_BTN_STYLE)
        layout.addWidget(close_btn)
        
        return layout

    def load_version_info(self):
        self._fetch_versions()
        
    def on_source_changed(self):
        self._fetch_versions()
        
    def _fetch_versions(self):
        self.table.setRowCount(0)
        self.switch_btn.setEnabled(False)
        self.switch_btn.setText("正在获取版本列表...")
        self.source_combo.setEnabled(False)
        
        source = self._get_current_source()
        
        # Start fetch worker
        self.fetch_worker = VersionFetchWorker(self.version_manager, source)
        self.fetch_worker.finished_signal.connect(self.on_fetch_finished)
        self.fetch_worker.error_signal.connect(self.on_fetch_error)
        self.fetch_worker.start()
        
    def on_fetch_finished(self, versions):
        self.current_versions = versions
        self.table.setRowCount(len(self.current_versions))
        
        for i, ver in enumerate(self.current_versions):
            self._add_table_row(i, ver)
            
        self.switch_btn.setText("切换至选中版本")
        self.source_combo.setEnabled(True)
        self.on_selection_changed()
        
        if not versions:
            self.status_label.setText("未找到版本信息，请尝试切换代码源")
            self.status_label.setVisible(True)
        else:
            self.status_label.setVisible(False)

    def on_fetch_error(self, error):
        self.switch_btn.setText("获取失败")
        self.source_combo.setEnabled(True)
        self.status_label.setText(f"获取版本列表失败: {error}")
        self.status_label.setVisible(True)

    def _get_current_source(self):
        return VersionManager.SOURCE_GITEE if self.source_combo.currentIndex() == 0 else VersionManager.SOURCE_GITHUB

    def _add_table_row(self, row, ver):
        tag = ver.get('tag', '')
        msg = ver.get('message', '')
        
        # Clean up message
        short_msg = msg.replace('\n', ' ').strip()
        if len(short_msg) > 100:
            short_msg = short_msg[:97] + "..."
        
        item_tag = QTableWidgetItem(tag)
        item_tag.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 0, item_tag)
        
        item_msg = QTableWidgetItem(short_msg)
        item_msg.setToolTip(msg)
        self.table.setItem(row, 1, item_msg)
            
    def on_selection_changed(self):
        selected = self.table.selectedItems()
        self.switch_btn.setEnabled(len(selected) > 0)
            
    def switch_version(self):
        row = self.table.currentRow()
        if row < 0:
            return
            
        tag = self.table.item(row, 0).text()
        source = self._get_current_source()
        
        # Check Python for Gitee
        if source == VersionManager.SOURCE_GITEE and not self.version_manager.check_python_available():
            BilibiliMessageBox.error(self, "环境检查失败", 
                "使用 Gitee 源需要本地安装 Python 环境进行编译。\n"
                "检测到您的电脑未安装 Python，请切换至 GitHub 源下载编译好的版本。")
            return
            
        source_name = "Gitee" if source == VersionManager.SOURCE_GITEE else "GitHub"
        reply = BilibiliMessageBox.question(
            self, "确认切换", 
            f"确定要从 {source_name} 下载并切换到版本 {tag} 吗？\n\n"
            "1. 程序将自动下载并覆盖当前版本\n"
            "2. 配置文件可能被重置\n"
            "3. 程序将自动重启"
        )
        
        if reply == QDialog.Accepted:
            self.switch_btn.setEnabled(False)
            self.switch_btn.setText("正在更新...")
            self.table.setEnabled(False)
            self.source_combo.setEnabled(False)
            
            # Show progress
            self.status_label.setVisible(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("准备开始...")
            
            assets = None
            if source == VersionManager.SOURCE_GITHUB:
                 for v in self.current_versions:
                     if v['tag'] == tag:
                         assets = v.get('assets')
                         break
            
            # Start update worker
            self.update_worker = VersionUpdateWorker(self.version_manager, tag, source, assets)
            self.update_worker.progress_signal.connect(self.on_update_progress)
            self.update_worker.finished_signal.connect(self.on_update_finished)
            self.update_worker.start()
            
    def on_update_progress(self, msg, percent):
        self.status_label.setText(msg)
        self.progress_bar.setValue(percent)
        
    def on_update_finished(self, success, msg):
        if success:
            sys.exit(0)
        else:
            self.switch_btn.setEnabled(True)
            self.switch_btn.setText("切换至选中版本")
            self.table.setEnabled(True)
            self.source_combo.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.status_label.setText(f"更新失败: {msg}")
            BilibiliMessageBox.error(self, "更新失败", msg)
