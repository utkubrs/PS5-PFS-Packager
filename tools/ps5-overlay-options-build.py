#!/usr/bin/env python3
"""Build patch for PS5 KUS v1.0.19: Turkish interface and OPTIONS long-press HUD toggle."""
from pathlib import Path
import re

root = Path("upstream")
main_file = root / "payload/main.cpp"
loader_file = root / "loader/main.c"
web_file = root / "payload/web_server.cpp"

def replace_one(source, original, replacement, context):
    count = source.count(original)
    if count != 1:
        raise RuntimeError(f"{context}: expected 1 occurrence, found {count}: {original[:70]!r}")
    return source.replace(original, replacement, 1)

main = main_file.read_text(encoding="utf-8")
hook = r'''
// No controller hooks. Web UI is the only source of visibility toggles.
volatile bool g_overlay_visible = true;
'''

main = replace_one(main, "bool has_hv_bypass = false;", "bool has_hv_bypass = false;\n" + hook, "insert controller poll")
build_call = "build_hud(Root_Domain, pui_img, widget_class, panel_class, label_class, root_widget, &hud_ctx);"
if main.count(build_call) != 2:
    raise RuntimeError("Expected exactly two HUD build call sites in v1.0.19")
main = main.replace(build_call, "if (g_overlay_visible) " + build_call)
main_file.write_text(main, encoding="utf-8")

loader = loader_file.read_text(encoding="utf-8")
for old, new in [
    ("PS5 Overlay Active! Web Settings: port 8585", "PS5 FPS aktif! Web ayarlari: 8585 portu"),
    ("Overlay Error: SceShellUI not found!", "Hata: SceShellUI bulunamadi!"),
    ("Overlay Error: Injection failed! Check /data/overlay/overlay.log",
     "Hata: Yukleme basarisiz! /data/overlay/overlay.log"),
]:
    loader = replace_one(loader, old, new, "loader notification")
loader_file.write_text(loader, encoding="utf-8")

web = web_file.read_text(encoding="utf-8")
translations = r"""
PS5 Telemetry Overlay|PS5 Telemetri Paneli
Панель управления и настройка отображения оверлея|Katman yönetimi ve görünüm ayarları
Предпросмотр на экране PS5|PS5 ekran önizlemesi
Масштаб 16:9|Ölçek 16:9
Данные телеметрии и их порядок|Telemetri verileri ve sıralama
Используйте ▲ / ▼ для сортировки|Sıralamak için ▲ / ▼ kullanın
Расположение на экране|Ekran konumu
По вертикали|Dikey konum
Сверху|Üstte
Снизу|Altta
По горизонтали|Yatay konum
Слева|Solda
По центру|Ortada
Справа|Sağda
Смещение по X|X kaydırma
Смещение по Y|Y kaydırma
Внешний вид и размер|Görünüm ve boyut
Размер шрифта|Yazı boyutu
Высота плашки|Çubuk yüksekliği
Прозрачность фона|Arka plan saydamlığı
Цвет фоновой плашки|Arka plan rengi
Завершение и выгрузка оверлея|Katmanı kapat ve kaldır
Полностью выгружает модуль оверлея из памяти SceShellUI, удаляет HUD с экрана и освобождает сетевой порт. После выгрузки можно запустить новую версию ELF через Netcat без перезагрузки консоли.|Katmanı SceShellUI belleğinden kaldırır, göstergeleri kapatır ve ağ portunu serbest bırakır. Ardından konsolu yeniden başlatmadan Netcat ile yeni ELF yüklenebilir.
Выгрузить оверлей из SceShellUI|Katmanı SceShellUI belleğinden kaldır
Сохранить и применить на PS5|Kaydet ve PS5 sistemine uygula
По умолчанию|Varsayılana dön
Настройки успешно применены!|Ayarlar uygulandı!
Частота кадров в секунду (Framerate)|Saniyedeki kare sayısı (FPS)
Температура процессора (Zen 2 Tctl)|İşlemci sıcaklığı (Zen 2 Tctl)
Общая загрузка процессора (CPU %)|Toplam işlemci kullanımı (CPU %)
Частота ядер процессора (Zen 2 CPU Clock)|İşlemci çekirdek hızı (Zen 2 CPU Clock)
Температура видеочипа (SoC / GPU)|Grafik yongası sıcaklığı (SoC / GPU)
Частота видеоядра (RDNA 2 GFXCLK)|Grafik çekirdeği hızı (RDNA 2 GFXCLK)
Использование системной памяти|Sistem belleği kullanımı
Использование видеопамяти (VRAM)|Video belleği kullanımı (VRAM)
Температура накопителя M.2 NVMe SSD|M.2 NVMe SSD sıcaklığı
Скорость вращения кулера консоли|Konsol fan hızı
Энергопотребление SoC APU в Ваттах|SoC APU güç tüketimi (Watt)
Локальный IP-адрес консоли|Konsolun yerel IP adresi
Сохранение...|Kaydediliyor...
Настройки успешно применены на PS5!|Ayarlar PS5 sistemine uygulandı!
Ошибка сохранения: |Kaydetme hatası:
Ошибка сети при сохранении|Kaydetme sırasında ağ hatası
Сбросить все настройки оверлея по умолчанию?|Tüm ayarlar sıfırlansın mı?
Настройки сброшены по умолчанию!|Ayarlar sıfırlandı!
Сброшено по умолчанию|Varsayılan ayarlar yüklendi
Вы уверены, что хотите завершить и выгрузить оверлей из памяти SceShellUI?|Katmanı SceShellUI belleğinden kaldırmak istiyor musunuz?
HUD исчезнет с экрана, а сетевой порт освободится для загрузки нового ELF.|Gösterge kapanır ve ağ portu yeni ELF yüklemek için serbest kalır.
Выгрузка...|Kaldırılıyor...
Оверлей успешно выгружен!|Katman başarıyla kaldırıldı!
Оверлей успешно выгружен|Katman başarıyla kaldırıldı
Модуль оверлея завершил работу в SceShellUI. Память очищена, порт освобожден.|Katman SceShellUI üzerinden kapatıldı. Bellek ve port serbest bırakıldı.
Теперь можно отправить новую версию ELF через Netcat / Payload Sender без перезагрузки консоли.|Konsolu yeniden başlatmadan Netcat / Payload Sender ile yeni ELF gönderebilirsiniz.
Запрос на выгрузку отправлен!|Kaldırma isteği gönderildi!
""".strip()
for line in sorted(translations.splitlines(), key=len, reverse=True):
    original, target = line.split("|", 1)
    if original not in web:
        raise RuntimeError("Web translation phrase missing: " + original)
    web = web.replace(original, target)
