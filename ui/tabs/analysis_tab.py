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
            cid = video_data.get('cid')
            
            # 2. Get comments for word cloud
            comments = []
            if aid:
                replies = self.crawler.api.get_video_comments(aid)
                if replies:
                    for r in replies:
                        content = r.get('content', {}).get('message', '')
                        if content:
                            comments.append(content)
            
            # 2.5 Get Danmaku
            danmaku = []
            if cid:
                try:
                    danmaku = self.crawler.get_video_danmaku(cid)
                except Exception as e:
                    logger.error(f"Failed to get danmaku: {e}")

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
            
            # 4. Sentiment Analysis
            sentiment_score = 0.5
            try:
                from snownlp import SnowNLP
                if comments:
                    scores = []
                    for c in comments:
                        if len(c) > 1:
                            s = SnowNLP(c)
                            scores.append(s.sentiments)
                    if scores:
                        sentiment_score = sum(scores) / len(scores)
            except ImportError:
                logger.warning("SnowNLP not installed, skipping sentiment analysis")
            except Exception as e:
                logger.error(f"Sentiment analysis failed: {e}")

            # 4. Keyword Analysis
            keywords = []
            try:
                import jieba.analyse
                if comments:
                    text = " ".join(comments)
                    keywords = jieba.analyse.extract_tags(text, topK=10, withWeight=True)
            except Exception as e:
                logger.error(f"Keyword extraction failed: {e}")

            result = {
                'info': video_data,
                'comments': comments,
                'danmaku': danmaku,
                'cover_data': cover_data,
                'sentiment': sentiment_score,
                'keywords': keywords
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

    def add_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #e0e0e0; margin: 10px 0;")
        line.hide() # Hide by default
        layout.addWidget(line)
        self.separators.append(line)
        return line

    def init_ui(self):
        self.separators = [] # Track separators
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
        
        self.add_separator(self.content_layout)

        # 2.5 Danmaku Analysis Card
        self.danmaku_card = CardWidget("弹幕趋势分析")
        self.danmaku_layout = QVBoxLayout()
        self.danmaku_label = QLabel()
        self.danmaku_label.setAlignment(Qt.AlignCenter)
        self.danmaku_layout.addWidget(self.danmaku_label)
        self.danmaku_card.add_layout(self.danmaku_layout)
        self.danmaku_card.hide()
        self.content_layout.addWidget(self.danmaku_card)
        
        self.add_separator(self.content_layout)
        
        # 3. Sentiment Card
        self.sentiment_card = CardWidget("情感倾向分析")
        self.sentiment_layout = QVBoxLayout()
        self.sentiment_label = QLabel()
        self.sentiment_label.setAlignment(Qt.AlignCenter)
        self.sentiment_layout.addWidget(self.sentiment_label)
        self.sentiment_card.add_layout(self.sentiment_layout)
        self.sentiment_card.hide()
        self.content_layout.addWidget(self.sentiment_card)

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
        import time
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
        
        # 2. Stats Chart
        stat = info.get('stat', {})
        self.generate_stats_chart(stat)
        self.generate_ratio_chart(stat)
        self.stats_card.show()
        
        # 2.5 Danmaku Chart
        duration = info.get('duration', 0)
        self.generate_danmaku_chart(danmaku, duration)
        self.danmaku_card.show()
        
        # 3. Sentiment
        sentiment_score = result.get('sentiment', 0.5)
        self.generate_sentiment_chart(sentiment_score)
        self.sentiment_card.show()
        
        # 4. Keywords
        keywords = result.get('keywords', [])
        if keywords:
            self.display_keywords(keywords)
            self.keyword_card.show()
        else:
            self.keyword_card.hide()
            
        # 5. Word Cloud
        if comments:
            self.generate_word_cloud(comments)
            self.cloud_card.show()
        else:
            self.cloud_card.hide()

    def generate_danmaku_chart(self, danmaku_list, duration=None):
        if not danmaku_list:
            self.danmaku_label.setText("无弹幕数据")
            return
            
        try:
            # danmaku_list items have 'time' (float, seconds from start)
            times = [d.get('time', 0) for d in danmaku_list]
            if not times:
                self.danmaku_label.setText("弹幕数据格式错误")
                return
                
            max_time = max(times)
            if duration and duration > max_time:
                max_time = duration
                
            # Binning
            bin_size = 30 if max_time < 600 else 60
            bins = range(0, int(max_time) + bin_size, bin_size)
            
            plt.figure(figsize=(8, 4))
            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False
            
            plt.hist(times, bins=bins, color='#fb7299', alpha=0.7, edgecolor='white')
            plt.title('弹幕时间分布 (密度)')
            plt.xlabel('时间 (秒)')
            plt.ylabel('弹幕数量')
            plt.grid(axis='y', linestyle='--', alpha=0.5)
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            image = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(image)
            self.danmaku_label.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"Generate danmaku chart error: {e}")
            self.danmaku_label.setText(f"图表生成失败: {e}")


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

    def generate_sentiment_chart(self, score):
        try:
            # Gauge Chart (simulated with half-pie)
            labels = ['负面', '正面']
            # score is 0-1, 0 is negative, 1 is positive
            
            plt.figure(figsize=(6, 3))
            plt.rcParams['font.sans-serif'] = ['SimHei']
            
            # Simple horizontal bar for sentiment
            color = '#67c23a' if score > 0.6 else '#f56c6c' if score < 0.4 else '#e6a23c'
            
            plt.barh(['情感倾向'], [score], color=color, height=0.5)
            plt.xlim(0, 1)
            plt.axvline(x=0.5, color='gray', linestyle='--', alpha=0.5)
            plt.title(f'评论情感得分: {score:.2f} (0=负面, 1=正面)')
            
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            image = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(image)
            self.sentiment_label.setPixmap(pixmap)
        except Exception as e:
             logger.error(f"Generate sentiment chart error: {e}")
             self.sentiment_label.setText("情感分析图表生成失败")

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

    def generate_word_cloud(self, comments):
        try:
            import jieba
            from wordcloud import WordCloud
            
            # Expanded stop words list based on user feedback
            STOP_WORDS = {
                "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
                "会", "着", "没有", "看", "好", "自己", "这", "那", "有", "什么", "个", "因为", "所以", "但是", "如果", "我们", "你们", "他们",
                "这个", "那个", "视频", "弹幕", "哈哈", "哈哈哈", "哈哈哈哈", "啊", "吧", "嘛", "呀", "呢", "哦", "嗯", "up", "UP", "怎么", "还是",
                "真的", "就是", "觉得", "喜欢", "支持", "加油", "其实", "然后", "现在", "时候", "已经", "可以", "一下", "这里", "那里",
                "doge", "call", "https", "com", "bilibili", "opus", "回复", "楼上", "转发", "点赞", "收藏", "关注", "投币",
                "星星",  "滑稽", "打卡", "第一", "前排", "沙发", "板凳", "地板", "热乎", "来了", "更新", "辛苦",
                "www", "http", "cn", "net", "org", "html", "htm"
            }
            
            text = " ".join(comments)
            
            # Cut words
            words = jieba.cut(text)
            
            # Filter stop words and short words
            filtered_words = []
            for w in words:
                w = w.strip()
                if len(w) > 1 and w not in STOP_WORDS and not w.isdigit():
                    # Filter pure numbers and specific garbage
                    filtered_words.append(w)
            
            if not filtered_words:
                self.cloud_label.setText("评论内容不足以生成词云")
                return

            wc = WordCloud(
                font_path="msyh.ttc", # Microsoft YaHei
                background_color="white",
                width=800,
                height=400,
                max_words=100,
                stopwords=STOP_WORDS,
                collocations=False # Avoid repeating phrases
            ).generate(" ".join(filtered_words))
            
            image = wc.to_image()
            pixmap = QPixmap.fromImage(QImage(image.tobytes(), image.width, image.height, QImage.Format_RGB888))
            self.cloud_label.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"Generate word cloud error: {e}")
            self.cloud_label.setText(f"词云生成失败: {e}")
