import os
import json

class AppConfig:
    DEFAULT_CONFIG = {
        "save_path": "",
        "format": "MP4",
        "quality": "Best",
        "theme": "Dark",
        "audio_only": False,
        "audio_format": "MP3"
    }

    def __init__(self):
        self.app_data_dir = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "YTDownloader")
        os.makedirs(self.app_data_dir, exist_ok=True)
        self.config_file = os.path.join(self.app_data_dir, "config.json")
        self.settings = self.DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        # Set default save_path to user's Downloads folder
        default_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        self.settings["save_path"] = default_downloads

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    loaded = json.load(f)
                    for key in self.DEFAULT_CONFIG:
                        if key in loaded:
                            self.settings[key] = loaded[key]
            except Exception as e:
                print(f"Error loading config: {e}")
                # Keep defaults on error

    def save(self):
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key):
        return self.settings.get(key, self.DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        if key in self.settings:
            self.settings[key] = value
            self.save()
