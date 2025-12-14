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
            
            # 3. Get cover image
            cover_data = None
            pic_url = video_data.get('pic', '')
            if pic_url:
                try:
                    import requests
                    resp = requests.get(pic_url, timeout=10)
                    if resp.status_code == 200:
                        cover_data = resp.content
                except Exception as e:
                    logger.error(f"Failed to download cover: {e}")

            result = {
                'info': video_data,
                'comments': comments,
                'cover_data': cover_data
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
        
        # Cover Image
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(320, 200)
        self.cover_label.setScaledContents(True)
        self.cover_label.setStyleSheet("background-color: #eee; border-radius: 5px;")
        self.info_layout.addWidget(self.cover_label, 0, 0, 4, 1)
        
        # Details
        self.title_label = QLabel("标题: --")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.info_layout.addWidget(self.title_label, 0, 1)
        
        self.owner_label = QLabel("UP主: --")
        self.info_layout.addWidget(self.owner_label, 1, 1)
        
        self.time_label = QLabel("发布时间: --")
        self.info_layout.addWidget(self.time_label, 2, 1)
        
        self.desc_label = QLabel("简介: --")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #666;")
        self.info_layout.addWidget(self.desc_label, 3, 1)
        
        self.info_card.add_layout(self.info_layout)
        self.info_card.hide()
        self.content_layout.addWidget(self.info_card)
        
        # 2. Stats Chart Card
        self.stats_card = CardWidget("数据统计分析")
        self.stats_layout = QVBoxLayout() # Changed to VBox to display charts vertically
        self.stats_layout.setSpacing(20) # Add spacing between charts
        
        self.stats_label = QLabel()
        self.stats_label.setAlignment(Qt.AlignCenter)
        self.stats_layout.addWidget(self.stats_label)
        
        self.ratio_label = QLabel()
        self.ratio_label.setAlignment(Qt.AlignCenter)
        self.stats_layout.addWidget(self.ratio_label)
        
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
        cover_data = result.get('cover_data')
        
        # 1. Basic Info
        title = info.get('title', '')
        desc = info.get('desc', '')
        owner = info.get('owner', {}).get('name', '')
        pubdate = info.get('pubdate', 0)
        import time
        pub_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(pubdate))
        
        self.title_label.setText(f"标题: {title}")
        self.owner_label.setText(f"UP主: {owner}")
        self.time_label.setText(f"发布时间: {pub_time}")
        self.desc_label.setText(f"简介: {desc[:100]}..." if len(desc) > 100 else f"简介: {desc}")
        
        if cover_data:
            pixmap = QPixmap()
            pixmap.loadFromData(cover_data)
            self.cover_label.setPixmap(pixmap)
        
        self.info_card.show()
        
        # 2. Stats Chart
        stat = info.get('stat', {})
        self.generate_stats_chart(stat)
        self.generate_ratio_chart(stat)
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

    def generate_ratio_chart(self, stat):
        try:
            view = stat.get('view', 1) # Avoid div by zero
            like = stat.get('like', 0)
            coin = stat.get('coin', 0)
            fav = stat.get('favorite', 0)
            
            # Calculate ratios
            ratios = [
                (like / view) * 100,
                (coin / view) * 100,
                (fav / view) * 100
            ]
            labels = ['点赞率', '投币率', '收藏率']
            colors = ['#fb7299', '#e6a23c', '#67c23a']
            
            plt.figure(figsize=(4, 4))
            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False
            
            # Pie chart? Or Bar? Let's use Bar for rates as they are independent
            # Actually Pie chart is good for composition, but these are independent rates relative to View.
            # Let's use a Horizontal Bar Chart.
            
            plt.barh(labels, ratios, color=colors)
            plt.title('互动率 (%)')
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            
            # Add value labels
            for i, v in enumerate(ratios):
                plt.text(v, i, f' {v:.2f}%', va='center')
            
            plt.tight_layout()
            
            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            # Load to QPixmap
            image = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(image)
            self.ratio_label.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"Generate ratio chart error: {e}")
            self.ratio_label.setText("图表生成失败")

    def generate_word_cloud(self, comments):
        try:
            import jieba
            from wordcloud import WordCloud
            
            # Simple stop words list
            STOP_WORDS = {
                "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
                "会", "着", "没有", "看", "好", "自己", "这", "那", "有", "什么", "个", "因为", "所以", "但是", "如果", "我们", "你们", "他们",
                "这个", "那个", "视频", "弹幕", "哈哈", "哈哈哈", "哈哈哈哈", "啊", "吧", "嘛", "呀", "呢", "哦", "嗯", "up", "UP", "怎么", "还是",
                "真的", "就是", "觉得", "喜欢", "支持", "加油", "其实", "然后", "现在", "时候", "已经", "可以", "一下", "这里", "那里"
            }
            
            text = " ".join(comments)
            
            # Cut words
            words = jieba.cut(text)
            
            # Filter stop words and short words
            filtered_words = [w for w in words if w.strip() and w not in STOP_WORDS and len(w) > 1]
            text_space = " ".join(filtered_words)
            
            if not text_space:
                self.cloud_label.setText("评论内容不足以生成词云")
                return
            
            # Generate cloud
            wc = WordCloud(
                font_path="msyh.ttc", # Microsoft YaHei
                background_color="white",
                width=800,
                height=400,
                max_words=100,
                collocations=False # Avoid repeating words
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
