import os
import sys
import threading
import logging
from typing import Any, Optional
from PIL import Image
import pystray

try:
    import winreg
except ImportError:
    winreg = None

class TrayManager:
    """Manages the system tray icon and startup behavior for the application."""
    
    REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_REGISTRY_NAME = "YTDwonloder"
    TRAY_HOVER_TEXT = "YT DWONLODER"
    
    def __init__(self, app_instance: Any) -> None:
        self.app = app_instance
        self.tray_icon: Optional[pystray.Icon] = None

    def get_asset_path(self, relative_path: str) -> str:
        """Resolves the absolute path to an asset, handling PyInstaller environment."""
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, "assets", relative_path)

    def load_tray_icon_image(self) -> Image.Image:
        """Loads the tray icon image from the assets directory."""
        icon_path = self.get_asset_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                return Image.open(icon_path)
            except Exception as e:
                logging.error(f"Failed to load tray icon image from {icon_path}: {e}")
        else:
            logging.warning(f"Tray icon image not found at {icon_path}. Using fallback.")
            
        # Fallback to a simple colored square if the icon is missing
        return Image.new('RGBA', (64, 64), color=(59, 130, 246, 255))

    def get_startup_status(self) -> bool:
        """Checks if the application is set to start on Windows startup."""
        if winreg is None:
            return False
            
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, self.APP_REGISTRY_NAME)
                return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logging.error(f"Error reading startup registry key: {e}")
            return False

    def toggle_startup(self, enabled: bool) -> None:
        """Toggles the Windows startup registry key."""
        if winreg is None:
            logging.warning("winreg module not available; cannot toggle startup.")
            return
            
        # Get the path to run
        if getattr(sys, 'frozen', False):
            app_path = f'"{sys.executable}" --startup'
        else:
            app_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}" --startup'
            
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, self.APP_REGISTRY_NAME, 0, winreg.REG_SZ, app_path)
                else:
                    try:
                        winreg.DeleteValue(key, self.APP_REGISTRY_NAME)
                    except FileNotFoundError:
                        pass
        except Exception as e:
            logging.error(f"Error setting startup status: {e}")

    def start_tray_icon(self) -> None:
        """Initializes and runs the system tray icon in a background thread."""
        if self.tray_icon is not None:
            return
            
        image = self.load_tray_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Restore", self.restore_from_tray, default=True),
            pystray.MenuItem("Exit", self.exit_app)
        )
        self.tray_icon = pystray.Icon(self.APP_REGISTRY_NAME, image, self.TRAY_HOVER_TEXT, menu)
        
        # Run tray icon on a daemon thread so it doesn't block exit
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_to_tray(self) -> None:
        """Hides the main application window and shows the tray icon."""
        self.app.is_hidden_to_tray = True
        self.app.withdraw()
        self.start_tray_icon()

    def restore_from_tray(self, icon: Optional[pystray.Icon] = None, item: Optional[pystray.MenuItem] = None) -> None:
        """Restores the main application window from the tray."""
        self.app.is_hidden_to_tray = False
        self.app.after(0, self._restore_window)

    def _restore_window(self) -> None:
        """Internal method to restore the window on the main thread."""
        self.app.deiconify()
        self.app.lift()
        self.app.focus_force()
        self.app.attributes('-alpha', 1.0)

    def exit_app(self, icon: Optional[pystray.Icon] = None, item: Optional[pystray.MenuItem] = None) -> None:
        """Stops the tray icon and safely exits the application."""
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        self.app.after(0, self._destroy_app)

    def _destroy_app(self) -> None:
        """Internal method to destroy the application on the main thread."""
        self.app.destroy()
        sys.exit(0)
