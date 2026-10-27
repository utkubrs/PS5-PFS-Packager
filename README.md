# PS5 PFS Packager v1.0

**Windows 10/11 (64 bit)** için PS4/PS5 oyun klasörleri, exFAT ve FFPFSC dosyalarıyla çalışan grafik arayüz. MkPFS 1.1.0 tabanlıdır. Kullanıcıya sunulan Windows sürümü **tek EXE** olarak derlenir; Python kurulumu gerekmez.

**İndir:** [En son Windows ZIP paketini indir](https://github.com/utkubrs/PS5-PFS-Packager/releases/latest)

## Kurulum ve çalışma

1. **PS5-PFS-Packager-v1.0-Windows-x64.zip** dosyasını indirip ayıkla.
2. ZIP içindeki **PS5 PFS Packager** klasörünü bilgisayarında istediğin bir yere taşı.
3. **PS5-PFS-Packager.exe** dosyasını çalıştır. Yönetici izni, sanal sürücü bağlama işlemlerinde gerekebilir.
4. Kaynak klasör veya dosyayı, çıktı konumunu ve TEMP klasörünü seçerek dönüştürmeyi başlat.

Kurulum dosyası değil, taşınabilir (portable) pakettir. EXE'nin yanında uygulama ayarlarını saklayan `ps5-pfs-config.ini` dosyası otomatik oluşturulabilir; kişisel ayarlarını korumak istiyorsan bu dosyayı sakla.

## Özellikler

- PS5 oyun klasörü veya `.exfat` → `.ffpfsc` dönüştürme
- PS4 temel oyun + güncelleme birleştirme, güncellemesiz PS4 oyun desteği, sıralı işlem kuyruğu
- **Edit PARAM.SFO:** Mevcut `TITLE` ve `TITLE_XX` metin alanlarını ayrı ayrı veya toplu değiştirme; kaydetmeden önce `.bak` yedeği
- İşlemci çekirdeği, sıkıştırma profili, blok ve TEMP ayarları
- Çıktı doğrulama ve hata günlükleri; isteğe bağlı kaynak silme (yalnızca açıkça seçildiğinde)
- exFAT/FFPFSC açma, düzenleme ve yeniden paketleme
- 15 arayüz dili (Türkçe, English, Français, Español, Italiano, Ελληνικά, 한국어, 日本語, Deutsch, Português, Русский, 中文, العربية, Nederlands, Polski)

**Dağıtım yapısı:**

```text
PS5-PFS-Packager-v1.0-Windows-x64.zip
└── PS5 PFS Packager/
    ├── PS5-PFS-Packager.exe
    ├── README.md
    └── LICENSE
```

Python bileşenleri, MkPFS ve PS4 PKG çıkarıcı EXE içine dahil edilir. Farklı `.dll`/`.pyd` dosyalarını ayrıca taşıman gerekmez. Ayrı `fakelib` dosyaları dağıtılmaz; bunlar yalnızca kullanıcı tarafından sağlanabilir.

**Önemli:** Oyun ve güncelleme klasörlerinin yedeğini sakla. İşlemleri yasal olarak sahip olduğun içeriklerde veya homebrew üzerinde yap. PS5/PS4 firmware, oyun, lisans anahtarı veya Sony'ye ait tescilli dosyalar dağıtıma eklenmez. Konsolda çalışma, Windows derleme testinden ayrı olarak doğrulanmalıdır.

## English / Quick start

Download the [latest Windows x64 release](https://github.com/utkubrs/PS5-PFS-Packager/releases/latest), unzip it, open the **PS5 PFS Packager** folder, and launch **PS5-PFS-Packager.exe**. No Python installation is required. The archive contains exactly one Markdown file (this README), the portable EXE, and the GPL license. Supports PS5 folder/exFAT conversion, PS4 base/update merging and FIFO queues, editable existing PARAM.SFO title fields with backups, 15 UI languages, and MkPFS 1.1.0. An external `fakelib` is optional and not distributed.

## Derleme / Build

Sources are in `src/`, tests in `tests/`, and the Windows build entrypoint is `scripts/build_windows.bat`. GitHub Actions runs Windows tests and publishes the portable ZIP on `main`. The project is GPL-3.0 licensed: see `LICENSE`. Dependency acknowledgments: Python, Nuitka, Tkinter, MkPFS, psutil, cryptography and the pinned open-source `pkgextract` tool.

> Note: The release is unsigned; use the published `SHA256SUMS.txt` for verification. The executable extracts bundled runtime components into a temporary directory while running, but the distribution ZIP does not contain loose runtime DLL/PYD files.
