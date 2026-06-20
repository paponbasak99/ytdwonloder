import customtkinter
from PIL import Image
import math
import logging

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join([c*2 for c in hex_str])
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*(max(0, min(255, int(c))) for c in rgb))

def interpolate_color(color_start, color_end, t):
    rgb_start = hex_to_rgb(color_start)
    rgb_end = hex_to_rgb(color_end)
    rgb_interp = [s + (e - s) * t for s, e in zip(rgb_start, rgb_end)]
    return rgb_to_hex(rgb_interp)

def animate_border_color(widget, start_color, end_color, duration_ms=200, steps=10, step=0):
    """
    Smoothly transitions a CustomTkinter widget's border color.
    """
    if step > steps:
        widget.configure(border_color=end_color)
        return
        
    t = step / steps
    current_color = interpolate_color(start_color, end_color, t)
    widget.configure(border_color=current_color)
    
    delay = int(duration_ms / steps)
    widget.after(delay, lambda: animate_border_color(widget, start_color, end_color, duration_ms, steps, step + 1))

def shake_widget(widget, offsets=[10, -10, 8, -8, 6, -6, 4, -4, 2, -2, 0], delay_ms=30, step=0, original_info=None):
    """
    Shakes a widget side-to-side dynamically depending on its active layout manager.
    """
    if original_info is None:
        manager = widget.winfo_manager()
        if manager == 'pack':
            original_info = ('pack', widget.pack_info())
        elif manager == 'grid':
            original_info = ('grid', widget.grid_info())
        elif manager == 'place':
            original_info = ('place', widget.place_info())
        else:
            return

    if step >= len(offsets):
        # Restore original positioning perfectly
        manager_type, info = original_info
        if manager_type == 'pack':
            widget.pack_configure(**info)
        elif manager_type == 'grid':
            widget.grid_configure(**info)
        elif manager_type == 'place':
            widget.place_configure(**info)
        return

    offset = offsets[step]
    manager_type, info = original_info
    
    if manager_type == 'pack':
        new_info = info.copy()
        padx = new_info.get('padx', 0)
        if isinstance(padx, tuple):
            padx = padx[0]
        new_info['padx'] = (max(0, padx + offset), max(0, padx - offset))
        widget.pack_configure(**new_info)
    elif manager_type == 'grid':
        new_info = info.copy()
        padx = new_info.get('padx', 0)
        if isinstance(padx, tuple):
            padx = padx[0]
        new_info['padx'] = (max(0, padx + offset), max(0, padx - offset))
        widget.grid_configure(**new_info)
    elif manager_type == 'place':
        new_info = info.copy()
        # Ensure x is integer
        x = new_info.get('x', 0)
        try:
            x = int(x)
        except ValueError:
            x = 0
        new_info['x'] = x + offset
        widget.place_configure(**new_info)

    widget.after(delay_ms, lambda: shake_widget(widget, offsets, delay_ms, step + 1, original_info))

def fade_in_image(widget, pil_image, bg_color_hex, size=(120, 90), duration_ms=300, steps=8, step=0):
    """
    Smoothly fades in a PIL image against a background color using image blending.
    """
    if not pil_image:
        return
        
    if step > steps:
        # Complete fade-in: set target image directly
        ctk_image = customtkinter.CTkImage(light_image=pil_image, dark_image=pil_image, size=size)
        widget.configure(image=ctk_image)
        return

    alpha = step / steps
    bg_rgb = hex_to_rgb(bg_color_hex)
    
    # Resize thumbnail to correct aspect ratio
    resized_pil = pil_image.copy()
    resized_pil.thumbnail(size, Image.Resampling.LANCZOS)
    
    # Create background canvas image
    bg_canvas = Image.new("RGB", resized_pil.size, bg_rgb)
    blended = Image.blend(bg_canvas, resized_pil.convert("RGB"), alpha)
    
    ctk_image = customtkinter.CTkImage(light_image=blended, dark_image=blended, size=resized_pil.size)
    widget.configure(image=ctk_image)
    
    delay = int(duration_ms / steps)
    widget.after(delay, lambda: fade_in_image(widget, pil_image, bg_color_hex, size, duration_ms, steps, step + 1))

def animate_progress_smoothly(progress_bar, target_val, current_val=None, step_cb=None):
    """
    Interpolates progress values to eliminate jagged transitions.
    """
    if current_val is None:
        current_val = progress_bar.get()
        
    diff = target_val - current_val
    if abs(diff) < 0.005:
        progress_bar.set(target_val)
        if step_cb:
            step_cb(target_val)
        return

    # Exponential ease out
    next_val = current_val + diff * 0.15
    progress_bar.set(next_val)
    if step_cb:
        step_cb(next_val)
        
    progress_bar.after(16, lambda: animate_progress_smoothly(progress_bar, target_val, next_val, step_cb))

def animate_pulse_glow(button, normal_color, glow_color, is_glowing=True, step=0):
    """
    Pulses the button color dynamically on hover.
    """
    # Simple sine wave scaling
    t = (math.sin(step * 0.2) + 1.0) / 2.0
    current_color = interpolate_color(normal_color, glow_color, t)
    
    # Ensure button is still hovered to continue
    # CustomTkinter buttons have an internal state or we can use mouse binding
    # We will let the button component coordinate this
    button.configure(fg_color=current_color)
    
    # Check flag to continue
    if hasattr(button, 'should_pulse') and button.should_pulse:
        button.after(50, lambda: animate_pulse_glow(button, normal_color, glow_color, is_glowing, step + 1))
    else:
        # Restore normal
        button.configure(fg_color=normal_color)

def animate_window_fade_in(window, target_alpha=1.0, duration_ms=400, steps=20, step=0):
    """
    Fades in the application window on startup.
    """
    try:
        if step > steps:
            window.attributes('-alpha', target_alpha)
            return
            
        alpha = (step / steps) * target_alpha
        window.attributes('-alpha', alpha)
        delay = int(duration_ms / steps)
        window.after(delay, lambda: animate_window_fade_in(window, target_alpha, duration_ms, steps, step + 1))
    except Exception as e:
        logging.warning(f"Window fade animation failed: {e}")  # Failsafe if OS doesn't support alpha transparency

def skeleton_pulse_loader(widget, base_color, highlight_color, is_loading_func, step=0):
    """
    Pulses a widget background between base_color and highlight_color to simulate a loading skeleton.
    """
    if not is_loading_func():
        return
        
    # Sine wave oscillation
    t = (math.sin(step * 0.15) + 1.0) / 2.0
    current_color = interpolate_color(base_color, highlight_color, t)
    
    try:
        widget.configure(fg_color=current_color)
    except Exception as e:
        logging.debug(f"Skeleton loader color change failed (widget might be destroyed): {e}")
        
    widget.after(50, lambda: skeleton_pulse_loader(widget, base_color, highlight_color, is_loading_func, step + 1))

def animate_gradient_flow(widget, colors, is_active_func, step=0):
    """
    Simulates a gradient flowing by interpolating through a list of colors.
    """
    if not is_active_func():
        return
        
    n = len(colors)
    # Smooth transition
    idx1 = (step // 20) % n
    idx2 = (idx1 + 1) % n
    t = (step % 20) / 20.0
    
    current_color = interpolate_color(colors[idx1], colors[idx2], t)
    
    try:
        widget.configure(fg_color=current_color)
    except Exception as e:
        logging.debug(f"Gradient flow color change failed (widget might be destroyed): {e}")
        
    widget.after(30, lambda: animate_gradient_flow(widget, colors, is_active_func, step + 1))

