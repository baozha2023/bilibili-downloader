import logging
import requests
import jieba.analyse

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
                replies = self.crawler.api.get_video_comments(aid)
                if replies:
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
                            loc = r.get('reply_control', {}).get('location', '')
                            if loc:
                                locations.append(loc.replace('IP属地：', '').replace('IP属地:', '').strip())
                        except: pass
            
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
                if comments:
                    text = " ".join(comments)
                    keywords = jieba.analyse.extract_tags(text, topK=10, withWeight=True)
            except Exception as e:
                logger.error(f"Keyword extraction failed: {e}")

            result = {
                'info': video_data,
                'comments': comments,
                'comment_dates': comment_dates,
                'user_levels': user_levels,
                'locations': locations,
                'danmaku': danmaku,
                'cover_data': cover_data,
                'sentiment': sentiment_score,
                'keywords': keywords
            }
            self.finished_signal.emit(result, "")
        except Exception as e:
            self.finished_signal.emit({}, str(e))
