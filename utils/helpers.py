import os
import re

def format_size(bytes_val):
    if bytes_val is None:
        return "Unknown size"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def format_time(seconds):
    if seconds is None:
        return "--:--"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

def sanitize_filename(filename):
    # Remove characters that are illegal in Windows filenames
    # < > : " / \ | ? *
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Trim leading/trailing spaces and control characters
    sanitized = sanitized.strip().strip('.')
    # Fallback in case name is completely stripped
    if not sanitized:
        sanitized = "video"
    return sanitized

def get_unique_path(directory, filename):
    name, ext = os.path.splitext(filename)
    # Ensure name is not too long
    name = name[:200]
    counter = 1
    target_path = os.path.join(directory, f"{name}{ext}")
    while os.path.exists(target_path):
        target_path = os.path.join(directory, f"{name} ({counter}){ext}")
        counter += 1
    return target_path
