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
volatile bool g_options_overlay_visible = true;
volatile int g_hotkey_stage = 0;
volatile int g_hotkey_last_read = 0;
volatile int g_hotkey_handle = -1;
volatile unsigned int g_hotkey_buttons = 0;
volatile int g_hotkey_connected = 0;
volatile unsigned int g_hotkey_probe_count = 0;
volatile int g_hotkey_pad_module = 0;
volatile int g_hotkey_user_module = 0;
volatile int g_hotkey_symbol_mask = 0;
volatile int g_hotkey_fg_user = -1;
volatile int g_hotkey_fg_rc = 0;

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
        if (g_hotkey_stage == 0) g_hotkey_stage = 1;
        if (++tick_retry < 50) return false;
        tick_retry = 0;
        g_hotkey_probe_count++;
        uintptr_t pad_base = 0, user_base = 0;
        int pad_mod = get_module_handle(getpid(), "libScePad.sprx", &pad_base);
        if (pad_mod <= 0) pad_mod = get_module_handle(getpid(), "libScePad.prx", &pad_base);
        int user_mod = get_module_handle(getpid(), "libSceUserService.sprx", &user_base);
        if (user_mod <= 0) user_mod = get_module_handle(getpid(), "libSceUserService.prx", &user_base);
        g_hotkey_pad_module = pad_mod;
        g_hotkey_user_module = user_mod;
        if (pad_mod <= 0 || user_mod <= 0) g_hotkey_stage = 2;
        int pad_lookup = pad_mod > 0 ? pad_mod : 0x2001;
        int user_lookup = user_mod > 0 ? user_mod : 0x2001;
        {
            p_pad_open = (pad_open_fn)resolve_symbol(pad_lookup, pad_base, "scePadOpen");
            p_pad_get_handle = (pad_get_handle_fn)resolve_symbol(pad_lookup, pad_base, "scePadGetHandle");
            p_pad_read = (pad_read_fn)resolve_symbol(pad_lookup, pad_base, "scePadReadState");
            p_user_fg = (user_fg_fn)resolve_symbol(user_lookup, user_base, "sceUserServiceGetForegroundUser");
        }
        g_hotkey_symbol_mask = (p_pad_open ? 1 : 0) | (p_pad_get_handle ? 2 : 0) |
                               (p_pad_read ? 4 : 0) | (p_user_fg ? 8 : 0);
        if (!p_pad_read || !p_user_fg || (!p_pad_open && !p_pad_get_handle)) {
            if (g_hotkey_stage != 2) g_hotkey_stage = 3;
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
        if (g_hotkey_stage < 4) g_hotkey_stage = 4;
        if (++tick_retry < 10) return false;
        tick_retry = 0;
        int user_id = -1;
        int fg_rc = p_user_fg(&user_id);
        g_hotkey_fg_user = user_id;
        g_hotkey_fg_rc = fg_rc;
        if (fg_rc < 0 || user_id == -1) {
            g_hotkey_stage = 10;
            return false;
        }
        int h = p_pad_get_handle ? p_pad_get_handle(user_id, 0, 0) : -1;
        if (h < 0 && p_pad_open) h = p_pad_open(user_id, 0, 0, nullptr);
        if (h < 0) {
            g_hotkey_stage = 5;
            g_hotkey_handle = h;
            if (!init_logged) {
                LOG_WARN("OPTIONS shortcut pad handle unavailable: 0x%x", h);
                init_logged = true;
            }
            return false;
        }
        pad_handle = h;
        g_hotkey_handle = h;
        LOG_INFO("OPTIONS shortcut pad opened: handle=0x%x", pad_handle);
    }

    unsigned char state[256] = {0};
    int rc = p_pad_read(pad_handle, state);
    g_hotkey_last_read = rc;
    if (rc < 0) {
        g_hotkey_stage = 6;
        pad_handle = -1;
        g_hotkey_handle = -1;
        held_ticks = 0;
        fired_this_hold = false;
        return false;
    }

    uint32_t buttons = 0;
    int connected = 0;
    memcpy(&buttons, state + 0x00, sizeof(buttons));
    memcpy(&connected, state + 0x4c, sizeof(connected));
    g_hotkey_buttons = buttons;
    g_hotkey_connected = connected;
    g_hotkey_stage = 7;
    bool options_pressed = connected != 0 && !(buttons & 0x80000000u) &&
                           (buttons & 0x00000008u);

    if (!options_pressed) {
        held_ticks = 0;
        fired_this_hold = false;
        return false;
    }
    g_hotkey_stage = 8;
    if (fired_this_hold) return false;
    if (++held_ticks >= 20) {
        g_hotkey_stage = 9;
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
if main.count(build_call) != 2:
    raise RuntimeError("Expected exactly two HUD build call sites in v1.0.19")
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

# Experimental, user-triggered attempt to load ScePad and UserService into
# the injected ShellUI process. NO automatic loading: explicit panel click.
load_module_code = r'''
// Explicit, one-time request from the web UI; keep normal overlay independent.
volatile int g_hotkey_load_request = 0; // 0 idle, 1 requested, 2 busy, 3 done, 4 error
volatile int g_hotkey_load_kernel_rc = -1;
volatile int g_hotkey_load_sysmodule_rc = -1;
volatile int g_hotkey_load_user_rc = -1;
volatile int g_hotkey_load_pad_rc = -1;
volatile int g_hotkey_loaded_user_handle = 0;
volatile int g_hotkey_loaded_pad_handle = 0;

static void try_load_pad_modules(void) {
    if (g_hotkey_load_request != 1) return;
    g_hotkey_load_request = 2;

    typedef int (*module_load_t)(const char*, size_t, const void*, unsigned int, void*, int*);
    typedef int (*sysmodule_load_t)(unsigned int);

    uintptr_t kernel_base = 0;
    int kernel_handle = get_module_handle(getpid(), "libkernel_sys.sprx", &kernel_base);
    if (kernel_handle <= 0) kernel_handle = 0x2001;
    module_load_t load_module =
      (module_load_t)resolve_symbol(kernel_handle, kernel_base, "sceKernelLoadStartModule");
    if (!load_module) {
        g_hotkey_load_kernel_rc = -2;
        g_hotkey_load_request = 4;
        LOG_WARN("Controller module loader unavailable");
        return;
    }
    g_hotkey_load_kernel_rc = kernel_handle;

    uintptr_t sysbase = 0;
    int sysh = get_module_handle(getpid(), "libSceSysmodule.sprx", &sysbase);
    if (sysh <= 0) {
        sysh = load_module("/system/common/lib/libSceSysmodule.sprx", 0, nullptr, 0, nullptr, nullptr);
    }
    g_hotkey_load_sysmodule_rc = sysh;
    if (sysh > 0) {
        sysmodule_load_t load_internal =
          (sysmodule_load_t)resolve_symbol(sysh, sysbase, "sceSysmoduleLoadModuleInternal");
        if (load_internal) {
            // IDs are taken from the PS5 payload SDK module table.
            int urc = load_internal(0x80000011u);
            int prc = load_internal(0x80000024u);
            LOG_INFO("sceSysmoduleLoadModuleInternal: user=%x pad=%x", urc, prc);
        }
    }

    uintptr_t pad_base = 0, user_base = 0;
    int existing_user = get_module_handle(getpid(), "libSceUserService.sprx", &user_base);
    int existing_pad = get_module_handle(getpid(), "libScePad.sprx", &pad_base);

    int user_result = existing_user > 0 ? existing_user :
      load_module("/system/common/lib/libSceUserService.sprx", 0, nullptr, 0, nullptr, nullptr);
    int pad_result = existing_pad > 0 ? existing_pad :
      load_module("/system/common/lib/libScePad.sprx", 0, nullptr, 0, nullptr, nullptr);

    g_hotkey_load_user_rc = user_result;
    g_hotkey_load_pad_rc = pad_result;
    if (user_result > 0) g_hotkey_loaded_user_handle = user_result;
    if (pad_result > 0) g_hotkey_loaded_pad_handle = pad_result;

    g_hotkey_load_request = (user_result > 0 && pad_result > 0) ? 3 : 4;
    LOG_INFO("Pad load attempt: sysmodule=%d user=%d pad=%d status=%d",
             sysh, user_result, pad_result, g_hotkey_load_request);
}
'''
old = "volatile int g_hotkey_fg_rc = 0;"
if main.count(old) != 1: raise RuntimeError("V4 insertion marker missing")
main = main.replace(old, old + "\n" + load_module_code, 1)

old = '        if (pad_mod <= 0 || user_mod <= 0) g_hotkey_stage = 2;'
new = '''        if (pad_mod <= 0 && g_hotkey_loaded_pad_handle > 0)
            pad_mod = g_hotkey_loaded_pad_handle;
        if (user_mod <= 0 && g_hotkey_loaded_user_handle > 0)
            user_mod = g_hotkey_loaded_user_handle;
        g_hotkey_pad_module = pad_mod;
        g_hotkey_user_module = user_mod;
        if (pad_mod <= 0 || user_mod <= 0) g_hotkey_stage = 2;'''
if main.count(old) != 1: raise RuntimeError("V4 handle marker missing")
main = main.replace(old, new, 1)
old = '        for (int hotkey_tick = 0; hotkey_tick < 10; ++hotkey_tick) {'
new = '        try_load_pad_modules();\n' + old
if main.count(old) != 1: raise RuntimeError("V4 polling marker missing")
main = main.replace(old, new, 1)

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
                  "Katman yönetimi ve görünüm ayarları — OPTIONS 2 sn basılı tutarak aç/kapat",
                  "hotkey instructions")