web = replace_one(web, 'lang="ru"', 'lang="tr"', "Turkish html language")
if re.search(r"[\u0400-\u04ff]", web):
    found = [line for line in web.splitlines() if re.search(r"[\u0400-\u04ff]", line)]
    raise RuntimeError("Remaining Cyrillic: " + repr(found[:3]))
web = replace_one(web, "Katman yönetimi ve görünüm ayarları",
                  "Katman yönetimi ve görünüm ayarları",
                  "hotkey instructions")

quickPanel = r'''
  <div class="card" id="quickToggleCard">
    <div class="card-header"><div class="card-title">🎮 FPS Göster / Gizle</div></div>
    <button id="btnWebToggle" type="button" onclick="toggleHudWeb()"
      style="display:block;width:100%;background:#0070d1;color:white;padding:13px;border:0;border-radius:10px;font-weight:bold;font-size:15px;">
      🙈 Göstergeyi gizle
    </button>
    <p style="color:#8b9bb4;font-size:13px;margin-top:12px;">
      FPS ve sıcaklık bilgilerini buradan açıp kapatabilirsiniz. Ölçümler ve ayarlar korunur.
    </p>
  </div>
'''

web = replace_one(web, '  <!-- Unload / Exit Overlay Card -->',
                  quickPanel + '  <!-- Unload / Exit Overlay Card -->', 'add quick toggle panel')
quickJS = r'''
async function refreshHudState() {
  try {
    const res = await fetch('/api/hud-state', {cache:'no-store'});
    if (!res.ok) throw new Error('HTTP '+res.status);
    const data = await res.json();
    const btn = document.getElementById('btnWebToggle');
    if (btn) btn.textContent = data.visible ? '🙈 Göstergeyi gizle' : '👁️ Göstergeyi aç';
  } catch(err) {
    console.log('Gösterge durumu okunamadı', err);
  }
}
async function toggleHudWeb() {
  const btn = document.getElementById('btnWebToggle');
  if (btn) btn.disabled = true;
  try {
    const res = await fetch('/api/toggle-hud', {method:'POST'});
    if (!res.ok) throw new Error('HTTP '+res.status);
    await refreshHudState();
  } catch(err) {
    showToast('Gösterge değiştirilemedi!');
  } finally {
    if (btn) btn.disabled = false;
  }
}
'''

web = replace_one(web, "window.addEventListener('DOMContentLoaded', () => {\n  bindControls();\n  loadConfigFromServer();",
                  quickJS + "window.addEventListener('DOMContentLoaded', () => {\n  bindControls();\n  loadConfigFromServer();\n  refreshHudState();\n  setInterval(refreshHudState, 1500);",
                  "add client status polling")
web = replace_one(web, '#include "web_server.hpp"',
                  '#include "web_server.hpp"\nextern volatile bool g_overlay_visible;',
                  'visibility declaration')

api = r'''
    if (strncmp(req, "GET /api/hud-state", 18) == 0) {
        const char *json = g_overlay_visible ? "{\"visible\":true}" : "{\"visible\":false}";
        char hdr[256];
        int n = snprintf(hdr, sizeof(hdr),
          "HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\n"
          "Cache-Control: no-store\r\nContent-Length: %zu\r\nConnection: close\r\n\r\n",
          strlen(json));
        socket_send_all(client_fd, hdr, n);
        socket_send_all(client_fd, json, strlen(json));
        return;
    }
    if (strncmp(req, "POST /api/toggle-hud", 20) == 0) {
        g_overlay_visible = !g_overlay_visible;
        g_config_changed = true;
        const char resp[] = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"status\":\"ok\"}";
        socket_send_all(client_fd, resp, sizeof(resp)-1);
        return;
    }
'''

web = replace_one(web, '    if (strncmp(req, "GET /api/config", 15) == 0) {',api+'    if (strncmp(req, "GET /api/config", 15) == 0) {','hotkey APIs')
web_file.write_text(web, encoding="utf-8")
print("OK: Turkish UI with web-only HUD toggle (no controller code).")
web_file.write_text(web, encoding="utf-8")

