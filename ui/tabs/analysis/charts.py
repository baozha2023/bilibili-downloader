import io
import logging
import matplotlib.pyplot as plt
import datetime
import jieba

from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QLabel
from collections import Counter
from wordcloud import WordCloud

logger = logging.getLogger('bilibili_desktop')

class ChartGenerator:
    @staticmethod
    def generate_stats_chart(label: QLabel, stat: dict):
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
            label.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"Generate chart error: {e}")
            label.setText(f"图表生成失败: {e}")

    @staticmethod
    def generate_ratio_chart(label: QLabel, stat: dict):
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
            
            # Horizontal Bar Chart
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
            label.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"Generate ratio chart error: {e}")
            label.setText("图表生成失败")

    @staticmethod
    def generate_danmaku_chart(label: QLabel, danmaku_list: list, duration=None):
        if not danmaku_list:
            label.setText("无弹幕数据")
            return
            
        try:
            # danmaku_list items have 'time' (float, seconds from start)
            times = [d.get('time', 0) for d in danmaku_list]
            if not times:
                label.setText("弹幕数据格式错误")
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
            label.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"Generate danmaku chart error: {e}")
            label.setText(f"图表生成失败: {e}")

    @staticmethod
    def generate_date_chart(label: QLabel, dates: list):
        try:
            if not dates:
                label.setText("无评论时间数据")
                return
                

            # Convert timestamps to dates
            date_objs = [datetime.datetime.fromtimestamp(ts).date() for ts in dates]

            counts = Counter(date_objs)
            
            sorted_dates = sorted(counts.keys())
            values = [counts[d] for d in sorted_dates]
            x_labels = [d.strftime("%m-%d") for d in sorted_dates]
            
            plt.figure(figsize=(8, 4))
            plt.rcParams['font.sans-serif'] = ['SimHei']
            
            plt.plot(x_labels, values, marker='o', linestyle='-', color='#fb7299')
            plt.title('评论时间趋势')
            plt.xticks(rotation=45)
            plt.grid(True, linestyle='--', alpha=0.5)
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            image = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(image)
            label.setPixmap(pixmap)
        except Exception as e:
            logger.error(f"Generate date chart error: {e}")
            label.setText(f"图表生成失败")

    @staticmethod
    def generate_level_chart(label: QLabel, levels: list):
        try:
            if not levels:
                label.setText("无用户等级数据")
                return

            # Count levels
            counts = Counter(levels)
            labels = sorted(counts.keys())
            values = [counts[l] for l in labels]
            labels_str = [f"Lv{l}" for l in labels]
            
            plt.figure(figsize=(6, 4))
            plt.rcParams['font.sans-serif'] = ['SimHei']
            
            # Pie chart
            plt.pie(values, labels=labels_str, autopct='%1.1f%%', startangle=90, 
                   colors=['#c0c4cc', '#909399', '#67c23a', '#409eff', '#e6a23c', '#f56c6c', '#ff0000'])
            plt.title('评论用户等级分布')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            image = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(image)
            label.setPixmap(pixmap)
        except Exception as e:
            logger.error(f"Generate level chart error: {e}")
            label.setText(f"图表生成失败")

    @staticmethod
    def generate_sentiment_chart(label: QLabel, score: float):
        try:
            # Gauge Chart (simulated with half-pie)
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
            label.setPixmap(pixmap)
        except Exception as e:
             logger.error(f"Generate sentiment chart error: {e}")
             label.setText("情感分析图表生成失败")

    @staticmethod
    def generate_location_chart(label: QLabel, locations: list):
        try:
            if not locations:
                label.setText("无IP属地数据")
                return

            counts = Counter(locations)
            # Top 10
            top_locs = counts.most_common(10)
            labels = [l[0] for l in top_locs]
            values = [l[1] for l in top_locs]
            
            plt.figure(figsize=(6, 4))
            plt.rcParams['font.sans-serif'] = ['SimHei']
            
            # Horizontal Bar
            y_pos = range(len(labels))
            plt.barh(y_pos, values, color='#409eff')
            plt.yticks(y_pos, labels)
            plt.title('评论用户IP属地分布 (Top 10)')
            plt.xlabel('用户数量')
            plt.grid(axis='x', linestyle='--', alpha=0.5)
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            image = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(image)
            label.setPixmap(pixmap)
        except Exception as e:
            logger.error(f"Generate location chart error: {e}")
            label.setText("图表生成失败")

    @staticmethod
    def generate_danmaku_color_chart(label: QLabel, danmaku: list):
        try:
            if not danmaku:
                label.setText("无弹幕颜色数据")
                return
            
            # Extract colors
            colors = [d.get('color') for d in danmaku if d.get('color')]
            if not colors:
                label.setText("无颜色数据")
                return
                
            counts = Counter(colors)
            
            # Group by hex
            hex_counts = {}
            for color_int, count in counts.items():
                hex_color = f"#{color_int:06x}"
                hex_counts[hex_color] = hex_counts.get(hex_color, 0) + count
            
            # Top 10 colors
            sorted_colors = sorted(hex_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            labels = [c[0] for c in sorted_colors]
            values = [c[1] for c in sorted_colors]
            chart_colors = [c[0] for c in sorted_colors]
            
            plt.figure(figsize=(6, 4))
            plt.rcParams['font.sans-serif'] = ['SimHei']
            
            # Horizontal Bar Chart
            y_pos = range(len(labels))
            plt.barh(y_pos, values, color=chart_colors, edgecolor='black', linewidth=0.5)
            plt.yticks(y_pos, labels)
            plt.title('弹幕颜色分布 (Top 10)')
            plt.xlabel('弹幕数量')
            plt.gca().invert_yaxis() # Top to bottom
            
            # Add value labels
            for i, v in enumerate(values):
                plt.text(v, i, f' {v}', va='center')

            plt.grid(axis='x', linestyle='--', alpha=0.5)
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            image = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(image)
            label.setPixmap(pixmap)
        except Exception as e:
            logger.error(f"Generate color chart error: {e}")
            label.setText("图表生成失败")

    @staticmethod
    def generate_gender_chart(label: QLabel, genders: list):
        try:
            if not genders:
                label.setText("无性别数据")
                return

            counts = Counter(genders)
            labels = list(counts.keys())
            values = list(counts.values())
            
            plt.figure(figsize=(6, 4))
            plt.rcParams['font.sans-serif'] = ['SimHei']
            
            colors = []
            for l in labels:
                if l == '男': colors.append('#409eff')
                elif l == '女': colors.append('#fb7299')
                else: colors.append('#909399')
            
            plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
            plt.title('评论用户性别分布')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            image = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(image)
            label.setPixmap(pixmap)
        except Exception as e:
            logger.error(f"Generate gender chart error: {e}")
            label.setText("图表生成失败")

    @staticmethod
    def generate_active_time_chart(label: QLabel, hours: list):
        try:
            if not hours:
                label.setText("无活跃时间数据")
                return
            
            counts = Counter(hours)
            # 0-23 hours
            x = list(range(24))
            y = [counts.get(h, 0) for h in x]
            
            plt.figure(figsize=(8, 4))
            plt.rcParams['font.sans-serif'] = ['SimHei']
            
            plt.plot(x, y, marker='o', linestyle='-', color='#e6a23c')
            plt.fill_between(x, y, color='#e6a23c', alpha=0.3)
            plt.title('评论活跃时间分布 (24小时)')
            plt.xlabel('小时')
            plt.ylabel('评论数')
            plt.xticks(range(0, 24, 2))
            plt.grid(True, linestyle='--', alpha=0.5)
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            image = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(image)
            label.setPixmap(pixmap)
        except Exception as e:
            logger.error(f"Generate active time chart error: {e}")
            label.setText("图表生成失败")

    @staticmethod
    def generate_emoji_chart(label: QLabel, emojis: list):
        try:
            if not emojis:
                label.setText("无表情包使用数据")
                return

            counts = Counter(emojis)
            # Top 10
            top_emojis = counts.most_common(10)
            labels = [e[0] for e in top_emojis]
            values = [e[1] for e in top_emojis]
            
            plt.figure(figsize=(6, 4))
            plt.rcParams['font.sans-serif'] = ['SimHei']
            
            # Vertical Bar Chart
            x_pos = range(len(labels))
            plt.bar(x_pos, values, color='#fb7299', alpha=0.7)
            plt.xticks(x_pos, labels, rotation=45)
            plt.title('评论表情包分布 (Top 10)')
            plt.ylabel('使用次数')
            plt.grid(axis='y', linestyle='--', alpha=0.5)
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            image = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(image)
            label.setPixmap(pixmap)
        except Exception as e:
            logger.error(f"Generate emoji chart error: {e}")
            label.setText("图表生成失败")

    @staticmethod
    def generate_word_cloud(label: QLabel, comments: list):
        try:
            # Expanded stop words list
            STOP_WORDS = {
                "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
                "会", "着", "没有", "看", "好", "自己", "这", "那", "有", "什么", "个", "因为", "所以", "但是", "如果", "我们", "你们", "他们",
                "这个", "那个", "视频", "弹幕", "哈哈", "哈哈哈", "哈哈哈哈", "啊", "吧", "嘛", "呀", "呢", "哦", "嗯", "up", "UP", "怎么", "还是",
                "真的", "就是", "觉得", "喜欢", "支持", "加油", "其实", "然后", "现在", "时候", "已经", "可以", "一下", "这里", "那里",
                "doge", "call", "https", "com", "bilibili", "opus", "回复", "楼上", "转发", "点赞", "收藏", "关注", "投币",
                "星星",  "滑稽", "打卡", "第一", "前排", "沙发", "板凳", "地板", "热乎", "来了", "更新", "辛苦",
                "www", "http", "cn", "net", "org", "html", "htm", "感觉", "有没有", "是不是", "或者", "只是", "为了", "不过", "只要", "只有"
            }
            
            text = " ".join(comments)
            
            # Cut words
            words = jieba.cut(text)
            
            # Filter stop words and short words
            filtered_words = []
            for w in words:
                w = w.strip()
                if len(w) > 1 and w not in STOP_WORDS and not w.isdigit():
                    filtered_words.append(w)
            
            if not filtered_words:
                label.setText("评论内容不足以生成词云")
                return

            wc = WordCloud(
                font_path="msyh.ttc", # Microsoft YaHei
                background_color="white",
                width=800,
                height=400,
                max_words=150, # Increased
                stopwords=STOP_WORDS,
                collocations=False,
                mask=None # Can add shape mask if needed
            ).generate(" ".join(filtered_words))
            
            image = wc.to_image()
            pixmap = QPixmap.fromImage(QImage(image.tobytes(), image.width, image.height, QImage.Format_RGB888))
            label.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"Generate word cloud error: {e}")
            label.setText(f"词云生成失败: {e}")
