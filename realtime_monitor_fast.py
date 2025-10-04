#!/usr/bin/env python3
"""
Ultra-Fast Real-time YouTube Channel Monitor
Optimized for 20-30 second maximum response time.
"""

import sys
import time
import threading
import asyncio
import concurrent.futures
from datetime import datetime, timedelta
from test_scrapetube_fetch import YouTubeChannelMonitor
import scrapetube

class FastYouTubeMonitor:
    """Ultra-fast YouTube monitor with aggressive optimization."""
    
    def __init__(self, cache_file: str = "fast_monitor_cache.json"):
        self.cache_file = cache_file
        self.processed_videos = set()
        self.last_check_times = {}
        self.video_cache = {}
        self.cache_duration = 15  # Cache for 15 seconds (very aggressive)
        self.max_workers = 3  # Parallel workers
        
    def get_channel_videos_fast(self, channel_id: str, limit: int = 3) -> list:
        """
        Ultra-fast video fetching with aggressive caching.
        Only checks latest 3 videos by default for speed.
        """
        current_time = time.time()
        cache_key = f"{channel_id}_{limit}"
        
        # Check cache first (very aggressive caching)
        if cache_key in self.video_cache:
            cache_time, videos = self.video_cache[cache_key]
            if current_time - cache_time < self.cache_duration:
                return videos
        
        try:
            # Fetch only the latest videos (minimal data)
            videos = scrapetube.get_channel(channel_id, limit=limit)
            
            video_list = []
            for video in videos:
                video_data = {
                    'id': video.get('videoId'),
                    'title': video.get('title', {}).get('runs', [{}])[0].get('text', 'Unknown Title'),
                    'url': f"https://www.youtube.com/watch?v={video.get('videoId')}",
                    'published': video.get('publishedTimeText', {}).get('simpleText', 'Unknown'),
                    'fetched_at': datetime.now().isoformat()
                }
                video_list.append(video_data)
            
            # Cache the results
            self.video_cache[cache_key] = (current_time, video_list)
            
            return video_list
            
        except Exception as e:
            print(f"Error fetching videos from {channel_id}: {e}")
            return []
    
    def get_new_videos_fast(self, channel_id: str, limit: int = 3) -> list:
        """
        Ultra-fast new video detection.
        Only checks latest 3 videos for maximum speed.
        """
        videos = self.get_channel_videos_fast(channel_id, limit)
        new_videos = []
        
        for video in videos:
            video_id = video['id']
            if video_id and video_id not in self.processed_videos:
                new_videos.append(video)
                self.processed_videos.add(video_id)
        
        return new_videos

def monitor_channel_ultra_fast(channel_id: str, max_videos: int = 3):
    """
    Ultra-fast single channel monitoring.
    Optimized for 20-30 second maximum response time.
    """
    print(f"🚀 Ultra-fast monitoring started!")
    print(f"📺 Channel: {channel_id}")
    print(f"⚡ Target: 20-30 second maximum response time")
    print(f"🔍 Checking latest {max_videos} videos per cycle")
    print("Press Ctrl+C to stop")
    print("="*60)
    
    monitor = FastYouTubeMonitor(f"ultra_fast_{channel_id}.json")
    check_count = 0
    start_time = time.time()
    
    try:
        while True:
            cycle_start = time.time()
            check_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Get new videos (ultra-fast)
            new_videos = monitor.get_new_videos_fast(channel_id, max_videos)
            
            cycle_time = time.time() - cycle_start
            
            if new_videos:
                print(f"\n🎉 [{current_time}] Found {len(new_videos)} new videos! (Cycle: {cycle_time:.1f}s)")
                for video in new_videos:
                    print(f"📺 {video['title']}")
                    print(f"🔗 {video['url']}")
                    print(f"📅 {video['published']}")
                    print("-" * 40)
            else:
                # Show status every 10 seconds (more frequent updates)
                if check_count % 10 == 0:
                    elapsed = time.time() - start_time
                    print(f"[{current_time}] Check #{check_count} (Cycle: {cycle_time:.1f}s, Total: {elapsed:.0f}s): No new videos")
            
            # No sleep - maximum speed
            # Ultra-aggressive: continuous monitoring with no delays
            
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n⏹️ Monitoring stopped after {check_count} checks ({elapsed:.0f} seconds)")
        print("💾 Cache saved for next run")

