"""
Etsy API v3 ile konusan basit bir istemci.
- OAuth2 (PKCE) yetkilendirme URL'si olusturma
- Authorization code -> access/refresh token degisimi
- refresh_token ile yeni access_token alma
- Magaza ID bulma
- Aktif urun listelerini (listings) cekme
"""
import base64
import hashlib
import os
import secrets
import requests

ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
ETSY_AUTH_URL = "https://www.etsy.com/oauth/connect"
ETSY_API_BASE = "https://api.etsy.com/v3/application"

SCOPES = "shops_r listings_r"


def generate_pkce_pair():
    """Rastgele bir code_verifier ve ona karsilik gelen code_challenge uretir."""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).decode("utf-8").rstrip("=")
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return code_verifier, code_challenge


def build_auth_url(client_id: str, redirect_uri: str, code_challenge: str, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return f"{ETSY_AUTH_URL}?{query}"


def exchange_code_for_tokens(client_id: str, redirect_uri: str, code: str, code_verifier: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code": code,
        "code_verifier": code_verifier,
    }
    resp = requests.post(ETSY_TOKEN_URL, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(client_id: str, refresh_token: str) -> dict:
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    resp = requests.post(ETSY_TOKEN_URL, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _headers(api_key: str, shared_secret: str, access_token: str) -> dict:
    return {
        "x-api-key": f"{api_key}:{shared_secret}",
        "Authorization": f"Bearer {access_token}",
    }


def get_user_id_from_access_token(access_token: str) -> str:
    """Etsy access token'lari 'USERID.rastgelekisim' formatindadir."""
    return access_token.split(".")[0]


def get_shop_id(api_key: str, shared_secret: str, access_token: str) -> int:
    user_id = get_user_id_from_access_token(access_token)
    url = f"{ETSY_API_BASE}/users/{user_id}/shops"
    resp = requests.get(url, headers=_headers(api_key, shared_secret, access_token), timeout=30)
    if not resp.ok:
        print("ETSY HATA DETAYI:", resp.status_code, resp.text)
    resp.raise_for_status()
    shop = resp.json()
    return shop["shop_id"]


def get_active_listings(api_key: str, shared_secret: str, access_token: str, shop_id: int, limit: int = 100) -> list:
    """Magazadaki aktif urunleri, gorselleriyle birlikte ceker."""
    url = f"{ETSY_API_BASE}/shops/{shop_id}/listings/active"
    params = {"limit": limit, "includes": "Images"}
    resp = requests.get(url, headers=_headers(api_key, shared_secret, access_token), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("results", [])


def get_image_urls(listing: dict) -> list:
    """Bir listing objesindeki tum gorsellerin en yuksek kaliteli URL'lerini sirayla dondurur."""
    images = listing.get("images") or []
    urls = []
    for img in images:
        url = img.get("url_fullxfull") or img.get("url_570xN")
        if url:
            urls.append(url)
    return urls


def get_first_image_url(listing: dict) -> str | None:
    """Geriye donuk uyumluluk icin: ilk gorseli dondurur."""
    urls = get_image_urls(listing)
    return urls[0] if urls else None


def get_listing_url(listing: dict) -> str:
    return listing.get("url", "")
