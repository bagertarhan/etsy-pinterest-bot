"""
Pinterest API v5 ile konusan basit bir istemci.
- OAuth2 yetkilendirme URL'si olusturma
- Authorization code -> access/refresh token degisimi
- refresh_token ile yeni access_token alma
- Board (pano) ID bulma
- Pin olusturma (base64 gorsel ile)
"""

import base64
import requests

PINTEREST_AUTH_URL = "https://www.pinterest.com/oauth/"
PINTEREST_TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
PINTEREST_API_BASE = "https://api.pinterest.com/v5"

SCOPES = "boards:read,pins:read,pins:write"


def build_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
    }
    query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return f"{PINTEREST_AUTH_URL}?{query}"


def _basic_auth_header(client_id: str, client_secret: str) -> dict:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    token = base64.b64encode(raw).decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def exchange_code_for_tokens(client_id: str, client_secret: str, redirect_uri: str, code: str) -> dict:
    headers = _basic_auth_header(client_id, client_secret)
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    resp = requests.post(PINTEREST_TOKEN_URL, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    headers = _basic_auth_header(client_id, client_secret)
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    resp = requests.post(PINTEREST_TOKEN_URL, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def get_board_id(access_token: str, board_name: str) -> str:
    url = f"{PINTEREST_API_BASE}/boards"
    resp = requests.get(url, headers=_headers(access_token), params={"page_size": 100}, timeout=30)
    resp.raise_for_status()
    boards = resp.json().get("items", [])
    for board in boards:
        if board.get("name", "").strip().lower() == board_name.strip().lower():
            return board["id"]
    raise ValueError(
        f"'{board_name}' adinda bir pano bulunamadi. Pinterest hesabinizdaki panolardan "
        f"birinin adini PINTEREST_BOARD_NAME olarak ayarlayin. Bulunan panolar: "
        f"{[b.get('name') for b in boards]}"
    )


def create_pin(access_token: str, board_id: str, image_bytes: bytes, title: str,
               description: str, link: str) -> dict:
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "board_id": board_id,
        "title": title[:100],
        "description": description[:500],
        "link": link,
        "media_source": {
            "source_type": "image_base64",
            "content_type": "image/jpeg",
            "data": image_b64,
        },
    }
        url = f"{PINTEREST_API_BASE}/pins"
    resp = requests.post(url, headers=_headers(access_token), json=payload, timeout=60)
    if not resp.ok:
        print("PINTEREST HATA DETAYI:", resp.status_code, resp.text)
    resp.raise_for_status()
    return resp.json()
