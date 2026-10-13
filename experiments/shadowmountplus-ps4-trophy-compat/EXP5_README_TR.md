# EXP5 — PS4 PKG / FFPFSC başlatma evreleri (yalnızca okuma)

Hedef: PS5 FW 10.01; ShadowMountPlus 1.7-beta5fix1; EXP2A + EXP2B + EXP4 üzerine EXP5 tanılama.

## Önceki testlerden somut bulgular

- AER (CUSA08005) normal PS4 PKG: /mnt/sandbox/pfsmnt/CUSA08005-app0 yerel PFS, kupalar çalışıyor.
- Adam's Venture (CUSA03772) FFPFSC: /mnt/shadowmnt/... exFAT → /system_ex/app/CUSA03772 nullfs → sandbox app0 nullfs; kupalar Trophy registration failed.
- PKG contentLocation=0, FFPFSC contentLocation=2. Bu değeri değiştirerek bağlamayı taklit etmeyin.
- EXP3'te npbind.dat, nptitle.dat ve trophy00.trp başarıyla kopyalanmasına rağmen hata sürdü.

## EXP5 gözlem noktaları

EXP5 ek kodu ShellCore'un zaten var olan launch/sandbox hazır çağrılarının çevresinde üç evreyi loglar:
1. phase=launch-request: uygulama başlatma isteği geldiğinde
2. phase=launch-prepared: mevcut ShadowMountPlus mount_managed_title_runtime çağrısı bittiğinde
3. phase=sandbox-ready: mevcut sandbox-ready aşamasında, fakelib hazırlığı öncesi

Her evre için salt okunur gözlem:
- /mnt/sandbox/pfsmnt/<CUSA>-app0 ve -app0-nest
- /system_ex/app/<CUSA> ve /mnt/sandbox/<CUSA>_000/app0
- fs türü, bağlama kaynağı ve tam bağlama noktası (exact-mount, ancestor, unavailable)
- Mevcut mount.lnk kaydı ve /system_data/priv/appmeta/<CUSA> dosyalarının varlığı
- EXP2B app.db gözlemleri ve EXP4 oyun sonrası snapshot aynen korunmuştur.

## Sınırlar

EXP5 yeni bir NPDRM/LNC hook'u kurmaz, gerçek BeginAppMount çağrılarını yakalamaz.
Ek metadata kopyalamaz; app.db, kupa sistemi, mount listesi, kayıtlar değiştirilmez.
Bir önceki EXP3'ten diskte kalan dosyaları temizlemez. EXP3 etkinleştirme işaretleyicisi EXP5'te kullanılmaz.
Bu **kupa düzeltmesi değildir**; PS5 üzerinde henüz test edilmemiştir.

## Test

1. Çalışan kararlı ShadowMountPlus ELF'i yedekleyin. Takılı LVD varsa PS5'i tamamen kapatıp açın.
2. EXP5 ELF'i eski instance durdurulmuşken yükleyin; kararlı payloadı silmeyin.
3. AER (CUSA08005) normal PKG oyununu açıp kapatın.
4. Adam's Venture (CUSA03772) FFPFSC oyununu açıp kapatın.
5. /data/shadowmount/debug.log dosyasını ve iki oyun için kupa sonucunu gönderin.

Logda PS4-TROPHY-EXP5 phase=launch-request, launch-prepared ve sandbox-ready
ve PS4-TROPHY-EXP4 game-start kayıtlarını arayın.
Yeni gözlemden sonra yerel PFS'nin hangi aşamada oluştuğunu karşılaştırabiliriz.
İki oyunun gerçek kupa servis çağrılarını bu sürüm doğrudan kaydetmeyecektir.