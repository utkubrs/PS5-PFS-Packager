# EXP6 — PS4 Trophy Namespace / Sandboxed Metadata Diagnostics

**FW:** PS5 10.01; **Base:** ShadowMountPlus 1.7-beta5fix1 + EXP2A + EXP2B + EXP4 + EXP5.

## Ne bulduk?

- AER CUSA08005 normal PKG: native /mnt/sandbox/pfsmnt/CUSA08005-app0 PFS mount; kupalar çalışıyor.
- Adam's Venture Origins CUSA03772 FFPFSC: /mnt/shadowmnt → /system_ex/app (nullfs) → sandbox app0; Trophy registration failed.
- EXP5'e göre native PFS montajı AER için launch-prepared sonrasında, sandbox-ready öncesinde oluşuyor; FFPFSC yerel pfsmnt oluşturmuyor.
- AER sistem özel uygulama metadata dizininde param.sfo, npbind.dat ve nptitle.dat mevcut. Adam's Venture aynı dizinde yalnızca nptitle.dat gösterdi.
- EXP3'ün /user/appmeta altına kopyaladığı dosyalar kupa kaydını düzeltmedi.

## Bu deneyin kapsamı

EXP6, mevcut ShellCore sandbox-ready gözlem anında, yalnızca CUSA##### başlıkları için şu dizinlerin dosya meta verilerini lstat(2) kullanarak kaydeder:

1. /mnt/sandbox/CUSA#####_000/app0/sce_sys (oyun sandbox'ının gördüğü görüntü)
2. /system_ex/app/CUSA#####/sce_sys (ShadowMount üzerinden gerçek sunulan görüntü)
3. /user/app/CUSA#####/sce_sys (uygulamanın klasik dosya yolu)
4. /user/appmeta/CUSA##### (uygulama metadata)
5. /system_data/priv/appmeta/CUSA##### (sistem özel metadata)

Her birinde kök klasör ve şu dört dosya incelenir: param.sfo, npbind.dat, nptitle.dat, trophy/trophy00.trp.
Log alanları: `kind=regular|directory|symlink|other|unavailable`, dosya boyutu, mode ve errno.
Dosyanın içeriği okunmaz, hash veya gizli NPDRM bilgisi dışa çıkarılmaz.

Yeni log öneki: `[PS4-TROPHY-EXP6]`.

**Not:** Sony'nin PS4 libSceNpTrophy API'sindeki sceNpTrophyRegisterContext sembolü açık kaynak PS4 başlıklarında belgelenmiştir; ancak PS5 FW 10.01 ShadowMount sürecinden güvenle çağrılabildiği veya bu şekilde oyun kupa hatasının okunabildiği doğrulanmadı. Bu deneyde söz konusu API ÇAĞRILMAZ, hook kurulmaz.

## Test sırası

1. Kararlı ShadowMountPlus ELF yedeğini koru. Öneri: önce PS5'i tamamen kapatıp aç.
2. EXP6 ELF dosyasını payload yükleyicisiyle başlat; aynı anda ikinci bir ShadowMountPlus instance'ı bırakma.
3. AER CUSA08005 normal PKG oyununu aç, 10–20 saniye bekle, kapat.
4. Adam's Venture Origins CUSA03772 FFPFSC oyununu aç, kupa mesajını gözle, kapat.
5. /data/shadowmount/debug.log dosyasını gönder. Her oyunda EXP5 phase kayıtları, EXP6 `snapshot=complete roots=5` ve EXP4 game-start logları beklenir.

EXP6 kupa düzeltmesi DEĞİLDİR; sistem dosyalarını değiştirmeyi amaçlamaz.
Kupa dosyalarını, app.db ve sistem metadata klasörlerini silme. Önceki EXP3 ile taşınmış dosyaları EXP6 ne temizler ne değiştirir.
EXP6'nın bulguları yalnızca dosyaya erişilebilirlik/başlatma durumuna ilişkindir; tek başına NPDRM yetkilendirmesinin başarısızlığını veya kupa servis hatasının kök nedenini kanıtlamaz.

## Kaynak notları

- OpenOrbis PS4: https://github.com/OpenOrbis/OpenOrbis-PS4-Toolchain/blob/master/include/orbis/NpTrophy.h
- ShadowMountPlus: https://github.com/drakmor/ShadowMountPlus
- EXP6 dalı: https://github.com/utkubrs/PS5-PFS-Packager/tree/experimental/ps4-trophy-exp6-runtime-metadata-probe