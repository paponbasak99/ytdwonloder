import os
import customtkinter
from PIL import Image
from utils.helpers import format_size, format_time
from ui.animations import fade_in_image, shake_widget, animate_progress_smoothly, interpolate_color

class SpinnerCanvas(customtkinter.CTkCanvas):
    """
    Custom canvas that draws and animates a rotating loading spinner.
    """
    def __init__(self, master, size=24, color="#3B82F6", bg_color=None, **kwargs):
        # Determine background color based on CustomTkinter appearance
        if bg_color is None:
            bg_color = master.cget("fg_color")
            if isinstance(bg_color, list):  # CTk colors can be list/tuple
                bg_color = bg_color[1] if customtkinter.get_appearance_mode() == "Dark" else bg_color[0]
            if bg_color == "transparent" or bg_color is None:
                bg_color = "#1E293B" if customtkinter.get_appearance_mode() == "Dark" else "#F1F5F9"

        super().__init__(master, width=size, height=size, bg=bg_color, highlightthickness=0, **kwargs)
        self.size = size
        self.color = color
        self.angle = 0
        self.spinning = False
        self.arc_id = None

    def start_spinning(self):
        if self.spinning:
            return
        self.spinning = True
        self.draw_spinner()

    def stop_spinning(self):
        self.spinning = False
        self.delete("all")
        self.arc_id = None

    def draw_spinner(self):
        if not self.spinning:
            return
        self.delete("all")
        # Draw a thick rotating arc
        padding = 4
        self.arc_id = self.create_arc(
            padding, padding, self.size - padding, self.size - padding,
            start=self.angle, extent=90, outline=self.color, width=3, style="arc"
        )
        self.angle = (self.angle + 12) % 360
        self.after(30, self.draw_spinner)


