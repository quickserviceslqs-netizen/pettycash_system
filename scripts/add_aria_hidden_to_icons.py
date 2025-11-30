#!/usr/bin/env python3
"""
Scan template files and add aria-hidden="true" to <i> tags that are likely decorative
"""
import os
import re

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates')

ICON_RE = re.compile(r'<i\s+([^>]*?)>')
ARIA_RE = re.compile(r'aria-hidden\s*=')

modified_files = []

for root, dirs, files in os.walk(TEMPLATES_DIR):
    for file in files:
        if not file.endswith('.html'):
            continue
        path = os.path.join(root, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = content
        def repl(m):
            attrs = m.group(1)
            if 'aria-hidden' in attrs:
                return m.group(0)
            # If the icon has an explicit textual sibling within same tag (like <i class="...">text</i>), skip.
            # We'll conservatively add aria-hidden when no inner text is present.
            return '<i aria-hidden="true" ' + attrs + '>'

        new_content = ICON_RE.sub(repl, content)

        if new_content != content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            modified_files.append(path)

print(f"Modified {len(modified_files)} files")
for p in modified_files:
    print(p)
