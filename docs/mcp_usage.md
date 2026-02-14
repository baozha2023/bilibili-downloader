# Bilibili Downloader MCP 服务使用指南

本项目现已支持模型上下文协议 (Model Context Protocol, MCP)，允许您通过兼容 MCP 的客户端（如 Claude Desktop）与 Bilibili Downloader 进行交互。

## 功能特性

MCP 服务暴露了以下工具：

- `search_popular_videos(page)`: 搜索 Bilibili 热门视频。
- `get_video_details(bvid)`: 获取指定视频的详细信息。
- `download_video(bvid)`: 根据 BVID 下载视频。
- `get_version()`: 获取当前应用程序版本。

## 安装与配置

### 选项 1：使用打包好的可执行文件（推荐）

如果您下载的是打包版本（ZIP 文件），则无需 Python 环境。

1.  将压缩包解压到一个文件夹（例如 `C:\Apps\bilibili-downloader`）。
2.  在文件夹中找到 `mcp_server.exe`。
3.  配置您的 MCP 客户端（例如 `claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "bilibili-downloader": {
      "command": "C:/Apps/bilibili-downloader/mcp_server.exe",
    }
  }
}
```

### 选项 2：从源码运行

#### 前置要求

- Python 3.8+
- `pip`

#### 1. 安装依赖

如果您尚未安装，请安装项目依赖：

```bash
pip install -r requirements.txt
```

#### 2. 配置 MCP 客户端

将以下配置添加到您的 MCP 客户端设置中：

```json
{
  "mcpServers": {
    "bilibili-downloader": {
      "command": "python",
      "args": [
        "f:/IDEA/idea-workspace/bilibili-downloader/mcp_server.py"
      ]
    }
  }
}
```

## 使用方法

配置完成后，您可以要求您的 AI 助手执行如下任务：

- "搜索 Bilibili 热门视频"
- "获取视频 BV1xx... 的详情"
- "下载视频 BV1xx..."

## 故障排除

### 找不到下载的文件？

下载目录取决于 MCP 服务的运行位置。

- 使用 `get_download_path()` 工具查找确切位置。
- 默认情况下，文件保存在项目目录内的 `bilibili_data/downloads` 中（如果配置了正确的 `cwd`）。
- 如果您使用的是 Claude Code，它可能运行在临时目录或与您预期不同的位置。

