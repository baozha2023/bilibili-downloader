import json
import os
import logging
from core.crawler import BilibiliCrawler

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def verify_crawling():
    # Load cookies
    cookies = None
    config_path = os.path.join('bilibili_data', 'config', 'login_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            cookies = data.get('cookies')
            print("Loaded cookies from config")
    else:
        print("No login config found, proceeding without cookies")

    crawler = BilibiliCrawler(cookies=cookies)
    bvid = "BV1YWSiBjEZ2"
    
    print(f"\nVerifying video: {bvid}")
    
    # Test combinations
    test_cases = [
        ("1080P 高清", "H.264/AVC", "高音质 (Hi-Res/Dolby)"),
        ("4K 超清", "H.265/HEVC", "高音质 (Hi-Res/Dolby)"),
        ("1080P+ 高码率", "AV1", "中等音质"),
        ("720P 高清", "H.264/AVC", "低音质")
    ]
    
    for q, c, a in test_cases:
        print(f"\nTesting: Quality={q}, Codec={c}, Audio={a}")
        result = crawler.api.get_video_download_url(bvid, q, c, a)
        
        if result:
            print("Success!")
            print(f"  Title: {result.get('title')}")
            print(f"  Quality: {result.get('quality')} ({result.get('quality_desc')})")
            print(f"  Codec: {result.get('codecid')} ({result.get('codec_desc')})")
            print(f"  Video URL: {result.get('video_url')[:50]}...")
            print(f"  Audio URL: {result.get('audio_url')[:50]}..." if result.get('audio_url') else "  No Audio URL")
        else:
            print("Failed to get download URL")

if __name__ == "__main__":
    verify_crawling()
