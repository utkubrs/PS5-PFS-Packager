# EXP7 — PS4 kupa kayıt hata kodu için pasif SDK logu taraması

**Platform:** PS5 FW 10.01, ShadowMountPlus 1.7-beta5fix1.
**Zincir:** EXP2A + EXP2B + EXP4 + EXP5 + EXP6 + EXP7.

## Önceki kanıt

- Normal PS4 PKG: AER, CUSA08005. Kupalar çalışıyor; sandbox app0 kaynağı yerel PFS.
- PS4 FFPFSC: Adam's Venture Origins, CUSA03772. Oyun açılıyor ama Trophy registration failed.
- EXP3 metadata dosyalarını kopyaladı, hata düzelmedi.
- EXP5, native pfsmnt bağlamasının PKG'de launch-prepared ile sandbox-ready arasında gerçekleştiğini; FFPFSC'de gerçekleşmediğini gösterdi.
- EXP6, FFPFSC'nin sce_sys dosyalarını oyun dizininde görebildiğini ve özel sistem metadata dizininde param.sfo / npbind.dat bulunmadığını kanıtladı.

## EXP7 ne yapar?

Mevcut ShadowMountPlus MDBG bileşeni, oyun başladığında yaklaşık 60 saniye boyunca sceKernelDebugGetSdkLogText üzerinden SDK loglarını izler. Normalde yalnızca fatal signal / rtld hata satırlarını işler.

EXP7 buna yeni bir salt-okunur filtre ekler:
- Mevcut MDBG akışında yalnızca CUSA##### oyunu izlenirken, büyük/küçük harf duyarsız 'trophy' sözcüğü içeren yeni log satırlarını sayar.
- Aynı satırda 0x ile başlayan TAM SEKİZ haneli hex değer varsa bunu 'candidate=0x...' olarak kaydeder.
- En fazla ilk 12 aday için ayrıntılı işaret satırı yazar. İzleyici kapanırken toplam satır ve kod adedi özetini basar.
- Hiç kupa mesajı yoksa 'matched=0 candidate-hex-count=0' açıkça gösterilir.
- İşlenen ham log satırları, anahtarlar, kişisel yollar ve kupa dosyalarının içerikleri asla yazdırılmaz.

Her kayıt açıkça 'source=shared-sdk-log', 'attribution=unverified', 'api-return=unknown' etiketlerini taşır. SDK günlüğü birden fazla sürece ait olabilir. Buradan çıkan bir hex sayı gerçek sceNpTrophyRegisterContext dönüş değeri olarak SUNULMAMALIDIR. Kaynak koduna yeni bir trophy API çağrısı, oyun içi hook veya shellcore patch'i EKLENMEMİŞTİR.

## Test

1. Mevcut kararlı ELF'yi yedekle. Mümkünse PS5'i tamamen kapatıp yeniden aç.
2. EXP7 ELF dosyasını yükle. Kstuff 1.13 Test4 ve diğer ayarlar değişmeden kalsın.
3. Normal PS4 PKG AER / CUSA08005 oyununu aç; 10-20 saniye bekle; kapat.
4. FFPFSC Adam's Venture / CUSA03772 oyununu aç. 'Trophy registration failed' mesajını gözle; 10-20 saniye bekle ve kapat.
5. /data/shadowmount/debug.log dosyasını paylaş.

Aranacak satırlar:

    [PS4-TROPHY-EXP7] title=CUSA08005 ...
    [PS4-TROPHY-EXP7] title=CUSA03772 ...
    [PS4-TROPHY-EXP7] title=CUSA03772 ... summary=complete matched=... candidate-hex-count=... direct-trophy-api-captured=0

EXP2B/EXP4/EXP5/EXP6 gözlemleri de aynen devam eder.

## Uyarılar

Bu bir **kupa düzeltmesi değildir**; konsolda test edilmemiştir.
SDK loglarında trophy kaydı yoksa EXP7 gerçek API dönüş kodunu yakalayamaz. Bu durumda ek kernel/oyun içi hook denemeden önce kaynakların ve riski düşük yöntemlerin gözden geçirilmesi gerekir.
app.db, kupa verileri, sistem metadata dizinleri ve mevcut mountlar EXP7 tarafından değiştirilmez.
EXP3'ten kalan dosyaları, kupaları veya oyun kayıtlarını silmeyin; kararlı sürüme geri dönmek için yalnızca kararlı ELF'yi yükleyin.