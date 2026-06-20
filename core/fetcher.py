import yt_dlp
import urllib.request
import re
from PIL import Image
from io import BytesIO
from typing import Dict, Any, Optional

class VideoFetcher:
    """Handles fetching video metadata and thumbnails using yt-dlp."""
    def __init__(self) -> None:
        pass

    def fetch_metadata(self, url: str) -> Dict[str, Any]:
        """
        Extracts metadata for a video or playlist.
        Returns a dictionary with status and info.
        """
        ydl_opts = {
            'extract_flat': 'in_playlist',  # Don't extract all playlist items recursively yet
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'playlist_items': '1-100', # Limit to first 100 items to avoid freezing for massive playlists
            'check_formats': False,
            'force_ipv4': True,
            'socket_timeout': 5,
        }

        is_instagram = "instagram.com" in url or "instagr.am" in url
        try_browsers = [None]
        if is_instagram:
            try_browsers.extend(['chrome', 'edge', 'firefox', 'brave', 'opera'])

        info = None
        first_exception = None
        last_exception = None

        for i, browser in enumerate(try_browsers):
            opts = ydl_opts.copy()
            if browser:
                opts['cookiesfrombrowser'] = (browser,)
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                first_exception = None
                last_exception = None
                break
            except Exception as e:
                if i == 0:
                    first_exception = e
                last_exception = e
                if not is_instagram:
                    break
                err_str = str(e).lower()
                if any(x in err_str for x in ["cookie", "login", "empty media response", "sign in", "decrypt"]):
                    continue
                else:
                    break

        try:
            if first_exception:
                raise first_exception
            elif last_exception:
                raise last_exception
            
            if not info:
                raise Exception("Failed to retrieve information.")
                
            # Check if it is a playlist
            is_playlist = info.get('_type') == 'playlist' or 'entries' in info
            
            if is_playlist:
                entries = list(info.get('entries', []))
                # Filter out entries that might be None or deleted
                valid_entries = [e for e in entries if e is not None]
                return {
                    "status": "success",
                    "type": "playlist",
                    "title": info.get('title') or "Untitled Playlist",
                    "uploader": info.get('uploader') or info.get('uploader_id') or "Unknown Channel",
                    "entries_count": len(valid_entries),
                    "entries": [
                        {
                            "title": e.get('title') or "Untitled Video",
                            "url": f"https://www.youtube.com/watch?v={e.get('id')}" if e.get('id') else e.get('url'),
                            "duration": e.get('duration')
                        }
                        for e in valid_entries
                    ],
                    "raw_info": info
                }
            else:
                # Single video
                # Fetch best thumbnail URL
                thumbnails = info.get('thumbnails', [])
                thumbnail_url = None
                if thumbnails:
                    # Find highest quality or first one
                    thumbnail_url = thumbnails[-1].get('url')
                
                return {
                    "status": "success",
                    "type": "video",
                    "title": info.get('title') or "Untitled Video",
                    "uploader": info.get('uploader') or "Unknown Channel",
                    "duration": info.get('duration'),
                    "thumbnail_url": thumbnail_url,
                    "url": url,
                    "raw_info": info
                }

        except yt_dlp.utils.DownloadError as de:
            error_msg = str(de)
            friendly_msg = "An error occurred while fetching information."
            if "private" in error_msg.lower():
                friendly_msg = "This video is private and cannot be downloaded."
            elif "age-restricted" in error_msg.lower() or "confirm your age" in error_msg.lower():
                friendly_msg = "This video is age-restricted and requires authentication."
            elif "not available" in error_msg.lower() or "deleted" in error_msg.lower():
                friendly_msg = "This video is unavailable or has been deleted."
            elif "sign in" in error_msg.lower():
                friendly_msg = "This video requires signing in."
            else:
                # Extract clean error message from yt-dlp error output
                clean_match = re.search(r'ERROR:\s*(.*)', error_msg)
                if clean_match:
                    friendly_msg = clean_match.group(1)
            
            return {
                "status": "error",
                "message": friendly_msg
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def fetch_thumbnail_image(self, url: str) -> Optional[Image.Image]:
        """
        Fetches the thumbnail image and returns a PIL Image object.
        """
        if not url:
            return None
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                img_data = response.read()
                return Image.open(BytesIO(img_data))
        except Exception as e:
            import logging
            logging.warning(f"Error fetching thumbnail image: {e}")
            return None
