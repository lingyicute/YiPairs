#!/usr/bin/env python3
"""
Font subsetting

python3 font_subsetting.py [path/to/index.html]

pip install fonttools brotli
"""
import base64
import os
import re
import sys

from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter, Options

INDEX = sys.argv[1] if len(sys.argv) > 1 else '/home/user/uploads/index.html'

with open(INDEX, encoding='utf-8') as f:
    html = f.read()

# ---- 1. Collect all characters needed (same as 92li) ----
chars = set(html)
for c in range(32, 127):            # full printable ASCII
    chars.add(chr(c))
chars.update(['：', '，', '。', '！', '？', '；', '“', '”', '‘', '’',
              '（', '）', '【', '】', '—', '…', '·', '《', '》', '×', '＝', '÷', '＋', '－'])
text = ''.join(sorted(chars))
print(f'Nebulove charset: {len(chars)} unique chars')

# ---- emoji charset: only emoji codepoints present in the page ----
emoji = {c for c in html
         if ord(c) >= 0x1F000                      # emoji blocks (card symbols, 🎉 …)
         or 0x2600 <= ord(c) <= 0x27BF             # misc symbols & dingbats (❤ …)
         or ord(c) in (0xFE0F, 0x200D)}            # VS16 / ZWJ
emoji_text = ''.join(sorted(emoji))
print(f'Yomi-UI-Emoji charset: {len(emoji)} codepoints -> {emoji_text}')


def subset(src, text_, out):
    font = TTFont(src)
    subsetter = Subsetter(options=Options())
    subsetter.populate(text=text_)
    subsetter.subset(font)
    font.flavor = 'woff2'
    font.save(out)
    size = os.path.getsize(out)
    print(f'{os.path.basename(out)}: {size} bytes ({size / 1024:.1f} KB), glyphs={font["maxp"].numGlyphs}')
    return out


neb = subset('/home/user/fonts/Nebulove.ttf', text, '/tmp/Nebulove-subset.woff2')
emo = subset('/home/user/fonts/Yomi-UI-Emoji.ttf', emoji_text, '/tmp/Yomi-UI-Emoji-subset.woff2')


def b64(p):
    with open(p, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


font_css = f'''@font-face {{
    font-family: 'Nebulove';
    src: url('data:font/woff2;charset=utf-8;base64,{b64(neb)}') format('woff2');
    font-weight: normal;
    font-style: normal;
    font-display: swap;
}}
@font-face {{
    font-family: 'Yomi-UI-Emoji';
    src: url('data:font/woff2;charset=utf-8;base64,{b64(emo)}') format('woff2');
    font-weight: normal;
    font-style: normal;
    font-display: swap;
}}'''

# ---- replace the inline-fonts <style> block in place (sentinel keeps it findable) ----
BLOCK_RE = re.compile(r'<style>\s*(?:/\*\s*INLINE_FONTS\s*\*/\s*)?@font-face.*?</style>', re.S)
new_block = '<style>\n/* INLINE_FONTS */\n' + font_css + '\n</style>'
html, n = BLOCK_RE.subn(lambda m: new_block, html, count=1)
if n != 1:
    print('Error: inline-fonts <style> block not found in', INDEX, file=sys.stderr)
    sys.exit(1)

with open(INDEX, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'{INDEX} updated: {os.path.getsize(INDEX)} bytes ({os.path.getsize(INDEX) / 1024:.1f} KB)')
