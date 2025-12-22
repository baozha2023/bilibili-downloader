import logging
import requests
import jieba.analyse
import re
from collections import Counter

from PyQt5.QtCore import QThread, pyqtSignal
from snownlp import SnowNLP

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
            
            # 2. Get comments for word cloud and other analysis
            comments = []
            comment_dates = []
            user_levels = []
            locations = []
            
            if aid:
                # Fetch multiple pages (Limit to 20 pages / 400 comments to avoid slow analysis)
                # API default page size is 20
                max_pages = 20
                for page in range(1, max_pages + 1):
                    try:
                        replies = self.crawler.api.get_video_comments(aid, page=page)
                        if not replies:
                            break
                            
                        for r in replies:
                            content = r.get('content', {}).get('message', '')
                            if content:
                                comments.append(content)
                                
                            # Extract date
                            ctime = r.get('ctime', 0)
                            if ctime:
                                comment_dates.append(ctime)
                                
                            # Extract level
                            level = r.get('member', {}).get('level_info', {}).get('current_level', 0)
                            user_levels.append(level)
                            
                            # Extract location
                            try:
                                # 优化IP属地提取逻辑
                                loc = ""
                                # 1. Try standard field
                                reply_control = r.get('reply_control', {})
                                if reply_control and 'location' in reply_control:
                                    loc = reply_control['location']
                                # 2. Try root field (sometimes)
                                elif 'location' in r:
                                    loc = r['location']
                                
                                if loc:
                                    # Remove prefix if present, support both colon types
                                    clean_loc = loc.replace('IP属地：', '').replace('IP属地:', '').strip()
                                    if clean_loc and clean_loc != "未知":
                                        locations.append(clean_loc)
                            except: pass
                            
                    except Exception as e:
                        logger.error(f"Error fetching comments page {page}: {e}")
                        break
            
            # 2.5 Get Danmaku (Fixed: Added back)
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
                    resp = requests.get(pic_url, timeout=10)
                    if resp.status_code == 200:
                        cover_data = resp.content
                except Exception as e:
                    logger.error(f"Failed to download cover: {e}")
            
            # 4. Sentiment Analysis
            sentiment_score = 0.5
            try:
                if comments:
                    scores = []
                    for c in comments:
                        # 简单的过滤：移除纯表情、纯符号
                        clean_c = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', c)
                        if len(clean_c) > 1:
                            s = SnowNLP(clean_c)
                            scores.append(s.sentiments)
                    if scores:
                        sentiment_score = sum(scores) / len(scores)
            except ImportError:
                logger.warning("SnowNLP not installed, skipping sentiment analysis")
            except Exception as e:
                logger.error(f"Sentiment analysis failed: {e}")

            # 4. Keyword Analysis (Optimized)
            keywords = []
            try:
                if comments:
                    # 预处理：合并所有评论
                    text = " ".join(comments)
                    
                    # 自定义停用词 (优化版)
                    stop_words = {
                        "视频", "弹幕", "这个", "那个", "什么", "因为", "所以", "如果", "但是", "就是", 
                        "真的", "觉得", "喜欢", "支持", "加油", "其实", "然后", "现在", "时候", "已经", 
                        "可以", "一下", "这里", "那里", "哈哈", "哈哈哈", "up", "UP", "Up", "怎么",
                        "还是", "感觉", "有没有", "是不是", "或者", "只是", "为了", "不过", "只要", "只有",
                        "回复", "查看", "图片", "表情", "doge", "妙啊", "吃瓜", "滑稽", "笑死", "甚至",
                        "虽然", "但是", "看到", "知道", "告诉", "希望", "今天", "明天", "今年", "明年",
                        "还是", "还有", "and", "the", "of", "to", "in", "it", "is", "for",
                        "啊", "呀", "呢", "吧", "嘛", "哦", "嗯", "哼", "哈", "咳", "呸", "嘘",
                        "b站", "B站", "哔哩哔哩", "投币", "点赞", "收藏", "关注", "三连", "白嫖", "下次一定"
                    }
                    
                    # 使用 jieba 提取关键词
                    # topK=50，提取更多以供筛选
                    tags = jieba.analyse.extract_tags(text, topK=50, withWeight=True)
                    
                    # 过滤停用词和单字
                    keywords = []
                    for word, weight in tags:
                        if word.lower() not in stop_words and len(word) > 1 and not word.isdigit():
                            keywords.append((word, weight))
                            if len(keywords) >= 20: # 保留前20个
                                break
            except Exception as e:
                logger.error(f"Keyword extraction failed: {e}")

            # 5. Emoji Analysis
            emojis = []
            try:
                emoji_pattern = re.compile(r'\[(.*?)\]')
                for c in comments:
                    found = emoji_pattern.findall(c)
                    if found:
                        emojis.extend(found)
            except Exception as e:
                logger.error(f"Emoji extraction failed: {e}")

            result = {
                'info': video_data,
                'comments': comments,
                'comment_dates': comment_dates,
                'user_levels': user_levels,
                'locations': locations,
                'danmaku': danmaku,
                'cover_data': cover_data,
                'sentiment': sentiment_score,
                'keywords': keywords,
                'emojis': emojis
            }
            self.finished_signal.emit(result, "")
        except Exception as e:
            self.finished_signal.emit({}, str(e))
