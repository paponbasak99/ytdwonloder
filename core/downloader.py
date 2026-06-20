import os
import sys
import shutil
import threading
import uuid
import yt_dlp
from utils.helpers import sanitize_filename, get_unique_path

from typing import Callable, Any, Optional

class DownloadCancelledException(Exception):
    """Exception raised when download is cancelled by the user."""
    pass

class YoutubeDownloader:
    """Manages the lifecycle of a single video/audio download."""
    def __init__(self, url: str, save_path: str, format_choice: str = "MP4", quality_choice: str = "Best", 
                 audio_only: bool = False, audio_format: str = "MP3", progress_callback: Optional[Callable[[dict], None]] = None) -> None:
        self.url = url
        self.save_path = save_path
        self.format_choice = format_choice
        self.quality_choice = quality_choice
        self.audio_only = audio_only
        self.audio_format = audio_format
        self.progress_callback = progress_callback
        
        self.cancel_event = threading.Event()
        self.download_id = uuid.uuid4().hex[:8]
        self.temp_dir = os.path.join(self.save_path, f".tmp_ytdl_{self.download_id}")
        
        self.title = "Fetching Title..."
        self.status = "Pending"  # Pending, Downloading, Paused, Completed, Failed, Cancelled
        self.error_message = ""
        self.final_file_path = None

    def get_ffmpeg_path(self):
        if getattr(sys, 'frozen', False):
            # PyInstaller environment
            base_path = sys._MEIPASS
        else:
            # Development environment
            # Move up from core to project root
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        ffmpeg_path = os.path.join(base_path, "assets", "ffmpeg.exe")
        if os.path.exists(ffmpeg_path):
            return ffmpeg_path
        return "ffmpeg" # Fallback to PATH

    def get_ydl_format(self):
        if self.audio_only:
            return "bestaudio/best"
        
        heights = {
            "4K": "2160",
            "1440p": "1440",
            "1080p": "1080",
            "720p": "720",
            "480p": "480",
            "360p": "360",
        }
        height_limit = heights.get(self.quality_choice, "")
        height_str = f"[height<={height_limit}]" if height_limit else ""
        
        if self.format_choice == "MP4":
            return f"bestvideo{height_str}[ext=mp4]+bestaudio[ext=m4a]/best{height_str}[ext=mp4]"
        elif self.format_choice == "WEBM":
            return f"bestvideo{height_str}[ext=webm]+bestaudio[ext=webm]/best{height_str}[ext=webm]"
        elif self.format_choice == "MKV":
            # For MKV, get best quality and merge into mkv format
            return f"bestvideo{height_str}+bestaudio/best{height_str}"
        else:
            return f"bestvideo{height_str}+bestaudio/best{height_str}"

    def progress_hook(self, d):
        if self.cancel_event.is_set():
            raise DownloadCancelledException("Download cancelled by user")

        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            
            percent = (downloaded / total * 100) if total > 0 else 0
            
            # Send status update back to UI thread
            if self.progress_callback:
                self.progress_callback({
                    "id": self.download_id,
                    "status": "Downloading",
                    "downloaded_bytes": downloaded,
                    "total_bytes": total,
                    "percent": percent,
                    "speed": speed,
                    "eta": eta
                })
        elif d['status'] == 'finished':
            if self.progress_callback:
                self.progress_callback({
                    "id": self.download_id,
                    "status": "Merging",
                    "percent": 99,
                    "speed": 0,
                    "eta": 0
                })

    def run(self):
        self.status = "Downloading"
        os.makedirs(self.temp_dir, exist_ok=True)

        # Output template puts the files inside the temporary subdirectory
        outtmpl = os.path.join(self.temp_dir, "%(title)s.%(ext)s")

        ydl_opts = {
            'format': self.get_ydl_format(),
            'outtmpl': outtmpl,
            'progress_hooks': [self.progress_hook],
            'ffmpeg_location': self.get_ffmpeg_path(),
            'quiet': True,
            'no_warnings': True,
            'force_ipv4': True,
            'socket_timeout': 10,
            # Speed Optimizations
            'concurrent_fragment_downloads': 16,
            'http_chunk_size': 10485760,  # 10M
            'buffer_size': 16384,          # 16K
            'retries': 10,
            'fragment_retries': 10,
            'nopart': True,
            'throttled_rate': 102400,      # 100K
        }

        # Handle postprocessors for Audio-Only mode
        if self.audio_only:
            codec = self.audio_format.lower()
            # If standard MP3/AAC/OPUS
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': codec,
                'preferredquality': '320', # Highest possible music quality
            }]
        elif self.format_choice in ["MP4", "MKV", "WEBM"]:
            # Set merge output format
            ydl_opts['merge_output_format'] = self.format_choice.lower()
            # Instant merge using -c copy
            ydl_opts['postprocessor_args'] = {
                'merger': ['-c', 'copy']
            }

        is_instagram = "instagram.com" in self.url or "instagr.am" in self.url
        try_browsers = [None]
        if is_instagram:
            try_browsers.extend(['chrome', 'edge', 'firefox', 'brave', 'opera'])

        first_exception = None
        last_exception = None

        for i, browser in enumerate(try_browsers):
            opts = ydl_opts.copy()
            if browser:
                opts['cookiesfrombrowser'] = (browser,)
            try:
                if self.cancel_event.is_set():
                    raise DownloadCancelledException("Download cancelled by user")

                with yt_dlp.YoutubeDL(opts) as ydl:
                    # First extract info to get the actual title for UI
                    info = ydl.extract_info(self.url, download=False)
                    self.title = info.get('title', 'Unknown Title')
                    
                    if self.progress_callback:
                        self.progress_callback({
                            "id": self.download_id,
                            "status": "Downloading",
                            "title": self.title,
                            "percent": 0
                        })
                    
                    # Run the actual download
                    ydl.download([self.url])
                first_exception = None
                last_exception = None
                break
            except Exception as e:
                if i == 0:
                    first_exception = e
                last_exception = e
                if not is_instagram or isinstance(e, DownloadCancelledException):
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

            # Once download completes successfully, find the merged/downloaded file in temp_dir
            temp_files = os.listdir(self.temp_dir)
            if not temp_files:
                raise Exception("Download completed but no file was found.")

            # Look for the target file in the temp dir (there should typically be only 1 final file)
            # Sometimes there are leftovers, let's pick the largest or the most logical one.
            temp_file_path = None
            for f in temp_files:
                full_p = os.path.join(self.temp_dir, f)
                # Ignore folder files or temp files if any
                if os.path.isfile(full_p):
                    temp_file_path = full_p
                    break

            if not temp_file_path:
                raise Exception("Could not locate the downloaded file.")

            # Sanitize final filename and resolve any naming conflict in the final save directory
            filename = os.path.basename(temp_file_path)
            name, ext = os.path.splitext(filename)
            sanitized_name = sanitize_filename(name)
            final_filename = f"{sanitized_name}{ext}"
            
            self.final_file_path = get_unique_path(self.save_path, final_filename)
            
            # Move from temp folder to final destination
            shutil.move(temp_file_path, self.final_file_path)
            self.status = "Completed"
            
            if self.progress_callback:
                self.progress_callback({
                    "id": self.download_id,
                    "status": "Completed",
                    "percent": 100,
                    "file_path": self.final_file_path
                })

        except DownloadCancelledException:
            self.status = "Cancelled"
            if self.progress_callback:
                self.progress_callback({
                    "id": self.download_id,
                    "status": "Cancelled"
                })
        except Exception as e:
            self.status = "Failed"
            self.error_message = str(e)
            if self.progress_callback:
                self.progress_callback({
                    "id": self.download_id,
                    "status": "Failed",
                    "error": self.error_message
                })
        finally:
            # Clean up the unique temporary folder
            if os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                except Exception as cleanup_err:
                    import logging
                    logging.warning(f"Error cleaning up temp directory {self.temp_dir}: {cleanup_err}")

    def cancel(self):
        self.cancel_event.set()
        self.status = "Cancelled"
