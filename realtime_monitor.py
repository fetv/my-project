#!/usr/bin/env python3
"""
Real-time YouTube Channel Monitor
Checks for new videos every second using scrapetube.
"""

import sys
import time
from datetime import datetime
from test_scrapetube_fetch import YouTubeChannelMonitor

def monitor_channel_realtime(channel_id: str, max_videos: int = 5):
    """
    Monitor a single channel every second for new videos.
    
    Args:
        channel_id: YouTube channel ID
        max_videos: Maximum videos to check per cycle
    """
    print(f"🚀 Real-time monitoring started!")
    print(f"📺 Channel: {channel_id}")
    print(f"⏱️ Checking every second for new videos")
    print(f"🔍 Checking latest {max_videos} videos per cycle")
    print("Press Ctrl+C to stop")
    print("="*60)
    
    # Create monitor with persistent cache
    monitor = YouTubeChannelMonitor(f"realtime_{channel_id}.json")
    check_count = 0
    start_time = time.time()
    
    try:
        while True:
            check_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Get new videos
            new_videos = monitor.get_new_videos(channel_id, max_videos)
            
            if new_videos:
                print(f"\n🎉 [{current_time}] Found {len(new_videos)} new videos!")
                for video in new_videos:
                    print(f"📺 {video['title']}")
                    print(f"🔗 {video['url']}")
                    print(f"📅 {video['published']}")
                    print(f"👁️ {video['view_count']}")
                    print("-" * 40)
            else:
                # Show status every 30 seconds to avoid spam
                if check_count % 30 == 0:
                    elapsed = time.time() - start_time
                    print(f"[{current_time}] Check #{check_count} ({elapsed:.0f}s elapsed): No new videos")
            
            # No wait - maximum speed
            # Continuous monitoring with no delays
            
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n⏹️ Monitoring stopped after {check_count} checks ({elapsed:.0f} seconds)")
        print("💾 Cache saved for next run")


def monitor_multiple_channels_realtime(channel_ids: list, max_videos: int = 3):
    """
    Monitor multiple channels every second.
    
    Args:
        channel_ids: List of YouTube channel IDs
        max_videos: Maximum videos to check per channel
    """
    print(f"🚀 Multi-channel real-time monitoring started!")
    print(f"📺 Channels: {len(channel_ids)}")
    for i, channel in enumerate(channel_ids, 1):
        print(f"  {i}. {channel}")
    print(f"⏱️ Checking every second for new videos")
    print(f"🔍 Checking latest {max_videos} videos per channel")
    print("Press Ctrl+C to stop")
    print("="*60)
    
    # Create monitors for each channel
    monitors = {}
    for channel_id in channel_ids:
        monitors[channel_id] = YouTubeChannelMonitor(f"realtime_{channel_id}.json")
    
    check_count = 0
    start_time = time.time()
    
    try:
        while True:
            check_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            total_new_videos = 0
            
            # Check each channel
            for channel_id in channel_ids:
                monitor = monitors[channel_id]
                new_videos = monitor.get_new_videos(channel_id, max_videos)
                
                if new_videos:
                    total_new_videos += len(new_videos)
                    print(f"\n🎉 [{current_time}] Channel {channel_id}: {len(new_videos)} new videos!")
                    for video in new_videos:
                        print(f"  📺 {video['title']}")
                        print(f"  🔗 {video['url']}")
            
            # Show status every 30 seconds
            if check_count % 30 == 0:
                elapsed = time.time() - start_time
                print(f"[{current_time}] Check #{check_count} ({elapsed:.0f}s elapsed): {total_new_videos} total new videos")
            
            # No wait - maximum speed
            # Continuous monitoring with no delays
            
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n⏹️ Monitoring stopped after {check_count} checks ({elapsed:.0f} seconds)")
        print("💾 Cache saved for next run")


def main():
    """Main function with configuration."""
    
    # CONFIGURATION - Change these values as needed
    CHANNEL_ID = "UCnyrsGaLYX2GEALD_FzxdIA"  # Your target channel ID
    CHANNEL_IDS = [
        "UCnyrsGaLYX2GEALD_FzxdIA",  # Your channel
    ]
    MAX_VIDEOS = 5  # Number of videos to check per cycle
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "single":
            monitor_channel_realtime(CHANNEL_ID, MAX_VIDEOS)
        elif mode == "multi":
            monitor_multiple_channels_realtime(CHANNEL_IDS, MAX_VIDEOS)
        else:
            print("Usage:")
            print("  python realtime_monitor.py single  - Monitor one channel")
            print("  python realtime_monitor.py multi   - Monitor multiple channels")
    else:
        # Default: monitor single channel
        print("🚀 Starting real-time monitoring...")
        print("💡 Tip: Use 'python realtime_monitor.py multi' for multiple channels")
        print()
        monitor_channel_realtime(CHANNEL_ID, MAX_VIDEOS)


if __name__ == "__main__":
    main()
