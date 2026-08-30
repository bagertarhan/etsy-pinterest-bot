"""
Gorsel indirme ve Pinterest icin 2:3 dikey orana ortadan kirpma islemleri.
"""

import io
import requests
from PIL import Image

TARGET_RATIO = 2 / 3  # genislik:yukseklik = 2:3 (dikey)
MAX_WIDTH = 1000  # Pinterest icin onerilen genislik


def download_image_bytes(url: str) -> bytes:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


def crop_to_2_3(image_bytes: bytes) -> bytes:
    """Verilen gorseli ortadan kirpip 2:3 dikey orana getirir, JPEG olarak dondurur."""
    im = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = im.size
    current_ratio = w / h

    if current_ratio > TARGET_RATIO:
        # gorsel gereginden genis -> yanlardan kirp
        new_w = int(h * TARGET_RATIO)
        left = (w - new_w) // 2
        im = im.crop((left, 0, left + new_w, h))
    elif current_ratio < TARGET_RATIO:
        # gorsel gereginden uzun/dar -> ustten/alttan kirp
        new_h = int(w / TARGET_RATIO)
        top = (h - new_h) // 2
        im = im.crop((0, top, w, top + new_h))
    # esitse (zaten 2:3) kirpmaya gerek yok

    # makul bir boyuta olcekle (cok buyukse kucult)
    if im.width > MAX_WIDTH:
        new_height = int(MAX_WIDTH / TARGET_RATIO)
        im = im.resize((MAX_WIDTH, new_height), Image.LANCZOS)

    out = io.BytesIO()
    im.save(out, format="JPEG", quality=88)
    return out.getvalue()


def fetch_and_crop(url: str) -> bytes:
    raw = download_image_bytes(url)
    return crop_to_2_3(raw)
