# PS5 PFS Packager / FFPFSC - exFAT Dönüştürücü

**PS5 oyun klasörlerini ve exFAT imajlarını FFPFSC biçimine dönüştüren Windows arayüzü.**

Bu proje MkPFS 1.1.0 tabanlıdır ve PS5/PS4 platform seçimi, sıkıştırma profilleri, batch dönüştürme ve yazılabilir U: sürücüsü üzerinden exFAT/FFPFSC düzenleme iş akışını destekler.

## Ana özellikler

- PS5 oyun klasörü → `.ffpfsc`
- `.exfat` → `.ffpfsc`
- Tekli ve çoklu dönüştürme
- PS5 / PS4 platform seçici
- Profil, blok, CPU ve sıkıştırma ayarları
- Bellek hatasında otomatik güvenli tekrar
- EXFAT dosyasını yazılabilir `U:` olarak açma
- FFPFSC dosyasını temp klasörüne çıkarıp U: üzerinden düzenleme
- Değişiklikleri güvenli şekilde orijinal FFPFSC üzerine yazma
- 15 dil desteği

## Gereksinimler

- Windows 10 / Windows 11 64-bit
- Yönetici izni
- Python 3.11 ile kaynak koddan derleme
- Büyük dosyalar için NTFS temp klasörü ve tercihen SSD/NVMe

Windows 7 / 8 / 8.1 desteklenmez.

## PS4 oyun + update tek tuşla FFPFSC\n\n1. **PS4 Oyun + Update Birleştir** düğmesini açın.\n2. Ana oyun ve update için PKG veya çıkarılmış klasör seçin. Oyun adı ve CUSA kodlu çıktı adı otomatik önerilir; ikisini de elle değiştirebilirsiniz.\n3. Çıkış ve TEMP klasörünü seçip **Birleştir ve FFPFSC Oluştur** düğmesine basın.\n4. PKG çıkarma, birleşim ve FFPFSC paketleme otomatik tamamlanır.\n\nPKG'den çıkarılan geçici dosyalar gereksiz kopyalanmaz. Doğrudan seçilen orijinal klasörler değiştirilmez.\n\n## Hızlı kullanım

1. Programı çalıştırın.
2. Kaynak oyun klasörünü veya `.exfat` dosyasını seçin.
3. Çıkış ve temp klasörlerini seçin.
4. Platformu `PS5` veya `PS4` olarak belirleyin.
5. Profil ve sıkıştırma ayarlarını seçin.
6. Dönüştürmeyi başlatın.

## Kaynak koddan çalıştırma

```bat
scripts\run_source.bat
```

## Windows EXE derleme

```bat
scripts\build_windows.bat
```

## Güvenlik notu

Bu proje oyun, firmware, anahtar veya Sony'ye ait özel dosya içermez. Yalnızca homebrew içerikler ve yasal olarak sahip olduğunuz yedeklerle kullanın.

## Lisans

GPL-3.0-or-later. Ayrıntılar için `LICENSE` ve `THIRD_PARTY_NOTICES.md` dosyalarına bakın.
