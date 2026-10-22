#!/usr/bin/env python3
"""
Font subsetting

python3 font_subsetting.py [path/to/index.html] --nebulove /path/to/Nebulove.ttf --emoji /path/to/Yomi-UI-Emoji.ttf

pip install fonttools brotli
"""
import argparse
import base64
import re
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.subset import Options, Subsetter

BLOCK_RE = re.compile(r'<style>\s*(?:/\*\s*INLINE_FONTS\s*\*/\s*)?@font-face.*?</style>', re.S)


def parse_args():
    parser = argparse.ArgumentParser(description='Subset and inline the fonts used by YiPairs.')
    parser.add_argument('index', nargs='?', type=Path,
                        default=Path(__file__).with_name('index.html'),
                        help='HTML file to update (default: index.html next to this script)')
    parser.add_argument('--nebulove', required=True, type=Path, help='path to Nebulove.ttf')
    parser.add_argument('--emoji', required=True, type=Path, help='path to Yomi-UI-Emoji.ttf')
    return parser.parse_args()


def subset(src, text_, out):
    font = TTFont(src)
    try:
        subsetter = Subsetter(options=Options())
        subsetter.populate(text=text_)
        subsetter.subset(font)
        font.flavor = 'woff2'
        font.save(out)
        size = out.stat().st_size
        print(f'{out.name}: {size} bytes ({size / 1024:.1f} KB), glyphs={font["maxp"].numGlyphs}')
    finally:
        font.close()
    return out


def b64(path):
    return base64.b64encode(path.read_bytes()).decode('ascii')


def main():
    args = parse_args()
    html = args.index.read_text(encoding='utf-8')
    if not BLOCK_RE.search(html):
        raise SystemExit(f'Error: inline-fonts <style> block not found in {args.index}')

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

    with tempfile.TemporaryDirectory(prefix='yipairs-fonts-') as tmp:
        tmp = Path(tmp)
        neb = subset(args.nebulove, text, tmp / 'Nebulove-subset.woff2')
        emo = subset(args.emoji, emoji_text, tmp / 'Yomi-UI-Emoji-subset.woff2')

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
    new_block = '<style>\n/* INLINE_FONTS */\n' + font_css + '\n</style>'
    html, n = BLOCK_RE.subn(lambda m: new_block, html, count=1)
    if n != 1:
        raise SystemExit(f'Error: inline-fonts <style> block not found in {args.index}')

    args.index.write_text(html, encoding='utf-8')
    size = args.index.stat().st_size
    print(f'{args.index} updated: {size} bytes ({size / 1024:.1f} KB)')


if __name__ == '__main__':
    main()
