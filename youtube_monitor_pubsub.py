#!/usr/bin/env python3
"""
YouTube Channel Monitor using PubSubHubbub
Provides real-time video notifications via webhooks instead of polling.
"""

import asyncio
import json
import os
import time
import threading
from datetime import datetime
from typing import List, Dict, Optional, Callable
import logging
import requests
from pubsubhubbub_server import PubSubHubbubServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YouTubeMonitorPubSub:
    """YouTube monitor using PubSubHubbub for real-time notifications."""
    
    def __init__(self, config_file="monitor_config.json", log_callback=None):
        # Set log_callback first before any methods that might use it
        self.log_callback = log_callback
        
        # Load configuration
        self.config = self.load_config(config_file)
        self.processed_videos = set()
        
        # PubSubHubbub server
        self.pubsub_server = None
        self.server_runner = None
        
        # Video processing state
        self.processing_video = False
        self.upload_workers = []
        self.upload_worker_lock = threading.Lock()
        
        # Load processed videos
        self.load_processed_videos()
        
        # Statistics
        self.stats = {
            'notifications_received': 0,
            'videos_processed': 0,
            'subscriptions_active': 0,
            'last_notification': None,
            'start_time': datetime.now().isoformat()
        }
    
    def log(self, message, level="info"):
        """Log message with callback support."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        if level == "error":
            logger.error(formatted_message)
        elif level == "warning":
            logger.warning(formatted_message)
        else:
            logger.info(formatted_message)
        
        if self.log_callback:
            try:
                self.log_callback(formatted_message, level)
            except Exception as e:
                logger.error(f"Error in log callback: {e}")
    
    def load_config(self, config_file: str) -> Dict:
        """Load configuration from file."""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                if hasattr(self, 'log_callback') and self.log_callback:
                    self.log(f"Configuration loaded from {config_file}")
                return config
            else:
                # Create default config
                default_config = {
                    "channels": [],
                    "check_interval_seconds": 1,
                    "auto_upload": True,
                    "download_path": "VideosDirPath",
                    "pubsub_port": 8080,
                    "use_ngrok": True,
                    "ngrok_url": None
                }
                
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=4)
                
                if hasattr(self, 'log_callback') and self.log_callback:
                    self.log(f"Created default configuration: {config_file}")
                return default_config
                
        except Exception as e:
            if hasattr(self, 'log_callback') and self.log_callback:
                self.log(f"Error loading config: {e}", "error")
            return {}
    
    def load_processed_videos(self):
        """Load processed videos from file."""
        try:
            processed_file = self.config.get("processed_videos_file", "processed_videos.json")
            if os.path.exists(processed_file):
                with open(processed_file, 'r') as f:
                    processed = json.load(f)
                    self.processed_videos = set(processed)
                if hasattr(self, 'log_callback') and self.log_callback:
                    self.log(f"Loaded {len(self.processed_videos)} processed videos")
        except Exception as e:
            if hasattr(self, 'log_callback') and self.log_callback:
                self.log(f"Error loading processed videos: {e}", "error")
            self.processed_videos = set()
    
    def save_processed_videos(self):
        """Save processed videos to file."""
        try:
            processed_file = self.config.get("processed_videos_file", "processed_videos.json")
            with open(processed_file, 'w') as f:
                json.dump(list(self.processed_videos), f)
        except Exception as e:
            if hasattr(self, 'log_callback') and self.log_callback:
                self.log(f"Error saving processed videos: {e}", "error")
    
    async def video_notification_callback(self, video: Dict):
        """Callback function called when a new video is detected via PubSubHubbub."""
        try:
            video_id = video.get('id')
            title = video.get('title', 'Unknown Title')
            
            if video_id in self.processed_videos:
                self.log(f"Video already processed: {title}", "info")
                return
            
            self.log(f"🎉 New video detected via PubSubHubbub: {title}", "success")
            self.log(f"📺 Video ID: {video_id}", "info")
            self.log(f"🔗 URL: {video.get('url', 'N/A')}", "info")
            self.log(f"👤 Author: {video.get('author', 'Unknown')}", "info")
            
            # Update statistics
            self.stats['notifications_received'] += 1
            self.stats['last_notification'] = datetime.now().isoformat()
            
            # Mark as processed
            self.processed_videos.add(video_id)
            self.save_processed_videos()
            
            # Auto upload if enabled
            if self.config.get("auto_upload", True):
                await self.process_video_async(video)
            
        except Exception as e:
            self.log(f"Error in video notification callback: {e}", "error")
    
    async def process_video_async(self, video: Dict):
        """Process video asynchronously."""
        if self.processing_video:
            self.log(f"⏳ Already processing a video, skipping: {video.get('title', 'Unknown')}", "warning")
            return
        
        self.processing_video = True
        
        try:
            title = video.get('title', 'Unknown Title')
            self.log(f"🚀 Starting processing for: {title}", "info")
            
            # Import YouTubeMonitor for video processing
            from youtube_monitor import YouTubeMonitor
            
            # Initialize YouTubeMonitor if needed
            if not hasattr(self, 'yt_monitor'):
                self.yt_monitor = YouTubeMonitor(log_callback=self.log)
            
            # Get the video URL
            video_url = video.get('url')
            if not video_url:
                self.log(f"❌ No video URL found for: {title}", "error")
                return
            
            # Find matching channel for TikTok cookie
            channel = self.find_channel_for_video(video)
            tiktok_cookie = channel.get("tiktok_cookie", "default") if channel else "default"
            channel_name = channel.get("name", "Unknown") if channel else "Unknown"
            
            self.log(f"🎯 Processing video for channel: '{channel_name}' with TikTok cookie: '{tiktok_cookie}'")
            
            # Step 1: Download the video
            self.log(f"📥 Step 1: Downloading video...", "info")
            output_path = os.path.join(
                os.path.abspath(self.yt_monitor.config["download_path"]), 
                f"new_video_{video['id']}.mp4"
            )
            
            downloaded_path = self.yt_monitor.download_video(video_url, output_path)
            if not downloaded_path:
                self.log(f"❌ Failed to download video: {title}", "error")
                return
            
            self.log(f"✅ Step 1 completed: Video downloaded successfully", "success")
            
            # Step 2: Split the video into 5 parts with immediate upload and duration processing
            self.log(f"✂️ Step 2: Processing video duration and splitting into 5 parts...", "info")
            
            # Get proxy configuration for this channel
            proxy_config = None
            if channel and channel.get("proxy"):
                proxy_info = channel["proxy"]
                proxy_config = f"{proxy_info['ip']}:{proxy_info['port']}:{proxy_info['username']}:{proxy_info['password']}"
                self.log(f"🌐 Using proxy for channel {channel_name}: {proxy_info['ip']}:{proxy_info['port']}")
            else:
                self.log(f"📡 No proxy configured for channel {channel_name}")
            
            split_videos = self.yt_monitor.split_video(downloaded_path, 5, title, tiktok_cookie, channel_name, proxy_config)
            if not split_videos:
                self.log(f"❌ Failed to split video: {title}", "error")
                try:
                    os.remove(downloaded_path)
                except:
                    pass
                return
            
            self.log(f"✅ Step 2 completed: Video split and uploads initiated", "success")
            
            # Step 3: Cleanup
            self.log(f"🧹 Step 3: Cleaning up temporary files...", "info")
            try:
                os.remove(downloaded_path)
            except:
                pass
            
            self.log(f"✅ Step 3 completed: Cleanup finished", "success")
            
            # Update statistics
            self.stats['videos_processed'] += 1
            
            self.log(f"🎉 Video processing completed: All parts processed and uploaded", "success")
            
        except Exception as e:
            self.log(f"❌ Error processing video {video.get('title', 'unknown')}: {str(e)}", "error")
            import traceback
            self.log(f"Error details: {traceback.format_exc()}", "error")
        
        finally:
            self.processing_video = False
    
    def find_channel_for_video(self, video: Dict) -> Optional[Dict]:
        """Find the channel configuration for a video based on channel ID."""
        try:
            video_author = video.get('author', 'Unknown')
            video_channel_id = video.get('channel_id')  # Get the channel ID from the video
            
            self.log(f"🔍 Looking for channel match for video author: '{video_author}' with channel ID: {video_channel_id}")
            
            if not video_channel_id:
                self.log(f"⚠️ No channel ID found in video data, falling back to first channel", "warning")
                channels = self.config.get("channels", [])
                if channels:
                    default_channel = channels[0]
                    self.log(f"📺 Using default channel: '{default_channel['name']}' with TikTok cookie: {default_channel.get('tiktok_cookie', 'default')}")
                    return default_channel
                else:
                    self.log(f"❌ No channels configured!")
                    return None
            
            # Find channel by exact channel ID match
            for channel in self.config.get("channels", []):
                channel_name = channel.get("name", "Unknown")
                channel_id = channel.get("channel_id", "")
                tiktok_cookie = channel.get("tiktok_cookie", "default")
                
                self.log(f"🔍 Checking channel: '{channel_name}' (ID: {channel_id}, TikTok: {tiktok_cookie})")
                
                if channel_id == video_channel_id:
                    self.log(f"✅ Found exact channel ID match: '{channel_name}' for video author: '{video_author}'")
                    self.log(f"🍪 Will use TikTok cookie: {tiktok_cookie}")
                    return channel
            
            # If no exact channel ID match found, return the first channel as default
            channels = self.config.get("channels", [])
            if channels:
                default_channel = channels[0]
                self.log(f"⚠️ No channel ID match found for '{video_channel_id}', using default channel: '{default_channel['name']}' with TikTok cookie: {default_channel.get('tiktok_cookie', 'default')}")
                return default_channel
            
            self.log(f"❌ No channels configured!")
            return None
            
        except Exception as e:
            self.log(f"Error finding channel for video: {e}", "error")
            return None
    
    async def subscribe_to_channels(self):
        """Subscribe to all configured channels."""
        try:
            channels = self.config.get("channels", [])
            if not channels:
                self.log("No channels configured for subscription", "warning")
                return
            
            self.log(f"Subscribing to {len(channels)} channels...", "info")
            
            for channel in channels:
                channel_id = channel.get("channel_id")
                channel_name = channel.get("name", "Unknown")
                
                if not channel_id:
                    self.log(f"Missing channel_id for channel: {channel_name}", "warning")
                    continue
                
                success = await self.pubsub_server.subscribe_to_channel(channel_id, channel_name)
                
                if success:
                    self.log(f"✅ Successfully subscribed to: {channel_name}", "success")
                else:
                    self.log(f"❌ Failed to subscribe to: {channel_name}", "error")
            
            self.stats['subscriptions_active'] = len(self.pubsub_server.subscriptions)
            
        except Exception as e:
            self.log(f"Error subscribing to channels: {e}", "error")
    
    async def start_monitoring(self):
        """Start the PubSubHubbub-based monitoring."""
        try:
            # Initialize PubSubHubbub server
            port = self.config.get("pubsub_port", 8080)
            ngrok_url = self.config.get("ngrok_url")
            
            self.log(f"Starting PubSubHubbub server on port {port}...", "info")
            
            self.pubsub_server = PubSubHubbubServer(port=port, ngrok_url=ngrok_url)
            
            # Add video notification callback
            self.pubsub_server.add_video_callback(self.video_notification_callback)
            
            # Start the server
            self.server_runner = await self.pubsub_server.start_server()
            
            # Subscribe to channels
            await self.subscribe_to_channels()
            
            self.log("🚀 PubSubHubbub monitoring started successfully!", "success")
            self.log(f"📡 Webhook URL: {self.pubsub_server.get_webhook_url()}", "info")
            self.log(f"📊 Active subscriptions: {len(self.pubsub_server.subscriptions)}", "info")
            
            # Keep the server running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                self.log("Shutting down monitoring...", "info")
            finally:
                await self.stop_monitoring()
                
        except Exception as e:
            self.log(f"Error starting monitoring: {e}", "error")
    
    async def stop_monitoring(self):
        """Stop the monitoring service."""
        try:
            if self.server_runner:
                await self.pubsub_server.stop_server(self.server_runner)
                self.log("PubSubHubbub server stopped", "info")
        except Exception as e:
            self.log(f"Error stopping monitoring: {e}", "error")
    
    def get_status(self) -> Dict:
        """Get current monitoring status."""
        status = {
            'monitoring_active': self.pubsub_server is not None,
            'webhook_url': self.pubsub_server.get_webhook_url() if self.pubsub_server else None,
            'subscriptions': len(self.pubsub_server.subscriptions) if self.pubsub_server else 0,
            'processed_videos': len(self.processed_videos),
            'stats': self.stats
        }
        return status
    
    def is_running(self) -> bool:
        """Check if the PubSubHubbub server is running."""
        return self.pubsub_server is not None and self.server_runner is not None
    
    async def add_channel(self, channel_id: str, channel_name: str, tiktok_cookie: str = "default"):
        """Add a new channel and subscribe to it."""
        try:
            # Add to config
            new_channel = {
                "name": channel_name,
                "channel_id": channel_id,
                "tiktok_cookie": tiktok_cookie
            }
            
            self.config["channels"].append(new_channel)
            
            # Save config
            with open("monitor_config.json", 'w') as f:
                json.dump(self.config, f, indent=4)
            
            # Subscribe to the channel if server is running
            if self.pubsub_server:
                success = await self.pubsub_server.subscribe_to_channel(channel_id, channel_name)
                if success:
                    self.log(f"✅ Added and subscribed to channel: {channel_name}", "success")
                else:
                    self.log(f"❌ Added channel but failed to subscribe: {channel_name}", "error")
            else:
                self.log(f"✅ Added channel: {channel_name} (will subscribe when monitoring starts)", "success")
            
            return True
            
        except Exception as e:
            self.log(f"Error adding channel: {e}", "error")
            return False
    
    async def remove_channel(self, channel_id: str):
        """Remove a channel and unsubscribe from it."""
        try:
            # Find and remove from config
            channels = self.config.get("channels", [])
            self.config["channels"] = [ch for ch in channels if ch.get("channel_id") != channel_id]
            
            # Save config
            with open("monitor_config.json", 'w') as f:
                json.dump(self.config, f, indent=4)
            
            # Unsubscribe if server is running
            if self.pubsub_server:
                success = await self.pubsub_server.unsubscribe_from_channel(channel_id)
                if success:
                    self.log(f"✅ Removed and unsubscribed from channel: {channel_id}", "success")
                else:
                    self.log(f"❌ Removed channel but failed to unsubscribe: {channel_id}", "error")
            else:
                self.log(f"✅ Removed channel: {channel_id}", "success")
            
            return True
            
        except Exception as e:
            self.log(f"Error removing channel: {e}", "error")
            return False

async def main():
    """Main function to run the PubSubHubbub-based monitor."""
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Monitor with PubSubHubbub')
    parser.add_argument('--config', type=str, default='monitor_config.json', help='Configuration file')
    parser.add_argument('--port', type=int, default=8080, help='PubSubHubbub server port')
    parser.add_argument('--ngrok', action='store_true', help='Use ngrok tunnel')
    parser.add_argument('--ngrok-url', type=str, help='Existing ngrok URL')
    
    args = parser.parse_args()
    
    # Create monitor
    monitor = YouTubeMonitorPubSub(config_file=args.config)
    
    # Update config with command line arguments
    if args.port != 8080:
        monitor.config['pubsub_port'] = args.port
    
    if args.ngrok_url:
        monitor.config['ngrok_url'] = args.ngrok_url
    elif args.ngrok:
        monitor.config['use_ngrok'] = True
    
    # Save updated config
    with open(args.config, 'w') as f:
        json.dump(monitor.config, f, indent=4)
    
    # Start monitoring
    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
