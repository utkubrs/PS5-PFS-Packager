# EXP4 — PS4 PKG vs FFPFSC: salt okunur bağlama karşılaştırması

**Kapsam:** PS5 FW 10.01; ShadowMountPlus \`1.7-beta5fix1\`, upstream commit \`98c524890176c7b474fcb03387bec88c4a559861\`. EXP2A + EXP2B tanılama koduna ek olarak EXP4 mount gözlemcisi eklenmiştir.

## Neden?

Gerçek konsol testleri:
- AER (CUSA08005) **PKG** — kupalar çalışıyor.
- Adam's Venture Origins (CUSA03772) **FFPFSC** — oyun açılıyor ama \`Trophy registration failed\`.
- EXP3'te FFPFSC için \`npbind.dat\`, \`nptitle.dat\`, \`trophy/trophy00.trp\` başarıyla /user/appmeta/CUSA03772 altına kopyalandı fakat hata devam etti.
- Normal PKG'de daha önce \`contentLocation=0\`, \`metaDataPath=/user/appmeta/CUSA08005\`; FFPFSC'de \`contentLocation=2\`, \`metaDataPath=/user/app/CUSA03772/sce_sys\` loglandı.

**Hipotez:** Kupa servisini etkileyen asıl fark paket tabanlı PS4 başlangıç bağlamında olabilir. Bu deney, gerçek LNC/NPDRM çağrılarını doğrudan yakalamaz. Yalnızca bu hipotezi ayrıştırmak için **başlatılmış** oyunların gözlenebilir dosya sistemi yapılarını karşılaştırır.

## EXP4 yeni kayıtları

\`[PS4-TROPHY-EXP4]\` ile başlayan kayıtlar:
1. Başlatılan \`CUSA#####\` için PID, appId ve \`mode=readonly\`.
2. ShadowMountPlus \`mount.lnk\` izleme kaydının mevcut olup olmadığı (yalnızca okuma).
3. \`statfs\` ile \`/mnt/sandbox/CUSA#####_000/app0\`, \`parent/app0\`, \`/system_ex/app/CUSA#####\` bağlama türü, \`mounted-on\`, \`from\`.
4. \`sm_mount_table_snapshot\` ile başlığın kimliğini içeren en fazla 24 bağlama katmanının dosya sistemi ve kaynak yolu.
5. \`/user/appmeta/<CUSA>\`, \`/user/app/<CUSA>/sce_sys\`, \`/system_data/priv/appmeta/<CUSA>\` köklerinde 4 PS4 metadata dosyasının sadece varlık kontrolü.
6. \`snapshot=complete\` son kaydı.

**Sınırlamalar:** Yerel NPDRM anahtarları/oyun lisansları okunmaz; ShellCore içinde yeni hook kurulmaz. Gerçek \`BeginAppMount\` çağrıları/yetkilendirme kararları izlenmez, kupa hata kodunu doğrudan kaydetmez. Sonuçlardan eksik bir çağrıyı kesin olarak ileri sürmeyin.

## Test

1. Kararlı ShadowMountPlus ELF dosyanızı yedekleyin. **EXP3A'yı yüklemeyin**; EXP4, EXP2B dalından türetildi ve ekstra metadata yazmaz.
2. Mümkünse PS5'i **tamamen kapatıp yeniden açın** (önceki oturumlarda LVD/nullfs katmanları kullanımda kaldı).
3. EXP4 ELF'i var olan payload yükleyicisiyle bir defa başlatın.
4. **AER / CUSA08005 / PKG** oyununu açın; kupa ekranını kontrol edip kapatın.
5. **Adam's Venture Origins / CUSA03772 / FFPFSC** oyununu açın; kupa hatasının olup olmadığını not edip kapatın.
6. \`/data/shadowmount/debug.log\` dosyasını gönderin; en az iki oyun için \`[GAME] started\`, \`EXP2B\`, \`EXP4\` satırlarını içermeli.

**Önemli:** Önceki EXP3 uygulama meta dosyaları fiziksel olarak kalmış olabilir; EXP4 bunları temizlemez ve değiştirmez. Mevcut \`/user/appmeta\`, \`app.db\`, oyunlar ve kupaları **silmeyin**. Etkinleştirme dosyası \`exp3_CUSA03772.enable\` EXP4 için gerekli değil; EXP4 onu kullanmıyor.

Yama izolasyonu: \`experiments/shadowmountplus-ps4-trophy-compat/patches/0005-exp4-readonly-ps4-mount-snapshot.patch\`; uygulanan dosya \`src/sm_game_lifecycle.c\`. Yeni bir sistem hook'u veya yeni bağımlılık yok.

Derleme CI'nın başarılı olması yalnızca kaynak ve ELF bütünlüğünü doğrular; gerçek PS5 uyumluluğu konsol testiyle doğrulanır.
