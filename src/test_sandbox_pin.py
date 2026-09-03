"""
SADECE VIDEO/DEMO icin: Etsy magazasindan GERCEK bir urun cekip,
Pinterest Sandbox ortaminda gercek bir pin olusturur (tam entegrasyon gosterimi).
"""

import base64
import os
import sys
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
import etsy_client
import image_utils

SANDBOX_API_BASE = "https://api-sandbox.pinterest.com/v5"


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Eksik ortam degiskeni: {name}")
    return value


def main():
    etsy_client_id = get_env("ETSY_KEYSTRING")
    etsy_refresh_token = get_env("ETSY_REFRESH_TOKEN")

    print("Etsy erisim token'i yenileniyor...")
    etsy_tokens = etsy_client.refresh_access_token(etsy_client_id, etsy_refresh_token)
    etsy_access_token = etsy_tokens["access_token"]

    shop_id = etsy_client.get_shop_id(etsy_client_id, etsy_access_token)
    print(f"Magaza ID: {shop_id}")

    listings = etsy_client.get_active_listings(etsy_client_id, etsy_access_token, shop_id, limit=1)
    if not listings:
        raise RuntimeError("Magazada aktif urun bulunamadi.")

    listing = listings[0]
    title = listing.get("title", "")
    listing_url = etsy_client.get_listing_url(listing)
    image_url = etsy_client.get_first_image_url(listing)
    print(f"Secilen urun: {title}")
    print(f"Urun gorseli: {image_url}")

    print("Gorsel indirilip 2:3 orana kirpiliyor...")
    cropped_bytes = image_utils.fetch_and_crop(image_url)
    image_b64 = base64.b64encode(cropped_bytes).decode("utf-8")

    token = get_env("PINTEREST_SANDBOX_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}

    board_name = f"Etsy Demo {int(time.time())}"
    print(f"Sandbox'ta yeni pano olusturuluyor: {board_name}")
    create_resp = requests.post(
        f"{SANDBOX_API_BASE}/boards",
        headers=headers,
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
    pin_resp = requests.post(f"{SANDBOX_API_BASE}/pins", headers=headers, json=pin_payload)
    print("Pin olusturma durumu:", pin_resp.status_code)
    if not pin_resp.ok:
        print("HATA:", pin_resp.text)
        pin_resp.raise_for_status()

    result = pin_resp.json()
    print("BASARILI! Pin ID:", result.get("id"))
    print("Bu pin, GERCEK Etsy urun gorseliyle olusturuldu:", title)


if __name__ == "__main__":
    main()