quickPanel = r'''
  <div class="card" id="quickToggleCard">
    <div class="card-header">
      <div class="card-title">🎮 FPS Göster / Gizle</div>
    </div>
    <button id="btnWebToggle" type="button" onclick="toggleHudWeb()"
            style="display:block;width:100%;background:#0070d1;color:white;padding:13px;border:0;border-radius:10px;font-weight:bold;font-size:15px;">
      🎮 Göstergeyi gizle
    </button>
    <p style="color:#8b9bb4;font-size:13px;margin-top:12px;">OPTIONS 2 saniye basılı tutma denemesi. Tuş algılanmazsa buradaki düğmeyi kullanabilirsiniz.</p>
    <div id="hotkeyDiag" style="color:#c7d4e6;font-size:13px;margin-top:8px;">Kontrolcü bağlantısı inceleniyor...</div>
    <div id="hotkeyResolver" style="color:#7dd3fc;font-size:13px;margin-top:6px;">Modül ve fonksiyon tanılama bilgileri okunuyor...</div>
  </div>
'''
web = replace_one(web, '  <!-- Unload / Exit Overlay Card -->',
                  quickPanel + '  <!-- Unload / Exit Overlay Card -->', 'add quick toggle panel')
quickJS = r'''
async function refreshHotkeyStatus() {
  try {
    const r = await fetch('/api/hotkey-status', {cache: 'no-store'});
    if (!r.ok) return;
    const d = await r.json();
    const labels = {
      0:'Bekliyor', 1:'Modül çözümleme bekleniyor',
      2:'Kontrolcü kitaplıkları bulunamadı',
      3:'Kontrolcü fonksiyonları çözümlenemedi',
      4:'Kontrolcü bağlantısı aranıyor',
      5:'Kontrolcü tanıtıcısı alınamadı',
      6:'Kontrolcü okuma hatası',
      7:'Tuşlar okunuyor',
      8:'OPTIONS algılandı; basılı tutuluyor',
      9:'OPTIONS kısayolu tetiklendi', 10:'Aktif kullanıcı bulunamadı'
    };
    const el = document.getElementById('hotkeyDiag');
    if (el) el.textContent = 'Kontrolcü: ' + (labels[d.stage] || '?') +
       ' · Tuş: 0x' + Number(d.buttons).toString(16).padStart(8,'0') +
       ' · Bağlantı: ' + d.connected + ' · Okuma: ' + d.read_rc +
       ' · Tanıtıcı: ' + d.pad_handle;
    const b = document.getElementById('btnWebToggle');
    if (b) b.textContent = d.visible ? '🙈 Göstergeyi gizle' : '👁️ Göstergeyi aç';
    try {
      const q = await fetch('/api/hotkey-debug', {cache:'no-store'});
      if (q.ok) {
        const x = await q.json();
        const y = document.getElementById('hotkeyResolver');
        if (y) y.textContent = 'Deneme: ' + x.probes +
          ' · PadMod: ' + x.pad_mod + ' · UserMod: ' + x.user_mod +
          ' · Fonksiyonlar: ' + x.symbols +
          ' · Kullanıcı: ' + x.user_id + ' · KullanıcıRC: ' + x.user_rc;
      }
    } catch(ex) {}
  } catch(e) {
    const el = document.getElementById('hotkeyDiag');
    if (el) el.textContent = 'Kontrolcü durumuna erişilemiyor';
  }
}
async function toggleHudWeb() {
  const b = document.getElementById('btnWebToggle');
  if (b) b.disabled = true;
  try {
    const r = await fetch('/api/toggle-hud', {method:'POST'});
    if (!r.ok) throw new Error('HTTP ' + r.status);
    await refreshHotkeyStatus();
  } catch(e) {
    showToast('Gösterge değiştirilemedi!');
  } finally {
    if (b) b.disabled = false;
  }
}
'''
web = replace_one(web, "window.addEventListener('DOMContentLoaded', () => {\n  bindControls();\n  loadConfigFromServer();",
                  quickJS + "window.addEventListener('DOMContentLoaded', () => {\n  bindControls();\n  loadConfigFromServer();\n  refreshHotkeyStatus();\n  setInterval(refreshHotkeyStatus, 1500);",
                  "add client status polling")
