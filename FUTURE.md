# Future Development Plan

## 1. Advanced API Integration
- **GRPC API Support**: Migrate critical APIs to gRPC (using protobuf) for better stability and performance, as Bilibili is moving towards gRPC for mobile apps.
- **WBI Signature**: Implement WBI (Web Basic Information) signature algorithm to support latest Web APIs which are replacing old endpoints.
- **Login Security**: Support QR Code login via TV API or gRPC to reduce risk of cookie invalidation.

## 2. Enhanced Downloader
- **Multi-threaded/Async Download**: Switch to `aiohttp` or `httpx` for fully asynchronous downloading to improve speed.
- **External Downloader Support**: Integrate `aria2` or `yt-dlp` as optional download engines.
- **Batch Download**: Support downloading entire channel, series, or user submissions.
- **Dash Format Support**: Better support for Dash (Dynamic Adaptive Streaming over HTTP) to get higher resolutions (4K/8K) and better audio.

## 3. Richer Analysis
- **Sentiment Analysis**: Integrate `SnowNLP` or `TextBlob` to analyze comment sentiment (Positive/Negative/Neutral).
- **Danmaku Analysis**: Analyze danmaku density, keywords over time, and color distribution.
- **User Portrait**: Analyze audience demographics (if available via API or deduced from public info).

## 4. UI/UX Improvements
- **Dark Mode**: Full support for dark theme.
- **Custom Themes**: Allow users to customize colors.
- **Plugin System**: Allow third-party plugins.

## 5. Mobile Companion
- **Remote Control**: Control PC downloader from mobile.
- **Push Notifications**: Notify mobile when download completes.

## 6. Open Source Integration
- **FFmpeg**: Update to latest version and support hardware acceleration (NVENC/QSV).
- **MPV/VLC**: Embed a more powerful player (e.g., using `python-mpv`) instead of WebView for better playback experience.
