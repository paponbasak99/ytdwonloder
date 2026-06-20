import os
import sys
import threading
import customtkinter
from tkinter import filedialog
from PIL import Image
import math
import pystray
try:
    import winreg
except ImportError:
    winreg = None

from core.fetcher import VideoFetcher
from core.queue_manager import DownloadQueueManager
from utils.config import AppConfig
from utils.helpers import sanitize_filename, format_size, format_time
from ui.components import QueueItemWidget, SpinnerCanvas, DashboardCard
from ui.animations import fade_in_image, shake_widget, animate_pulse_glow, animate_border_color, skeleton_pulse_loader, animate_gradient_flow, animate_window_fade_in

class PlaylistChoiceDialog(customtkinter.CTkToplevel):
    def __init__(self, master, playlist_title, count, **kwargs):
        super().__init__(master, fg_color="#0D1117", **kwargs)
        self.title("Playlist Detected")
        self.geometry("400x220")
        self.resizable(False, False)
        # Center logic
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - 200
        y = master.winfo_y() + (master.winfo_height() // 2) - 110
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()
        self.choice = None
        
        self.label = customtkinter.CTkLabel(self, text="🎬 Playlist Detected", font=("Segoe UI Variable Display", 18, "bold"), text_color="#3B82F6")
        self.label.pack(pady=(20, 5))
        
        disp_title = playlist_title if len(playlist_title) <= 40 else playlist_title[:38] + "..."
        self.sub_label = customtkinter.CTkLabel(self, text=f"Playlist: {disp_title}\nThis playlist contains {count} videos.\nDownload entire playlist or just this video?", font=("Segoe UI Variable Display", 12), justify="center", text_color="#94A3B8")
        self.sub_label.pack(pady=10)
        
        self.btn_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)
        self.playlist_btn = customtkinter.CTkButton(self.btn_frame, text="Download Playlist", fg_color="#3B82F6", hover_color="#2563EB", corner_radius=8, command=self.choose_playlist)
        self.playlist_btn.pack(side="left", padx=10)
        self.video_btn = customtkinter.CTkButton(self.btn_frame, text="Just This Video", fg_color="#1E293B", text_color="#FFFFFF", hover_color="#334155", corner_radius=8, command=self.choose_video)
        self.video_btn.pack(side="left", padx=10)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.wait_window()
        
    def choose_playlist(self): self.choice = "playlist"; self.destroy()
    def choose_video(self): self.choice = "video"; self.destroy()
    def on_close(self): self.choice = None; self.destroy()

