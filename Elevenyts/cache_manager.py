# Elevenyts/cache_manager.py
import os
import shutil
import threading
import time

class CacheManager:
    def __init__(self, cache_dir="/tmp/bot_cache", cleanup_interval_minutes=30, min_free_mb=500):
        self.cache_dir = cache_dir
        self.cleanup_interval_minutes = cleanup_interval_minutes
        self.min_free_mb = min_free_mb
        
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        self.start_cleanup_thread()
        print(f"✅ CacheManager started | Dir: {cache_dir} | Interval: {cleanup_interval_minutes}min | Min free: {min_free_mb}MB")
    
    def start_cleanup_thread(self):
        def cleanup_loop():
            while True:
                time.sleep(self.cleanup_interval_minutes * 60)
                self.run_cleanup()
        
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
    
    def run_cleanup(self):
        try:
            stat = shutil.disk_usage(self.cache_dir)
            free_mb = stat.free / (1024 * 1024)
            
            if free_mb < self.min_free_mb:
                deleted_count = 0
                for filename in os.listdir(self.cache_dir):
                    filepath = os.path.join(self.cache_dir, filename)
                    try:
                        if os.path.isfile(filepath):
                            os.remove(filepath)
                            deleted_count += 1
                    except:
                        pass
                print(f"🧹 Cache cleaned: {deleted_count} files removed | Free: {free_mb:.0f}MB -> {shutil.disk_usage(self.cache_dir).free / (1024*1024):.0f}MB")
            else:
                print(f"✓ Cache OK: {free_mb:.0f}MB free (above {self.min_free_mb}MB limit)")
        except Exception as e:
            print(f"❌ Cache cleanup error: {e}")

_cache_manager = None

def init_cache_manager(cache_dir="/tmp/bot_cache", cleanup_interval_minutes=30, min_free_mb=500):
    global _cache_manager
    _cache_manager = CacheManager(cache_dir, cleanup_interval_minutes, min_free_mb)
    return _cache_manager
