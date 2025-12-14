import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QGroupBox, QScrollArea, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
from ui.message_box import BilibiliMessageBox
from ui.widgets.card_widget import CardWidget
import matplotlib.pyplot as plt
import io

logger = logging.getLogger('bilibili_desktop')

class AnalysisWorker(QThread):
    finished_signal = pyqtSignal(dict, str) # result, error

    def __init__(self, crawler, bvid):
        super().__init__()
        self.crawler = crawler
        self.bvid = bvid

    def run(self):
        try:
            # 1. Get video info
            info = self.crawler.api.get_video_info(self.bvid)
            if not info or 'data' not in info:
                raise Exception("无法获取视频信息")
            
            video_data = info['data']
            aid = video_data.get('aid')
            
            # 2. Get comments for word cloud
            comments = []
            if aid:
                replies = self.crawler.api.get_video_comments(aid)
                if replies:
                    for r in replies:
                        content = r.get('content', {}).get('message', '')
                        if content:
                            comments.append(content)
            
            result = {
                'info': video_data,
                'comments': comments
            }
            self.finished_signal.emit(result, "")
        except Exception as e:
            self.finished_signal.emit({}, str(e))

class AnalysisTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.crawler = main_window.crawler
        self.init_ui()

    def init_ui(self):
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
        
        layout.addLayout(input_layout)
        
        # Content Area (Scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignTop)
        
        # 1. Basic Info Card
        self.info_card = CardWidget("视频基本信息")
        self.info_layout = QGridLayout()
        self.info_card.add_layout(self.info_layout)
        self.info_card.hide()
        self.content_layout.addWidget(self.info_card)
        
        # 2. Stats Chart Card
        self.stats_card = CardWidget("数据统计分析")
        self.stats_layout = QVBoxLayout()
        self.stats_label = QLabel()
        self.stats_label.setAlignment(Qt.AlignCenter)
        self.stats_layout.addWidget(self.stats_label)
        self.stats_card.add_layout(self.stats_layout)
        self.stats_card.hide()
        self.content_layout.addWidget(self.stats_card)
        
        # 3. Word Cloud Card
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
            
        self.show_results(result)

    def show_results(self, result):
        info = result.get('info', {})
        comments = result.get('comments', [])
        
        # 1. Basic Info
        # Clear layout
        for i in reversed(range(self.info_layout.count())): 
            self.info_layout.itemAt(i).widget().setParent(None)
            
        title = info.get('title', '')
        desc = info.get('desc', '')
        owner = info.get('owner', {}).get('name', '')
        pubdate = info.get('pubdate', 0)
        import time
        pub_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(pubdate))
        
        self.info_layout.addWidget(QLabel(f"标题: {title}"), 0, 0, 1, 2)
        self.info_layout.addWidget(QLabel(f"UP主: {owner}"), 1, 0)
        self.info_layout.addWidget(QLabel(f"发布时间: {pub_time}"), 1, 1)
        desc_label = QLabel(f"简介: {desc[:100]}..." if len(desc) > 100 else f"简介: {desc}")
        desc_label.setWordWrap(True)
        self.info_layout.addWidget(desc_label, 2, 0, 1, 2)
        
        self.info_card.show()
        
        # 2. Stats Chart
        stat = info.get('stat', {})
        self.generate_stats_chart(stat)
        self.stats_card.show()
        
        # 3. Word Cloud
        if comments:
            self.generate_word_cloud(comments)
            self.cloud_card.show()
        else:
            self.cloud_card.hide()

    def generate_stats_chart(self, stat):
        try:
            # Data
            labels = ['播放', '点赞', '投币', '收藏', '转发']
            values = [
                stat.get('view', 0),
                stat.get('like', 0),
                stat.get('coin', 0),
                stat.get('favorite', 0),
                stat.get('share', 0)
            ]
            
            # Matplotlib
            plt.figure(figsize=(8, 4))
            plt.rcParams['font.sans-serif'] = ['SimHei'] # Support Chinese
            plt.rcParams['axes.unicode_minus'] = False
            
            colors = ['#409eff', '#fb7299', '#e6a23c', '#67c23a', '#909399']
            bars = plt.bar(labels, values, color=colors)
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom')
            
            plt.title('视频数据统计')
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            # Load to QPixmap
            image = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(image)
            self.stats_label.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"Generate chart error: {e}")
            self.stats_label.setText(f"图表生成失败: {e}")

    def generate_word_cloud(self, comments):
        try:
            import jieba
            from wordcloud import WordCloud
            
            text = " ".join(comments)
            
            # Cut words
            words = jieba.cut(text)
            text_space = " ".join(words)
            
            # Generate cloud
            wc = WordCloud(
                font_path="msyh.ttc", # Microsoft YaHei
                background_color="white",
                width=800,
                height=400,
                max_words=100
            ).generate(text_space)
            
            # Save to buffer
            image = wc.to_image()
            buf = io.BytesIO()
            image.save(buf, format='PNG')
            buf.seek(0)
            
            # Load to QPixmap
            qimage = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(qimage)
            self.cloud_label.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"Generate word cloud error: {e}")
            self.cloud_label.setText(f"词云生成失败 (可能缺少字体或库): {e}")
