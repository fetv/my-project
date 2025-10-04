import scrapetube
import os
import time
import json
import hashlib
import pickle
from datetime import datetime, timedelta
from tiktok_uploader import tiktok, Video
from tiktok_uploader.Config import Config
import yt_dlp
from moviepy.editor import VideoFileClip, concatenate_videoclips
import argparse
import threading
import requests
from collections import OrderedDict
from typing import List, Dict, Optional, Set


class YouTubeMonitor:
    def __init__(self, config_file="monitor_config.json", log_callback=None):
        self.config = self.load_config(config_file)
        self.tiktok_config = Config.get()
        self.processed_videos = self.load_processed_videos()
        self.channel_last_check = self.load_channel_last_check()
        self.log_callback = log_callback  # Callback function for logging
        
        # AGGRESSIVE CACHING: Multiple cache layers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # In-memory cache for scrapetube data (fastest access)
        self.scrapetube_cache = OrderedDict()
        self.max_cache_size = 50  # Keep last 50 channel checks in memory
        
        # Cache for parsed video data
        self.parsed_cache = {}
        
        # Cache for video hashes (avoid reprocessing)
        self.video_hash_cache = set()
        
        # Load existing caches
        self.load_scrapetube_cache()
        self.load_video_hash_cache()
        
    def log(self, message, level="info"):
        """Log message with optional callback to GUI"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Print to console
        print(formatted_message)
        
        # Send to GUI if callback is provided
        if self.log_callback:
            self.log_callback(message, level)
        
    def load_config(self, config_file):
        """Load monitoring configuration"""
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
                         # Create default config
            default_config = {
                "channels": [],
                "check_interval_seconds": 1,  # Check every 1 second
                "video_duration_limit": 113,  # seconds per split (1:53 minutes)
                "video_parts": 3,  # Number of parts to split video into (faster with fewer parts)
                "auto_upload": True,
                "download_path": "VideosDirPath",
                "processed_videos_file": "processed_videos.json",
                "channel_last_check_file": "channel_last_check.json"
            }
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
    
    def load_processed_videos(self):
        """Load list of already processed videos"""
        file_path = self.config.get("processed_videos_file", "processed_videos.json")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return []
    
    def save_processed_videos(self):
        """Save list of processed videos"""
        file_path = self.config.get("processed_videos_file", "processed_videos.json")
        with open(file_path, 'w') as f:
            json.dump(self.processed_videos, f, indent=4)
    
    def load_channel_last_check(self):
        """Load last check time for each channel"""
        file_path = self.config.get("channel_last_check_file", "channel_last_check.json")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return {}
    
    def save_channel_last_check(self):
        """Save last check time for each channel"""
        file_path = self.config.get("channel_last_check_file", "channel_last_check.json")
        with open(file_path, 'w') as f:
            json.dump(self.channel_last_check, f, indent=4)
    
    def load_scrapetube_cache(self):
        """Load scrapetube cache from disk"""
        cache_file = "scrapetube_cache.pkl"
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    self.scrapetube_cache = pickle.load(f)
                self.log(f"Loaded scrapetube cache with {len(self.scrapetube_cache)} entries")
        except Exception as e:
            self.log(f"Failed to load scrapetube cache: {e}", "warning")
            self.scrapetube_cache = OrderedDict()
    
    def save_scrapetube_cache(self):
        """Save scrapetube cache to disk"""
        cache_file = "scrapetube_cache.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(self.scrapetube_cache, f)
        except Exception as e:
            self.log(f"Failed to save scrapetube cache: {e}", "warning")
    
    def load_video_hash_cache(self):
        """Load video hash cache from disk"""
        hash_file = "video_hash_cache.pkl"
        try:
            if os.path.exists(hash_file):
                with open(hash_file, 'rb') as f:
                    self.video_hash_cache = pickle.load(f)
                self.log(f"Loaded video hash cache with {len(self.video_hash_cache)} entries")
        except Exception as e:
            self.log(f"Failed to load video hash cache: {e}", "warning")
            self.video_hash_cache = set()
    
    def save_video_hash_cache(self):
        """Save video hash cache to disk"""
        hash_file = "video_hash_cache.pkl"
        try:
            with open(hash_file, 'wb') as f:
                pickle.dump(self.video_hash_cache, f)
        except Exception as e:
            self.log(f"Failed to save video hash cache: {e}", "warning")
    
    def get_cached_scrapetube_data(self, channel_id, max_age_seconds=300):
        """Get scrapetube data from cache if available and fresh"""
        cache_key = f"scrapetube_{channel_id}"
        
        if cache_key in self.scrapetube_cache:
            cached_data = self.scrapetube_cache[cache_key]
            cache_time = cached_data.get('timestamp', 0)
            current_time = time.time()
            
            # Check if cache is still fresh (5 minutes by default)
            if current_time - cache_time < max_age_seconds:
                self.log(f"Using cached scrapetube data for {channel_id} (age: {current_time - cache_time:.1f}s)")
                return cached_data.get('videos')
        
        return None
    
    def cache_scrapetube_data(self, channel_id, videos):
        """Cache scrapetube data"""
        cache_key = f"scrapetube_{channel_id}"
        
        # Add to cache
        self.scrapetube_cache[cache_key] = {
            'videos': videos,
            'timestamp': time.time()
        }
        
        # Maintain cache size (LRU)
        if len(self.scrapetube_cache) > self.max_cache_size:
            self.scrapetube_cache.popitem(last=False)  # Remove oldest
        
        # Save to disk periodically
        if len(self.scrapetube_cache) % 10 == 0:  # Save every 10 additions
            self.save_scrapetube_cache()
    
    def is_video_processed(self, video_hash):
        """Check if video hash is in cache (fast in-memory check)"""
        return video_hash in self.video_hash_cache
    
    def mark_video_processed(self, video_hash):
        """Mark video as processed in cache"""
        self.video_hash_cache.add(video_hash)
        
        # Save periodically
        if len(self.video_hash_cache) % 50 == 0:  # Save every 50 additions
            self.save_video_hash_cache()
    
    def get_channel_id_from_url(self, channel_url):
        """Extract channel ID from various YouTube URL formats"""
        if "channel/" in channel_url:
            return channel_url.split("channel/")[1].split("/")[0]
        elif "c/" in channel_url:
            # Handle custom URLs - this is more complex and may need additional handling
            return None
        return None
    
    def get_channel_videos_scrapetube(self, channel_id: str, limit: int = 5) -> List[Dict]:
        """
        Fetch videos from a YouTube channel using scrapetube.
        
        Args:
            channel_id: YouTube channel ID or username
            limit: Maximum number of videos to fetch
            
        Returns:
            List of video dictionaries with metadata
        """
        try:
            # AGGRESSIVE CACHING: Check cache first
            cached_videos = self.get_cached_scrapetube_data(channel_id, max_age_seconds=300)
            if cached_videos:
                return cached_videos[:limit]  # Return only requested number
            
            self.log(f"Fetching videos from channel: {channel_id}")
            
            # Get videos using scrapetube
            videos = scrapetube.get_channel(channel_id, limit=limit)
            
            video_list = []
            for video in videos:
                video_data = {
                    'id': video.get('videoId'),
                    'title': video.get('title', {}).get('runs', [{}])[0].get('text', 'Unknown Title'),
                    'url': f"https://www.youtube.com/watch?v={video.get('videoId')}",
                    'published': video.get('publishedTimeText', {}).get('simpleText', 'Unknown'),
                    'view_count': video.get('viewCountText', {}).get('simpleText', '0'),
                    'duration': video.get('lengthText', {}).get('simpleText', 'Unknown'),
                    'thumbnail': video.get('thumbnail', {}).get('thumbnails', [{}])[-1].get('url', ''),
                    'channel_name': video.get('ownerText', {}).get('runs', [{}])[0].get('text', 'Unknown Channel'),
                    'fetched_at': datetime.now().isoformat()
                }
                video_list.append(video_data)
            
            # Cache the results
            self.cache_scrapetube_data(channel_id, video_list)
            
            self.log(f"Successfully fetched {len(video_list)} videos from {channel_id}")
            return video_list
            
        except Exception as e:
            self.log(f"Error fetching videos from {channel_id}: {e}", "error")
            return []
    
    def download_video(self, video_url, output_path):
        """Download video using yt-dlp with retries and better timeout handling"""
        # Ensure the download directory exists
        download_dir = os.path.dirname(output_path)
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        ydl_opts = {
            'format': 'best[ext=mp4]/best[ext=webm]/best',  # Best quality MP4/WebM
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 30,  # Reasonable timeout
            'retries': 3,  # Number of retries for http/https requests
            'fragment_retries': 5,  # Number of retries for fragments
            'retry_sleep': lambda n: 5 * (n + 1),  # Sleep between retries: 5s, 10s, 15s...
            'file_access_retries': 3,  # Retry on file access issues
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
            },
            # Try cookies file if available, but don't fail if not found
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'extract_flat': False,
            'ignoreerrors': False,
            'no_check_certificate': True,
            'prefer_insecure': True,
        }
        
        max_attempts = 2
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            try:
                self.log(f"Downloading video (attempt {attempt}/{max_attempts}): {video_url}")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
                
                if os.path.exists(output_path):
                    # Verify the file is valid and not empty
                    if os.path.getsize(output_path) > 0:
                        self.log(f"Download completed successfully: {output_path}", "success")
                        return output_path
                    else:
                        self.log("Download resulted in empty file, retrying...", "warning")
                        try:
                            os.remove(output_path)
                        except:
                            pass
                else:
                    self.log("Download failed - file not found, retrying...", "warning")
                
                # If we get here, the download failed but didn't raise an exception
                if attempt < max_attempts:
                    wait_time = 5 * attempt  # 5s, 10s
                    self.log(f"Waiting {wait_time} seconds before next attempt...", "info")
                    time.sleep(wait_time)
                
            except Exception as e:
                self.log(f"Error during download attempt {attempt}: {str(e)}", "error")
                if attempt < max_attempts:
                    wait_time = 5 * attempt
                    self.log(f"Waiting {wait_time} seconds before next attempt...", "info")
                    time.sleep(wait_time)
                else:
                    self.log("All download attempts failed", "error")
                    # Clean up any partial download
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except:
                            pass
                    return None
        
        # Try fallback method with pytube
        self.log("yt-dlp failed, trying pytube fallback...", "warning")
        return self.download_video_pytube_fallback(video_url, output_path)
    
    def upload_part_worker(self, part_path, part_title, tiktok_cookie, part_num, total_parts, proxy_config=None):
        """Worker thread to upload a single video part immediately"""
        try:
            self.log(f"📤 Worker {part_num}: Starting upload for part {part_num}/{total_parts} to TikTok account: {tiktok_cookie}", "info")
            
            # Check if file exists and has content
            if not os.path.exists(part_path):
                self.log(f"❌ Worker {part_num}: Part file not found: {part_path}", "error")
                return
                
            file_size = os.path.getsize(part_path)
            if file_size == 0:
                self.log(f"❌ Worker {part_num}: Part file is empty (0 bytes)", "error")
                return
                
            self.log(f"📁 Worker {part_num}: Part file size: {file_size} bytes", "info")
            
            # Upload the part immediately with proxy configuration
            success = self.upload_to_tiktok(part_path, part_title, tiktok_cookie, proxy_config)
            
            if success:
                self.log(f"✅ Worker {part_num}: Successfully uploaded part {part_num} of {total_parts} to {tiktok_cookie}", "success")
                # Clean up the part file immediately after successful upload
                try:
                    os.remove(part_path)
                    self.log(f"🧹 Worker {part_num}: Cleaned up part file", "info")
                except Exception as e:
                    self.log(f"⚠️ Worker {part_num}: Failed to clean up part file: {e}", "warning")
            else:
                self.log(f"❌ Worker {part_num}: Failed to upload part {part_num} of {total_parts} to {tiktok_cookie}", "error")
                # Keep the file for potential retry or manual upload
                self.log(f"💾 Worker {part_num}: Keeping part file for potential retry", "info")
                
        except Exception as e:
            self.log(f"❌ Worker {part_num}: Error uploading part {part_num} to {tiktok_cookie}: {str(e)}", "error")
            import traceback
            self.log(f"Worker {part_num} error details: {traceback.format_exc()}", "error")
    
    def download_video_pytube_fallback(self, video_url, output_path):
        """Fallback download method using pytube"""
        try:
            from pytube import YouTube
            
            self.log("Attempting download with pytube fallback...", "info")
            
            # Configure pytube with better settings
            yt = YouTube(
                video_url,
                use_oauth=False,
                allow_oauth_cache=False
            )
            
            # Get the best quality stream
            streams = yt.streams.filter(progressive=True, file_extension='mp4')
            if not streams:
                streams = yt.streams.filter(file_extension='mp4')
            
            if not streams:
                self.log("No suitable streams found with pytube", "error")
                return None
            
            # Get the highest resolution stream
            stream = streams.get_highest_resolution()
            
            self.log(f"Downloading with pytube: {stream.resolution} quality", "info")
            
            # Download the video
            stream.download(
                output_path=os.path.dirname(output_path),
                filename=os.path.basename(output_path)
            )
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                self.log(f"Pytube download successful: {output_path}", "success")
                return output_path
            else:
                self.log("Pytube download failed - file not found or empty", "error")
                return None
                
        except Exception as e:
            self.log(f"Pytube fallback failed: {str(e)}", "error")
            return None
    
    def split_video(self, video_path, num_parts=3, video_title="", tiktok_cookie="default", channel_name="Unknown", proxy_config=None):
        """Split video into specified number of parts - ULTRA FAST VERSION with duration processing"""
        video = None
        split_videos = []
        temp_files = []
        extended_video_path = None
        
        try:
            if not os.path.exists(video_path):
                self.log(f"Error: Video file not found: {video_path}", "error")
                return []
            
            self.log(f"🚀 Starting video processing with duration requirements: {video_path}")
            
            # Import duration processing utilities
            from video_duration_utils import process_video_for_upload, cleanup_extended_video
            
            # Process video according to duration requirements
            should_upload, message, processed_video_path = process_video_for_upload(
                video_path, 
                log_callback=self.log
            )
            
            if not should_upload:
                self.log(f"❌ Video rejected: {message}", "error")
                return []
            
            # Use the processed video path (original or extended)
            video_to_split = processed_video_path
            if processed_video_path != video_path:
                extended_video_path = processed_video_path
                self.log(f"📹 Using extended video for splitting: {processed_video_path}", "info")
            
            self.log(f"✅ Duration processing completed: {message}", "success")
            
            # Use the ffmpeg splitting method (actually crops the video with ffmpeg)
            from ffmpeg_split import ffmpeg_split_video
            
            # Split video using ffmpeg method (crops into time segments with ffmpeg)
            # Get the maximum duration limit from config (default 113 seconds = 1:53 minutes)
            max_duration = self.config.get("video_duration_limit", 113)
            split_videos = ffmpeg_split_video(video_to_split, num_parts, max_duration=max_duration)
            
            if not split_videos:
                self.log("❌ Fast splitting failed", "error")
                return []
            
            # Convert to absolute paths
            split_videos = [os.path.abspath(path) for path in split_videos]
            
            self.log(f"✅ Fast splitting completed: {len(split_videos)} parts created", "success")
            
            # Handle uploads if auto-upload is enabled
            if self.config.get("auto_upload", True):
                upload_workers = []
                
                for i, part_path in enumerate(split_videos):
                    self.log(f"🚀 Starting upload worker for part {i+1}...", "info")
                    
                    # Create upload worker thread for this part with base title only
                    upload_title = video_title
                    upload_worker = threading.Thread(
                        target=self.upload_part_worker,
                        args=(part_path, upload_title, tiktok_cookie, i+1, len(split_videos), proxy_config),
                        daemon=True
                    )
                    upload_workers.append(upload_worker)
                    upload_worker.start()
                
                # Wait for all upload workers to complete
                if upload_workers:
                    self.log(f"⏳ Waiting for all upload workers to complete...", "info")
                    for worker in upload_workers:
                        worker.join()
                    
                    self.log(f"✅ All upload workers completed", "success")
            else:
                self.log(f"📁 Parts created successfully (auto-upload disabled)", "info")
            
            return split_videos
            
        except Exception as e:
            self.log(f"Error in split_video: {str(e)}", "error")
            import traceback
            self.log(f"Error details: {traceback.format_exc()}", "error")
            return []
            
        finally:
            # Clean up main video
            if video:
                try:
                    video.close()
                except:
                    pass
            # Clean up any temp files that might be left
            for file in temp_files:
                try:
                    if os.path.exists(file) and file.endswith('_temp_audio.m4a'):
                        os.remove(file)
                except:
                    pass
            # Clean up extended video if it was created
            if extended_video_path and extended_video_path != video_path:
                try:
                    from video_duration_utils import cleanup_extended_video
                    cleanup_extended_video(extended_video_path)
                except Exception as e:
                    self.log(f"⚠️ Failed to clean up extended video: {e}", "warning")
    
    def upload_to_tiktok(self, video_path, title, cookie_name, proxy_config=None):
        """Upload video to TikTok"""
        try:
            self.log(f"🍪 Uploading to TikTok account '{cookie_name}': {title}")
            self.log(f"📁 File path: {video_path}")
            self.log(f"📁 File exists: {os.path.exists(video_path)}")
            
            # Additional file checks
            if os.path.exists(video_path):
                file_size = os.path.getsize(video_path)
                self.log(f"📊 File size: {file_size} bytes")
                
                # Check if file is too small (TikTok minimum requirements)
                if file_size < 100000:  # Less than 100KB
                    self.log(f"⚠️ Warning: File seems very small ({file_size} bytes)", "warning")
            
            # Load and verify cookies before upload
            from tiktok_uploader.cookies import load_cookies_from_file
            cookies = load_cookies_from_file(f"tiktok_session-{cookie_name}")
            session_id = next((c["value"] for c in cookies if c["name"] == 'sessionid'), None)
            dc_id = next((c["value"] for c in cookies if c["name"] == 'tt-target-idc'), None)
            
            if session_id and dc_id:
                self.log(f"🔐 Using session ID: {session_id[:10]}... (datacenter: {dc_id})")
            else:
                self.log(f"⚠️ Warning: Could not load cookies for {cookie_name}")
            
            # Configure proxy if available
            proxy_url = None
            if proxy_config:
                try:
                    # Parse proxy format: ip:port:username:password
                    parts = proxy_config.split(':')
                    if len(parts) == 4:
                        ip, port, username, password = parts
                        proxy_url = f"http://{username}:{password}@{ip}:{port}"
                        self.log(f"🌐 Using proxy: {ip}:{port}")
                    else:
                        self.log(f"⚠️ Invalid proxy format: {proxy_config}", "warning")
                except Exception as e:
                    self.log(f"⚠️ Error parsing proxy: {e}", "warning")
            
            self.log(f"🚀 Starting TikTok upload with session_user: {cookie_name}")
            
            tiktok.upload_video(
                session_user=cookie_name, 
                video=video_path, 
                title=title, 
                schedule_time=0, 
                allow_comment=1, 
                allow_duet=0, 
                allow_stitch=0, 
                visibility_type=0, 
                brand_organic_type=0, 
                branded_content_type=0, 
                ai_label=0, 
                proxy=proxy_url
            )
            self.log(f"✅ Successfully uploaded to TikTok account '{cookie_name}': {title}", "success")
            return True
        except Exception as e:
            self.log(f"❌ Error uploading to TikTok account '{cookie_name}': {e}", "error")
            import traceback
            self.log(f"Upload error details for '{cookie_name}': {traceback.format_exc()}", "error")
            return False
    
    def check_channel_for_new_videos(self, channel_info):
        """Check a specific channel for new videos using scrapetube - THREADED VERSION with proper cookie handling"""
        channel_id = channel_info.get("channel_id")
        channel_name = channel_info.get("name", "Unknown")
        tiktok_cookie = channel_info.get("tiktok_cookie", "default")
        
        if not channel_id:
            self.log(f"❌ Invalid channel ID for: {channel_name}", "error")
            return []
        
        try:
            self.log(f"🔍 Thread: Checking channel {channel_name} with TikTok cookie: {tiktok_cookie}")
            
            # Get only the latest video
            videos = self.get_channel_videos_scrapetube(channel_id, limit=1)
            
            if not videos:
                self.log(f"⚠️ Thread: No videos found for {channel_name}", "warning")
                return []
            
            # We only care about the newest video
            video_data = videos[0]
            video_id = video_data.get("id")
            video_url = video_data.get("url")
            video_title = video_data.get("title", "Untitled")
            published = video_data.get("published", "Unknown")
            
            if not video_id or not video_url:
                self.log(f"⚠️ Thread: Invalid video data for {channel_name}", "warning")
                return []
            
            # Check if this is a new video
            video_hash = hashlib.md5(f"{video_id}_{video_title}".encode()).hexdigest()
            
            # If we've already processed this video, skip it
            if self.is_video_processed(video_hash):
                self.log(f"⏭️ Thread: Video already processed for {channel_name}: {video_title[:50]}...", "info")
                return []
            
            self.log(f"🎉 Thread: Found NEW video for {channel_name}: {video_title}", "success")
            self.log(f"📅 Thread: Published: {published}")
            self.log(f"🍪 Thread: Will upload to TikTok account: {tiktok_cookie}")
            
            # Download the video
            output_path = os.path.join(
                os.path.abspath(self.config["download_path"]), 
                f"{channel_name}_{video_id}.mp4"
            )
            
            downloaded_path = self.download_video(video_url, output_path)
            if not downloaded_path:
                self.log(f"❌ Thread: Failed to download video for {channel_name}", "error")
                return []
            
            # Split the video into parts (TikTok max is 3 minutes) - use fewer parts for speed
            num_parts = min(3, self.config.get("video_parts", 3))  # Default to 3 parts for speed
            
            # Get proxy configuration for this channel
            proxy_config = channel_info.get("proxy")
            if proxy_config:
                # Convert proxy dict to string format
                proxy_string = f"{proxy_config['ip']}:{proxy_config['port']}:{proxy_config['username']}:{proxy_config['password']}"
                self.log(f"🌐 Using proxy for channel {channel_name}: {proxy_config['ip']}:{proxy_config['port']}")
            else:
                proxy_string = None
                self.log(f"📡 No proxy configured for channel {channel_name}")
            
            split_videos = self.split_video(downloaded_path, num_parts, video_title, tiktok_cookie, channel_name, proxy_string)
            if not split_videos:
                self.log(f"❌ Thread: Failed to split video for {channel_name}", "error")
                return []
            
            # Uploads are now handled automatically in split_video function
            # Each part is uploaded immediately when it's created
            if self.config.get("auto_upload", True):
                self.log(f"✅ Thread: Auto-upload enabled for {channel_name} - parts will be uploaded to {tiktok_cookie}", "info")
            else:
                self.log(f"⚠️ Thread: Auto-upload disabled for {channel_name} - parts created but not uploaded", "warning")
            
            # Mark video as processed
            self.mark_video_processed(video_hash)
            self.processed_videos.append(video_hash)
            self.save_processed_videos()
            
            # Clean up the original downloaded file
            try:
                os.remove(downloaded_path)
                self.log(f"🧹 Thread: Cleaned up original video for {channel_name}", "info")
            except Exception as e:
                self.log(f"⚠️ Thread: Failed to clean up original video for {channel_name}: {e}", "warning")
            
            self.log(f"✅ Thread: Completed processing for {channel_name}: {video_title}", "success")
            
            # Return the video info for GUI updates
            return [{
                'title': video_title,
                'url': video_url,
                'id': video_id,
                'published': published,
                'channel_name': channel_name,
                'tiktok_cookie': tiktok_cookie
            }]
                
        except Exception as e:
            self.log(f"❌ Thread: Error checking channel {channel_name}: {e}", "error")
            import traceback
            self.log(f"Thread error details for {channel_name}: {traceback.format_exc()}", "error")
            return []
    
    def monitor_all_channels(self):
        """Monitor all configured channels - THREADED VERSION with proper cookie handling"""
        channel_count = len(self.config['channels'])
        self.log(f"🚀 Checking {channel_count} channels in parallel...")
        
        # Create threads for each channel to process them simultaneously
        threads = []
        
        for channel in self.config['channels']:
            thread = threading.Thread(
                target=self.check_channel_for_new_videos,
                args=(channel,),
                daemon=True
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # AGGRESSIVE CACHING: Save caches periodically
        if hasattr(self, 'save_counter'):
            self.save_counter += 1
        else:
            self.save_counter = 1
        
        if self.save_counter % 5 == 0:  # Save every 5 monitoring cycles
            self.save_scrapetube_cache()
            self.save_video_hash_cache()
    
    def start_monitoring(self):
        """Start the monitoring service"""
        interval = self.config.get("check_interval_seconds", 1)
        channel_count = len(self.config['channels'])
        
        self.log(f"🚀 Starting THREADED YouTube monitor with {channel_count} channels")
        self.log(f"⚡ Channels will be checked in parallel every {interval} second")
        self.log(f"🍪 Each channel will upload to its own TikTok account")
        
        # Show channel configuration
        self.log(f"\n📋 Channel Configuration:")
        for i, channel in enumerate(self.config['channels'], 1):
            self.log(f"  {i}. {channel['name']} -> TikTok: {channel['tiktok_cookie']}")
        
        self.log("\n🎯 Press Ctrl+C to stop monitoring")
        self.log("=" * 60)
        
        check_count = 0
        try:
            while True:
                check_count += 1
                self.log(f"\n🔄 Check #{check_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Run the threaded check
                self.monitor_all_channels()
                
                # No wait - maximum speed
                # Continuous monitoring with no delays
                
        except KeyboardInterrupt:
            self.log("\n⏹️ Monitoring stopped by user")
        except Exception as e:
            self.log(f"❌ Monitoring error: {e}", "error")
            self.log("🔄 Restarting monitoring immediately...")
            # No delay - restart immediately
            self.start_monitoring()

def main():
    parser = argparse.ArgumentParser(description="YouTube Channel Monitor and TikTok Auto-Uploader (Scrapetube Version)")
    parser.add_argument("--config", default="monitor_config.json", help="Configuration file path")
    parser.add_argument("--add-channel", help="Add a new channel (format: name,channel_id,tiktok_cookie)")
    parser.add_argument("--list-channels", action="store_true", help="List configured channels")
    parser.add_argument("--remove-channel", help="Remove a channel by name")
    parser.add_argument("--start", action="store_true", help="Start monitoring")
    parser.add_argument("--check-once", action="store_true", help="Check channels once and exit")
    
    args = parser.parse_args()
    
    monitor = YouTubeMonitor(args.config)
    
    if args.add_channel:
        parts = args.add_channel.split(",", 2)
        if len(parts) >= 2:
            name = parts[0].strip()
            channel_id = parts[1].strip()
            tiktok_cookie = parts[2].strip() if len(parts) > 2 else "default"
            
            monitor.config["channels"].append({
                "name": name,
                "channel_id": channel_id,
                "tiktok_cookie": tiktok_cookie
            })
            with open(args.config, 'w') as f:
                json.dump(monitor.config, f, indent=4)
            print(f"Added channel: {name} with TikTok cookie: {tiktok_cookie}")
        else:
            print("Invalid format. Use: name,channel_id,tiktok_cookie")
    
    elif args.list_channels:
        print("Configured channels:")
        for channel in monitor.config["channels"]:
            print(f"  - {channel['name']}: {channel['channel_id']} (TikTok: {channel.get('tiktok_cookie', 'default')})")
    
    elif args.remove_channel:
        monitor.config["channels"] = [
            ch for ch in monitor.config["channels"] 
            if ch["name"] != args.remove_channel
        ]
        with open(args.config, 'w') as f:
            json.dump(monitor.config, f, indent=4)
        print(f"Removed channel: {args.remove_channel}")
    
    elif args.check_once:
        monitor.monitor_all_channels()
    
    elif args.start:
        monitor.start_monitoring()
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
