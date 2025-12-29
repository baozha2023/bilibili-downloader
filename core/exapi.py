import requests
import logging
import re

logger = logging.getLogger('bilibili_core.exapi')

class ExAPI:
    """
    负责非B站API调用 (如Gitee, GitHub)
    """
    GITEE_API_BASE = "https://gitee.com/api/v5/repos"
    GITHUB_BASE = "https://github.com"
    ALIYUN_PYPI_MIRROR = "https://mirrors.aliyun.com/pypi/simple/"

    def get_gitee_tags(self, repo):
        """获取Gitee仓库的Tags"""
        url = f"{self.GITEE_API_BASE}/{repo}/tags"
        try:
            logger.info(f"正在从Gitee获取版本: {url}")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Gitee API请求失败: {e}")
        return None

    def get_github_releases_page(self, repo):
        """获取GitHub Releases页面HTML"""
        url = f"{self.GITHUB_BASE}/{repo}/releases"
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            logger.info(f"正在解析Releases页面: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Releases页面解析失败: {response.status_code}")
        except Exception as e:
            logger.error(f"GitHub页面请求失败: {e}")
        return None

    def get_github_assets_page(self, repo, tag):
        """获取GitHub Assets页面HTML"""
        url = f"{self.GITHUB_BASE}/{repo}/releases/expanded_assets/{tag}"
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logger.error(f"GitHub Assets页面请求失败: {e}")
        return None

    def get_gitee_repo_url(self, repo):
        return f"https://gitee.com/{repo}.git"

    def get_github_source_zip_url(self, repo, tag):
        return f"{self.GITHUB_BASE}/{repo}/archive/refs/tags/{tag}.zip"