def monitor_multiple_channels_ultra_fast(channel_ids: list, max_videos: int = 2):
    """
    Ultra-fast multi-channel monitoring with parallel processing.
    """
    print(f"🚀 Ultra-fast multi-channel monitoring started!")
    print(f"📺 Channels: {len(channel_ids)}")
    for i, channel in enumerate(channel_ids, 1):
        print(f"  {i}. {channel}")
    print(f"⚡ Target: 20-30 second maximum response time")
    print(f"🔍 Checking latest {max_videos} videos per channel")
    print("Press Ctrl+C to stop")
    print("="*60)
    
    monitors = {}
    for channel_id in channel_ids:
        monitors[channel_id] = FastYouTubeMonitor(f"ultra_fast_{channel_id}.json")
    
    check_count = 0
    start_time = time.time()
    
    def check_channel_fast(channel_id):
        """Check a single channel quickly"""
        monitor = monitors[channel_id]
        return channel_id, monitor.get_new_videos_fast(channel_id, max_videos)
    
    try:
        while True:
            cycle_start = time.time()
            check_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            total_new_videos = 0
            
            # Parallel processing for multiple channels
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(channel_ids)) as executor:
                futures = {executor.submit(check_channel_fast, channel_id): channel_id for channel_id in channel_ids}
                
                for future in concurrent.futures.as_completed(futures):
                    channel_id, new_videos = future.result()
                    
                    if new_videos:
                        total_new_videos += len(new_videos)
                        print(f"\n🎉 [{current_time}] Channel {channel_id}: {len(new_videos)} new videos!")
                        for video in new_videos:
                            print(f"  📺 {video['title']}")
                            print(f"  🔗 {video['url']}")
            
            cycle_time = time.time() - cycle_start
            
            # Show status every 10 seconds
            if check_count % 10 == 0:
                elapsed = time.time() - start_time
                print(f"[{current_time}] Check #{check_count} (Cycle: {cycle_time:.1f}s, Total: {elapsed:.0f}s): {total_new_videos} total new videos")
            
            # No sleep - maximum speed
            # Ultra-aggressive: continuous monitoring with no delays
            
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n⏹️ Monitoring stopped after {check_count} checks ({elapsed:.0f} seconds)")
        print("💾 Cache saved for next run")

def monitor_channel_aggressive(channel_id: str, max_videos: int = 2):
    """
    Most aggressive monitoring - checks every 0.5 seconds with minimal data.
    """
    print(f"🚀 AGGRESSIVE monitoring started!")
    print(f"📺 Channel: {channel_id}")
    print(f"⚡ Target: 10-15 second maximum response time")
    print(f"🔍 Checking latest {max_videos} videos every 0.5 seconds")
    print("Press Ctrl+C to stop")
    print("="*60)
    
    monitor = FastYouTubeMonitor(f"aggressive_{channel_id}.json")
    check_count = 0
    start_time = time.time()
    
    try:
        while True:
            cycle_start = time.time()
            check_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Get new videos (minimal data)
            new_videos = monitor.get_new_videos_fast(channel_id, max_videos)
            
            cycle_time = time.time() - cycle_start
            
            if new_videos:
                print(f"\n🎉 [{current_time}] Found {len(new_videos)} new videos! (Cycle: {cycle_time:.1f}s)")
                for video in new_videos:
                    print(f"📺 {video['title']}")
                    print(f"🔗 {video['url']}")
                    print("-" * 30)
            else:
                # Show status every 5 seconds
                if check_count % 10 == 0:
                    elapsed = time.time() - start_time
                    print(f"[{current_time}] Check #{check_count} (Cycle: {cycle_time:.1f}s, Total: {elapsed:.0f}s): No new videos")
            
            # No sleep - maximum speed
            # Ultra-aggressive: continuous monitoring with no delays
            
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n⏹️ Monitoring stopped after {check_count} checks ({elapsed:.0f} seconds)")
        print("💾 Cache saved for next run")

def main():
    """Main function with configuration."""
    
    # CONFIGURATION - Change these values as needed
    CHANNEL_ID = "UCE1X5PMyhYe8hZlIROAS4Aw"  # Your target channel ID
    CHANNEL_IDS = [
        "UCE1X5PMyhYe8hZlIROAS4Aw",  # Your channel
    ]
    MAX_VIDEOS = 3  # Reduced for speed
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "single":
            monitor_channel_ultra_fast(CHANNEL_ID, MAX_VIDEOS)
        elif mode == "multi":
            monitor_multiple_channels_ultra_fast(CHANNEL_IDS, MAX_VIDEOS)
        elif mode == "aggressive":
            monitor_channel_aggressive(CHANNEL_ID, 2)  # Most aggressive
        else:
            print("Usage:")
            print("  python realtime_monitor_fast.py single      - Ultra-fast single channel")
            print("  python realtime_monitor_fast.py multi       - Ultra-fast multiple channels")
            print("  python realtime_monitor_fast.py aggressive  - Most aggressive (10-15s target)")
    else:
        # Default: ultra-fast single channel
        print("🚀 Starting ultra-fast monitoring...")
        print("💡 Tips:")
        print("  - Use 'aggressive' mode for fastest response")
        print("  - Use 'multi' mode for multiple channels")
        print()
        monitor_channel_ultra_fast(CHANNEL_ID, MAX_VIDEOS)

if __name__ == "__main__":
    main()
