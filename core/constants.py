# 视频画质常量
class VideoQuality:
    Q_8K = "8K 超高清"
    Q_DOLBY = "Dolby Vision"
    Q_HDR = "HDR"
    Q_4K = "4K 超清"
    Q_1080P_60 = "1080P 60帧"
    Q_1080P_PLUS = "1080P 高码率"  # 112
    Q_1080P = "1080P 高清"        # 80
    Q_720P_60 = "720P 60帧"       # 74
    Q_720P = "720P 高清"          # 64
    Q_480P = "480P 清晰"          # 32
    Q_360P = "360P 流畅"          # 16

    # 映射到 B站 API ID
    QUALITY_MAP = {
        Q_8K: 127,
        Q_DOLBY: 126,
        Q_HDR: 125,
        Q_4K: 120,
        Q_1080P_60: 116,
        Q_1080P_PLUS: 112,
        Q_1080P: 80,
        Q_720P_60: 74,
        Q_720P: 64,
        Q_480P: 32,
        Q_360P: 16,
    }

    # 反向映射 (ID -> Description)
    # 注意：可能有多个描述对应同一个ID，这里只保留主描述
    ID_TO_DESC = {
        127: Q_8K,
        126: Q_DOLBY,
        125: Q_HDR,
        120: Q_4K,
        116: Q_1080P_60,
        112: Q_1080P_PLUS,
        80: Q_1080P,
        74: Q_720P_60,
        64: Q_720P,
        32: Q_480P,
        16: Q_360P
    }

    @classmethod
    def get_qn(cls, quality_desc):
        """根据描述获取QN值，默认为80 (1080P)"""
        return cls.QUALITY_MAP.get(quality_desc, 80)

    @classmethod
    def get_desc(cls, qn):
        """根据QN值获取描述"""
        return cls.ID_TO_DESC.get(qn, f"QN-{qn}")


# 视频编码常量
class VideoCodec:
    AVC = "H.264/AVC"
    HEVC = "H.265/HEVC"
    AV1 = "AV1"

    CODEC_MAP = {
        AVC: 7,
        HEVC: 12,
        AV1: 13
    }

    ID_TO_DESC = {
        7: AVC,
        12: HEVC,
        13: AV1
    }

    @classmethod
    def get_codecid(cls, codec_desc):
        """根据描述获取CodecID，默认为7 (AVC)"""
        return cls.CODEC_MAP.get(codec_desc, 7)
    
    @classmethod
    def get_desc(cls, codecid):
        """根据CodecID获取描述"""
        return cls.ID_TO_DESC.get(codecid, f"Codec-{codecid}")


# 音频质量常量
class AudioQuality:
    HI_RES = "高音质 (Hi-Res/Dolby)"
    MEDIUM = "中等音质"
    LOW = "低音质"

    # 这里主要用于UI显示和偏好选择，API中是根据bandwidth排序选择
    ALL_QUALITIES = [HI_RES, MEDIUM, LOW]
