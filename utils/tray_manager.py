import os
import sys
import threading
from PIL import Image
import pystray

try:
    import winreg
except ImportError:
    winreg = None

class TrayManager:
    def __init__(self, app_instance):
        self.app = app_instance
        self.tray_icon = None

    def get_asset_path(self, relative_path):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, "assets", relative_path)

    def load_tray_icon_image(self):
        try:
            icon_path = self.get_asset_path("icon.ico")
            if os.path.exists(icon_path):
                return Image.open(icon_path)
        except Exception as e:
            import logging
            logging.warning(f"Error loading tray icon image: {e}")
        return Image.new('RGBA', (64, 64), color=(59, 130, 246, 255))

    def get_startup_status(self):
        if winreg is None:
            return False
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        val_name = "PaponYTDwonloderSystem"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, val_name)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def toggle_startup(self, enabled):
        if winreg is None:
            return
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        val_name = "PaponYTDwonloderSystem"
        
        # Get the path to run
        if getattr(sys, 'frozen', False):
            app_path = f'"{sys.executable}" --startup'
        else:
            app_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}" --startup'
            
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                winreg.SetValueEx(key, val_name, 0, winreg.REG_SZ, app_path)
            else:
                try:
                    winreg.DeleteValue(key, val_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            import logging
            logging.warning(f"Error setting startup: {e}")

    def start_tray_icon(self):
        if self.tray_icon is not None:
            return
        
        image = self.load_tray_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Restore", self.restore_from_tray, default=True),
            pystray.MenuItem("Exit", self.exit_app)
        )
        self.tray_icon = pystray.Icon("PaponYTDwonloderSystem", image, "PAPON YT DWONLODER SYSTEM", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_to_tray(self):
        self.app.is_hidden_to_tray = True
        self.app.withdraw()
        self.start_tray_icon()

    def restore_from_tray(self, icon=None, item=None):
        self.app.is_hidden_to_tray = False
        self.app.after(0, self._restore_window)

    def _restore_window(self):
        self.app.deiconify()
        self.app.lift()
        self.app.focus_force()
        self.app.attributes('-alpha', 1.0)

    def exit_app(self, icon=None, item=None):
        if self.tray_icon is not None:
            self.tray_icon.stop()
        self.app.after(0, self._destroy_app)

    def _destroy_app(self):
        self.app.destroy()
        sys.exit(0)