web = replace_one(web, '#include "web_server.hpp"',
                  '#include "web_server.hpp"\nextern volatile bool g_options_overlay_visible;\nextern volatile int g_hotkey_stage;\nextern volatile int g_hotkey_last_read;\nextern volatile int g_hotkey_handle;\nextern volatile unsigned int g_hotkey_buttons;\nextern volatile int g_hotkey_connected;\nextern volatile unsigned int g_hotkey_probe_count;\nextern volatile int g_hotkey_pad_module;\nextern volatile int g_hotkey_user_module;\nextern volatile int g_hotkey_symbol_mask;\nextern volatile int g_hotkey_fg_user;\nextern volatile int g_hotkey_fg_rc;',
                  'status externs')
api = r'''
    if (strncmp(req, "GET /api/hotkey-debug", 21) == 0) {
        char body[320];
        int len = snprintf(body, sizeof(body),
            "{\"probes\":%u,\"pad_mod\":%d,\"user_mod\":%d,\"symbols\":%d,\"user_id\":%d,\"user_rc\":%d}",
            g_hotkey_probe_count, g_hotkey_pad_module, g_hotkey_user_module,
            g_hotkey_symbol_mask, g_hotkey_fg_user, g_hotkey_fg_rc);
        if (len < 0 || len >= (int)sizeof(body)) return;
        char hdr[240];
        int hlen = snprintf(hdr, sizeof(hdr),
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
            "Cache-Control: no-store\r\nContent-Length: %d\r\nConnection: close\r\n\r\n", len);
        socket_send_all(client_fd, hdr, hlen);
        socket_send_all(client_fd, body, len);
        return;
    }

    if (strncmp(req, "GET /api/hotkey-status", 22) == 0) {
        char body[320];
        int len = snprintf(body, sizeof(body),
            "{\"visible\":%s,\"stage\":%d,\"buttons\":%u,\"connected\":%d,\"read_rc\":%d,\"pad_handle\":%d}",
            g_options_overlay_visible ? "true" : "false", g_hotkey_stage,
            g_hotkey_buttons, g_hotkey_connected, g_hotkey_last_read, g_hotkey_handle);
        if (len < 0 || len >= (int)sizeof(body)) return;
        char hdr[240];
        int hlen = snprintf(hdr, sizeof(hdr),
            "HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\n"
            "Cache-Control: no-store\r\nContent-Length: %d\r\nConnection: close\r\n\r\n", len);
        socket_send_all(client_fd, hdr, hlen);
        socket_send_all(client_fd, body, len);
        return;
    }

    if (strncmp(req, "POST /api/toggle-hud", 20) == 0) {
        g_options_overlay_visible = !g_options_overlay_visible;
        g_config_changed = true;
        const char resp[] = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"status\":\"ok\"}";
        socket_send_all(client_fd, resp, sizeof(resp)-1);
        return;
    }

'''
web = replace_one(web, '    if (strncmp(req, "GET /api/config", 15) == 0) {',api+'    if (strncmp(req, "GET /api/config", 15) == 0) {','hotkey APIs')

