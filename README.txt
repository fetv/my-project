# YouTube Monitor GUI - Standalone Executable

## 🚀 New Features (v2.0)

✅ **Threaded Monitoring**: All channels are now checked simultaneously  
✅ **Cookie Isolation**: Each channel uses its own TikTok account  
✅ **Enhanced Login Function**: Improved TikTok account login with validation and better UX  
✅ **PubSubHubbub Support**: Real-time video notifications  
✅ **Enhanced Video Splitting**: Multiple splitting methods available  
✅ **Improved Logging**: Better tracking and debugging  
✅ **Proxy Management**: Full proxy support with GUI management  
✅ **CLI Proxy Support**: Command-line proxy configuration for uploads  
✅ **Channel ID Matching**: Reliable channel identification using YouTube channel IDs  

## Quick Start

1. **Double-click** `LAUNCH.bat` to start the application
2. **Or** double-click `YouTubeMonitorGUI.exe` directly

## First Time Setup

1. **Add Channels**: Go to Channels tab → Add Channel
2. **Login TikTok**: Go to Settings tab → Login Account (Enhanced with validation)  
3. **Configure**: Set check interval and download path
4. **Start Monitoring**: Go to Dashboard → Start Monitoring

## Login Features

- **Enhanced Validation**: Account name validation with error checking
- **Better UX**: Improved dialog with clear instructions and keyboard shortcuts
- **Session Information**: View detailed session status for each account
- **Cross-Compatible**: Works with both GUI and CLI methods

## Monitoring Modes

### 🔄 **Standard Monitoring** (Polling)
- Uses `start_monitor.bat` or GUI Start button
- Checks channels every few seconds
- Good for most use cases

### ⚡ **PubSubHubbub Monitoring** (Real-time)
- Uses `start_pubsub_monitor.bat`
- Instant notifications when videos are uploaded
- Requires ngrok tunnel setup
- See `PubSubHubbub_README.md` for setup

## Files Included

- `YouTubeMonitorGUI.exe` - Main application
- `LAUNCH.bat` - Easy launcher script
- `start_monitor.bat` - Standard monitoring
- `start_pubsub_monitor.bat` - Real-time monitoring
- `tiktok_uploader/` - TikTok uploader module with proxy support
- `CookiesDir/` - TikTok login cookies
- `VideosDirPath/` - Downloaded videos (temporary)
- `ffmpeg_split.py` - Video splitting utilities
- `youtube_monitor_pubsub.py` - PubSubHubbub monitor
- `pubsubhubbub_server.py` - Webhook server
- `cli.py` - Command-line interface with proxy support
- `video_duration_utils.py` - Video duration processing
- `youtube_downloader.py` - YouTube video downloader
- `PROXY_INTEGRATION_README.md` - Proxy management documentation
- `PROXY_CLI_USAGE.md` - CLI proxy usage guide
- `sample_proxies.txt` - Example proxy configuration
- `monitor_config.json` - Application configuration

## Requirements

- Windows 10/11
- Internet connection
- TikTok accounts (login through the app)
- Node.js (for TikTok signature generation)

## Cookie Management

Each channel can use a different TikTok account:
- Channel 1 → TikTok Account A
- Channel 2 → TikTok Account B
- Videos are automatically uploaded to the correct account

## Proxy Management

The application now supports full proxy management:
- **GUI Proxy Management**: Add, edit, remove, and import proxies
- **Channel-Specific Proxies**: Assign different proxies to different channels
- **CLI Proxy Support**: Use `--proxy` argument for command-line uploads
- **Proxy Format**: `IP:PORT:USERNAME:PASSWORD`
- **Automatic Proxy Selection**: Videos use the proxy assigned to their channel

## Channel Matching

Improved channel identification system:
- **Channel ID Based**: Uses unique YouTube channel IDs for reliable matching
- **No More False Matches**: Eliminates incorrect channel assignments
- **Automatic Proxy Selection**: Correct proxy is automatically selected based on channel

## Support

If you encounter issues:
1. Check the logs in the GUI
2. Ensure you have internet connection
3. Verify TikTok logins are valid
4. Check the README for troubleshooting
5. See `PROXY_INTEGRATION_README.md` for proxy setup
6. See `PROXY_CLI_USAGE.md` for CLI proxy usage
7. Verify channel matching is working correctly
8. Check proxy configurations in Settings → Proxy Management

## Legal Notice

- Ensure you have permission to re-upload content
- Respect YouTube and TikTok Terms of Service
- Consider fair use and copyright laws
