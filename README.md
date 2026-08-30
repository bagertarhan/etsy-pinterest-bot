# Etsy → Pinterest Otomatik Pin Botu

GorgeousWallClock Etsy mağazasındaki ürünleri her gün otomatik olarak
Pinterest'e 2-3 pin şeklinde paylaşır. Görseller Pinterest için 2:3 dikey
orana otomatik kırpılır.

## Kurulum sırası

1. Bu dosyaları GitHub reposuna yükleyin (klasör yapısını koruyarak).
2. **Settings → Secrets and variables → Actions → Secrets** kısmına şunları ekleyin:
   - `ETSY_KEYSTRING`
   - `PINTEREST_APP_ID`
   - `PINTEREST_APP_SECRET`
3. **Settings → Secrets and variables → Actions → Variables** kısmına ekleyin:
   - `PINTEREST_BOARD_NAME` → pin atılacak panonun tam adı
4. **Actions** sekmesinden `OAuth Setup` workflow'unu `step: start` ile çalıştırın,
   çıkan linkleri tarayıcıda açıp izin verin, `code` değerlerini callback
   sayfasından kopyalayın.
5. Aynı workflow'u `step: finish` ile, kopyaladığınız `etsy_code`,
   `pinterest_code`, `code_verifier` değerlerini girerek tekrar çalıştırın.
6. Çıkan `ETSY_REFRESH_TOKEN` ve `PINTEREST_REFRESH_TOKEN` değerlerini
   Secrets kısmına ekleyin.
7. `Daily Etsy to Pinterest Pinning` workflow'unu bir kere elle çalıştırıp
   (workflow_dispatch) test edin. Sorun yoksa her gün otomatik çalışacaktır.