# Display an opt-in module-load experiment and error codes separately.
extra_button = r'''
    <button id="btnTryModules" type="button" onclick="tryControllerModules()"
      style="display:block;width:100%;margin-top:10px;padding:12px;border:1px solid #f59e0b;border-radius:10px;background:#29231b;color:#fbbf24;font-weight:600;">
       Deneysel: Kontrolcü modüllerini yüklemeyi dene
    </button>
    <div id="moduleLoadInfo" style="color:#fbbf24;font-size:13px;margin-top:8px;">Modül yükleme henüz denenmedi.</div>
'''
old = '    <div id="hotkeyResolver"'
if web.count(old) != 1: raise RuntimeError("missing diagnostic box")
web = web.replace(old, extra_button+old,1)
js = r'''
async function tryControllerModules() {
  if (!confirm('Bu işlem PS5 sistem arayüzüne kontrolcü kütüphanelerini yüklemeyi dener. Deneyseldir ve SceShellUI yeniden başlatılabilir. Devam edilsin mi?')) return;
  const b = document.getElementById('btnTryModules');
  if (b) b.disabled = true;
  try {
    const r = await fetch('/api/hotkey-load', {method: 'POST'});
    if (!r.ok) throw new Error(r.status);
    setTimeout(refreshHotkeyStatus, 1500);
  } catch(ex) {
    showToast('Modül yükleme isteği gönderilemedi');
    if (b) b.disabled = false;
  }
}
'''
old = 'async function toggleHudWeb() {'
if web.count(old) != 1: raise RuntimeError("missing JS web toggle")
web = web.replace(old, js + old, 1)
old = '''        if (y) y.textContent = 'Deneme: ' + x.probes +'''
new = '''        const m = document.getElementById('moduleLoadInfo');
        const statuses = {0:'Henüz denenmedi',1:'İstek alındı',2:'Yükleniyor',3:'Kütüphaneler yüklendi',4:'Yükleme başarısız'};
        if (m) m.textContent = 'Yükleme: ' + (statuses[x.load_state] || x.load_state) +
          ' · Kernel: ' + x.kernel_rc + ' · Sysmodule: ' + x.sysmodule_rc +
          ' · User: ' + x.load_user_rc + ' · Pad: ' + x.load_pad_rc;
        const bt = document.getElementById('btnTryModules');
        if (bt) bt.disabled = x.load_state !== 0;
        if (y) y.textContent = 'Deneme: ' + x.probes +'''