class YTDownloaderApp(customtkinter.CTk):
    def __init__(self):
        super().__init__(fg_color="#0D1117")
        self.config = AppConfig()
        
        # Window Configuration
        self.title("PAPON YT DWONLODER SYSTEM")
        self.geometry("540x580")
        self.resizable(False, False)
        self.attributes('-alpha', 0.0) # Start transparent for fade-in
        
        # Lock theme to Dark
        customtkinter.set_appearance_mode("Dark")
        
        # App State
        self.fetcher = VideoFetcher()
        self.queue_manager = DownloadQueueManager(max_concurrent=3, progress_callback=self.handle_queue_progress)
        self.fetched_metadata = None
        self.last_clipboard_url = ""
        self.is_fetching = False
        self._auto_fetch_timer = None
        
        # Tray and Startup State
        self.tray_icon = None
        self.is_hidden_to_tray = False
        
        self.setup_ui()
        self.bind("<FocusIn>", self.check_clipboard)
        self.load_settings_to_ui()
        
        # Start animations
        animate_window_fade_in(self, target_alpha=1.0, duration_ms=600, steps=30)
        
        # Start button flow background logic
        self.start_button_gradient_flow()
        
        # Protocol handling
        self.protocol("WM_DELETE_WINDOW", self.exit_app)
        
    def setup_ui(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        # Main Content Area
        self.main_frame = customtkinter.CTkFrame(self, fg_color="#0D1117", corner_radius=0)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(5, weight=1) # Queue expands
        
        # URL Input Row
        self.url_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.url_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.url_frame.columnconfigure(0, weight=1)
        
        self.url_var = customtkinter.StringVar()
        self.url_var.trace_add("write", self.on_url_changed)
        self.url_entry = customtkinter.CTkEntry(self.url_frame, textvariable=self.url_var, placeholder_text="Paste YouTube or Instagram URL here...", height=40, font=("Segoe UI Variable Display", 13), border_width=1, corner_radius=12, border_color="#1E293B", fg_color="#161B22", text_color="#FFFFFF")
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 0))
        self.url_entry.bind("<FocusIn>", lambda e: animate_border_color(self.url_entry, "#1E293B", "#3B82F6"))
        self.url_entry.bind("<FocusOut>", lambda e: animate_border_color(self.url_entry, "#3B82F6", "#1E293B"))
        
        self.spinner = SpinnerCanvas(self.url_frame, size=20, color="#3B82F6", bg_color="#161B22")
        
        # Preview Card
        self.preview_frame = customtkinter.CTkFrame(self.main_frame, fg_color="#161B22", corner_radius=16, border_width=1, border_color="#1E293B")
        self.preview_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.preview_frame.columnconfigure(1, weight=1)
        
        self.thumb_label = customtkinter.CTkLabel(self.preview_frame, text="No Preview", width=140, height=90, fg_color="#0D1117", corner_radius=10, font=("Segoe UI Variable Display", 11))
        self.thumb_label.grid(row=0, column=0, padx=15, pady=15)
        
        self.details_frame = customtkinter.CTkFrame(self.preview_frame, fg_color="transparent")
        self.details_frame.grid(row=0, column=1, sticky="nsew", pady=15, padx=(0, 15))
        
        self.prev_title = customtkinter.CTkLabel(self.details_frame, text="Awaiting Input...", font=("Segoe UI Variable Display", 15, "bold"), text_color="#FFFFFF", anchor="w", justify="left")
        self.prev_title.pack(anchor="w", pady=(0, 3))
        self.prev_channel = customtkinter.CTkLabel(self.details_frame, text="Channel: --", font=("Segoe UI Variable Display", 12), text_color="#94A3B8", anchor="w")
        self.prev_channel.pack(anchor="w", pady=1)
        self.prev_duration = customtkinter.CTkLabel(self.details_frame, text="Duration: --", font=("Segoe UI Variable Display", 12), text_color="#94A3B8", anchor="w")
        self.prev_duration.pack(anchor="w", pady=1)
        
        # Settings Row
        self.settings_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.settings_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        
        self.fmt_dropdown = customtkinter.CTkOptionMenu(self.settings_frame, values=["MP4", "MKV", "WEBM"], width=90, height=32, font=("Segoe UI Variable Display", 12), fg_color="#161B22", button_color="#1E293B", corner_radius=8, command=self.on_format_change)
        self.fmt_dropdown.pack(side="left", padx=(0, 8))
        
        self.qty_dropdown = customtkinter.CTkOptionMenu(self.settings_frame, values=["Best", "4K", "1440p", "1080p", "720p", "480p", "360p"], width=90, height=32, font=("Segoe UI Variable Display", 12), fg_color="#161B22", button_color="#1E293B", corner_radius=8, command=self.on_quality_change)
        self.qty_dropdown.pack(side="left", padx=8)
        
        self.aud_dropdown = customtkinter.CTkOptionMenu(self.settings_frame, values=["MP3", "AAC", "OPUS"], width=90, height=32, font=("Segoe UI Variable Display", 12), fg_color="#161B22", button_color="#1E293B", corner_radius=8, command=self.on_audio_format_change)
        
        self.audio_only_var = customtkinter.BooleanVar(value=False)
        self.audio_only_check = customtkinter.CTkCheckBox(self.settings_frame, text="Audio Only", variable=self.audio_only_var, font=("Segoe UI Variable Display", 12), text_color="#FFFFFF", border_color="#3B82F6", command=self.toggle_audio_only)
        self.audio_only_check.pack(side="left", padx=12)
        
        self.save_entry = customtkinter.CTkEntry(self.settings_frame, height=32, width=160, font=("Segoe UI Variable Display", 11), border_width=1, border_color="#1E293B", fg_color="#161B22")
        self.save_entry.pack(side="left", padx=(8, 4), fill="x", expand=True)
        self.save_btn = customtkinter.CTkButton(self.settings_frame, text="📁", width=32, height=32, fg_color="#161B22", hover_color="#1E293B", corner_radius=8, command=self.browse_folder)
        self.save_btn.pack(side="left", padx=(0, 0))
        
        # Utilities Row (Startup and Minimize to Tray)
        self.utils_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.utils_frame.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        self.utils_frame.columnconfigure(0, weight=1)
        self.utils_frame.columnconfigure(1, weight=1)

        self.startup_var = customtkinter.BooleanVar(value=self.get_startup_status())
        self.startup_check = customtkinter.CTkCheckBox(
            self.utils_frame, 
            text="Start on Windows Startup", 
            variable=self.startup_var, 
            font=("Segoe UI Variable Display", 12), 
            text_color="#FFFFFF", 
            border_color="#3B82F6", 
            command=self.toggle_startup
        )
        self.startup_check.grid(row=0, column=0, sticky="w")

        self.tray_btn = customtkinter.CTkButton(
            self.utils_frame, 
            text="Hide to System Tray", 
            width=150, 
            height=32, 
            font=("Segoe UI Variable Display", 12), 
            fg_color="#1E293B", 
            text_color="#FFFFFF", 
            hover_color="#334155", 
            corner_radius=8, 
            command=self.hide_to_tray
        )
        self.tray_btn.grid(row=0, column=1, sticky="e")

        # CTA Download Button
        self.dl_btn = customtkinter.CTkButton(self.main_frame, text="DOWNLOAD NOW", height=48, corner_radius=12, font=("Segoe UI Variable Display", 15, "bold"), fg_color="#06B6D4", text_color="#FFFFFF", hover_color="#0891B2", command=self.download_action)
        self.dl_btn.grid(row=4, column=0, sticky="ew", pady=(0, 20))
        
        # Start animated gradient flow on button flag
        self.dl_gradient_colors = ["#06B6D4", "#3B82F6", "#6366F1", "#3B82F6"]
        self.dl_btn_is_hovered = False
        self.dl_btn.bind("<Enter>", lambda e: self.set_btn_hover(True))
        self.dl_btn.bind("<Leave>", lambda e: self.set_btn_hover(False))
        
        # Queue Label & Scroll
        q_header = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        q_header.grid(row=5, column=0, sticky="nsew")
        q_header.columnconfigure(0, weight=1)
        q_header.rowconfigure(1, weight=1)
        
        self.queue_label = customtkinter.CTkLabel(q_header, text="Download Queue", font=("Segoe UI Variable Display", 14, "bold"), text_color="#FFFFFF")
        self.queue_label.grid(row=0, column=0, sticky="w", pady=(0, 8))
        
        self.queue_scroll = customtkinter.CTkScrollableFrame(q_header, fg_color="transparent")
        self.queue_scroll.grid(row=1, column=0, sticky="nsew")
        
        self.queue_widgets = {}

    def set_btn_hover(self, state):
        self.dl_btn_is_hovered = state
        if not state:
            # Revert to base cyan color
            self.dl_btn.configure(fg_color="#06B6D4")

    def start_button_gradient_flow(self):
        animate_gradient_flow(self.dl_btn, self.dl_gradient_colors, lambda: self.dl_btn_is_hovered)

    def on_url_changed(self, *args):
        if hasattr(self, "_auto_fetch_timer") and self._auto_fetch_timer:
            self.after_cancel(self._auto_fetch_timer)
            self._auto_fetch_timer = None

        url = self.url_var.get().strip()
        if url and ("youtube.com" in url or "youtu.be" in url or "instagram.com" in url or "instagr.am" in url):
            self._auto_fetch_timer = self.after(150, self.auto_fetch_action)

    def auto_fetch_action(self):
        url = self.url_entry.get().strip()
        if self.fetched_metadata and self.fetched_metadata.get("url") == url:
            return
        if self.is_fetching:
            return
        self.fetch_info_action()

    def check_clipboard(self, event):
        try:
            clip = self.clipboard_get().strip()
            if clip and ("youtube.com" in clip or "youtu.be" in clip or "instagram.com" in clip or "instagr.am" in clip):
                if clip != self.last_clipboard_url:
                    current_val = self.url_entry.get().strip()
                    if not current_val:
                        self.url_entry.delete(0, "end")
                        self.url_entry.insert(0, clip)
                        self.last_clipboard_url = clip
                        self.url_entry.focus_set()
                        animate_border_color(self.url_entry, "#1E293B", "#10B981")
                        self.after(500, lambda: animate_border_color(self.url_entry, "#10B981", "#3B82F6"))
        except Exception:
            pass

    def load_settings_to_ui(self):
        save_path = self.config.get("save_path")
        self.save_entry.insert(0, save_path)
        fmt = self.config.get("format")
        if fmt in ["MP4", "MKV", "WEBM"]: self.fmt_dropdown.set(fmt)
        qty = self.config.get("quality")
        self.qty_dropdown.set(qty)
        audio_only = self.config.get("audio_only")
        self.audio_only_var.set(audio_only)
        self.toggle_audio_only()
        audio_fmt = self.config.get("audio_format")
        self.aud_dropdown.set(audio_fmt)

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.save_entry.get())
        if folder:
            self.save_entry.delete(0, "end")
            self.save_entry.insert(0, folder)
            self.config.set("save_path", folder)

    def on_format_change(self, value): self.config.set("format", value)
    def on_quality_change(self, value): self.config.set("quality", value)
    def on_audio_format_change(self, value): self.config.set("audio_format", value)
    def toggle_audio_only(self):
        audio_only = self.audio_only_var.get()
        self.config.set("audio_only", audio_only)
        if audio_only:
            self.fmt_dropdown.pack_forget()
            self.aud_dropdown.pack(side="left", padx=(0, 10), before=self.qty_dropdown)
            self.qty_dropdown.configure(state="disabled")
        else:
            self.aud_dropdown.pack_forget()
            self.fmt_dropdown.pack(side="left", padx=(0, 10), before=self.qty_dropdown)
            self.qty_dropdown.configure(state="normal")

    def fetch_info_action(self):
        url = self.url_entry.get().strip()
        if not url:
            shake_widget(self.url_entry)
            return

        self.spinner.place(in_=self.url_entry, relx=0.96, rely=0.5, anchor="center")
        self.spinner.start_spinning()
        self.is_fetching = True
        
        # Start skeleton loader on thumb
        skeleton_pulse_loader(self.thumb_label, "#0D1117", "#1E293B", lambda: self.is_fetching)
        self.thumb_label.configure(text="")

        def run_fetch():
            res = self.fetcher.fetch_metadata(url)
            self.after(0, self.on_fetch_complete, res)
        threading.Thread(target=run_fetch, daemon=True).start()

    def on_fetch_complete(self, result):
        self.spinner.stop_spinning()
        self.spinner.place_forget()

        if not result or result.get("status") == "error":
            self.is_fetching = False
            shake_widget(self.url_entry)
            self.prev_title.configure(text="Error Fetching", text_color="#EF4444")
            err_msg = result.get("message", "Unknown error") if result else "Metadata fetch returned empty results."
            self.prev_channel.configure(text=err_msg, text_color="#EF4444")
            self.thumb_label.configure(text="Failed", fg_color="#0D1117", image=None)
            return

        self.fetched_metadata = result
        self.prev_title.configure(text_color="#FFFFFF")
        self.prev_channel.configure(text_color="#94A3B8")
        
        title = result.get("title")
        disp_title = title if len(title) <= 50 else title[:47] + "..."
        self.prev_title.configure(text=disp_title)
        self.prev_channel.configure(text=f"Channel: {result.get('uploader')}")
        
        if result.get("type") == "playlist":
            self.is_fetching = False
            self.prev_duration.configure(text=f"Playlist ({result.get('entries_count', 0)} videos)")
            self.thumb_label.configure(text="🎬 Playlist", fg_color="#0D1117", image=None)
        else:
            self.prev_duration.configure(text=f"Duration: {format_time(result.get('duration'))}")
            
            thumbnail_url = result.get("thumbnail_url")
            if thumbnail_url:
                def run_thumb():
                    pil_img = self.fetcher.fetch_thumbnail_image(thumbnail_url)
                    if pil_img: self.after(0, self.on_thumbnail_ready, pil_img)
                    else: self.after(0, self.on_thumbnail_failed)
                threading.Thread(target=run_thumb, daemon=True).start()
            else:
                self.is_fetching = False
                self.thumb_label.configure(text="No Preview", fg_color="#0D1117", image=None)

    def on_thumbnail_ready(self, pil_image):
        self.is_fetching = False
        fade_in_image(self.thumb_label, pil_image, "#0D1117", size=(140, 90))

    def on_thumbnail_failed(self):
        self.is_fetching = False
        self.thumb_label.configure(text="No Preview", fg_color="#0D1117", image=None)

    def download_action(self):
        url = self.url_entry.get().strip()
        save_path = self.save_entry.get().strip()
        
        if not url:
            shake_widget(self.url_entry)
            return
        if not os.path.exists(save_path):
            shake_widget(self.save_entry)
            return

        audio_only = self.audio_only_var.get()
        format_choice = self.aud_dropdown.get() if audio_only else self.fmt_dropdown.get()
        quality_choice = self.qty_dropdown.get()
        
        if self.fetched_metadata and self.fetched_metadata.get("url") == url:
            self._handle_metadata_download(self.fetched_metadata, save_path, format_choice, quality_choice, audio_only)
        else:
            self.dl_btn.configure(state="disabled", text="Initializing...")
            def run_quick_fetch():
                res = self.fetcher.fetch_metadata(url)
                self.after(0, self._on_quick_fetch_complete, res, save_path, format_choice, quality_choice, audio_only)
            threading.Thread(target=run_quick_fetch, daemon=True).start()

    def _on_quick_fetch_complete(self, res, save_path, format_choice, quality_choice, audio_only):
        self.dl_btn.configure(state="normal", text="DOWNLOAD NOW")
        if res.get("status") == "error":
            self.add_single_video_to_queue(self.url_entry.get().strip(), save_path, format_choice, quality_choice, audio_only)
        else:
            self.fetched_metadata = res
            self._handle_metadata_download(res, save_path, format_choice, quality_choice, audio_only)

    def _handle_metadata_download(self, metadata, save_path, format_choice, quality_choice, audio_only):
        if metadata.get("type") == "playlist":
            entries = metadata.get("entries", [])
            playlist_title = metadata.get("title", "Playlist")
            count = len(entries)
            if not entries:
                shake_widget(self.url_entry)
                return
            url = self.url_entry.get().strip()
            
            # Always ask if they want to download the whole playlist if it's a playlist URL
            # or if it's a video within a playlist. If it's pure playlist, we still ask
            # to confirm because they might just want to back out or know what's happening.
            if "watch?" in url and "list=" in url:
                dialog = PlaylistChoiceDialog(self, playlist_title, count)
                if dialog.choice == "playlist":
                    self.queue_playlist(entries, save_path, format_choice, quality_choice, audio_only, playlist_title)
                elif dialog.choice == "video":
                    self.add_single_video_to_queue(url, save_path, format_choice, quality_choice, audio_only)
            else:
                dialog = PlaylistChoiceDialog(self, playlist_title, count)
                if dialog.choice == "playlist":
                    self.queue_playlist(entries, save_path, format_choice, quality_choice, audio_only, playlist_title)
                # If they pasted a pure playlist link, there is no "Just this video", but the UI will still show the option.
                # It will just download the first video if they click it, or we could customize the dialog.
                # Actually, if they chose "video" on a pure playlist, we can just download the first entry.
                elif dialog.choice == "video":
                    first_video = entries[0].get("url")
                    if first_video:
                        self.add_single_video_to_queue(first_video, save_path, format_choice, quality_choice, audio_only)
        else:
            self.add_single_video_to_queue(metadata.get("url"), save_path, format_choice, quality_choice, audio_only)

    def queue_playlist(self, entries, save_path, format_choice, quality_choice, audio_only, playlist_title=None):
        if playlist_title:
            # Create a dedicated folder for the playlist
            safe_title = sanitize_filename(playlist_title)
            if not safe_title:
                safe_title = "Playlist"
            save_path = os.path.join(save_path, safe_title)
            os.makedirs(save_path, exist_ok=True)
            
        for item in entries:
            video_url = item.get("url")
            video_title = item.get("title", "Initializing...")
            if video_url:
                dl = self.queue_manager.add_task(url=video_url, save_path=save_path, format_choice=format_choice if not audio_only else "MP4", quality_choice=quality_choice, audio_only=audio_only, audio_format=format_choice if audio_only else "MP3")
                dl.title = video_title
                self.create_queue_widget_item(dl.download_id, video_title, video_url)

    def add_single_video_to_queue(self, url, save_path, format_choice, quality_choice, audio_only):
        dl = self.queue_manager.add_task(url=url, save_path=save_path, format_choice=format_choice if not audio_only else "MP4", quality_choice=quality_choice, audio_only=audio_only, audio_format=format_choice if audio_only else "MP3")
        title = self.fetched_metadata.get("title") if (self.fetched_metadata and self.fetched_metadata.get("url") == url) else "Initializing..."
        dl.title = title
        self.create_queue_widget_item(dl.download_id, title, url)

    def create_queue_widget_item(self, download_id, title, url):
        item_widget = QueueItemWidget(self.queue_scroll, self.queue_manager, download_id, title, url)
        item_widget.pack(fill="x", pady=5, padx=5)
        self.queue_widgets[download_id] = item_widget

    def handle_queue_progress(self, data):
        download_id = data.get("id")
        if download_id in self.queue_widgets:
            widget = self.queue_widgets[download_id]
            widget.update_progress(data)

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
            print(f"Error loading tray icon image: {e}")
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

    def toggle_startup(self):
        if winreg is None:
            return
        enabled = self.startup_var.get()
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
                print("App added to startup.")
            else:
                try:
                    winreg.DeleteValue(key, val_name)
                    print("App removed from startup.")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Error setting startup: {e}")

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
        self.is_hidden_to_tray = True
        self.withdraw()
        self.start_tray_icon()

    def restore_from_tray(self, icon=None, item=None):
        self.is_hidden_to_tray = False
        self.after(0, self._restore_window)

    def _restore_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self.attributes('-alpha', 1.0)

    def exit_app(self, icon=None, item=None):
        if self.tray_icon is not None:
            self.tray_icon.stop()
        self.after(0, self._destroy_app)

    def _destroy_app(self):
        self.destroy()
        sys.exit(0)
