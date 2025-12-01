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

    def get_favorite_resources(self, media_id, page=1):
        """获取收藏夹内容"""
        url = f'https://api.bilibili.com/x/v3/fav/resource/list?media_id={media_id}&pn={page}&ps=20'
        response = self.network.make_request(url)
        if isinstance(response, dict):
            return response.get('data', {}).get('medias', [])
        return []
    
    def get_video_info(self, bvid):
        """获取视频详细信息"""
        url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
        return self.network.make_request(url)
    
    def get_video_download_url(self, bvid, quality_preference='1080p', codec_preference='H.264/AVC', audio_quality_preference='高音质 (Hi-Res/Dolby)'):
        """
        获取视频下载链接
        quality_preference: '4k', '1080p', '720p', etc.
        codec_preference: 'H.264/AVC', 'H.265/HEVC', 'AV1'
        audio_quality_preference: '高音质 (Hi-Res/Dolby)', '中等音质', '低音质'
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
            '8K 超高清': 127,
            '4K 超清': 120,
            '1080P+ 高码率': 112,
            '1080P 高清': 80,
            '720P 高清': 64,
            '480P 清晰': 32,
            '360P 流畅': 16,
        }
        
        target_qn = quality_map.get(quality_preference, 80)
        
        # 权限控制
        if not is_login:
            # 未登录强制 <= 720p
            if target_qn > 64:
                target_qn = 64
                logger.info("未登录用户，画质限制为 720p")
        
        # fnval参数说明: 4048 包含DASH, HDR, 4K等
        fnval = 4048
        # 如果请求的是4K或8K，确保fourk=1
        fourk = 1 if target_qn >= 120 else 0
        
        download_url_api = f'https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn={target_qn}&fnval={fnval}&fourk={fourk}'
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
            
        # 编码映射
        # 7: AVC, 12: HEVC, 13: AV1
        codec_map = {
            'H.264/AVC': 7,
            'H.265/HEVC': 12,
            'AV1': 13
        }
        target_codec = codec_map.get(codec_preference, 7)
        
        # 筛选逻辑优化：
        # 优先级：Quality > Codec
        
        best_video = None
        
        # 1. 尝试找到 Quality 匹配且 Codec 匹配的流
        candidates = [s for s in video_streams if s.get('id') == target_qn]
        if candidates:
            # 在匹配画质的流中找匹配编码的
            for s in candidates:
                if s.get('codecid') == target_codec:
                    best_video = s
                    break
            # 如果没找到匹配编码的，就取画质匹配的第一个（或者可以进一步策略，比如HEVC > AVC）
            if not best_video:
                # 尝试找HEVC作为备选 (节省带宽)
                for s in candidates:
                    if s.get('codecid') == 12:
                        best_video = s
                        break
                # 还是没有，就取第一个
                if not best_video:
                    best_video = candidates[0]
        
        # 2. 如果没有找到目标画质，尝试降级查找 (找 <= target_qn 的最大值)
        if not best_video:
            logger.info(f"未找到目标画质 {target_qn}，尝试降级查找...")
            
            # 按画质降序排序
            video_streams.sort(key=lambda x: x.get('id', 0), reverse=True)
            
            # 找到第一个 <= target_qn 的画质
            fallback_qn = None
            for s in video_streams:
                if s.get('id') <= target_qn:
                    fallback_qn = s.get('id')
                    break
            
            if fallback_qn:
                logger.info(f"已降级到画质: {self._get_quality_desc(fallback_qn)}")
                # 在降级画质中找匹配编码
                candidates = [s for s in video_streams if s.get('id') == fallback_qn]
                for s in candidates:
                    if s.get('codecid') == target_codec:
                        best_video = s
                        break
                if not best_video:
                    best_video = candidates[0]
                    logger.info(f"降级画质中未找到目标编码 {self._get_codec_desc(target_codec)}，使用: {self._get_codec_desc(best_video.get('codecid'))}")
            else:
                # 如果连降级都找不到（理论上不可能，除非target_qn比所有流都小），取最小的
                best_video = video_streams[-1]
                logger.warning("无法找到合适画质，使用最低画质")

        # 音频选择逻辑
        best_audio = None
        if audio_streams:
            # 30280: 192K, 30232: 132K, 30216: 64K
            # 优先下载的视频音质: 高音质 (Hi-Res/Dolby), 中等音质, 低音质
            
            # 按bandwidth降序
            audio_streams.sort(key=lambda x: x.get('bandwidth', 0), reverse=True)
            
            if "低音质" in audio_quality_preference:
                best_audio = audio_streams[-1]
            elif "中等音质" in audio_quality_preference and len(audio_streams) > 1:
                # 取中间的，或者如果不确定，取倒数第二个
                mid_index = len(audio_streams) // 2
                best_audio = audio_streams[mid_index]
            else:
                # 默认高音质
                best_audio = audio_streams[0]
            
        return {
            'video_url': best_video.get('baseUrl'),
            'audio_url': best_audio.get('baseUrl') if best_audio else None,
            'title': video_info['data'].get('title', f'video_{bvid}'),
            'quality': best_video.get('id'),
            'quality_desc': self._get_quality_desc(best_video.get('id')),
            'codecid': best_video.get('codecid'),
            'codec_desc': self._get_codec_desc(best_video.get('codecid')),
            'video_info': video_info['data']
        }

    def _get_codec_desc(self, codecid):
        mapping = {
            7: "AVC/H.264",
            12: "HEVC/H.265", 
            13: "AV1"
        }
        return mapping.get(codecid, f"Codec-{codecid}")

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
    
    def get_history(self, page=1):
        """获取历史记录"""
        # 游标分页: view_at, max 0, ps 20
        # 但web接口通常是：https://api.bilibili.com/x/web-interface/history/cursor?ps=20&type=archive
        # 或者旧接口: https://api.bilibili.com/x/v2/history?pn={page}&ps=20 (可能已废弃)
        # 使用cursor接口更稳，但分页麻烦。这里尝试简化，只获取最近的
        # 这里的page参数可能无法直接映射到cursor接口，除非我们保存了cursor
        # 为了简单，我们只获取第一页，或者如果真的需要分页，需要重构逻辑
        # 暂时只实现获取最新20条，或者如果传入了view_at参数
        
        # 尝试使用cursor接口
        # max=0 表示获取最新的
        url = f'https://api.bilibili.com/x/web-interface/history/cursor?ps=20&type=archive'
        # 如果需要翻页，通常需要传入 view_at (上一页最后一条的时间戳)
        # 暂时简单实现
        response = self.network.make_request(url)
        if isinstance(response, dict):
            return response.get('data', {}).get('list', [])
        return []
