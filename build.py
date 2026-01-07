#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
bilibiliDownloader打包脚本
"""

import os
import sys
import shutil
import subprocess
import platform
import zipfile
import datetime
from core.config import APP_VERSION

def print_step(message):
    """打印带有格式的步骤信息 / Print formatted step info"""
    print("\n" + "=" * 60)
    print(f"  {message}")
    print("=" * 60)

def clean_build_dirs():
    """清理旧的构建目录 / Clean old build directories"""
    print_step("清理旧的构建目录 / Cleaning build directories")
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"已删除 {dir_name} 目录")
            except Exception as e:
                print(f"删除 {dir_name} 失败: {e}")

def build_executable():
    """使用PyInstaller构建可执行文件 / Build executable with PyInstaller"""
    print_step("开始构建可执行文件 / Building executable")
    
    # 构建命令 / Build command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=bilibili_downloader',
        '--windowed',  # 无控制台窗口 / No console window
        '--noconfirm',  # 不确认覆盖 / Do not confirm overwrite
        '--clean',      # 清理缓存 / Clean cache
        '--add-data=README.md;.',  # 添加说明文件 / Add README
        '--add-data=credits.txt;.',  # 添加致谢文件 / Add credits
        '--add-data=resource;resource',  # 添加资源文件夹 / Add resource folder
        '--collect-data=snownlp',  # 收集snownlp数据文件 / Collect snownlp data
        '--collect-data=fake_useragent', # 收集fake_useragent数据 / Collect fake_useragent data
        '--collect-all=jieba',     # 收集jieba数据 / Collect jieba data
        '--collect-all=wordcloud', # 收集wordcloud数据 / Collect wordcloud data
        '--hidden-import=cv2',     # OpenCV
        '--hidden-import=fake_useragent', # fake_useragent
        '--hidden-import=openpyxl', # Excel Export
        '--hidden-import=core.crawler',
        '--hidden-import=core.network',
        '--hidden-import=core.api',
        '--hidden-import=core.downloader',
        '--hidden-import=core.processor',
        '--hidden-import=core.version_manager', # 新增版本管理模块 / Version manager
        '--hidden-import=ui.main_window',
        '--hidden-import=ui.workers',
        '--hidden-import=ui.login_dialog',
        '--hidden-import=ui.message_box',
        '--hidden-import=ui.widgets.custom_combobox',
        '--hidden-import=ui.widgets.floating_window',
        '--hidden-import=core.watermark',
        '--hidden-import=ui.update_dialog',
        '--hidden-import=ui.tabs.download_tab',
        '--hidden-import=ui.tabs.popular_tab',
        '--hidden-import=ui.tabs.account_tab',
        '--hidden-import=ui.tabs.video_edit',
        '--hidden-import=ui.tabs.video_edit.pages.remove_watermark_page',
        '--hidden-import=ui.tabs.settings_tab',
        '--hidden-import=ui.tabs.bangumi_tab',
        '--hidden-import=ui.tabs.user_search_tab',
        '--hidden-import=ui.tabs.analysis',
        '--hidden-import=ui.tabs.analysis.analysis_tab',
        '--hidden-import=ui.tabs.analysis.worker',
        '--hidden-import=ui.tabs.analysis.charts',
        # Exclude unnecessary modules to prevent build hanging and reduce size
        '--exclude-module=paddle',
        '--exclude-module=paddlepaddle',
        '--exclude-module=torch',
        '--exclude-module=torchvision',
        '--exclude-module=torchaudio',
        '--exclude-module=tensorboard',
        '--exclude-module=caffe2',
        '--exclude-module=triton',
        '--exclude-module=scipy',
        '--exclude-module=matplotlib.tests',
        '--exclude-module=numpy.tests',
        'main.py'
    ]
    
    # 如果存在图标，添加图标参数 / Add icon if exists
    if os.path.exists('resource/icon.ico'):
        cmd.insert(3, '--icon=resource/icon.ico')
    
    # 执行构建命令 / Execute build command
    print(f"执行命令: {' '.join(cmd)}")
    process = subprocess.run(cmd)
    
    if process.returncode != 0:
        print("构建失败！/ Build failed!")
        sys.exit(1)
    
    print("构建完成！/ Build completed!")

def copy_resources():
    """复制必要的资源文件到dist目录 / Copy resources to dist directory"""
    print_step("复制资源文件 / Copying resources")
    
    # 确保dist目录存在 / Ensure dist dir exists
    dist_dir = 'dist/bilibili_downloader'
    if not os.path.exists(dist_dir):
        os.makedirs(dist_dir)
    
    # 复制ffmpeg文件夹(如果存在) / Copy ffmpeg folder if exists
    if os.path.exists('ffmpeg'):
        ffmpeg_dest = os.path.join(dist_dir, 'ffmpeg')
        if not os.path.exists(ffmpeg_dest):
            os.makedirs(ffmpeg_dest)
        
        # 复制ffmpeg文件 / Copy ffmpeg files
        ffmpeg_files = ['ffmpeg.exe',
         'ffplay.exe',
         'ffprobe.exe',
         'avcodec-61.dll',
        'avdevice-61.dll' ,
         'avfilter-10.dll' ,
        'avformat-61.dll',
         'avutil-59.dll',
         'postproc-58.dll',
        'swresample-5.dll',
        'swscale-8.dll' 
        ]
        for file in ffmpeg_files:
            src_file = os.path.join('ffmpeg', file)
            if os.path.exists(src_file):
                shutil.copy2(src_file, ffmpeg_dest)
                print(f"已复制 {src_file} 到 {ffmpeg_dest}")
    
    # 复制 .git 文件夹 (已禁用：不再依赖本地 .git 文件夹)
    # Copy .git folder (Disabled: No longer rely on local .git folder)
    
    # 复制集成式 Git (MinGit)
    # Copy bundled Git (MinGit)
    local_git_dir = 'git'
    if os.path.exists(local_git_dir):
        git_dest_dir = os.path.join(dist_dir, 'git')
        if os.path.exists(git_dest_dir):
             shutil.rmtree(git_dest_dir)
        try:
            shutil.copytree(local_git_dir, git_dest_dir)
            print(f"已复制本地 Git 环境到 {git_dest_dir}")
        except Exception as e:
            print(f"复制本地 Git 失败: {e}")
    else:
        print("警告: 未在项目根目录发现 'git' 文件夹，版本管理功能将无法使用！")

    # 复制集成式 Python (python_embed)
    # Copy bundled Python (python_embed)
    local_python_dir = 'python_embed'
    if os.path.exists(local_python_dir):
        python_dest_dir = os.path.join(dist_dir, 'python_embed')
        if os.path.exists(python_dest_dir):
             shutil.rmtree(python_dest_dir)
        try:
            shutil.copytree(local_python_dir, python_dest_dir)
            print(f"已复制本地 Python 环境到 {python_dest_dir}")
        except Exception as e:
            print(f"复制本地 Python 失败: {e}")
    else:
        print("警告: 未在项目根目录发现 'python_embed' 文件夹，自动更新编译功能将无法在无Python电脑上使用！")

    # 创建初始数据目录 / Create initial data dirs
    data_dir = os.path.join(dist_dir, 'bilibili_data')
    downloads_dir = os.path.join(data_dir, 'downloads')
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"已创建目录: {data_dir}")
    
    if not os.path.exists(downloads_dir):
        os.makedirs(downloads_dir)
        print(f"已创建目录: {downloads_dir}")
    
    # 创建空的历史记录文件 / Create empty history file
    history_file = os.path.join(data_dir, 'download_history.json')
    if not os.path.exists(history_file):
        with open(history_file, 'w', encoding='utf-8') as f:
            f.write('[]')
        print(f"已创建空历史记录文件: {history_file}")

def create_zip_archive():
    """创建ZIP压缩包 / Create ZIP archive"""
    print_step("创建发布压缩包 / Creating ZIP archive")
    
    # 确定系统类型和版本信息
    system = platform.system().lower()
    architecture = '64bit' if sys.maxsize > 2**32 else '32bit'
    
    # 获取当前日期
    today = datetime.datetime.now().strftime("%Y%m%d")
    
    # 创建zip文件名
    zip_filename = f"bilibili_downloader_{APP_VERSION}_{system}_{architecture}_{today}.zip"
    
    # 创建压缩文件
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('dist/bilibili_downloader'):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, 'dist')
                zipf.write(file_path, arcname)
    
    print(f"压缩包已创建: {zip_filename}")
    return zip_filename

def verify_build():
    """验证构建结果 / Verify build result"""
    print_step("验证构建结果 / Verifying build")
    
    # 检查可执行文件是否存在
    exe_path = os.path.abspath('dist/bilibili_downloader/bilibili_downloader.exe')
    if not os.path.exists(exe_path):
        print(f"错误: 可执行文件不存在: {exe_path}")
        return False
    
    # 检查文件大小
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"可执行文件大小: {size_mb:.2f} MB")
    
    # 检查必要的目录和文件
    required_paths = [
        'dist/bilibili_downloader/bilibili_data',
        'dist/bilibili_downloader/bilibili_data/downloads',
        'dist/bilibili_downloader/git' # 验证git目录是否复制
    ]
    
    for path in required_paths:
        if not os.path.exists(path):
            if path.endswith('git'):
                 print(f"警告: git 目录不存在，版本管理功能无法使用。")
            else:
                print(f"错误: 必要的目录不存在: {path}")
                return False
    
    print("验证通过！构建结果符合要求。")
    return True

def main():
    """主函数 / Main function"""
    print("\n" + "=" * 60)
    print(f"  bilibiliDownloader打包工具 {APP_VERSION}")
    print("=" * 60 + "\n")

    # 1. 清理旧的构建目录
    clean_build_dirs()
    
    # 2. 构建可执行文件
    build_executable()
    
    # 3. 复制资源文件
    copy_resources()
    
    # 4. 验证构建结果
    if not verify_build():
        print("构建验证失败，请检查错误并修复。")
        sys.exit(1)
    
    # 5. 创建压缩包
    zip_file = create_zip_archive()
    
    print("\n" + "=" * 60)
    print("  打包过程完成！")
    print("=" * 60)
    print(f"可执行文件位于: {os.path.abspath('dist/bilibili_downloader/bilibili_downloader.exe')}")
    print(f"压缩包位于: {os.path.abspath(zip_file)}")
    print(f"\n新版本 {APP_VERSION} 更新内容:")
    print("- 新增：用户查询CRC32反推本地缓存")
    print("- 新增：番剧下载支持BV号输入及合集检测")
    print("- 新增：视频下载支持合集检测跳转")
    print("- 优化：代码结构清理和优化")
    print(f"- 更新：版本号更新至 {APP_VERSION}")

if __name__ == "__main__":
    main() 
