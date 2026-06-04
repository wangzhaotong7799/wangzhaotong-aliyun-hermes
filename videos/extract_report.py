#!/usr/bin/env python3
"""Extract report content from docx and print key sections."""
from docx import Document

doc = Document('/root/wangzhaotong-hermes/videos/prompt_report_20260512.docx')
lines = []
for p in doc.paragraphs:
    t = p.text.strip()
    if t:
        lines.append(t)

# Print first 50 lines to see structure
print('\n'.join(lines[:60]))
print(f'\n--- TOTAL: {len(lines)} paragraphs ---')
