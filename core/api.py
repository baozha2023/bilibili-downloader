import logging
from .network import NetworkManager

logger = logging.getLogger('bilibili_core.api')

class BilibiliAPI:
    """
    负责B站API调用
    """
    def __init__(self, network_manager: NetworkManager):
        self.network = network_manager
        
    def get_popular_videos(self, page=1):
        """获取B站热门视频列表"""
        url = f'https://api.bilibili.com/x/web-interface/popular?ps=20&pn={page}'
        response = self.network.make_request(url)
        if isinstance(response, dict):
            return response.get('data', {}).get('list', [])
        return []
    
    def get_video_info(self, bvid):
        """获取视频详细信息"""
        url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
        return self.network.make_request(url)
    
    def get_video_download_url(self, bvid, quality_preference='1080p'):
        """
        获取视频下载链接
        quality_preference: '4k', '1080p', '720p', etc.
        """
        # 1. 获取视频信息
        video_info = self.get_video_info(bvid)
        if not video_info or 'data' not in video_info:
            logger.error(f"无法获取视频 {bvid} 的信息")
            return None
        
        cid = video_info['data'].get('cid')
        if not cid:
            logger.error(f"无法获取视频 {bvid} 的cid")
            return None
        
        # 2. 确定请求的qn (Quality Number)
        # 默认策略
        target_qn = 80 # 1080p
        
        # 根据登录状态和偏好调整
        is_login = self.network.cookies and 'SESSDATA' in self.network.cookies
        
        # 映射表
        quality_map = {
            '4k': 120,
            '1080p+': 112,
            '1080p': 80,
            '720p': 64,
            '480p': 32,
            '360p': 16
        }
        
        target_qn = quality_map.get(quality_preference, 80)
        
        # 权限控制
        if not is_login:
            # 未登录强制 <= 720p
            if target_qn > 64:
                target_qn = 64
                logger.info("未登录用户，画质限制为 720p")
        
        # 注意：大会员检查通常需要单独的API，这里假设如果用户请求4k且已登录，就尝试请求
        # API会返回实际可用的最高画质
        
        # fnval=4048 (DASH格式, 包含HDR/4K等)
        download_url_api = f'https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn={target_qn}&fnval=4048&fourk=1'
        download_info = self.network.make_request(download_url_api)
        
        if not download_info or 'data' not in download_info:
            logger.error(f"无法获取视频 {bvid} 的下载链接")
            return None
        
        dash_data = download_info['data'].get('dash')
        if not dash_data:
            logger.error(f"视频 {bvid} 不支持DASH格式下载")
            return None
        
        # 3. 提取符合要求的流
        video_streams = dash_data.get('video', [])
        audio_streams = dash_data.get('audio', [])
        
        if not video_streams:
            return None
            
        # 按照id (qn) 排序
        video_streams.sort(key=lambda x: x.get('id', 0), reverse=True)
        
        # 寻找最接近target_qn的流
        best_video = None
        
        # 简单的筛选逻辑：
        # 如果有流的id == target_qn，选中
        # 否则选中 <= target_qn 的最高画质
        
        # 先尝试找完全匹配或更低
        for stream in video_streams:
            if stream.get('id', 0) <= target_qn:
                best_video = stream
                break
                
        # 如果没找到（比如所有流都比target_qn大？不太可能），就取最小的
        if not best_video:
            best_video = video_streams[-1]
            
        # 音频选最好的
        best_audio = None
        if audio_streams:
            audio_streams.sort(key=lambda x: x.get('bandwidth', 0), reverse=True)
            best_audio = audio_streams[0]
            
        return {
            'video_url': best_video.get('baseUrl'),
            'audio_url': best_audio.get('baseUrl') if best_audio else None,
            'title': video_info['data'].get('title', f'video_{bvid}'),
            'quality': best_video.get('id'),
            'quality_desc': self._get_quality_desc(best_video.get('id')),
            'video_info': video_info['data']
        }

    def _get_quality_desc(self, qn):
        mapping = {
            127: "8K", 126: "Dolby Vision", 125: "HDR", 120: "4K", 
            116: "1080p60", 112: "1080p+", 80: "1080p", 
            74: "720p60", 64: "720p", 32: "480p", 16: "360p"
        }
        return mapping.get(qn, f"QN-{qn}")

    def get_video_comments(self, aid, page=1):
        """获取视频评论"""
        url = f'https://api.bilibili.com/x/v2/reply?pn={page}&type=1&oid={aid}&sort=2'
        response = self.network.make_request(url)
        if isinstance(response, dict):
            return response.get('data', {}).get('replies', [])
        return []

    def get_video_danmaku(self, cid):
        """获取视频弹幕"""
        url = f'https://api.bilibili.com/x/v1/dm/list.so?oid={cid}'
        # 弹幕是XML，不需要JSON解析
        response = self.network.make_request(url, stream=False)
        # 注意：make_request在非JSON时可能返回bytes或None
        if isinstance(response, bytes):
            return response
        return None
