import os
import re

files = ['ui/app.py', 'ui/components.py']

def repl(match):
    return f'{match.group(1)}"{match.group(2).upper()}"'

for file in files:
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        content = re.sub(r'(text=)"([^"]+)"', repl, content)
        content = re.sub(r'(placeholder_text=)"([^"]+)"', repl, content)
        
        # Also fix the URL matching to be truly universal
        content = content.replace('("youtube.com" in url or "youtu.be" in url or "instagram.com" in url or "instagr.am" in url)', 'url.startswith("http")')
        content = content.replace('("youtube.com" in clip or "youtu.be" in clip or "instagram.com" in clip or "instagr.am" in clip)', 'clip.startswith("http")')

        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
