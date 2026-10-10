# GitHub'a yükleme rehberi

Bu paket GitHub'a yüklenmeye hazırdır.

## Önerilen proje bilgileri

**Repository adı**

```text
PS5-PFS-Packager
```

**Görünen başlık**

```text
PS5 PFS Packager / FFPFSC - exFAT Converter | 15 Languages
```

**Description**

```text
Windows GUI for converting PS5 game folders and exFAT images to FFPFSC, with writable image editing, batch processing, compression profiles and 15-language support.
```

**Topics**

```text
ps5
playstation-5
ffpfsc
ffpfs
exfat
pfs
mkpfs
ps5-homebrew
ps5-tools
windows
python
tkinter
converter
disk-image
virtual-drive
homebrew
```

## Çok önemli güvenlik uyarısı

GitHub kullanıcı adı ve şifrenizi kimseye göndermeyin. Sohbet içinde parola veya erişim anahtarı paylaşmayın.

Yükleme betiği GitHub CLI'nin tarayıcı girişini kullanır:

```text
gh auth login --web
```

Şifreniz programa veya projeye yazılmaz.

## En kolay yöntem

### 1. Gerekli programları kurun

- Git for Windows
- GitHub CLI

Kurulumdan sonra yeni bir Komut İstemi açın.

Kontrol:

```bat
git --version
gh --version
```

### 2. Proje ZIP'ini çıkarın

Örnek:

```text
D:\GitHub\PS5-PFS-Packager
```

### 3. Otomatik yayınlama betiğini çalıştırın

```bat
scripts\publish_to_github.bat
```

Betik:

1. GitHub CLI oturumunu kontrol eder.
2. Gerekirse tarayıcıda GitHub oturumu açtırır.
3. Yerel Git deposunu oluşturur.
4. İlk commit'i atar.
5. Public GitHub repository oluşturur.
6. Kaynak kodu `main` dalına gönderir.
7. Description ve topics alanlarını ayarlar.
8. `v2.13.0` Release oluşturur.
9. Windows ZIP ve SHA-256 dosyasını Release'e yükler.

## Manuel web yöntemi

### 1. Yeni repository oluşturun

GitHub'da sağ üstteki `+` düğmesine basın ve **New repository** seçin.

- Owner: hesabınız
- Repository name: `PS5-PFS-Packager`
- Visibility: Public
- Add README: işaretlemeyin
- Add .gitignore: seçmeyin
- Choose a license: seçmeyin

Bu dosyalar pakette zaten var.

### 2. Kaynak kodu gönderin

Proje klasöründe terminal açın:

```bat
git init -b main
git add .
git commit -m "Initial public release v2.13.0"
git remote add origin https://github.com/KULLANICI_ADINIZ/PS5-PFS-Packager.git
git push -u origin main
```

### 3. Description ve topics ekleyin

Repository ana sayfasındaki **About** bölümünün yanındaki dişli simgesine basın.

Yukarıdaki description ve topics listesini ekleyin.

### 4. Social preview ekleyin

Repository:

```text
Settings → General → Social preview
```

Şu dosyayı yükleyin:

```text
assets/social-preview.png
```

### 5. Release oluşturun

Repository ana sayfasında:

```text
Releases → Draft a new release
```

Alanlar:

- Tag: `v2.13.0`
- Release title: `PS5 PFS Packager v2.13.0`
- Description: `RELEASE_NOTES_v2.13.0.md`
- Asset: `release/PS5-PFS-Packager-v2.13.0-Windows-x64.zip`
- Asset: `release/SHA256SUMS.txt`

Son olarak **Publish release** düğmesine basın.

## SEO kontrol listesi

- Repository adı kısa ve anahtar kelime içeriyor.
- README'nin ilk paragrafında PS5, FFPFSC, FFPFS, exFAT, MkPFS ve Windows geçiyor.
- 15 dil özelliği başlıkta ve README'de bulunuyor.
- İngilizce ana README ve Türkçe ayrı README var.
- Topics alanı dolduruluyor.
- Release başlığı sürüm numarası içeriyor.
- Social preview hazırlanmış durumda.
- Screenshots klasörü mevcut.
- Issue şablonları ve katkı rehberi var.
- GPL lisansı ve üçüncü taraf bildirimleri var.

## Sonraki sürümü yayınlama

1. Kod ve sürüm numaralarını güncelleyin.
2. `docs/RELEASE_CHECKLIST.md` listesini tamamlayın.
3. Yeni tag oluşturun:

```bat
git tag v2.13.0
git push origin v2.13.0
```

4. Yeni Windows ZIP'i Release'e yükleyin.
