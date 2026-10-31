#!/usr/bin/env python3
"""Make the desktop wallpaper sizes from branding/wallpapers/wallpaper.png, a painting by byrotek. Needs Pillow."""
import hashlib, json, sys
from pathlib import Path
from PIL import Image, ImageFilter

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / 'branding/wallpapers/wallpaper.png'
PACKAGE = REPO / 'branding/wallpapers/VIGILOS-Desktop'
MANIFEST = REPO / 'branding/wallpapers/desktop-assets.json'
ARTIST = {'Name': 'byrotek', 'Website': 'https://www.deviantart.com/byrotek'}
SIZES = [
    (1366, 768), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160),  # 16:9
    (1280, 800), (1440, 900), (1680, 1050), (1920, 1200), (2560, 1600),  # 16:10
    (2560, 1080), (3440, 1440),  # 21:9
    (1024, 768), (1600, 1200),  # 4:3
    (1280, 1024),  # 5:4
]

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def centre_crop(width, height, target_w, target_h):
    """The largest centred box of the source with the target's aspect ratio."""
    if width * target_h > height * target_w:
        crop_w = height * target_w / target_h
        left = (width - crop_w) / 2
        return (left, 0, left + crop_w, height)
    crop_h = width * target_h / target_w
    top = (height - crop_h) / 2
    return (0, top, width, top + crop_h)

def main():
    image = Image.open(SOURCE).convert('RGB')
    icc = image.info.get('icc_profile')
    images = PACKAGE / 'contents/images'
    images.mkdir(parents=True, exist_ok=True)
    for old in images.glob('*.jpg'):
        old.unlink()
    variants = {}
    for w, h in SIZES:
        box = centre_crop(*image.size, w, h)
        out = image.resize((w, h), Image.Resampling.LANCZOS, box=box)
        if w / (box[2] - box[0]) > 1.05:
            out = out.filter(ImageFilter.UnsharpMask(radius=1.2, percent=35, threshold=2))
        path = images / f'{w}x{h}.jpg'
        out.save(path, 'JPEG', quality=95, subsampling=0, optimize=True, icc_profile=icc)
        variants[path.name] = {'sha256': sha256(path), 'width': w, 'height': h}
    metadata = {
        'KPlugin': {
            'Authors': [ARTIST],
            'Id': 'VIGILOS-Desktop',
            'Name': 'VIGIL OS Landscape',
            'Description': f"Painting by byrotek, used with the artist's permission. {ARTIST['Website']}",
        },
        'X-KDE-PlasmaImageWallpaper-AccentColor': '#719bff',
    }
    (PACKAGE / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    manifest = {
        'description': "Desktop wallpaper, a painting by byrotek used with the artist's permission. Each size is cropped from the centre to its aspect ratio and resized with Lanczos, never stretched; sizes wider than the source are upscaled.",
        'artist': ARTIST,
        'source': {'file': SOURCE.name, 'sha256': sha256(SOURCE), 'width': image.width, 'height': image.height},
        'variants': variants,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n')
    total = sum((images / name).stat().st_size for name in variants)
    print(f'{len(variants)} sizes in {images}, {total / 1e6:.1f} MB')

if __name__ == '__main__':
    main()
