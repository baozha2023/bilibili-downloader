import logging
import time
import json

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QScrollArea, QFrame, QGridLayout, QFileDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from ui.message_box import BilibiliMessageBox
from ui.widgets.card_widget import CardWidget
from .worker import AnalysisWorker
from .charts import ChartGenerator

logger = logging.getLogger('bilibili_desktop')

class AnalysisTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.crawler = main_window.crawler
        self.init_ui()

    def add_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #e0e0e0; margin: 10px 0;")
        line.hide()
        layout.addWidget(line)
        self.separators.append(line)
        return line

    def init_ui(self):
        self.separators = []
        layout = QVBoxLayout(self)
        
        # Input Area
        input_layout = QHBoxLayout()
        self.bvid_input = QLineEdit()
        self.bvid_input.setPlaceholderText("输入视频BV号 (例如: BV1xx411c7mD)")
        self.bvid_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 16px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
        """)
        input_layout.addWidget(self.bvid_input)
        
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.setCursor(Qt.PointingHandCursor)
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #fb7299;
                color: white;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
        """)
        self.analyze_btn.clicked.connect(self.start_analysis)
        input_layout.addWidget(self.analyze_btn)
        
        # Export Button
        self.export_btn = QPushButton("导出数据")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #67c23a;
                color: white;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #85ce61;
            }
            QPushButton:disabled {
                background-color: #c0c4cc;
            }
        """)
        self.export_btn.clicked.connect(self.export_analysis)
        self.export_btn.setEnabled(False)
        input_layout.addWidget(self.export_btn)
        
        layout.addLayout(input_layout)
        
        # Content Area (Scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: white;") # Set white background
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignTop)
        
        # 1. Basic Info Card
        self.info_card = CardWidget("视频基本信息")
        self.info_layout = QGridLayout()
        
        # Cover Image
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(320, 200)
        self.cover_label.setScaledContents(True)
        self.cover_label.setStyleSheet("background-color: #eee; border-radius: 5px;")
        self.info_layout.addWidget(self.cover_label, 0, 0, 5, 1) # Spanning 5 rows
        
        # Details
        self.title_label = QLabel("标题: --")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        self.info_layout.addWidget(self.title_label, 0, 1)
        
        self.owner_label = QLabel("UP主: --")
        self.owner_label.setStyleSheet("color: #fb7299; font-weight: bold;")
        self.info_layout.addWidget(self.owner_label, 1, 1)
        
        self.time_label = QLabel("发布时间: --")
        self.info_layout.addWidget(self.time_label, 2, 1)
        
        self.zone_label = QLabel("分区: --")
        self.info_layout.addWidget(self.zone_label, 3, 1)
        
        self.desc_label = QLabel("简介: --")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #666;")
        self.info_layout.addWidget(self.desc_label, 4, 1)
        
        self.info_card.add_layout(self.info_layout)
        self.info_card.hide()
        self.content_layout.addWidget(self.info_card)
        
        self.add_separator(self.content_layout)
        
        # 2. Charts Grid
        self.charts_card = CardWidget("深度数据分析")
        self.charts_layout = QGridLayout()
        self.charts_layout.setVerticalSpacing(30)
        self.charts_layout.setHorizontalSpacing(20)
        
        # Row 1: Stats & Ratio
        self.stats_label = QLabel()
        self.stats_label.setAlignment(Qt.AlignCenter)
        self.stats_label.setStyleSheet("background-color: transparent; padding: 10px;")
        self.charts_layout.addWidget(self.stats_label, 0, 0)
        
        self.ratio_label = QLabel()
        self.ratio_label.setAlignment(Qt.AlignCenter)
        self.ratio_label.setStyleSheet("background-color: transparent; padding: 10px;")
        self.charts_layout.addWidget(self.ratio_label, 0, 1)
        
        # Row 2: Danmaku & Date
        self.danmaku_label = QLabel()
        self.danmaku_label.setAlignment(Qt.AlignCenter)
        self.danmaku_label.setStyleSheet("background-color: transparent; padding: 10px;")
        self.charts_layout.addWidget(self.danmaku_label, 1, 0)
        
        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet("background-color: transparent; padding: 10px;")
        self.charts_layout.addWidget(self.date_label, 1, 1)
        
        # Row 3: Level & Sentiment
        self.level_label = QLabel()
        self.level_label.setAlignment(Qt.AlignCenter)
        self.level_label.setStyleSheet("background-color: transparent; padding: 10px;")
        self.charts_layout.addWidget(self.level_label, 2, 0)
        
        self.sentiment_label = QLabel()
        self.sentiment_label.setAlignment(Qt.AlignCenter)
        self.sentiment_label.setStyleSheet("background-color: transparent; padding: 10px;")
        self.charts_layout.addWidget(self.sentiment_label, 2, 1)

        # Row 4: Location & Danmaku Color
        self.location_label = QLabel()
        self.location_label.setAlignment(Qt.AlignCenter)
        self.location_label.setStyleSheet("background-color: transparent; padding: 10px;")
        self.charts_layout.addWidget(self.location_label, 3, 0)
        
        self.color_label = QLabel()
        self.color_label.setAlignment(Qt.AlignCenter)
        self.color_label.setStyleSheet("background-color: transparent; padding: 10px;")
        self.charts_layout.addWidget(self.color_label, 3, 1)
        
        self.charts_card.add_layout(self.charts_layout)
        self.charts_card.hide()
        self.content_layout.addWidget(self.charts_card)
        
        self.add_separator(self.content_layout)

        # 4. Keywords Card
        self.keyword_card = CardWidget("评论关键词")
        self.keyword_layout = QHBoxLayout() # Horizontal tags
        self.keyword_card.add_layout(self.keyword_layout)
        self.keyword_card.hide()
        self.content_layout.addWidget(self.keyword_card)
        
        self.add_separator(self.content_layout)
        
        # 5. Word Cloud Card
        self.cloud_card = CardWidget("评论词云分析")
        self.cloud_layout = QVBoxLayout()
        self.cloud_label = QLabel()
        self.cloud_label.setAlignment(Qt.AlignCenter)
        self.cloud_layout.addWidget(self.cloud_label)
        self.cloud_card.add_layout(self.cloud_layout)
        self.cloud_card.hide()
        self.content_layout.addWidget(self.cloud_card)
        
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)

    def start_analysis(self):
        bvid = self.bvid_input.text().strip()
        if not bvid:
            BilibiliMessageBox.warning(self, "提示", "请输入BV号")
            return
            
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("分析中...")
        
        self.worker = AnalysisWorker(self.crawler, bvid)
        self.worker.finished_signal.connect(self.on_analysis_finished)
        self.worker.start()

    def on_analysis_finished(self, result, error):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("开始分析")
        
        if error:
            BilibiliMessageBox.error(self, "分析失败", error)
            return
        
        self.last_result = result
        self.export_btn.setEnabled(True)
        self.show_results(result)

    def show_results(self, result):
        # Show all separators
        for sep in self.separators:
            sep.show()

        info = result.get('info', {})
        comments = result.get('comments', [])
        danmaku = result.get('danmaku', [])
        cover_data = result.get('cover_data')
        
        # 1. Basic Info
        title = info.get('title', '')
        desc = info.get('desc', '')
        owner = info.get('owner', {}).get('name', '')
        tname = info.get('tname', '未知分区')
        pubdate = info.get('pubdate', 0)
        
        pub_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(pubdate))
        
        self.title_label.setText(f"标题: {title}")
        self.owner_label.setText(f"UP主: {owner}")
        self.time_label.setText(f"发布时间: {pub_time}")
        self.zone_label.setText(f"分区: {tname}")
        self.desc_label.setText(f"简介: {desc[:100]}..." if len(desc) > 100 else f"简介: {desc}")
        
        if cover_data:
            pixmap = QPixmap()
            pixmap.loadFromData(cover_data)
            self.cover_label.setPixmap(pixmap)
        
        self.info_card.show()
        
        # 2. Charts Grid
        stat = info.get('stat', {})
        ChartGenerator.generate_stats_chart(self.stats_label, stat)
        ChartGenerator.generate_ratio_chart(self.ratio_label, stat)
        
        # Danmaku & Date
        duration = info.get('duration', 0)
        ChartGenerator.generate_danmaku_chart(self.danmaku_label, danmaku, duration)
        ChartGenerator.generate_date_chart(self.date_label, result.get('comment_dates', []))
        
        # Level & Sentiment
        ChartGenerator.generate_level_chart(self.level_label, result.get('user_levels', []))
        sentiment_score = result.get('sentiment', 0.5)
        ChartGenerator.generate_sentiment_chart(self.sentiment_label, sentiment_score)
        
        # Location & Danmaku Color
        ChartGenerator.generate_location_chart(self.location_label, result.get('locations', []))
        ChartGenerator.generate_danmaku_color_chart(self.color_label, result.get('danmaku', []))
        
        self.charts_card.show()
        
        # 4. Keywords
        keywords = result.get('keywords', [])
        if keywords:
            self.display_keywords(keywords)
            self.keyword_card.show()
        else:
            self.keyword_card.hide()
            
        # 5. Word Cloud
        if comments:
            ChartGenerator.generate_word_cloud(self.cloud_label, comments)
            self.cloud_card.show()
        else:
            self.cloud_card.hide()

    def display_keywords(self, keywords):
        # Clear previous
        while self.keyword_layout.count():
            item = self.keyword_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new tags
        for word, weight in keywords:
            label = QLabel(f"{word}")
            label.setStyleSheet("""
                QLabel {
                    background-color: #f0f5ff;
                    color: #409eff;
                    border: 1px solid #d9ecff;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
            self.keyword_layout.addWidget(label)
        
        self.keyword_layout.addStretch()

    def export_analysis(self):
        if not hasattr(self, 'last_result'):
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出分析数据", "video_analysis.json", "JSON Files (*.json);;Text Files (*.txt)"
        )
        
        if file_path:
            try:
                # Filter non-serializable data (like bytes)
                data = self.last_result.copy()
                if 'cover_data' in data:
                    del data['cover_data']
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
                BilibiliMessageBox.information(self, "成功", f"数据已导出到: {file_path}")
            except Exception as e:
                BilibiliMessageBox.error(self, "错误", f"导出失败: {e}")
