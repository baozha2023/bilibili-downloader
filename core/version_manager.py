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
from core.exapi import ExAPI

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

    # Regex Patterns
    TAG_PATTERN = r'href=["\'](.*?/releases/tag/([^"\']+))["\'][^>]*class=["\'][^"\']*Link--primary'
    MARKDOWN_BODY_PATTERN = r'class="markdown-body[^"]*">(.*?)</div>'
    PRE_BLOCK_PATTERN = r'<pre[^>]*>(.*?)</pre>'
    EXPANDED_ASSETS_PATTERN = r'href=["\'](.*?/releases/download/.*?/(.*?\.zip))["\']'

    def __init__(self):
        self.cwd = self._get_base_dir()
        self.git_exe = self._get_git_executable()
        self.exapi = ExAPI()

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
        return self._get_gitee_versions()

    def _get_gitee_versions(self):
        """从Gitee获取版本列表"""
        try:
            tags_data = self.exapi.get_gitee_tags(self.GITEE_REPO)
            
            if tags_data:
                versions = []
                for tag_info in tags_data:
                    versions.append({
                        'tag': tag_info.get('name'),
                        'date': tag_info.get('commit', {}).get('date', ''),
                        'message': tag_info.get('message', '').strip() or "暂无描述"
                    })
                return self._sort_versions(versions)
        except Exception as e:
            logger.error(f"Gitee API失败: {e}")

        # Fallback to git ls-remote if API fails
        return []

    def _get_github_versions(self):
        """从GitHub获取版本列表 (直接使用HTML解析)"""
        versions = []
        
        try:
            html_content = self.exapi.get_github_releases_page(self.GITHUB_REPO)
            
            if html_content:
                return self._parse_github_releases_html(html_content)
                
        except Exception as e:
            logger.error(f"HTML解析失败: {e}")
            
        return []

    def _parse_github_releases_html(self, html_content):
        """解析GitHub Releases HTML"""
        versions = []
        matches = list(re.finditer(self.TAG_PATTERN, html_content))
        
        seen_tags = set()
        for i, match in enumerate(matches):
            tag_name = match.group(2)
            
            if tag_name in seen_tags:
                continue
            seen_tags.add(tag_name)
            
            # 确定搜索范围
            start_pos = match.end()
            end_pos = matches[i+1].start() if i+1 < len(matches) else len(html_content)
            snippet = html_content[start_pos:end_pos]
            
            message = self._extract_release_message(snippet)

            versions.append({
                'tag': tag_name,
                'date': 'N/A',
                'message': message,
                'assets': None
            })
                
        return self._sort_versions(versions)

    def _extract_release_message(self, snippet):
        """从HTML片段中提取版本描述"""
        message = "暂无详细描述"
        
        # 1. Markdown Body
        md_match = re.search(self.MARKDOWN_BODY_PATTERN, snippet, re.DOTALL)
        if md_match:
            raw_html = md_match.group(1)
            message = self._clean_html(raw_html)
        else:
            # 2. Pre block
            pre_match = re.search(self.PRE_BLOCK_PATTERN, snippet, re.DOTALL)
            if pre_match:
                raw_html = pre_match.group(1)
                message = self._clean_html(raw_html)
        
        return message

    def _clean_html(self, raw_html):
        """去除HTML标签并处理实体"""
        message = re.sub(r'<[^>]+>', '', raw_html).strip()
        replacements = {
            '&nbsp;': ' ',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&amp;': '&'
        }
        for code, char in replacements.items():
            message = message.replace(code, char)
        return message

    def _sort_versions(self, versions):
        """版本号排序"""
        try:
            versions.sort(key=lambda x: [int(u) for u in x['tag'].lower().replace('v', '').split('.')], reverse=True)
        except Exception:
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
            except Exception:
                pass
        return None

    def switch_version(self, tag, source=SOURCE_GITEE, release_assets=None):
        """切换版本"""
        if source == self.SOURCE_GITEE:
            return self._update_from_source_code(tag)
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
            repo_url = self.exapi.get_gitee_repo_url(self.GITEE_REPO)
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
                              '-i', self.exapi.ALIYUN_PYPI_MIRROR], 
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
        # 1. 获取Assets
        if assets is None:
             logger.info(f"正在检查版本 {tag} 的 Assets...")
             assets = self._fetch_github_assets_html(tag)
        
        # 2. 寻找最佳下载目标
        target_asset = self._find_best_asset(assets)
        
        # 3. 下载或Fallback
        if target_asset:
            return self._download_and_extract_zip(target_asset['browser_download_url'])
            
        logger.warning(f"版本 {tag} 未找到预编译包，尝试源码编译...")
        python_exe = self._get_system_python()
        if not python_exe:
            return False, f"版本 {tag} 未提供预编译包(exe)，且检测到您的电脑未安装Python，无法进行源码编译。"
            
        return self._update_from_github_source_zip(tag, python_exe)

    def _find_best_asset(self, assets):
        """寻找最佳的zip资源"""
        if not assets:
            return None
            
        # Priority 1: 'bilibili_downloader' in name
        for asset in assets:
            name = asset.get('name', '')
            if name.endswith('.zip') and 'bilibili_downloader' in name:
                return asset
        
        # Priority 2: Any zip
        for asset in assets:
            if asset.get('name', '').endswith('.zip'):
                return asset
                
        return None

    def _fetch_github_assets_html(self, tag):
        """从Expanded Assets页面解析下载链接"""
        assets = []
        try:
            text = self.exapi.get_github_assets_page(self.GITHUB_REPO, tag)
            if text:
                matches = re.findall(self.EXPANDED_ASSETS_PATTERN, text)
                for url_part, filename in matches:
                    download_url = url_part if url_part.startswith('http') else f"https://github.com{url_part}"
                    assets.append({
                        'name': filename,
                        'browser_download_url': download_url
                    })
        except Exception as e:
            logger.error(f"解析Assets失败: {e}")
        return assets

    def _update_from_github_source_zip(self, tag, python_exe):
        """下载GitHub源码Zip并编译"""
        download_url = self.exapi.get_github_source_zip_url(self.GITHUB_REPO, tag)
        temp_dir = tempfile.mkdtemp(prefix="bilibili_gh_src_")
        zip_path = os.path.join(temp_dir, "source.zip")
        
        try:
            self._download_file(download_url, zip_path)
            
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
            self._download_file(download_url, zip_path)
            
            logger.info("正在解压...")
            extract_dir = os.path.join(temp_dir, "extracted")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # 寻找解压后的根目录
            new_build_dir = self._find_build_dir_in_extracted(extract_dir)
            if not new_build_dir:
                return False, "解压后的文件结构不正确"
            
            return self._apply_update(new_build_dir, temp_dir)

        except Exception as e:
            logger.error(f"下载更新包失败: {e}")
            return False, f"下载或解压失败: {e}"

    def _download_file(self, url, save_path):
        """通用文件下载方法"""
        logger.info(f"正在下载: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        with requests.get(url, headers=headers, stream=True) as r:
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    def _find_build_dir_in_extracted(self, extract_dir):
        """在解压目录中查找构建目录"""
        target_dir = os.path.join(extract_dir, 'bilibili_downloader')
        if os.path.exists(target_dir):
            return target_dir
            
        if os.path.exists(os.path.join(extract_dir, 'bilibili_downloader.exe')):
            return extract_dir
            
        for root, dirs, files in os.walk(extract_dir):
            if 'bilibili_downloader.exe' in files:
                return root
        return None

    def _apply_update(self, new_dir, temp_root):
        """应用更新 (生成批处理脚本并重启)"""
        if not os.path.exists(os.path.join(new_dir, 'bilibili_downloader.exe')):
            return False, "新版本中未找到可执行文件"

        current_dir = self.cwd
        bat_path = os.path.join(os.path.dirname(current_dir), 'update_bilibili.bat')
        
        batch_content = self._generate_batch_script(current_dir, new_dir, temp_root)
        
        try:
            with open(bat_path, 'w', encoding='gbk') as f:
                f.write(batch_content)
            
            subprocess.Popen(['cmd', '/c', bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            return True, "更新准备就绪，程序即将重启..."
        except Exception as e:
            return False, f"生成更新脚本失败: {e}"

    def _generate_batch_script(self, current_dir, new_dir, temp_root):
        """生成更新批处理脚本内容"""
        exe_path = os.path.join(current_dir, 'bilibili_downloader.exe')
        return f"""
@echo off
chcp 65001
echo 正在更新 Bilibili Downloader...

:check_lock
echo 等待主程序关闭...
timeout /t 2 /nobreak > nul
2>nul (
  >>"{exe_path}" (call )
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
start "" "{exe_path}"

echo 清理临时文件...
rd /s /q "{temp_root}"
del "%~f0"
"""
