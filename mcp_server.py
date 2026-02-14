import logging
import json
import os
import sys
from mcp.server.fastmcp import FastMCP
from core.crawler import BilibiliCrawler
from core.config import APP_VERSION

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bilibili_mcp')

# Initialize FastMCP
mcp = FastMCP("bilibili-downloader")

# Determine Base Directory and Data Directory
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    base_dir = os.path.dirname(sys.executable)
else:
    # Running from source
    base_dir = os.path.dirname(os.path.abspath(__file__))

data_dir = os.path.join(base_dir, 'bilibili_data')
logger.info(f"Base Directory: {base_dir}")
logger.info(f"Data Directory: {data_dir}")

# Initialize Crawler with custom data_dir
crawler = BilibiliCrawler(data_dir=data_dir)

# Force initialization of directories to ensure they exist and we can get absolute paths
if not os.path.exists(crawler.download_dir):
    os.makedirs(crawler.download_dir)

logger.info(f"MCP Server started. Download directory: {os.path.abspath(crawler.download_dir)}")

def _to_absolute_path(path_str):
    if path_str and not os.path.isabs(path_str):
        return os.path.abspath(path_str)
    return path_str

@mcp.tool()
def search_popular_videos(page: int = 1) -> str:
    """
    Search for popular videos on Bilibili.
    
    Args:
        page: The page number to retrieve (default: 1).
        
    Returns:
        JSON string containing popular videos list.
    """
    try:
        logger.info(f"Searching popular videos, page: {page}")
        data = crawler.get_popular_videos(page)
        # Ensure data is serializable
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error searching popular videos: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def get_video_info(bvid: str) -> str:
    """
    Get detailed information for a specific video.
    
    Args:
        bvid: The Bilibili Video ID (e.g., BV1xx...).
        
    Returns:
        JSON string containing video details.
    """
    try:
        logger.info(f"Getting video info for: {bvid}")
        data = crawler.get_video_info(bvid)
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def download_video(bvid: str) -> str:
    """
    Download a video by its BVID.
    
    Args:
        bvid: The Bilibili Video ID.
        
    Returns:
        JSON string containing the result of the download operation.
        Includes absolute paths to the downloaded files.
    """
    try:
        logger.info(f"Downloading video: {bvid}")
        # Using default settings for download
        result = crawler.download_video(bvid)
        
        # Convert paths to absolute paths for better UX
        if isinstance(result, dict):
            for key in ['video_path', 'audio_path', 'output_path', 'download_dir']:
                if key in result and result[key]:
                    result[key] = _to_absolute_path(result[key])
            
            # Add explicit absolute path field
            if 'output_path' in result and result['output_path']:
                 result['absolute_path'] = result['output_path']
            elif 'video_path' in result and result['video_path']:
                 result['absolute_path'] = result['video_path']
                 
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def get_download_path() -> str:
    """
    Get the absolute path to the download directory.
    
    Returns:
        The absolute path string.
    """
    return os.path.abspath(crawler.download_dir)

@mcp.tool()
def get_version() -> str:
    """
    Get the current version of the Bilibili Downloader.
    
    Returns:
        The version string.
    """
    return APP_VERSION

if __name__ == "__main__":
    mcp.run()
