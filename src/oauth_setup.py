"""
TEK SEFERLIK kurulum scripti. Etsy ve Pinterest icin yetkilendirme (OAuth) surecini
GitHub Actions log ciktisi uzerinden yurutmeye yarar. Kullanici bu scripti dogrudan
calistirmaz; .github/workflows/setup-oauth.yml workflow'u araciligiyla calisir.

Kullanim (workflow icinden):
  python src/oauth_setup.py start
      -> Etsy ve Pinterest yetkilendirme linklerini ve code_verifier degerini yazdirir

  python src/oauth_setup.py finish --etsy-code XXX --pinterest-code YYY --code-verifier ZZZ
      -> Kodlari refresh token'lara cevirir ve tokens_output.txt dosyasina yazar
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import etsy_client
import pinterest_client

REDIRECT_URI = "https://bagertarhan.github.io/etsy-pinterest-bot/callback"


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Eksik ortam degiskeni: {name}")
    return value


def do_start():
    etsy_client_id = get_env("ETSY_KEYSTRING")
    pinterest_client_id = get_env("PINTEREST_APP_ID")

    code_verifier, code_challenge = etsy_client.generate_pkce_pair()

    etsy_url = etsy_client.build_auth_url(
        client_id=etsy_client_id,
        redirect_uri=REDIRECT_URI,
        code_challenge=code_challenge,
        state="etsystate123",
    )
    pinterest_url = pinterest_client.build_auth_url(
        client_id=pinterest_client_id,
        redirect_uri=REDIRECT_URI,
        state="pinterestate123",
    )

    print("=" * 70)
    print("ADIM 1 TAMAMLANDI. Asagidaki bilgileri NOT ALIN:")
    print("=" * 70)
    print()
    print("CODE_VERIFIER (2. adimda lazim olacak, kopyalayin):")
    print(code_verifier)
    print()
    print("1) Once bu linki tarayicida acin, Etsy ile giris yapip izin verin:")
    print(etsy_url)
    print()
    print("2) Sonra bu linki tarayicida acin, Pinterest ile giris yapip izin verin:")
    print(pinterest_url)
    print()
    print("Her ikisinde de, izin verdikten sonra callback sayfasinda bir 'code' ")
    print("degeri gorunecek. Ikisini de not alin, 2. adimda kullanacaksiniz.")
    print("=" * 70)


def do_finish(etsy_code: str, pinterest_code: str, code_verifier: str):
    """
    Etsy ve Pinterest kodlarindan istedigi olani isler. Ikisi ayni anda hazir
    olmak zorunda degil -- sadece biri girilirse sadece o servis icin token alinir.
    Sonuclar 'tokens_output.txt' dosyasina yazilir (log maskeleme sorunundan kacinmak icin).
    """
    did_something = False

    if etsy_code:
        etsy_client_id = get_env("ETSY_KEYSTRING")
        print("Etsy token degisimi yapiliyor...")
        etsy_tokens = etsy_client.exchange_code_for_tokens(
            client_id=etsy_client_id,
            redirect_uri=REDIRECT_URI,
            code=etsy_code,
            code_verifier=code_verifier,
        )
        print("ETSY BASARILI! Deger dosyaya yazildi (tokens_output.txt), asagida indirin.")
        with open("tokens_output.txt", "a", encoding="utf-8") as f:
            f.write("ETSY_REFRESH_TOKEN=" + etsy_tokens["refresh_token"] + "\n")
        did_something = True
    else:
        print("Etsy kodu girilmedi, Etsy adimi atlandi.")

    if pinterest_code:
        pinterest_client_id = get_env("PINTEREST_APP_ID")
        pinterest_client_secret = get_env("PINTEREST_APP_SECRET")
        print("Pinterest token degisimi yapiliyor...")
        pinterest_tokens = pinterest_client.exchange_code_for_tokens(
            client_id=pinterest_client_id,
            client_secret=pinterest_client_secret,
            redirect_uri=REDIRECT_URI,
            code=pinterest_code,
        )
        print("PINTEREST BASARILI! Deger dosyaya yazildi (tokens_output.txt), asagida indirin.")
        with open("tokens_output.txt", "a", encoding="utf-8") as f:
            f.write("PINTEREST_REFRESH_TOKEN=" + pinterest_tokens["refresh_token"] + "\n")
        did_something = True
    else:
        print("Pinterest kodu girilmedi, Pinterest adimi atlandi.")

    if not did_something:
        print("Hic kod girilmedi, yapilacak bir sey yok.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("start")

    finish_parser = sub.add_parser("finish")
    finish_parser.add_argument("--etsy-code", required=False, default="")
    finish_parser.add_argument("--pinterest-code", required=False, default="")
    finish_parser.add_argument("--code-verifier", required=False, default="")

    args = parser.parse_args()

    if args.command == "start":
        do_start()
    elif args.command == "finish":
        do_finish(args.etsy_code, args.pinterest_code, args.code_verifier)
