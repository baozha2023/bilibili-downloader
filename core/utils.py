import xml.etree.ElementTree as ET
import logging
import base64

logger = logging.getLogger('bilibili_core.utils')

def xor_cipher(data: bytes, key: bytes) -> bytes:
    """简单的XOR加密"""
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

def decrypt_data(encrypted_str):
    """解密数据"""
    try:
        key = b"bilibili_downloader_v5_secret_key"
        # 1. To bytes
        b64_bytes = encrypted_str.encode('utf-8')
        # 2. Base64 decode
        xor_bytes = base64.b64decode(b64_bytes)
        # 3. XOR
        data_bytes = xor_cipher(xor_bytes, key)
        # 4. To string
        return data_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"解密失败: {e}")
        return None

def parse_danmaku_xml(xml_bytes):
    """
    解析B站弹幕XML数据
    :param xml_bytes: XML字节数据
    :return: 弹幕列表
    """
    if not xml_bytes:
        return []

    try:
        root = ET.fromstring(xml_bytes)
        danmaku_list = []
        for d in root.findall('./d'):
            p_attr = d.get('p', '')
            text = d.text or ''
            if p_attr and text:
                p_parts = p_attr.split(',')
                if len(p_parts) >= 8:
                    danmaku_list.append({
                        'time': float(p_parts[0]),
                        'mode': int(p_parts[1]),
                        'fontsize': int(p_parts[2]),
                        'color': int(p_parts[3]),
                        'timestamp': int(p_parts[4]),
                        'pool': int(p_parts[5]),
                        'user_id': p_parts[6],
                        'dmid': p_parts[7],
                        'text': text
                    })
        return danmaku_list
    except Exception as e:
        logger.error(f"解析弹幕失败: {e}")
        return []

def format_size(size_bytes):
    """
    格式化文件大小
    """
    if size_bytes < 1024: return f"{size_bytes} B"
    elif size_bytes < 1024**2: return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3: return f"{size_bytes/1024**2:.1f} MB"
    return f"{size_bytes/1024**3:.2f} GB"
