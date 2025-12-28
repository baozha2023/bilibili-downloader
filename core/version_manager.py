import subprocess
import os
import shutil
import logging
import sys
import tempfile
import time
import requests
from core.config import APP_VERSION

logger = logging.getLogger('bilibili_desktop')

class VersionManager:
    """
    版本管理核心类
    负责与Git交互，获取版本列表，切换版本等操作
    Version Management Core Class
    Responsible for interacting with Git, retrieving version lists, switching versions, etc.
    """
    def __init__(self, main_window):
        self.main_window = main_window
        self.repo_url = "https://gitee.com/bzJAVA/bilibili-downloader.git"
        self.api_url = "https://gitee.com/api/v5/repos/bzJAVA/bilibili-downloader/tags"
        # 确定当前工作目录
        # Determine current working directory
        if getattr(sys, 'frozen', False):
            # 如果是打包后的环境，使用可执行文件所在目录
            # If running in a frozen (packaged) environment, use the directory of the executable
            self.cwd = os.path.dirname(sys.executable)
        else:
            self.cwd = os.getcwd()
        
        self.git_exe = self._get_git_executable()

    def _get_git_executable(self):
        """
        获取Git可执行文件路径
        优先查找打包环境下的本地Git，否则查找系统Git
        Get Git executable path
        Prioritize local Git in packaged environment, otherwise use system Git
        """
        # 1. 检查是否有环境变量指定的GIT
        env_git = os.environ.get('GIT_PYTHON_GIT_EXECUTABLE')
        if env_git and os.path.exists(env_git):
            return env_git

        # 2. 检查应用目录下的Git (打包集成模式)
        # MinGit通常结构: git/cmd/git.exe 或 git/bin/git.exe
        # Check relative to CWD
        paths_to_check = [
            os.path.join(self.cwd, 'git', 'cmd', 'git.exe'),
            os.path.join(self.cwd, 'git', 'bin', 'git.exe'),
            # Also check relative to project root if running from source
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'git', 'cmd', 'git.exe'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'git', 'bin', 'git.exe'),
        ]
        
        for path in paths_to_check:
            if os.path.exists(path):
                return path

        # 3. 检查系统PATH中的Git
        system_git = shutil.which('git')
        if system_git:
            return system_git

        # 4. 默认返回 'git'
        return 'git'

    def check_git_available(self):
        """
        检查git是否可用
        Check if git is available
        """
        try:
            subprocess.run([self.git_exe, '--version'], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            return True
        except Exception as e:
            logger.debug(f"Git不可用: {e}")
            return False

    def get_versions(self):
        """
        获取远程仓库的所有tag列表
        优先使用 Gitee API 获取详细信息（包括Tag描述），失败则回退到 git ls-remote
        Get all tags from remote repository
        Prioritize Gitee API to get details (including description), fallback to git ls-remote if failed
        """
        versions = []
        
        # 1. 尝试使用 Gitee API
        # 1. Try Gitee API
        try:
            logger.info(f"正在通过API获取版本列表: {self.api_url}")
            response = requests.get(self.api_url, timeout=10)
            if response.status_code == 200:
                tags = response.json()
                for tag_info in tags:
                    tag_name = tag_info.get('name')
                    message = tag_info.get('message', '').strip()
                    commit_date = tag_info.get('commit', {}).get('date', '')
                    
                    if tag_name:
                        versions.append({
                            'tag': tag_name,
                            'date': commit_date,
                            'message': message if message else "暂无描述"
                        })
                
                logger.info(f"API获取成功，共 {len(versions)} 个版本")
            else:
                logger.warning(f"API请求失败: {response.status_code}")
        except Exception as e:
            logger.error(f"API获取版本列表出错: {e}")

        # 如果API获取成功，直接返回
        if versions:
             # 排序 / Sort
            try:
                versions.sort(key=lambda x: [int(u) for u in x['tag'].lower().replace('v', '').split('.')], reverse=True)
            except:
                versions.sort(key=lambda x: x['tag'], reverse=True)
            return versions

        # 2. API失败，回退到 git ls-remote
        # 2. API failed, fallback to git ls-remote
        if not self.check_git_available():
            return []

        try:
            logger.info("API失败，正在使用 git ls-remote 获取远程版本列表...")
            # 使用 ls-remote 获取远程tags
            # git ls-remote --tags --refs https://...
            cmd = [self.git_exe, 'ls-remote', '--tags', '--refs', self.repo_url]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            for line in result.stdout.strip().split('\n'):
                parts = line.split('\t')
                if len(parts) > 1:
                    ref = parts[1]
                    # ref format: refs/tags/v1.0.0
                    tag = ref.replace('refs/tags/', '')
                    
                    # 由于 ls-remote 无法直接获取日期和提交信息，我们只能显示Tag
                    versions.append({
                        'tag': tag,
                        'date': 'N/A', # 无法获取
                        'message': 'Remote Tag (API Unavailable)' # 标记为API不可用
                    })
            
            # 排序 / Sort
            try:
                versions.sort(key=lambda x: [int(u) for u in x['tag'].lower().replace('v', '').split('.')], reverse=True)
            except:
                versions.sort(key=lambda x: x['tag'], reverse=True)
                
            return versions
        except Exception as e:
            logger.error(f"获取版本列表失败: {e}")
            return []

    def get_current_version(self):
        """
        获取当前版本信息
        Get current version info
        """
        # 由于移除了本地 .git，我们只能依赖配置文件中的版本号
        # Since local .git is removed, we rely on APP_VERSION
        return f"{APP_VERSION}"

    def switch_version(self, tag):
        """
        切换版本：下载源码 -> 编译 -> 替换
        Switch version: Download Source -> Compile -> Replace
        """
        if not self.check_git_available():
            return False, "Git环境不可用，无法切换版本"
            
        # 检查是否有名为 python 的命令可用 (编译需要)
        # Check if python is available
        python_exe = "python"
        
        # 优先使用集成的 Python 环境
        # Prioritize bundled Python environment
        bundled_python = os.path.join(self.cwd, 'python_embed', 'python.exe')
        if os.path.exists(bundled_python):
            python_exe = bundled_python
            logger.info(f"使用集成的 Python 环境: {python_exe}")
        else:
             # Fallback to system python
             python_exe = sys.executable if not getattr(sys, 'frozen', False) else "python"
             try:
                # 如果是打包环境，sys.executable 是 exe 本身，不能用来运行 py 脚本
                # 所以我们需要假设系统中有 python 环境
                if getattr(sys, 'frozen', False):
                     subprocess.run(["python", "--version"], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                     python_exe = "python"
             except:
                 return False, "切换版本需要编译环境，未检测到集成的 Python 或系统 Python。"

        temp_dir = tempfile.mkdtemp(prefix="bilibili_update_")
        try:
            logger.info(f"创建临时目录: {temp_dir}")
            
            # 1. Clone 指定 Tag 的源码
            # Clone source code of specified Tag
            logger.info(f"正在下载版本 {tag} 的源码...")
            clone_cmd = [self.git_exe, 'clone', '--depth', '1', '--branch', tag, self.repo_url, temp_dir]
            subprocess.run(clone_cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            # 2. 安装依赖 (可选，为了保险)
            # Install dependencies
            requirements_file = os.path.join(temp_dir, 'requirements.txt')
            if os.path.exists(requirements_file):
                logger.info("正在安装/更新依赖...")
                pip_cmd = [python_exe, '-m', 'pip', 'install', '-r', requirements_file, '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple']
                subprocess.run(pip_cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            # 3. 执行编译
            # Execute build
            build_script = os.path.join(temp_dir, 'build.py')
            if not os.path.exists(build_script):
                 return False, "下载的源码中不存在 build.py，无法编译。"
            
            logger.info("开始编译新版本...")
            # 注意：build.py 会在 temp_dir/dist/bilibili_downloader 生成文件
            build_cmd = [python_exe, build_script]
            # 我们需要在 temp_dir 下运行 build.py
            subprocess.run(build_cmd, cwd=temp_dir, check=True) # build.py might print to stdout, so we let it
            
            # 4. 验证编译结果
            # Verify build result
            new_build_dir = os.path.join(temp_dir, 'dist', 'bilibili_downloader')
            if not os.path.exists(new_build_dir):
                return False, "编译失败，未生成目标目录。"
            
            new_exe = os.path.join(new_build_dir, 'bilibili_downloader.exe')
            if not os.path.exists(new_exe):
                return False, "编译失败，未生成可执行文件。"

            # 5. 准备更新脚本 (Update Script)
            # Prepare update script
            logger.info("准备更新...")
            current_dir = self.cwd
            
            # 构造更新批处理脚本
            # Create update batch script
            bat_path = os.path.join(os.path.dirname(current_dir), 'update_bilibili.bat')
            # 如果是在开发环境(未打包)，current_dir 是项目根目录，不要覆盖自己
            # 但 switch_version 主要是给打包后的用户用的。
            # 假设 current_dir 是 .../bilibili_downloader/ (exe所在目录)
            # 这里的逻辑是：把 new_build_dir 的内容 覆盖到 current_dir
            
            # 注意：temp_dir 会在脚本结束后被清理吗？
            # 不，如果是 subprocess 调用 bat，bat 还在运行，temp_dir 不能被 python 删除
            # 我们让 bat 负责移动文件，然后 bat 自己退出
            
            # 但是 temp_dir 是在临时文件夹，跨分区移动可能慢。
            # 我们先把 new_build_dir 移动到 current_dir 的上级目录的一个临时名，然后再覆盖？
            # 简单点：xcopy
            
            batch_content = f"""
@echo off
chcp 65001
echo 正在更新 Bilibili Downloader...
echo 等待主程序关闭...
timeout /t 3 /nobreak > nul

echo 正在复制文件...
echo 源: "{new_build_dir}"
echo 目标: "{current_dir}"

xcopy /E /Y /I "{new_build_dir}" "{current_dir}"

if %errorlevel% neq 0 (
    echo 更新失败！
    pause
    exit /b %errorlevel%
)

echo 更新完成，正在重启...
start "" "{os.path.join(current_dir, 'bilibili_downloader.exe')}"

echo 清理临时文件...
rd /s /q "{temp_dir}"
del "%~f0"
"""
            with open(bat_path, 'w', encoding='gbk') as f: # Bat needs ANSI/GBK usually, or chcp 65001
                f.write(batch_content)
                
            logger.info(f"更新脚本已生成: {bat_path}")
            
            # 6. 启动更新脚本并退出
            # Launch update script and exit
            subprocess.Popen(['cmd', '/c', bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            
            # 返回 True 告诉调用者准备退出了
            return True, "更新准备就绪，程序即将重启..."
            
        except subprocess.CalledProcessError as e:
            return False, f"执行命令失败: {e}"
        except Exception as e:
            logger.error(f"更新过程出错: {e}")
            return False, f"更新过程出错: {str(e)}"
        # finally:
            # Do not clean up temp_dir here because the batch script needs it!
            # pass

    def get_latest_remote_tag(self):
        """
        获取远程最新Tag (复用 get_versions 逻辑)
        Get latest remote tag
        """
        versions = self.get_versions()
        if versions:
            return versions[0]['tag']
        return None
