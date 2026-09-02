"""
Gunluk otomatik pin atma islemini yoneten ana script.
GitHub Actions tarafindan her gun tetiklenir.

Yapilan islem:
1. Etsy'den magazadaki aktif urunleri ceker
2. Bu "tur" icinde daha once pinlenmemis urunlerden rastgele 2-3 tanesini secer
   (bir tur bitip yeniden basladiginda, her urun icin bir onceki turde kullanilan
   fotografin BIR SONRAKISI kullanilir; urunun fotograflari biterse basa doner)
3. Secilen gorseli indirir, 2:3 dikey orana kirpar
4. Aciklama metnine kucuk bir varyasyon ekler (ayni metnin surekli tekrarini onlemek icin)
5. Pinterest'teki belirtilen panoya pin olarak atar
6. Durumu data/posted.json dosyasina kaydeder
"""

import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

import etsy_client
import pinterest_client
import image_utils

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "posted.json")

PINS_PER_DAY_MIN = 2
PINS_PER_DAY_MAX = 3

# Aciklamanin sonuna rastgele eklenecek kucuk varyasyonlar.
# Ayni urun farkli turlarda pinlendiginde metin birebir ayni olmasin diye.
DESCRIPTION_VARIANTS = [
    "",
    "\n\n✨ Mağazamızdan.",
    "\n\n🎁 Hediyelik seçenekler için mağazamıza göz atın.",
    "\n\n🕰️ El işçiliğiyle hazırlandı.",
    "\n\n💫 Sınırlı sayıda üretim.",
    "\n\n🏠 Evinize sıcaklık katar.",
]


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"posted_current_round": [], "photo_index": {}}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("posted_current_round", [])
    data.setdefault("photo_index", {})
    return data


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Eksik ortam degiskeni: {name}. Bu degeri GitHub Secrets/Variables kismina eklemelisiniz.")
    return value


def pick_image_url(image_urls: list, listing_id: str, photo_index_map: dict) -> tuple:
    """
    Bu urun icin kullanilacak gorsel URL'sini ve kullanilan foto index'ini dondurur.
    Bir onceki turde kullanilan fotografin BIR SONRAKISINI secer; fotograflar
    biterse basa (0) doner.
    """
    if not image_urls:
        return None, None

    last_used = photo_index_map.get(listing_id, -1)
    next_index = (last_used + 1) % len(image_urls)
    return image_urls[next_index], next_index


def build_description(base_description: str) -> str:
    variant = random.choice(DESCRIPTION_VARIANTS)
    return (base_description[:400] + variant)[:500]


def main():
    # --- Ortam degiskenlerini oku ---
    etsy_client_id = get_env("ETSY_KEYSTRING")
    etsy_shared_secret = get_env("ETSY_SHARED_SECRET")
    etsy_refresh_token = get_env("ETSY_REFRESH_TOKEN")

    pinterest_client_id = get_env("PINTEREST_APP_ID")
    pinterest_client_secret = get_env("PINTEREST_APP_SECRET")
    pinterest_refresh_token = get_env("PINTEREST_REFRESH_TOKEN")
    pinterest_board_name = get_env("PINTEREST_BOARD_NAME")

    # --- Etsy: erisim token'i tazele ---
    print("Etsy erisim token'i yenileniyor...")
    etsy_tokens = etsy_client.refresh_access_token(etsy_client_id, etsy_refresh_token)
    etsy_access_token = etsy_tokens["access_token"]

    shop_id = etsy_client.get_shop_id(etsy_client_id, etsy_shared_secret, etsy_access_token)
    print(f"Magaza ID: {shop_id}")

    listings = etsy_client.get_active_listings(etsy_client_id, etsy_shared_secret, etsy_access_token, shop_id)
    print(f"Toplam aktif urun: {len(listings)}")
    if listings:
        print("DEBUG - ilk urunun anahtarlari:", list(listings[0].keys()))
        print("DEBUG - ilk urunun images alani:", listings[0].get("images"))
    if not listings:
        print("Aktif urun bulunamadi, islem sonlandiriliyor.")
        return

    # --- Pinterest: erisim token'i tazele ---
    print("Pinterest erisim token'i yenileniyor...")
    pin_tokens = pinterest_client.refresh_access_token(
        pinterest_client_id, pinterest_client_secret, pinterest_refresh_token
    )
    pinterest_access_token = pin_tokens["access_token"]

    board_id = pinterest_client.get_board_id(pinterest_access_token, pinterest_board_name)
    print(f"Pano ID: {board_id}")

    # --- Durum: bu turda pinlenenler + urun basina son kullanilan foto index'i ---
    state = load_state()
    posted_this_round = set(state["posted_current_round"])
    photo_index_map = state["photo_index"]

    unposted = [l for l in listings if str(l["listing_id"]) not in posted_this_round]

    if not unposted:
        print("Bu turda tum urunler pinlendi. Yeni tur basliyor (fotograflar bir sonrakine gececek).")
        posted_this_round = set()
        unposted = listings
        # photo_index_map KORUNUYOR -> yeni turda her urun bir sonraki fotografini kullanacak

    count = random.randint(PINS_PER_DAY_MIN, PINS_PER_DAY_MAX)
    count = min(count, len(unposted))
    chosen = random.sample(unposted, count)

    print(f"Bugun pinlenecek urun sayisi: {count}")

    # --- Her urun icin pin olustur ---
        for listing in chosen:
        listing_id = str(listing["listing_id"])
        title = listing.get("title", "")
        listing_url = etsy_client.get_listing_url(listing)

        images = etsy_client.get_listing_images(etsy_client_id, etsy_shared_secret, etsy_access_token, listing_id)
        image_urls = etsy_client.get_image_urls(images)
        image_url, used_index = pick_image_url(image_urls, listing_id, photo_index_map)

        if not image_url:
            print(f"[Atlandi] {listing_id} - gorsel bulunamadi")
            continue

        try:
            print(f"Isleniyor: {listing_id} - {title} (foto index: {used_index})")
            cropped = image_utils.fetch_and_crop(image_url)

            description = build_description(listing.get("description") or "")

            pinterest_client.create_pin(
                access_token=pinterest_access_token,
                board_id=board_id,
                image_bytes=cropped,
                title=title,
                description=description,
                link=listing_url,
            )
            print(f"[Basarili] Pin olusturuldu: {listing_id}")

            posted_this_round.add(listing_id)
            photo_index_map[listing_id] = used_index

            time.sleep(3)  # ardisik isteklerde rate limit'e takilmamak icin kucuk bir bekleme

        except Exception as e:
            print(f"[HATA] {listing_id} pinlenirken sorun olustu: {e}")

    state["posted_current_round"] = sorted(posted_this_round)
    state["photo_index"] = photo_index_map
    save_state(state)
    print("Islem tamamlandi.")


if __name__ == "__main__":
    main()
