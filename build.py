#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
哔哩哔哩视频下载器打包脚本
版本: 4.0
"""

import os
import sys
import shutil
import subprocess
import platform
import zipfile
import datetime

def print_step(message):
    """打印带有格式的步骤信息"""
    print("\n" + "=" * 60)
    print(f"  {message}")
    print("=" * 60)

def clean_build_dirs():
    """清理旧的构建目录"""
    print_step("清理旧的构建目录")
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已删除 {dir_name} 目录")

def build_executable():
    """使用PyInstaller构建可执行文件"""
    print_step("开始构建可执行文件")
    
    # 构建命令
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=bilibili_downloader',
        '--windowed',  # 无控制台窗口 (如果是调试模式可以去掉此行)
        '--noconfirm',  # 不确认覆盖
        '--clean',      # 清理缓存
        '--add-data=README.md;.',  # 添加说明文件
        '--add-data=credits.txt;.',  # 添加致谢文件
        '--add-data=resource;resource',  # 添加资源文件夹
        '--hidden-import=core.crawler',
        '--hidden-import=core.network',
        '--hidden-import=core.api',
        '--hidden-import=core.downloader',
        '--hidden-import=core.processor',
        '--hidden-import=ui.main_window',
        '--hidden-import=ui.workers',
        '--hidden-import=ui.login_dialog',
        '--hidden-import=ui.message_box', # 添加新模块
        '--hidden-import=ui.widgets.custom_combobox',
        '--hidden-import=core.watermark',
        '--hidden-import=ui.update_dialog',
        '--hidden-import=ui.tabs.download_tab',
        '--hidden-import=ui.tabs.popular_tab',
        '--hidden-import=ui.tabs.account_tab',
        '--hidden-import=ui.tabs.video_edit_tab',
        '--hidden-import=ui.tabs.settings_tab',
        'main.py'
    ]
    
    # 如果存在图标，添加图标参数
    if os.path.exists('resource/icon.ico'):
        cmd.insert(2, '--icon=resource/icon.ico')
    
    # 执行构建命令
    print(f"执行命令: {' '.join(cmd)}")
    process = subprocess.run(cmd)
    
    if process.returncode != 0:
        print("构建失败！")
        sys.exit(1)
    
    print("构建完成！")

def copy_resources():
    """复制必要的资源文件到dist目录"""
    print_step("复制资源文件")
    
    # 确保dist目录存在
    dist_dir = 'dist/bilibili_downloader'
    if not os.path.exists(dist_dir):
        os.makedirs(dist_dir)
    
    # 复制ffmpeg文件夹(如果存在)
    if os.path.exists('ffmpeg'):
        ffmpeg_dest = os.path.join(dist_dir, 'ffmpeg')
        if not os.path.exists(ffmpeg_dest):
            os.makedirs(ffmpeg_dest)
        
        # 复制ffmpeg文件
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
    
    # 创建初始数据目录
    data_dir = os.path.join(dist_dir, 'bilibili_data')
    downloads_dir = os.path.join(data_dir, 'downloads')
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"已创建目录: {data_dir}")
    
    if not os.path.exists(downloads_dir):
        os.makedirs(downloads_dir)
        print(f"已创建目录: {downloads_dir}")
    
    # 创建空的历史记录文件
    history_file = os.path.join(data_dir, 'download_history.json')
    if not os.path.exists(history_file):
        with open(history_file, 'w', encoding='utf-8') as f:
            f.write('[]')
        print(f"已创建空历史记录文件: {history_file}")

def create_zip_archive():
    """创建ZIP压缩包"""
    print_step("创建发布压缩包")
    
    # 确定系统类型和版本信息
    system = platform.system().lower()
    architecture = '64bit' if sys.maxsize > 2**32 else '32bit'
    
    # 获取当前日期
    today = datetime.datetime.now().strftime("%Y%m%d")
    
    # 创建zip文件名
    zip_filename = f"bilibili_downloader_v4.0_{system}_{architecture}_{today}.zip"
    
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
    """验证构建结果"""
    print_step("验证构建结果")
    
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
        'dist/bilibili_downloader/bilibili_data/downloads'
    ]
    
    for path in required_paths:
        if not os.path.exists(path):
            print(f"错误: 必要的目录不存在: {path}")
            return False
    
    print("验证通过！构建结果符合要求。")
    return True

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  哔哩哔哩视频下载器打包工具 v4.0")
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
    print("\n新版本 v4.0 更新内容:")
    print("- 日志系统：视频编辑功能新增详细日志输出，覆盖转换、剪辑、合并、去水印等操作")
    print("- 交互体验：优化视频剪辑和去水印功能的交互体验，增加状态反馈和更清晰的指引")
    print("- 下载优化：优化视频下载取消逻辑，取消后自动重置进度条和UI状态")
    print("- 作者声明：设置界面新增'作者声明'按钮，详细列出致谢名单和开源技术")
    print("- 完善文档：更新Credits文件，补全所有使用到的工具和库的声明")

if __name__ == "__main__":
    main() 
