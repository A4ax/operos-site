"""Generate a Pinterest-ready pin image for each article.

Creates a 1000x1500 (2:3) branded image using the article's product photo
with the title overlaid. Output to output/pins/<slug>.jpg so users can pin
directly, and the auto-pin bot can upload it.

Usage: python make_pins.py [limit]
"""
import json
import os
import sys
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(PROJECT_ROOT, 'data', 'pins')
WIDTH, HEIGHT = 1000, 1500
BAR_HEIGHT = 340


def get_font(size):
    for path in [
        'C:/Windows/Fonts/arialbd.ttf',
        'C:/Windows/Fonts/segoeuib.ttf',
        'C:/Windows/Fonts/calibrib.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_pin(article):
    slug = article['slug']
    image_url = article.get('image', '')
    title = article.get('title', slug)
    out_path = os.path.join(OUT_DIR, f'{slug}.jpg')
    if os.path.exists(out_path):
        return out_path, False

    try:
        if image_url:
            r = requests.get(image_url, timeout=20)
            if r.status_code == 200:
                img = Image.open(BytesIO(r.content)).convert('RGB')
                img = img.resize((WIDTH, HEIGHT - BAR_HEIGHT))
            else:
                img = Image.new('RGB', (WIDTH, HEIGHT - BAR_HEIGHT), (15, 23, 42))
        else:
            img = Image.new('RGB', (WIDTH, HEIGHT - BAR_HEIGHT), (15, 23, 42))

        canvas = Image.new('RGB', (WIDTH, HEIGHT), (15, 23, 42))
        canvas.paste(img, (0, 0))

        # Title bar
        bar = Image.new('RGB', (WIDTH, BAR_HEIGHT), (37, 99, 235))
        canvas.paste(bar, (0, HEIGHT - BAR_HEIGHT))

        draw = ImageDraw.Draw(canvas)
        font = get_font(52)
        # wrap title
        words = title.split()
        lines = []
        cur = ''
        for w in words:
            if len(cur) + len(w) + 1 <= 24:
                cur = (cur + ' ' + w).strip()
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        lines = lines[:3]

        y = HEIGHT - BAR_HEIGHT + 40
        for line in lines:
            draw.text((50, y), line, fill=(255, 255, 255), font=font)
            y += 72

        draw.text((50, HEIGHT - 70), 'operos.de', fill=(255, 255, 255), font=get_font(34))

        os.makedirs(OUT_DIR, exist_ok=True)
        canvas.save(out_path, quality=88)
        return out_path, True
    except Exception as e:
        print(f'  [pin error] {slug}: {e}')
        return None, False


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    articles = json.load(open(os.path.join(PROJECT_ROOT, 'data', 'articles.json'), encoding='utf-8'))
    # prioritize newest
    articles.sort(key=lambda a: a.get('published_at', ''), reverse=True)
    if limit:
        articles = articles[:limit]
    made = 0
    for a in articles:
        path, created = make_pin(a)
        if path and created:
            made += 1
    print(f'Created {made} new pin images in {OUT_DIR}')


if __name__ == '__main__':
    main()