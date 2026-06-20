import os
import sys
import urllib.request
import zipfile
import tempfile
import shutil
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def fetch_ffmpeg():
    # URL for a static Windows build of FFmpeg
    FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    
    # Determine assets directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    ffmpeg_exe_path = os.path.join(assets_dir, "ffmpeg.exe")
    
    if os.path.exists(ffmpeg_exe_path):
        logging.info(f"ffmpeg.exe already exists at {ffmpeg_exe_path}")
        return

    logging.info("Downloading FFmpeg... This may take a few minutes.")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, "ffmpeg.zip")
        
        try:
            # Download the zip file
            urllib.request.urlretrieve(FFMPEG_URL, zip_path)
            logging.info("Download complete. Extracting...")
            
            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Find ffmpeg.exe inside the zip
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith("ffmpeg.exe"):
                        # Extract this file specifically
                        source = zip_ref.open(file_info)
                        with open(ffmpeg_exe_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                        logging.info(f"Successfully extracted ffmpeg.exe to {ffmpeg_exe_path}")
                        break
        except Exception as e:
            logging.error(f"Failed to fetch FFmpeg: {e}")
            sys.exit(1)

if __name__ == "__main__":
    fetch_ffmpeg()