class QueueItemWidget(customtkinter.CTkFrame):
    """
    Represents an item in the download queue.
    Includes custom animations, progress bar, stats labels, and controls.
    """
    def __init__(self, master, manager, download_id, title, url, **kwargs):
        # Dark theme color for standard frame: #161B22 (Secondary panel)
        self.bg_color = "#161B22"
        super().__init__(master, height=80, fg_color=self.bg_color, corner_radius=12, border_width=1, border_color="#1E293B", **kwargs)
        
        self.manager = manager
        self.download_id = download_id
        self.title_str = title
        self.url = url
        
        self.pack_propagate(False) # Maintain exact height
        
        # Set up clipping container for slide-in animation
        self.inner_content = customtkinter.CTkFrame(self, fg_color="transparent", corner_radius=8)
        self.inner_content.place(x=520, y=0, relwidth=1.0, relheight=1.0)
        
        # Configure layout grids inside inner content
        self.inner_content.columnconfigure(0, weight=1)
        self.inner_content.columnconfigure(1, weight=0)
        
        # Left side: Title, Progress, Info
        self.left_frame = customtkinter.CTkFrame(self.inner_content, fg_color="transparent")
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=10)
        self.left_frame.columnconfigure(0, weight=1)
        
        # 1. Title Label
        self.title_label = customtkinter.CTkLabel(
            self.left_frame, text=self.title_str, font=("Segoe UI Variable Display", 13, "bold"),
            anchor="w", justify="left", text_color="#FFFFFF"
        )
        self.title_label.grid(row=0, column=0, sticky="ew")
        
        # 2. Progress Bar
        self.progress_bar = customtkinter.CTkProgressBar(
            self.left_frame, height=8, progress_color="#3B82F6", fg_color=["#E2E8F0", "#334155"]
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(8, 4))
        
        # 3. Stats label (ETA, Speed, Size)
        self.stats_label = customtkinter.CTkLabel(
            self.left_frame, text="Initializing...", font=("Segoe UI", 11),
            text_color=["#64748B", "#94A3B8"], anchor="w"
        )
        self.stats_label.grid(row=2, column=0, sticky="ew")
        
        # Right side: Control buttons
        self.controls_frame = customtkinter.CTkFrame(self.inner_content, fg_color="transparent")
        self.controls_frame.grid(row=0, column=1, sticky="ns", padx=(0, 15), pady=10)
        
        # Pause/Resume Button
        self.pause_btn = customtkinter.CTkButton(
            self.controls_frame, text="⏸", width=32, height=32, fg_color="#1E293B",
            text_color="#FFFFFF", hover_color="#334155", font=("Segoe UI Variable Display", 12), corner_radius=8,
            command=self.toggle_pause
        )
        self.pause_btn.pack(side="left", padx=4)
        
        # Cancel/Remove Button
        self.cancel_btn = customtkinter.CTkButton(
            self.controls_frame, text="✖", width=32, height=32, fg_color="#7F1D1D",
            text_color="#FCA5A5", hover_color="#991B1B", font=("Segoe UI Variable Display", 12), corner_radius=8,
            command=self.cancel_download
        )
        self.cancel_btn.pack(side="left", padx=4)
        
        self.status = "Pending"
        self.target_percent = 0.0
        
        # Start the slide-in animation
        self.animate_slide_in(520, 0, duration_ms=250, steps=15)

    def animate_slide_in(self, start_x, target_x, duration_ms=250, steps=15, step=0):
        if step > steps:
            self.inner_content.place(x=target_x, y=0, relwidth=1.0, relheight=1.0)
            return
            
        t = step / steps
        # Easing out quadratic
        ease_t = t * (2 - t)
        curr_x = start_x + (target_x - start_x) * ease_t
        self.inner_content.place(x=curr_x, y=0, relwidth=1.0, relheight=1.0)
        
        delay = int(duration_ms / steps)
        self.after(delay, lambda: self.animate_slide_in(start_x, target_x, duration_ms, steps, step + 1))

    def update_progress(self, data):
        """
        Updates the widget details thread-safely via root.after.
        """
        # Ensure we schedule UI updates on main thread
        self.after(0, self._process_update, data)

    def _process_update(self, data):
        status = data.get("status")
        self.status = status
        
        # Update title if retrieved
        if "title" in data and data["title"]:
            self.title_str = data["title"]
            # Truncate title if too long
            disp_title = self.title_str
            if len(disp_title) > 42:
                disp_title = disp_title[:40] + "..."
            self.title_label.configure(text=disp_title)

        if status == "Downloading":
            percent = data.get("percent", 0.0)
            speed = data.get("speed", 0)
            eta = data.get("eta", 0)
            downloaded = data.get("downloaded_bytes", 0)
            total = data.get("total_bytes", 0)

            # Animate the progress bar smoothly
            self.target_percent = percent / 100.0
            animate_progress_smoothly(self.progress_bar, self.target_percent)
            
            # Format display strings
            speed_str = format_size(speed) + "/s"
            size_str = format_size(downloaded) + " of " + format_size(total)
            eta_str = format_time(eta) + " left"
            
            self.stats_label.configure(
                text=f"{speed_str} · {percent:.1f}% · {size_str} · {eta_str}",
                text_color=["#475569", "#94A3B8"]
            )
            self.pause_btn.configure(text="⏸", state="normal")
            
        elif status == "Merging":
            animate_progress_smoothly(self.progress_bar, 0.99)
            self.stats_label.configure(text="Processing and merging audio/video streams...", text_color="#3B82F6")
            self.pause_btn.configure(state="disabled")
            
        elif status == "Completed":
            animate_progress_smoothly(self.progress_bar, 1.0)
            self.progress_bar.configure(progress_color="#10B981") # Green progress bar at 100%
            self.stats_label.configure(text="✅ Completed successfully!", text_color="#10B981")
            self.pause_btn.pack_forget()
            
            # Change cancel icon to "open folder" icon, or simply remove buttons
            self.cancel_btn.configure(
                text="📁", fg_color="#065F46",
                text_color="#D1FAE5", hover_color="#047857",
                command=self.open_folder
            )
            # Flash background green
            self.flash_green()
            
        elif status == "Paused":
            self.stats_label.configure(text="⏸ Paused", text_color="#EAB308")
            self.pause_btn.configure(text="▶", fg_color=["#FEF08A", "#854D0E"], 
                                     text_color=["#854D0E", "#FEF08A"], state="normal")
            
        elif status == "Failed":
            self.progress_bar.configure(progress_color="#EF4444")
            err = data.get("error", "Unknown error occurred.")
            if len(err) > 50:
                err = err[:47] + "..."
            self.stats_label.configure(text=f"❌ Error: {err}", text_color="#EF4444")
            self.pause_btn.pack_forget()
            self.cancel_btn.configure(text="🗑")
            shake_widget(self)
            
        elif status == "Cancelled":
            self.progress_bar.configure(progress_color="#64748B")
            self.stats_label.configure(text="Cancelled", text_color="#64748B")
            self.pause_btn.pack_forget()
            self.cancel_btn.configure(text="🗑")

    def toggle_pause(self):
        if self.status == "Paused":
            self.manager.resume_task(self.download_id)
        else:
            self.manager.pause_task(self.download_id)

    def cancel_download(self):
        if self.status in ["Completed", "Failed", "Cancelled"]:
            # If completed/failed, the cancel button acts as trash (removal)
            self.manager.remove_task(self.download_id)
            self.destroy()
        else:
            self.manager.cancel_task(self.download_id)

    def open_folder(self):
        # Get final file path from task
        for t in self.manager.tasks:
            if t.download_id == self.download_id:
                if t.final_file_path and os.path.exists(t.final_file_path):
                    # Open folder and highlight file
                    try:
                        os.system(f'explorer /select,"{os.path.normpath(t.final_file_path)}"')
                    except Exception as e:
                        print(f"Error opening file location: {e}")
                break

    def flash_green(self, step=0, max_steps=15):
        """
        Transition background to green on completion then fade back to normal.
        """
        normal_bg = self.bg_color
        # Soft dark green: #065F46
        flash_bg = "#065F46"
        
        if step > max_steps:
            self.configure(fg_color=self.bg_color)
            return

        # Simple triangular wave (0 -> 1 -> 0)
        half = max_steps / 2
        t = (half - abs(step - half)) / half
        
        current_bg = interpolate_color(normal_bg, flash_bg, t)
        self.configure(fg_color=current_bg)
        
        self.after(30, lambda: self.flash_green(step + 1, max_steps))

class DashboardCard(customtkinter.CTkFrame):
    """
    A modern dashboard metric card for the sidebar.
    """
    def __init__(self, master, title, icon, value="0", accent_color="#3B82F6", **kwargs):
        super().__init__(master, fg_color="#161B22", corner_radius=16, border_width=1, border_color="#1E293B", **kwargs)
        
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        
        self.title_label = customtkinter.CTkLabel(
            self, text=title, font=("Segoe UI Variable Display", 10, "bold"), text_color="#94A3B8", anchor="w"
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=(10, 5), pady=(10, 2))
        
        self.icon_label = customtkinter.CTkLabel(
            self, text=icon, font=("Segoe UI Emoji", 12), text_color=accent_color
        )
        self.icon_label.grid(row=0, column=1, sticky="e", padx=(5, 10), pady=(10, 2))
        
        self.value_label = customtkinter.CTkLabel(
            self, text=value, font=("Segoe UI Variable Display", 15, "bold"), text_color="#FFFFFF", anchor="w"
        )
        self.value_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(2, 10))
        
    def update_value(self, new_value):
        self.value_label.configure(text=new_value)
