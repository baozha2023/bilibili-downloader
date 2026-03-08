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

# Configuration
HIDDEN_IMPORTS = [
    'cv2',
    'fake_useragent',
    'openpyxl',
    'core.crawler',
    'core.network',
    'core.api',
    'core.downloader',
    'core.processor',
    'core.version_manager',
    'ui.main_window',
    'ui.workers',
    'ui.login_dialog',
    'ui.message_box',
    'ui.widgets.custom_combobox',
    'ui.widgets.floating_window',
    'core.watermark',
    'ui.update_dialog',
    'ui.tabs.download_tab',
    'ui.tabs.popular_tab',
    'ui.tabs.account_tab',
    'ui.tabs.video_edit',
    'ui.tabs.video_edit.pages.remove_watermark_page',
    'ui.tabs.settings_tab',
    'ui.tabs.bangumi_tab',
    'ui.tabs.user_search_tab',
    'ui.tabs.analysis',
    'ui.tabs.analysis.analysis_tab',
    'ui.tabs.analysis.worker',
    'ui.tabs.analysis.charts',
    'simple_lama_inpainting'
]

EXCLUDED_MODULES = [
    'paddle',
    'paddlepaddle',
    'tensorboard',
    'caffe2',
    'triton',
    'scipy',
    'matplotlib.tests',
    'numpy.tests'
]

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
    
    # 生成 Spec 文件
    spec_template = r"""# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_all, copy_metadata

block_cipher = None

# Base config
hidden_imports = {hidden_imports}
excluded_modules = {excluded_modules}

# Base datas
# credits.txt needs to be in datas because it's read by ui/about_module.py using sys._MEIPASS
# README.md and docs/mcp_usage.md are for user reference, so we copy them to dist folder via copy_resources(), 
# no need to pack them into _internal
datas = [('credits.txt', '.'), ('resource', 'resource')]
binaries = []

# Collect data for specific packages
datas += collect_data_files('snownlp')
datas += collect_data_files('fake_useragent')

# Copy metadata for mcp (just in case)
try:
    datas += copy_metadata('mcp')
except Exception:
    pass

# Collect all for complex packages
for pkg in ['jieba', 'wordcloud']:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hidden_imports += h
    except Exception:
        pass

# Analysis for Main Application
a1 = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Analysis for MCP Server
a2 = Analysis(
    ['mcp_server.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# PYZ Archives
pyz1 = PYZ(a1.pure, a1.zipped_data, cipher=block_cipher)
pyz2 = PYZ(a2.pure, a2.zipped_data, cipher=block_cipher)

# Main Executable (Windowed)
exe1 = EXE(
    pyz1,
    a1.scripts,
    [],
    exclude_binaries=True,
    name='bilibili_downloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resource/icon.ico'
)

# MCP Server Executable (Console)
exe2 = EXE(
    pyz2,
    a2.scripts,
    [],
    exclude_binaries=True,
    name='mcp_server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resource/icon.ico'
)

# Collection (Merge)
coll = COLLECT(
    exe1,
    exe2,
    a1.binaries,
    a1.zipfiles,
    a1.datas,
    a2.binaries,
    a2.zipfiles,
    a2.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='bilibili_downloader',
)
"""
    spec_content = spec_template.format(
        hidden_imports=HIDDEN_IMPORTS,
        excluded_modules=EXCLUDED_MODULES
    )
    
    spec_file = 'bilibili_downloader.spec'
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print(f"Spec file generated: {spec_file}")

    # 执行构建命令 / Execute build command
    cmd = [sys.executable, '-m', 'PyInstaller', spec_file, '--noconfirm', '--clean']
    
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

    # 复制文档目录 / Copy docs directory
    docs_src = 'docs'
    if os.path.exists(docs_src):
        docs_dest = os.path.join(dist_dir, 'docs')
        if os.path.exists(docs_dest):
            shutil.rmtree(docs_dest)
        try:
            shutil.copytree(docs_src, docs_dest)
            print(f"已复制文档到 {docs_dest}")
        except Exception as e:
            print(f"复制文档失败: {e}")

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

def verify_build():
    """验证构建结果 / Verify build result"""
    print_step("验证构建结果 / Verifying build")
    
    # 检查可执行文件是否存在
    exe_path = os.path.abspath('dist/bilibili_downloader/bilibili_downloader.exe')
    if not os.path.exists(exe_path):
        print(f"错误: 可执行文件不存在: {exe_path}")
        return False
        
    # 检查MCP服务可执行文件
    mcp_path = os.path.abspath('dist/bilibili_downloader/mcp_server.exe')
    if not os.path.exists(mcp_path):
        print(f"错误: MCP服务可执行文件不存在: {mcp_path}")
        return False
    
    # 检查文件大小
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"主程序大小: {size_mb:.2f} MB")
    
    mcp_size_mb = os.path.getsize(mcp_path) / (1024 * 1024)
    print(f"MCP服务大小: {mcp_size_mb:.2f} MB")
    
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
    
    # 5. 重命名输出目录 / Rename output directory
    print_step("重命名输出目录 / Renaming output directory")
    old_dist = os.path.join('dist', 'bilibili_downloader')
    new_folder_name = f'bilibili_downloader-{APP_VERSION}'
    new_dist = os.path.join('dist', new_folder_name)
    
    if os.path.exists(new_dist):
        try:
            shutil.rmtree(new_dist)
            print(f"已清理现有的目标目录: {new_dist}")
        except Exception as e:
            print(f"清理目标目录失败: {e}")
            sys.exit(1)
            
    try:
        os.rename(old_dist, new_dist)
        print(f"已重命名为: {new_dist}")
    except Exception as e:
        print(f"重命名失败: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  打包过程完成！")
    print("=" * 60)
    print(f"主程序位于: {os.path.abspath(os.path.join(new_dist, 'bilibili_downloader.exe'))}")
    print(f"MCP服务位于: {os.path.abspath(os.path.join(new_dist, 'mcp_server.exe'))}")
    print(f"\n新版本 {APP_VERSION}. 更新内容:")
    print("- 新增：支持 Model Context Protocol (MCP)，允许 AI 助手调用核心功能。")
    print("- 新增：`mcp_server.py` 作为 MCP 服务入口")
    print("- 文档：新增 MCP 使用文档 `docs/mcp_usage.md`")
    print(f"- 更新：版本号更新至 {APP_VERSION}")

if __name__ == "__main__":
    main() 
