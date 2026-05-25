# Elevenyts/yt.py (အသစ်)
import asyncio
import logging
from youtubesearchpython import VideosSearch  # ဒါကို အသစ်ထည့်
from Elevenyts.config import DURATION_LIMIT
from Elevenyts.helpers.telegram import Track

logger = logging.getLogger(__name__)

# မြန်မာသီချင်းအတွက် fallback keywords (လိုအပ်ရင်)
BURMESE_FALLBACK = {
    "အောင်လမင်း": "အောင်လမင်း official audio",
    "နေတိုး": "နေတိုး song",
    # လိုအပ်သလို ထပ်ထည့်
}

async def search(query: str, message_id: int = None) -> Track or None:
    """
    YouTube မှာ သီချင်းရှာတယ် - Innertube API သုံးတယ် (မြန်၊ အခမဲ့)
    """
    try:
        logger.info(f"Searching: {query}")
        
        # မြန်မာစာ Zawgyi ရှိရင် Unicode ပြောင်း (လိုအပ်ရင်)
        # import zawgyi
        # if zawgyi.detect(query):
        #     query = zawgyi.to_unicode(query)
        
        # Fallback စာရင်းထဲမှာ ရှိရင် ပြောင်းသုံး
        for burmese_name, search_term in BURMESE_FALLBACK.items():
            if burmese_name in query:
                query = search_term
                break
        
        # Innertube API နဲ့ ရှာ
        videos_search = VideosSearch(query, limit=1)
        result = await asyncio.get_event_loop().run_in_executor(
            None, videos_search.result
        )
        
        if result and result.get('result') and len(result['result']) > 0:
            video = result['result'][0]
            
            # Track object ဆောက်မယ်
            track = Track()
            track.id = video['id']
            track.url = video['link']
            track.title = video['title']
            track.duration = video['duration']
            track.duration_sec = _parse_duration(video['duration'])
            track.thumb = video.get('thumbnails', [{}])[-1].get('url', '')
            track.channel = video['channel']['name']
            track.is_live = 'live' in video.get('type', '').lower()
            
            logger.info(f"Found: {track.title} ({track.duration})")
            return track
        else:
            logger.warning(f"No results found for: {query}")
            return None
            
    except Exception as e:
        logger.error(f"Search error: {e}")
        # Fallback to yt-dlp if Innertube fails
        return await _search_fallback_ytdlp(query, message_id)

def _parse_duration(duration_str: str) -> int:
    """'3:45' ကို စက္ကန့် (225) ပြောင်း"""
    if not duration_str:
        return 0
    parts = duration_str.split(':')
    if len(parts) == 2:  # MM:SS
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:  # HH:MM:SS
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return int(parts[0]) if parts else 0

async def _search_fallback_ytdlp(query: str, message_id: int = None) -> Track or None:
    """
    Innertube အလုပ်မလုပ်ရင် yt-dlp နဲ့ fallback လုပ်
    """
    import yt_dlp
    
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(
                None,
                lambda: ydl.extract_info(f"ytsearch1:{query}", download=False)
            )
            
            if info and info.get('entries') and len(info['entries']) > 0:
                entry = info['entries'][0]
                track = Track()
                track.id = entry['id']
                track.url = f"https://youtu.be/{entry['id']}"
                track.title = entry['title']
                track.duration = entry.get('duration_string', '0:00')
                track.duration_sec = entry.get('duration', 0)
                track.is_live = entry.get('is_live', False)
                return track
    except Exception as e:
        logger.error(f"yt-dlp fallback error: {e}")
    
    return None

# playlist အတွက် function (အသစ်ပြင်ရန် လိုသေး)
async def playlist(limit: int, mention: str, url: str) -> list:
    """
    YouTube playlist က tracks တွေကို ယူတယ်
    """
    from youtubesearchpython import Playlist as YTPlaylist
    
    tracks = []
    try:
        playlist_obj = YTPlaylist(url)
        await asyncio.get_event_loop().run_in_executor(None, playlist_obj.get_next_page, 10)
        
        for video in playlist_obj.videos[:limit]:
            track = Track()
            track.id = video['id']
            track.url = video['link']
            track.title = video['title']
            track.duration = video.get('duration', '0:00')
            track.user = mention
            tracks.append(track)
    except Exception as e:
        logger.error(f"Playlist error: {e}")
        # Fallback to yt-dlp
        return await _playlist_fallback_ytdlp(limit, mention, url)
    
    return tracks

async def _playlist_fallback_ytdlp(limit: int, mention: str, url: str) -> list:
    """yt-dlp fallback for playlist"""
    import yt_dlp
    
    tracks = []
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            
            if info and info.get('entries'):
                for entry in info['entries'][:limit]:
                    if entry:
                        track = Track()
                        track.id = entry['id']
                        track.url = f"https://youtu.be/{entry['id']}"
                        track.title = entry['title']
                        track.duration = entry.get('duration_string', '0:00')
                        track.duration_sec = entry.get('duration', 0)
                        track.user = mention
                        tracks.append(track)
    except Exception as e:
        logger.error(f"Playlist fallback error: {e}")
    
    return tracks

async def download(file_id: str, is_live: bool = False, video: bool = False) -> str:
    """
    သီချင်းကို download လုပ်တယ် (မူရင်းအတိုင်း ထားလို့ရ)
    """
    import yt_dlp
    
    format_type = 'bestvideo+bestaudio' if video else 'bestaudio'
    ydl_opts = {
        'format': format_type,
        'outtmpl': f'downloads/{file_id}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    
    if is_live:
        ydl_opts['live_from_start'] = True
    
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(
                None,
                lambda: ydl.extract_info(f"https://youtu.be/{file_id}", download=True)
            )
            return ydl.prepare_filename(info)
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None
