import os
import re

files = ['ui/app.py', 'ui/components.py']
for file in files:
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        content = content.replace('"Roboto"', '"Segoe UI Variable Display"')
        content = content.replace("'Roboto'", '"Segoe UI Variable Display"')
        
        # Increase font sizes slightly for Segoe UI
        def repl(match):
            size = int(match.group(1))
            return f"{size + 1})"
            
        content = re.sub(r'(\d+)\)', repl, content)
        
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
