import subprocess
import os
import shutil
import logging
import sys

logger = logging.getLogger('bilibili_desktop')

class VersionManager:
    """
    版本管理核心类
    负责与Git交互，获取版本列表，切换版本等操作
    """
    def __init__(self, main_window):
        self.main_window = main_window
        self.repo_url = "https://gitee.com/bzJAVA/bilibili-downloader.git"
        self.cwd = os.getcwd() # 假设当前工作目录就是项目根目录

    def check_git_available(self):
        """检查git是否可用"""
        try:
            subprocess.run(['git', '--version'], check=True, capture_output=True)
            return True
        except:
            return False

    def get_versions(self):
        """
        获取远程仓库的所有tag列表
        """
        if not self.check_git_available():
            return []

        try:
            # 1. Fetch tags from remote to ensure we have latest
            # 使用 capture_output=True 避免输出干扰
            subprocess.run(['git', 'fetch', '--tags'], cwd=self.cwd, check=True, capture_output=True)
            
            # 2. List tags
            result = subprocess.run(['git', 'tag', '-l'], cwd=self.cwd, check=True, capture_output=True, text=True)
            tags = result.stdout.strip().split('\n')
            
            # 过滤空行
            tags = [t.strip() for t in tags if t.strip()]
            
            # 简单的版本排序 (假设格式为 v1.0, v1.1 等)
            # 尝试按语义版本排序，如果失败则按字母倒序
            try:
                tags.sort(key=lambda s: [int(u) for u in s.lower().replace('v', '').split('.')], reverse=True)
            except:
                tags.sort(reverse=True)
                
            return tags
        except Exception as e:
            logger.error(f"获取版本列表失败: {e}")
            return []

    def get_current_version(self):
        """获取当前版本信息"""
        if not self.check_git_available():
            return "未知 (Git不可用)"

        try:
            # 尝试获取当前tag
            result = subprocess.run(['git', 'describe', '--tags', '--exact-match'], cwd=self.cwd, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            
            # 如果不是tag，获取分支和commit hash
            branch_res = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=self.cwd, capture_output=True, text=True)
            commit_res = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=self.cwd, capture_output=True, text=True)
            
            branch = branch_res.stdout.strip()
            commit = commit_res.stdout.strip()
            
            return f"{branch} ({commit})"
        except Exception as e:
            logger.error(f"获取当前版本失败: {e}")
            return "未知"

    def switch_version(self, tag):
        """
        切换到指定版本(Tag)
        注意：这会重置工作区的修改，请谨慎使用
        """
        if not self.check_git_available():
            return False, "Git不可用"

        try:
            # 1. 强制checkout到指定tag
            # 注意：这里使用 -f 强制覆盖本地修改，因为需求是"切换和更新"
            subprocess.run(['git', 'checkout', '-f', tag], cwd=self.cwd, check=True, capture_output=True)
            
            # 2. 清除配置目录
            config_dir = os.path.join(self.cwd, 'bilibili_data', 'config')
            if os.path.exists(config_dir):
                try:
                    shutil.rmtree(config_dir)
                    logger.info(f"已清除配置目录: {config_dir}")
                except Exception as e:
                    logger.warning(f"清除配置目录失败: {e}")
            
            return True, f"成功切换到版本 {tag}"
        except subprocess.CalledProcessError as e:
            return False, f"Git操作失败: {e.stderr if hasattr(e, 'stderr') else str(e)}"
        except Exception as e:
            return False, f"切换版本发生错误: {str(e)}"

    def get_latest_remote_tag(self):
        """获取远程最新Tag"""
        try:
             # git ls-remote --tags --refs --sort='-v:refname' origin | head -n 1
             # Windows下没有head命令，且sort参数可能不支持，这里用python处理
             result = subprocess.run(['git', 'ls-remote', '--tags', '--refs', self.repo_url], capture_output=True, text=True, check=True)
             lines = result.stdout.strip().split('\n')
             tags = []
             for line in lines:
                 parts = line.split('\t')
                 if len(parts) > 1:
                     ref = parts[1]
                     tag_name = ref.replace('refs/tags/', '')
                     tags.append(tag_name)
             
             if tags:
                 # 排序
                 try:
                    tags.sort(key=lambda s: [int(u) for u in s.lower().replace('v', '').split('.')], reverse=True)
                 except:
                    tags.sort(reverse=True)
                 return tags[0]
             return None
        except Exception as e:
            logger.error(f"获取远程版本失败: {e}")
            return None
