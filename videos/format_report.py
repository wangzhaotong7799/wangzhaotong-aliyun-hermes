#!/usr/bin/env python3
"""Send report content to feishu group as formatted message."""
from docx import Document

doc = Document('/root/wangzhaotong-hermes/videos/prompt_report_20260512.docx')

# Extract text content organized by sections
sections = {}
current_section = "header"
sections[current_section] = []

for p in doc.paragraphs:
    t = p.text.strip()
    if not t:
        continue
    if t.startswith('## '):
        current_section = t[3:]
        sections[current_section] = []
    elif t.startswith('# ') and not t.startswith('## '):
        current_section = "header"
        sections[current_section].append(t)
    else:
        sections[current_section].append(t)

# Print organized content for sending
for section, content in sections.items():
    print(f"=== {section} ===")
    for line in content:
        print(line)
    print()