if web.count(old) != 1: raise RuntimeError("missing debug JS")
web = web.replace(old, new, 1)

old = 'extern volatile int g_hotkey_fg_rc;'
new = old + '''\nextern volatile int g_hotkey_load_request;
extern volatile int g_hotkey_load_kernel_rc;
extern volatile int g_hotkey_load_sysmodule_rc;
extern volatile int g_hotkey_load_user_rc;
extern volatile int g_hotkey_load_pad_rc;'''
if web.count(old) != 1: raise RuntimeError("missing debug declarations")
web = web.replace(old, new, 1)
old = 'char body[320];'
# Only change the first body inside debug GET, not other endpoints.
start = web.index('if (strncmp(req, "GET /api/hotkey-debug"')
end = web.index('if (strncmp(req, "GET /api/hotkey-status"', start)
section = web[start:end]
section = section.replace('char body[320];', 'char body[512];', 1)
section = section.replace('''"{\\"probes\\":%u,\\"pad_mod\\":%d,\\"user_mod\\":%d,\\"symbols\\":%d,\\"user_id\\":%d,\\"user_rc\\":%d}",''',
''' "{\\"probes\\":%u,\\"pad_mod\\":%d,\\"user_mod\\":%d,\\"symbols\\":%d,\\"user_id\\":%d,\\"user_rc\\":%d,"
            "\\"load_state\\":%d,\\"kernel_rc\\":%d,\\"sysmodule_rc\\":%d,\\"load_user_rc\\":%d,\\"load_pad_rc\\":%d}",''', 1)
section = section.replace('''g_hotkey_symbol_mask, g_hotkey_fg_user, g_hotkey_fg_rc);''',
'''g_hotkey_symbol_mask, g_hotkey_fg_user, g_hotkey_fg_rc,
            g_hotkey_load_request, g_hotkey_load_kernel_rc, g_hotkey_load_sysmodule_rc,
            g_hotkey_load_user_rc, g_hotkey_load_pad_rc);''', 1)
if "load_state" not in section: raise RuntimeError("V4 debug response edit failed")
web = web[:start] + section + web[end:]
api = r'''
    if (strncmp(req, "POST /api/hotkey-load", 21) == 0) {
        if (g_hotkey_load_request == 0) g_hotkey_load_request = 1;
        const char resp[] = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"status\":\"queued\"}";
        socket_send_all(client_fd, resp, sizeof(resp)-1);
        return;
    }
'''
old = '    if (strncmp(req, "GET /api/hotkey-debug", 21) == 0) {'
if web.count(old) != 1: raise RuntimeError("missing v3 debug endpoint")
web = web.replace(old, api+old, 1)

web_file.write_text(web, encoding="utf-8")
print("OK: OPTIONS diagnostics + web HUD toggle installed")
web_file.write_text(web, encoding="utf-8")
print("OK: OPTIONS long-press implementation + complete Turkish web interface applied.")
