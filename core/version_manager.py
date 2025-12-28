import subprocess
import os
import shutil
import logging
import sys
import tempfile
import zipfile
import requests
import re
from core.config import APP_VERSION

logger = logging.getLogger('bilibili_desktop')

class VersionManager:
    """
    版本管理核心类
    负责与Gitee/GitHub交互，获取版本列表，切换版本等操作
    """
    
    SOURCE_GITEE = "gitee"
    SOURCE_GITHUB = "github"
    
    GITEE_REPO = "bzJAVA/bilibili-downloader"
    GITHUB_REPO = "baozha2023/bilibili-downloader"

    def __init__(self, main_window):
        self.main_window = main_window
        self.cwd = self._get_base_dir()
        self.git_exe = self._get_git_executable()

    def _get_base_dir(self):
        """获取当前运行的基础目录"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.getcwd()

    def _get_git_executable(self):
        """获取Git可执行文件路径"""
        # 1. 环境变量
        env_git = os.environ.get('GIT_PYTHON_GIT_EXECUTABLE')
        if env_git and os.path.exists(env_git):
            return env_git

        # 2. 打包环境下的集成Git
        paths_to_check = [
            os.path.join(self.cwd, 'git', 'cmd', 'git.exe'),
            os.path.join(self.cwd, 'git', 'bin', 'git.exe'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'git', 'cmd', 'git.exe'),
        ]
        
        for path in paths_to_check:
            if os.path.exists(path):
                return path

        # 3. 系统PATH
        system_git = shutil.which('git')
        return system_git if system_git else 'git'

    def check_git_available(self):
        """检查git是否可用"""
        try:
            subprocess.run([self.git_exe, '--version'], check=True, capture_output=True, 
                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            return True
        except Exception:
            return False

    def get_versions(self, source=SOURCE_GITEE):
        """根据源获取版本列表"""
        if source == self.SOURCE_GITHUB:
            return self._get_github_versions()
        else:
            return self._get_gitee_versions()

    def _get_gitee_versions(self):
        """从Gitee获取版本列表"""
        api_url = f"https://gitee.com/api/v5/repos/{self.GITEE_REPO}/tags"
        versions = []
        
        try:
            logger.info(f"正在从Gitee获取版本: {api_url}")
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                for tag_info in response.json():
                    versions.append({
                        'tag': tag_info.get('name'),
                        'date': tag_info.get('commit', {}).get('date', ''),
                        'message': tag_info.get('message', '').strip() or "暂无描述"
                    })
                return self._sort_versions(versions)
        except Exception as e:
            logger.error(f"Gitee API失败: {e}")

        # Fallback to git ls-remote if API fails
        return self._get_remote_tags_via_git(f"https://gitee.com/{self.GITEE_REPO}.git")

    def _get_github_versions(self):
        """从GitHub获取版本列表 (使用Releases API，失败则回退到HTML解析)"""
        api_url = f"https://api.github.com/repos/{self.GITHUB_REPO}/releases"
        versions = []
        
        try:
            logger.info(f"正在从GitHub获取版本: {api_url}")
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                for release in response.json():
                    versions.append({
                        'tag': release.get('tag_name'),
                        'date': release.get('published_at', ''),
                        'message': release.get('body', '').strip() or release.get('name', '暂无描述'),
                        'assets': release.get('assets', [])
                    })
                return self._sort_versions(versions)
            else:
                logger.warning(f"GitHub API返回非200状态码: {response.status_code}, {response.text}")
                logger.info("尝试使用HTML解析作为Fallback...")
                return self._get_github_versions_html_fallback()
                
        except Exception as e:
            logger.error(f"GitHub API失败: {e}")
            logger.info("尝试使用HTML解析作为Fallback...")
            return self._get_github_versions_html_fallback()
            
        return []

    def _get_github_versions_html_fallback(self):
        """GitHub HTML解析 (Fallback)"""
        tags_url = f"https://github.com/{self.GITHUB_REPO}/tags"
        versions = []
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            logger.info(f"正在解析Tags页面: {tags_url}")
            response = requests.get(tags_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                html = response.text
                tag_pattern = r'href=["\'](.*?/releases/tag/([^"\']+))["\']'
                tags = re.findall(tag_pattern, html)
                
                seen_tags = set()
                for _, tag_name in tags:
                    if tag_name not in seen_tags:
                        versions.append({
                            'tag': tag_name,
                            'date': 'N/A',
                            'message': 'GitHub Tag (API Limited)',
                            'assets': None # 标记为None，后续按需获取
                        })
                        seen_tags.add(tag_name)
                        
                return self._sort_versions(versions)
            else:
                logger.error(f"Tags页面解析失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"HTML解析失败: {e}")
            
        return []

    def _get_remote_tags_via_git(self, repo_url):
        """使用git ls-remote获取版本 (备用方案)"""
        if not self.check_git_available():
            return []
            
        versions = []
        try:
            cmd = [self.git_exe, 'ls-remote', '--tags', '--refs', repo_url]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8',
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            for line in result.stdout.strip().split('\n'):
                parts = line.split('\t')
                if len(parts) > 1:
                    tag = parts[1].replace('refs/tags/', '')
                    versions.append({
                        'tag': tag,
                        'date': 'N/A',
                        'message': 'Remote Tag (API Unavailable)'
                    })
            return self._sort_versions(versions)
        except Exception as e:
            logger.error(f"Git ls-remote失败: {e}")
            return []

    def _sort_versions(self, versions):
        """版本号排序"""
        try:
            versions.sort(key=lambda x: [int(u) for u in x['tag'].lower().replace('v', '').split('.')], reverse=True)
        except:
            versions.sort(key=lambda x: x['tag'], reverse=True)
        return versions

    def get_current_version(self):
        return APP_VERSION

    def check_python_available(self):
        """检查是否有可用的 Python 环境"""
        return self._get_system_python() is not None

    def _get_system_python(self):
        """获取系统 Python 路径"""
        # 1. 环境变量
        env_python = os.environ.get('PYTHON_EXECUTABLE')
        if env_python and os.path.exists(env_python):
            return env_python
            
        # 2. 系统PATH
        system_python = shutil.which('python')
        if system_python:
            try:
                subprocess.run([system_python, '--version'], check=True, capture_output=True, 
                             creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                return system_python
            except:
                pass
        return None

    def switch_version(self, tag, source=SOURCE_GITEE, release_assets=None):
        """
        切换版本
        Gitee: 下载源码 -> 编译 -> 替换
        GitHub: 下载Release -> 解压 -> 替换 (Fallback: 源码编译)
        """
        if source == self.SOURCE_GITEE:
            return self._update_from_source_code(tag)
        else:
            return self._update_from_github_release(tag, release_assets)

    def _update_from_source_code(self, tag):
        """从源码编译更新 (Gitee)"""
        if not self.check_git_available():
            return False, "Git环境不可用"
            
        python_exe = self._get_system_python()
        if not python_exe:
            return False, "未检测到本地Python环境，无法从Gitee编译更新。\n请安装Python或选择GitHub源下载编译好的版本。"

        temp_dir = tempfile.mkdtemp(prefix="bilibili_update_src_")
        try:
            logger.info(f"正在下载源码: {tag}")
            repo_url = f"https://gitee.com/{self.GITEE_REPO}.git"
            subprocess.run([self.git_exe, 'clone', '--depth', '1', '--branch', tag, repo_url, temp_dir], 
                         check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            return self._build_and_update(temp_dir, python_exe)
            
        except Exception as e:
            logger.error(f"源码更新失败: {e}")
            return False, f"更新失败: {e}"

    def _build_and_update(self, source_dir, python_exe):
        """执行编译和更新流程"""
        try:
            # 安装依赖
            req_file = os.path.join(source_dir, 'requirements.txt')
            if os.path.exists(req_file):
                logger.info("安装依赖...")
                subprocess.run([python_exe, '-m', 'pip', 'install', '-r', req_file, 
                              '-i', 'https://mirrors.aliyun.com/pypi/simple/'], 
                              check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            # 编译
            build_script = os.path.join(source_dir, 'build.py')
            if not os.path.exists(build_script):
                return False, "源码中缺少build.py"
                
            logger.info("开始编译...")
            subprocess.run([python_exe, build_script], cwd=source_dir, check=True)
            
            new_build_dir = os.path.join(source_dir, 'dist', 'bilibili_downloader')
            return self._apply_update(new_build_dir, source_dir)
        except Exception as e:
             return False, f"编译失败: {e}"

    def _update_from_github_release(self, tag, assets):
        """从GitHub Release下载更新 (支持 fallback 到源码下载)"""
        
        # 1. 尝试寻找预编译包 (.zip)
        target_asset = None
        
        # 如果 assets 是 None (来自 HTML Fallback)，尝试获取 expanded assets
        if assets is None:
             logger.info(f"正在检查版本 {tag} 的 Assets...")
             assets = self._fetch_github_assets_html(tag)
        
        if assets:
            # Priority 1: Look for zip with 'bilibili_downloader' in name
            for asset in assets:
                if asset.get('name', '').endswith('.zip') and 'bilibili_downloader' in asset.get('name', ''):
                    target_asset = asset
                    break
            
            # Priority 2: Look for any zip file
            if not target_asset:
                for asset in assets:
                    if asset.get('name', '').endswith('.zip'):
                        target_asset = asset
                        break
        
        # 2. 如果找到了预编译包 -> 直接下载
        if target_asset:
            return self._download_and_extract_zip(target_asset['browser_download_url'])
            
        # 3. 如果没找到 -> Fallback 到源码编译
        logger.warning(f"版本 {tag} 未找到预编译包，尝试源码编译...")
        python_exe = self._get_system_python()
        if not python_exe:
            return False, f"版本 {tag} 未提供预编译包(exe)，且检测到您的电脑未安装Python，无法进行源码编译。"
            
        return self._update_from_github_source_zip(tag, python_exe)

    def _fetch_github_assets_html(self, tag):
        """从Expanded Assets页面解析下载链接"""
        url = f"https://github.com/{self.GITHUB_REPO}/releases/expanded_assets/{tag}"
        assets = []
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                html = resp.text
                # Match download links
                pattern = r'href=["\'](.*?/releases/download/.*?/(.*?\.zip))["\']'
                matches = re.findall(pattern, html)
                for url_part, filename in matches:
                    if url_part.startswith('http'):
                        download_url = url_part
                    else:
                        download_url = f"https://github.com{url_part}"
                        
                    assets.append({
                        'name': filename,
                        'browser_download_url': download_url
                    })
        except Exception as e:
            logger.error(f"解析Assets失败: {e}")
        return assets

    def _update_from_github_source_zip(self, tag, python_exe):
        """下载GitHub源码Zip并编译"""
        download_url = f"https://github.com/{self.GITHUB_REPO}/archive/refs/tags/{tag}.zip"
        temp_dir = tempfile.mkdtemp(prefix="bilibili_gh_src_")
        zip_path = os.path.join(temp_dir, "source.zip")
        
        try:
            logger.info(f"正在下载源码Zip: {download_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            with requests.get(download_url, headers=headers, stream=True) as r:
                r.raise_for_status()
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            logger.info("解压源码...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                
            # GitHub zip 解压后通常是 repo-tag 文件夹
            extracted_root = None
            for item in os.listdir(temp_dir):
                if os.path.isdir(os.path.join(temp_dir, item)) and item != "__MACOSX":
                    extracted_root = os.path.join(temp_dir, item)
                    break
            
            if not extracted_root:
                return False, "源码解压结构异常"
                
            return self._build_and_update(extracted_root, python_exe)
            
        except Exception as e:
            logger.error(f"GitHub源码更新失败: {e}")
            return False, f"下载源码失败: {e}"

    def _download_and_extract_zip(self, download_url):
        """下载并解压预编译包"""
        temp_dir = tempfile.mkdtemp(prefix="bilibili_update_pkg_")
        zip_path = os.path.join(temp_dir, "update.zip")
        
        try:
            logger.info(f"正在下载: {download_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            with requests.get(download_url, headers=headers, stream=True) as r:
                r.raise_for_status()
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            logger.info("正在解压...")
            extract_dir = os.path.join(temp_dir, "extracted")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # 寻找解压后的根目录
            new_build_dir = os.path.join(extract_dir, 'bilibili_downloader')
            if not os.path.exists(new_build_dir):
                if os.path.exists(os.path.join(extract_dir, 'bilibili_downloader.exe')):
                    new_build_dir = extract_dir
                else:
                    # 尝试查找任意包含exe的子目录
                    found = False
                    for root, dirs, files in os.walk(extract_dir):
                        if 'bilibili_downloader.exe' in files:
                            new_build_dir = root
                            found = True
                            break
                    
                    if not found:
                        logger.error(f"解压后未找到exe. 目录结构: {os.listdir(extract_dir)}")
                        return False, "解压后的文件结构不正确"
            
            return self._apply_update(new_build_dir, temp_dir)

        except Exception as e:
            logger.error(f"下载更新包失败: {e}")
            return False, f"下载或解压失败: {e}"

    def _apply_update(self, new_dir, temp_root):
        """应用更新 (生成批处理脚本并重启)"""
        if not os.path.exists(os.path.join(new_dir, 'bilibili_downloader.exe')):
            return False, "新版本中未找到可执行文件"

        current_dir = self.cwd
        bat_path = os.path.join(os.path.dirname(current_dir), 'update_bilibili.bat')
        
        # 批处理脚本：等待主程序退出 -> 复制文件 -> 重启 -> 清理
        batch_content = f"""
@echo off
chcp 65001
echo 正在更新 Bilibili Downloader...

:check_lock
echo 等待主程序关闭...
timeout /t 2 /nobreak > nul
2>nul (
  >>"{os.path.join(current_dir, 'bilibili_downloader.exe')}" (call )
) && (
  echo 主程序已关闭。
) || (
  echo 主程序仍在运行，正在重试...
  goto check_lock
)

echo 正在复制文件...
xcopy /E /Y /I "{new_dir}" "{current_dir}"

if %errorlevel% neq 0 (
    echo 更新失败！
    pause
    exit /b %errorlevel%
)

echo 更新完成，正在重启...
start "" "{os.path.join(current_dir, 'bilibili_downloader.exe')}"

echo 清理临时文件...
rd /s /q "{temp_root}"
del "%~f0"
"""
        try:
            with open(bat_path, 'w', encoding='gbk') as f:
                f.write(batch_content)
            
            subprocess.Popen(['cmd', '/c', bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            return True, "更新准备就绪，程序即将重启..."
        except Exception as e:
            return False, f"生成更新脚本失败: {e}"
