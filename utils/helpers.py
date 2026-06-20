import os
import re
from typing import Optional, Union

def format_size(bytes_val: Optional[Union[int, float]]) -> str:
    """Formats a byte value into a human-readable string (e.g., KB, MB, GB)."""
    if bytes_val is None:
        return "Unknown size"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def format_time(seconds: Optional[Union[int, float]]) -> str:
    """Formats a time in seconds into a MM:SS or HH:MM:SS string."""
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

def sanitize_filename(filename: str) -> str:
    """
    Removes characters that are illegal in Windows filenames.
    Also trims leading/trailing spaces and dots.
    """
    # Remove characters that are illegal in Windows filenames
    # < > : " / \ | ? *
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Trim leading/trailing spaces and control characters
    sanitized = sanitized.strip().strip('.')
    # Fallback in case name is completely stripped
    if not sanitized:
        sanitized = "video"
    return sanitized

def get_unique_path(directory: str, filename: str) -> str:
    """
    Generates a unique file path in the given directory to prevent overwriting.
    Appends (1), (2), etc., to the filename if it already exists.
    """
    name, ext = os.path.splitext(filename)
    # Ensure name is not too long
    name = name[:200]
    counter = 1
    target_path = os.path.join(directory, f"{name}{ext}")
    while os.path.exists(target_path):
        target_path = os.path.join(directory, f"{name} ({counter}){ext}")
        counter += 1
    return target_path
