"""
SADECE VIDEO/DEMO icin: Pinterest Sandbox ortaminda tek bir test pini olusturur.
Her calistirmada benzersiz isimli yeni bir pano olusturur, karisiklik olmasin.
"""

import base64
import os
import time
import requests

SANDBOX_API_BASE = "https://api-sandbox.pinterest.com/v5"


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Eksik ortam degiskeni: {name}")
    return value


def main():
    token = get_env("PINTEREST_SANDBOX_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}

    board_name = f"Demo Board {int(time.time())}"

    print(f"Yeni pano olusturuluyor: {board_name}")
    create_resp = requests.post(
        f"{SANDBOX_API_BASE}/boards",
        headers=headers,
        json={"name": board_name, "description": "Sandbox demo panosu"},
    )
    print("Pano olusturma durumu:", create_resp.status_code)
    if not create_resp.ok:
        print("HATA:", create_resp.text)
        create_resp.raise_for_status()
    board_id = create_resp.json()["id"]
    print(f"Pano olusturuldu: {board_id}")

    test_image_url = "https://images.unsplash.com/photo-1509048191080-d2984bad6ae5?w=800"
    print("Test gorseli indiriliyor...")
    img_resp = requests.get(test_image_url, timeout=30)
    img_resp.raise_for_status()
    image_b64 = base64.b64encode(img_resp.content).decode("utf-8")

    print("Pin olusturuluyor...")
    pin_payload = {
        "board_id": board_id,
        "title": "Test Pin - Etsy Pinterest Bot Demo",
        "description": "Bu, GorgeousWallClock Pinbot entegrasyonunun demo pinidir.",
        "link": "https://etsy.com/shop/GorgeousWallClock",
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


if __name__ == "__main__":
    main()
