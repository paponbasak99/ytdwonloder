import os
import sys
import json
import threading
import subprocess
import urllib.request
import tkinter.messagebox as msgbox
import yt_dlp
import customtkinter

# Adjust sys.path to find packages
if getattr(sys, 'frozen', False):
    # In PyInstaller bundle, modules are extracted to sys._MEIPASS
    sys.path.append(sys._MEIPASS)
else:
    # In normal environment, use the script directory
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.app import YTDownloaderApp
from utils.config import AppConfig

def perform_pip_update(current_version, latest_version):
    """
    Runs pip upgrade in a background thread and alerts the user upon completion.
    """
    try:
        # Run pip upgrade command
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            startupinfo=startupinfo
        )
        msgbox.showinfo(
            "Update Complete",
            f"Downloader core successfully updated from {current_version} to {latest_version}!\n"
            "Please restart the application for changes to take effect."
        )
    except Exception as e:
        msgbox.showerror(
            "Update Failed",
            f"An error occurred while updating the download core: {e}"
        )

def prompt_update(app_window, current_version, latest_version):
    """
    Prompts the user to update the yt-dlp core.
    """
    is_frozen = getattr(sys, 'frozen', False)
    
    if is_frozen:
        # If running as packaged EXE, we cannot pip install to update.
        # Do not show any popup.
        return
    else:
        # If running in python environment, offer silent pip upgrade
        answer = msgbox.askyesno(
            "Update Available",
            f"A newer version of the download core (yt-dlp) is available: {latest_version} (Current: {current_version}).\n\n"
            "Would you like to update it silently in the background?"
        )
        if answer:
            threading.Thread(
                target=perform_pip_update, 
                args=(current_version, latest_version), 
                daemon=True
            ).start()

def check_updates_thread(app_window):
    """
    Checks PyPI for newer versions of yt-dlp.
    """
    current_version = yt_dlp.version.__version__
    try:
        req = urllib.request.Request(
            "https://pypi.org/pypi/yt-dlp/json",
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            latest_version = data.get('info', {}).get('version')
            
            if latest_version and latest_version != current_version:
                # Alert UI thread
                app_window.after(1000, lambda: prompt_update(app_window, current_version, latest_version))
    except Exception as e:
        print(f"Update check failed: {e}")

def main():
    config = AppConfig()
    is_startup = "--startup" in sys.argv
    # Initialize main App
    app = YTDownloaderApp()
    
    if is_startup:
        # Hide the main window and initialize system tray icon immediately
        app.withdraw()
        app.tray_manager.start_tray_icon()
    
    # Run update checker in the background
    threading.Thread(target=check_updates_thread, args=(app,), daemon=True).start()
    
    # Run CustomTkinter main loop
    app.mainloop()

if __name__ == "__main__":
    main()
