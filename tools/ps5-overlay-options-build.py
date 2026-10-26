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
// OPTIONS button = 0x00000008 in ScePadData on PS5.
// Only reads input; does not intercept or modify the game's controller input.
// Two seconds at 100 ms polling, triggered once per continuous hold.
static bool g_options_overlay_visible = true;

static bool poll_options_long_press(void) {
    typedef int (*pad_open_fn)(int, int, int, const void*);
    typedef int (*pad_get_handle_fn)(int, int, int);
    typedef int (*pad_read_fn)(int, void*);
    typedef int (*user_fg_fn)(int*);

    static pad_open_fn p_pad_open = nullptr;
    static pad_get_handle_fn p_pad_get_handle = nullptr;
    static pad_read_fn p_pad_read = nullptr;
    static user_fg_fn p_user_fg = nullptr;
    static int pad_handle = -1;
    static unsigned int tick_retry = 0;
    static unsigned int held_ticks = 0;
    static bool fired_this_hold = false;
    static bool init_logged = false;

    if (!p_pad_read || !p_user_fg) {
        if (++tick_retry < 50) return false;
        tick_retry = 0;
        uintptr_t pad_base = 0, user_base = 0;
        int pad_mod = get_module_handle(getpid(), "libScePad.sprx", &pad_base);
        int user_mod = get_module_handle(getpid(), "libSceUserService.sprx", &user_base);
        if (pad_mod > 0 && user_mod > 0) {
            p_pad_open = (pad_open_fn)resolve_symbol(pad_mod, pad_base, "scePadOpen");
            p_pad_get_handle = (pad_get_handle_fn)resolve_symbol(pad_mod, pad_base, "scePadGetHandle");
            p_pad_read = (pad_read_fn)resolve_symbol(pad_mod, pad_base, "scePadReadState");
            p_user_fg = (user_fg_fn)resolve_symbol(user_mod, user_base, "sceUserServiceGetForegroundUser");
        }
        if (!p_pad_read || !p_user_fg || (!p_pad_open && !p_pad_get_handle)) {
            p_pad_read = nullptr;
            p_user_fg = nullptr;
            if (!init_logged) {
                LOG_WARN("OPTIONS shortcut unavailable: Pad or UserService symbols not resolved");
                init_logged = true;
            }
            return false;
        }
        LOG_INFO("OPTIONS long-press shortcut symbols available");
    }

    if (pad_handle < 0) {
        if (++tick_retry < 10) return false;
        tick_retry = 0;
        int user_id = -1;
        if (p_user_fg(&user_id) < 0 || user_id == -1) return false;
        int h = p_pad_open ? p_pad_open(user_id, 0, 0, nullptr) : -1;
        if (h < 0 && p_pad_get_handle) h = p_pad_get_handle(user_id, 0, 0);
        if (h < 0) {
            if (!init_logged) {
                LOG_WARN("OPTIONS shortcut pad handle unavailable: 0x%x", h);
                init_logged = true;
            }
            return false;
        }
        pad_handle = h;
        LOG_INFO("OPTIONS shortcut pad opened: handle=0x%x", pad_handle);
    }

    unsigned char state[256] = {0};
    int rc = p_pad_read(pad_handle, state);
    if (rc < 0) {
        pad_handle = -1;
        held_ticks = 0;
        fired_this_hold = false;
        return false;
    }

    uint32_t buttons = 0;
    int connected = 0;
    memcpy(&buttons, state + 0x00, sizeof(buttons));
    memcpy(&connected, state + 0x4c, sizeof(connected));
    bool options_pressed = connected != 0 && !(buttons & 0x80000000u) &&
                           (buttons & 0x00000008u);

    if (!options_pressed) {
        held_ticks = 0;
        fired_this_hold = false;
        return false;
    }
    if (fired_this_hold) return false;
    if (++held_ticks >= 20) {
        fired_this_hold = true;
        held_ticks = 0;
        LOG_INFO("OPTIONS long-press detected");
        return true;
    }
    return false;
}
'''
main = replace_one(main, "bool has_hv_bypass = false;", "bool has_hv_bypass = false;\n" + hook, "insert controller poll")
build_call = "build_hud(Root_Domain, pui_img, widget_class, panel_class, label_class, root_widget, &hud_ctx);"
if main.count(build_call) != 3:
    raise RuntimeError("Expected exactly three HUD build call sites in v1.0.19")
main = main.replace(build_call, "if (g_options_overlay_visible) " + build_call)
end_loop = r'''        sleep(1);
    }

    return nullptr;
}'''
replacement_loop = r'''        // Poll OPTIONS ten times per second without speeding up the one-second
        // telemetry sampling loop. Mono UI changes happen on this same thread.
        for (int hotkey_tick = 0; hotkey_tick < 10; ++hotkey_tick) {
            if (poll_options_long_press()) {
                g_options_overlay_visible = !g_options_overlay_visible;
                LOG_INFO("OPTIONS toggled overlay visible=%d", g_options_overlay_visible ? 1 : 0);
                if (attached_to_game && root_widget) {
                    destroy_hud(root_widget, &hud_ctx, widget_class);
                    if (g_options_overlay_visible && g_config.enabled) {
                        build_hud(Root_Domain, pui_img, widget_class, panel_class, label_class, root_widget, &hud_ctx);
                    }
                }
            }
            usleep(100000);
        }
    }

    return nullptr;
}'''
main = replace_one(main, end_loop, replacement_loop, "hotkey polling loop")
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
                  "Katman yönetimi ve görünüm ayarları — OPTIONS tuşunu 2 saniye basılı tutarak göster/gizle",
                  "hotkey instructions")
web_file.write_text(web, encoding="utf-8")
print("OK: OPTIONS long-press implementation + complete Turkish web interface applied.")
