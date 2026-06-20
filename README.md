# YT Downloader

A graphical YouTube and Instagram downloader built in Python with `customtkinter` and `yt-dlp`.

## Features
- Clean and modern dark-mode GUI.
- Download single videos or entire playlists.
- Format selection (MP4, MKV, WEBM) and quality selection up to 4K.
- Audio-only downloads (MP3, AAC, OPUS).
- Thumbnail previews.
- Queue manager for concurrent downloads.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/paponbasak99/ytdwonloder.git
   cd ytdwonloder
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Download FFmpeg (Required for media processing):
   ```bash
   python scripts/fetch_ffmpeg.py
   ```
   *Note: This script will download a static Windows build of FFmpeg and place it in the `assets/` directory.*

## Usage

Run the main application:
```bash
python main.py
```

Paste a supported link into the URL bar, wait for the metadata to fetch, select your format and quality, and click **Download Now**.

![Usage Screenshot Placeholder](placeholder.png)

## Disclaimer

This application is intended strictly for personal use and for downloading content you have the right to access. Please respect the copyright of content creators. Do not use this tool to redistribute copyrighted material without permission.
