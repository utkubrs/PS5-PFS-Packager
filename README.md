# PS5 PFS Packager v1.0

**Windows 10/11 (64 bit)** için PS4/PS5 oyun klasörleri, exFAT ve FFPFSC dosyalarıyla çalışan grafik arayüz. MkPFS 1.1.0 tabanlıdır. Kullanıcıya sunulan Windows sürümü **tek EXE** olarak derlenir; Python kurulumu gerekmez.

**İndir:** [v1.0 tek EXE dosyasını indir](https://github.com/utkubrs/PS5-PFS-Packager/releases/download/v1.0/PS5-PFS-Packager-v1.0-Windows-x64.exe)

## Kurulum ve çalışma

1. **PS5-PFS-Packager-v1.0-Windows-x64.exe** dosyasını indir.
2. İstersen bilgisayarında **PS5 PFS Packager** klasörüne taşı.
3. İndirdiğin EXE dosyasını çalıştır. Yönetici izni, sanal sürücü bağlama işlemlerinde gerekebilir.
4. Kaynak klasör veya dosyayı, çıktı konumunu ve TEMP klasörünü seçerek dönüştürmeyi başlat.

Kurulum dosyası değil, taşınabilir (portable) pakettir. EXE'nin yanında uygulama ayarlarını saklayan `ps5-pfs-config.ini` dosyası otomatik oluşturulabilir; kişisel ayarlarını korumak istiyorsan bu dosyayı sakla.

## Özellikler

- PS5 oyun klasörü veya `.exfat` → `.ffpfsc` dönüştürme
- PS4 temel oyun + güncelleme birleştirme, güncellemesiz PS4 oyun desteği, sıralı işlem kuyruğu; **özel oyun adı girildiğinde tüm mevcut `TITLE` ve `TITLE_XX` alanlarına uygulanır**
- **Edit PARAM.SFO:** Mevcut `TITLE` ve `TITLE_XX` metin alanlarını ayrı ayrı veya toplu değiştirme; kaydetmeden önce `.bak` yedeği
- İşlemci çekirdeği, sıkıştırma profili, blok ve TEMP ayarları
- Çıktı doğrulama ve hata günlükleri; isteğe bağlı kaynak silme (yalnızca açıkça seçildiğinde)
- exFAT/FFPFSC açma, düzenleme ve yeniden paketleme
- 15 arayüz dili (Türkçe, English, Français, Español, Italiano, Ελληνικά, 한국어, 日本語, Deutsch, Português, Русский, 中文, العربية, Nederlands, Polski)

**Dağıtım:** Tek `PS5-PFS-Packager-v1.0-Windows-x64.exe` dosyası. ZIP veya ayrı DLL/PYD dosyası indirmek gerekmez. README ve GPL lisansı GitHub kaynak deposunda mevcuttur.

Python bileşenleri, MkPFS ve PS4 PKG çıkarıcı EXE içine dahil edilir. Farklı `.dll`/`.pyd` dosyalarını ayrıca taşıman gerekmez. Ayrı `fakelib` dosyaları dağıtılmaz; bunlar yalnızca kullanıcı tarafından sağlanabilir.

**Önemli:** Oyun ve güncelleme klasörlerinin yedeğini sakla. İşlemleri yasal olarak sahip olduğun içeriklerde veya homebrew üzerinde yap. PS5/PS4 firmware, oyun, lisans anahtarı veya Sony'ye ait tescilli dosyalar dağıtıma eklenmez. Konsolda çalışma, Windows derleme testinden ayrı olarak doğrulanmalıdır.

## English / Quick start

Download the [single Windows x64 EXE](https://github.com/utkubrs/PS5-PFS-Packager/releases/download/v1.0/PS5-PFS-Packager-v1.0-Windows-x64.exe) and run it. No ZIP extraction or Python installation is required. The repository contains the README and GPL license. Supports PS5 folder/exFAT conversion, PS4 base/update merging and FIFO queues, editable existing PARAM.SFO title fields with backups, 15 UI languages, and MkPFS 1.1.0. An external `fakelib` is optional and not distributed.

## Derleme / Build

Sources are in `src/`, tests in `tests/`, and the Windows build entrypoint is `scripts/build_windows.bat`. GitHub Actions runs Windows tests and publishes the standalone EXE on `main`. The project is GPL-3.0 licensed: see `LICENSE`. Dependency acknowledgments: Python, Nuitka, Tkinter, MkPFS, psutil, cryptography and the pinned open-source `pkgextract` tool.

> Note: The release is unsigned; use the published `SHA256SUMS.txt` for verification. The executable extracts bundled runtime components into a temporary directory while running, but the distributed EXE has no loose runtime DLL/PYD files.


## Third-party notices / Üçüncü taraf lisansları

- **MkPFS 1.1.0** (PSBrew/MkPFS): GPL-3.0, PFS/FFPFSC/exFAT işleme
- **Python + Tkinter**: Python Software Foundation License
- **Nuitka**: Apache-2.0
- **psutil**: BSD-3-Clause
- **cryptography**: Apache-2.0 / BSD

Yukarıdaki projelerin güncel tam lisans metinleri için kendi kaynak depolarına bakınız. **PlayStation** ve **PS5**, Sony Interactive Entertainment markalarıdır. Proje Sony ile ilişkili veya Sony tarafından desteklenen bir ürün değildir. Bu yazılım yalnızca homebrew, araştırma ve yasal olarak sahip olunan içeriklerin yedeklenmesi için tasarlanmıştır. Hukuki sorumluluk kullanıcıya aittir.
