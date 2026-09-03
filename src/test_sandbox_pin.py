"""
SADECE VIDEO/DEMO icin: Etsy magazasindan GERCEK bir urun cekip,
Pinterest Sandbox ortaminda gercek bir pin olusturur.
Bu dosya bagimsizdir (baska dosyaya import etmez), karisiklik olmasin diye.
"""

import base64
import io
import os
import time
import requests
from PIL import Image

ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
ETSY_API_BASE = "https://api.etsy.com/v3/application"
SANDBOX_API_BASE = "https://api-sandbox.pinterest.com/v5"


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Eksik ortam degiskeni: {name}")
    return value


def crop_to_2_3(image_bytes: bytes) -> bytes:
    im = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = im.size
    target_ratio = 2 / 3
    current_ratio = w / h
    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        im = im.crop((left, 0, left + new_w, h))
    elif current_ratio < target_ratio:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        im = im.crop((0, top, w, top + new_h))
    if im.width > 1000:
        im = im.resize((1000, int(1000 / target_ratio)), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=88)
    return out.getvalue()


def main():
    etsy_client_id = get_env("ETSY_KEYSTRING")
    etsy_shared_secret = get_env("ETSY_SHARED_SECRET")
    etsy_refresh_token = get_env("ETSY_REFRESH_TOKEN")

    print("Etsy erisim token'i yenileniyor...")
    token_resp = requests.post(ETSY_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "client_id": etsy_client_id,
        "refresh_token": etsy_refresh_token,
    })
    token_resp.raise_for_status()
    etsy_access_token = token_resp.json()["access_token"]
    user_id = etsy_access_token.split(".")[0]

    etsy_headers = {
        "x-api-key": f"{etsy_client_id}:{etsy_shared_secret}",
        "Authorization": f"Bearer {etsy_access_token}",
    }

    print("Magaza bilgisi aliniyor...")
    shop_resp = requests.get(f"{ETSY_API_BASE}/users/{user_id}/shops", headers=etsy_headers)
    if not shop_resp.ok:
        print("ETSY HATA DETAYI:", shop_resp.status_code, shop_resp.text)
    shop_resp.raise_for_status()
    shop_id = shop_resp.json()["shop_id"]
    print(f"Magaza ID: {shop_id}")

    print("Urun listesi cekiliyor...")
    listings_resp = requests.get(
        f"{ETSY_API_BASE}/shops/{shop_id}/listings/active",
        headers=etsy_headers,
        params={"limit": 1, "includes": "Images"},
    )
    listings_resp.raise_for_status()
    results = listings_resp.json().get("results", [])
    if not results:
        raise RuntimeError("Magazada aktif urun bulunamadi.")

    listing = results[0]
    title = listing.get("title", "")
    listing_url = listing.get("url", "")
    images = listing.get("images") or []
    image_url = None
    if images:
        image_url = images[0].get("url_fullxfull") or images[0].get("url_570xN")

    print(f"Secilen urun: {title}")
    print(f"Urun gorseli: {image_url}")

    if not image_url:
        raise RuntimeError("Urunun gorseli bulunamadi.")

    print("Gorsel indirilip 2:3 orana kirpiliyor...")
    img_resp = requests.get(image_url, timeout=30)
    img_resp.raise_for_status()
    cropped_bytes = crop_to_2_3(img_resp.content)
    image_b64 = base64.b64encode(cropped_bytes).decode("utf-8")

    pin_token = get_env("PINTEREST_SANDBOX_TOKEN")
    pin_headers = {"Authorization": f"Bearer {pin_token}"}

    board_name = f"Etsy Demo {int(time.time())}"
    print(f"Sandbox'ta yeni pano olusturuluyor: {board_name}")
    create_resp = requests.post(
        f"{SANDBOX_API_BASE}/boards",
        headers=pin_headers,
        json={"name": board_name, "description": "Etsy urunleri - Sandbox demo"},
    )
    if not create_resp.ok:
        print("HATA:", create_resp.text)
        create_resp.raise_for_status()
    board_id = create_resp.json()["id"]
    print(f"Pano olusturuldu: {board_id}")

    print("Pin olusturuluyor (gercek Etsy urunuyle)...")
    pin_payload = {
        "board_id": board_id,
        "title": title,
        "description": (listing.get("description") or "")[:400],
        "link": listing_url,
        "media_source": {
            "source_type": "image_base64",
            "content_type": "image/jpeg",
            "data": image_b64,
        },
    }
    pin_resp = requests.post(f"{SANDBOX_API_BASE}/pins", headers=pin_headers, json=pin_payload)
    print("Pin olusturma durumu:", pin_resp.status_code)
    if not pin_resp.ok:
        print("HATA:", pin_resp.text)
        pin_resp.raise_for_status()

    result = pin_resp.json()
    print("BASARILI! Pin ID:", result.get("id"))
    print("Bu pin, GERCEK Etsy urun gorseliyle olusturuldu:", title)


if __name__ == "__main__":
    main()
