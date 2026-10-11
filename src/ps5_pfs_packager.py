# -*- coding: utf-8 -*-
"""
PS5 PFS Paketleyici TR
Sürüm: 1

Yöntem (MkPFS 1.1.0):
  Oyun klasörü -> exFAT sarmallı .ffpfsc (tek aşama, varsayılan pack folder)
  .exfat dosyası -> .ffpfsc (pack file)

Not:
  Oyun klasörü dönüşümünde artık geçici image.dat veya .exfat dosyası oluşturulmaz.
  EXE olarak çalışırken MkPFS çağrısı aynı EXE içinde "--internal-mkpfs" modu ile yapılır.
"""

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tempfile
import time
import urllib.request
import multiprocessing
import random
import locale
import configparser
import html as html_lib
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

import native_exfat_mount as native_exfat

try:
    import psutil
except Exception:
    psutil = None


def detect_logical_cpu_count() -> int:
    """Sistemin kullanıma sunduğu mantıksal işlemci/thread sayısını döndür."""
    count = None

    try:
        if psutil is not None:
            count = psutil.cpu_count(logical=True)
    except Exception:
        count = None

    if not count:
        try:
            count = os.cpu_count()
        except Exception:
            count = None

    try:
        return max(1, int(count or 1))
    except Exception:
        return 1

APP_VERSION = "2.14"
APP_TITLE = "PS5 PFS Paketleyici"

MKPFS_RELEASES_URL = "https://github.com/PSBrew/MkPFS/releases"
MKPFS_LATEST_API_URL = "https://api.github.com/repos/PSBrew/MkPFS/releases/latest"

# Bu build ile test edilen MkPFS sürümü. Otomatik algılama başarısız olursa fallback olarak kullanılır.
BUNDLED_MKPFS_VERSION = "1.1.0"

# Fakelib dosyaları EXE içine gömülmez.
# Programın çalıştığı klasörde "fakelib" klasörü varsa oradan kopyalanır.
FAKELIB_FILES = [
    "libSceAmpr.sprx",
    "libScePlayGo.sprx",
]


LANGUAGE_DISPLAY = {
    "tr": "Türkçe",
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
    "el": "Ελληνικά",
    "ko": "한국어",
    "ja": "日本語",
    "de": "Deutsch",
    "pt": "Português",
    "ru": "Русский",
    "zh": "中文",
    "ar": "العربية",
    "nl": "Nederlands",
    "pl": "Polski",
}
LANGUAGE_CODE_BY_DISPLAY = {v: k for k, v in LANGUAGE_DISPLAY.items()}

_I18N = {
    "en": {
        "app_title": "PS5 PFS Packager",
        "subtitle": "Convert a game folder or exfat image to ffpfsc format.",
        "check_updates": "Check Updates",
        "checking_updates": "Checking...",
        "app_current": "App Up to Date",
        "new_version": "New Version",
        "buy_coffee": "Buy Me Coffee :)",
        "single_tab": "Convert Single Game",
        "multi_tab": "Convert Multiple Games",
        "source_path": "Source path:",
        "main_folder": "Main folder:",
        "output_folder": "Output folder:",
        "file_name": "File name:",
        "temp_folder": "Temp folder:",
        "select": "Select",
        "get_titleid": "Get TitleID",
        "test_sound": "Test Sound",
        "cpu": "CPU:",
        "compression": "Compression:",
        "keep_dat": "Keep image.dat file",
        "extra_verify": "Extra verification / comparison",
        "delete_game_folder": "Delete game folder",
        "play_sound": "Play sound when done",
        "single_start": "Convert Game",
        "multi_start": "Convert Games",
        "single_running": "Game Converting...",
        "multi_running": "Games Converting...",
        "cancel": "Cancel",
        "ready": "Ready",
        "waiting": "Waiting",
        "last_none": "Last job: No job yet",
        "language": "Language:",
        "single_phase": "Single mode: Select a game folder or .exfat file.",
        "multi_phase": "Multi mode: Select a main folder containing game folders.",
        "coffee_title": "☕ Buy Me Coffee :)",
        "coffee_msg": "This tool makes disks sweat while writing image.dat and keeps the CPU busy while creating .ffpfsc.\nA coffee for the developer may make the progress bar happier 😄",
        "copy": "Copy",
        "copied": "Copied",
        "close": "Close",
        "usdt": "USDT",
        "btc": "BTC",
        "eth": "ETH",
    },
    "tr": {
        "app_title": "PS5 PFS Paketleyici",
        "subtitle": "Oyun klasörü veya exfat imajını ffpfsc formatına çevirin.",
        "check_updates": "Güncellemeleri Denetle",
        "checking_updates": "Checking...",
        "app_current": "Uygulama Güncel",
        "new_version": "Yeni Sürüm Var",
        "buy_coffee": "Kahve Ismarla :)",
        "single_tab": "Tek Oyun Dönüştür",
        "multi_tab": "Çoklu Oyun Dönüştür",
        "source_path": "Kaynak yolu:",
        "main_folder": "Ana klasör:",
        "output_folder": "Çıkış klasörü:",
        "file_name": "Dosya adı:",
        "temp_folder": "Temp klasörü:",
        "select": "Seç",
        "get_titleid": "TitleID Al",
        "test_sound": "Sesi Test Et",
        "cpu": "CPU:",
        "compression": "Sıkıştırma:",
        "keep_dat": "image.dat dosyasını sakla",
        "extra_verify": "Ek doğrulama / karşılaştırma",
        "delete_game_folder": "Oyun klasörünü sil",
        "play_sound": "Bitince ses çal",
        "single_start": "Tek Oyunu Dönüştür",
        "multi_start": "Çoklu Oyunları Dönüştür",
        "single_running": "Oyun Dönüştürülüyor...",
        "multi_running": "Oyunlar Dönüştürülüyor...",
        "cancel": "İptal",
        "ready": "Hazır",
        "waiting": "Bekliyor",
        "last_none": "Son işlem: Henüz işlem yok",
        "language": "Dil:",
        "single_phase": "Tek oyun modu: Oyun klasörü veya .exfat seç.",
        "multi_phase": "Çoklu mod: İçinde oyun klasörleri olan ana klasörü seç.",
        "coffee_title": "☕ Kahve Ismarla :)",
        "coffee_msg": "Bu araç image.dat yazarken diskleri, .ffpfsc yaparken CPU'yu terletiyor.\nGeliştirici tarafına bir kahve gönderirsen progress bar daha mutlu akar 😄",
        "copy": "Kopyala",
        "copied": "Kopyalandı",
        "close": "Kapat",
        "usdt": "USDT",
        "btc": "BTC",
        "eth": "ETH",
    },
    "fr": {
        "app_title": "Emballeur PS5 PFS",
        "subtitle": "Convertissez un dossier de jeu ou une image exfat au format ffpfsc.",
        "check_updates": "Vérifier les mises à jour",
        "checking_updates": "Vérification...",
        "app_current": "Application à jour",
        "new_version": "Nouvelle version",
        "buy_coffee": "Offrir un café :)",
        "single_tab": "Convertir un jeu",
        "multi_tab": "Convertir plusieurs jeux",
        "source_path": "Chemin source :",
        "main_folder": "Dossier principal :",
        "output_folder": "Dossier de sortie :",
        "file_name": "Nom du fichier :",
        "temp_folder": "Dossier temporaire :",
        "select": "Choisir",
        "get_titleid": "Lire TitleID",
        "test_sound": "Tester le son",
        "cpu": "CPU :",
        "compression": "Compression :",
        "keep_dat": "Conserver image.dat",
        "extra_verify": "Vérification / comparaison extra",
        "delete_game_folder": "Supprimer le dossier du jeu",
        "play_sound": "Son à la fin",
        "single_start": "Convertir le jeu",
        "multi_start": "Convertir les jeux",
        "single_running": "Jeu en conversion...",
        "multi_running": "Jeux en conversion...",
        "cancel": "Annuler",
        "ready": "Prêt",
        "waiting": "En attente",
        "last_none": "Dernière tâche : aucune",
        "language": "Langue :",
        "single_phase": "Mode un jeu : sélectionnez un dossier de jeu ou un fichier .exfat.",
        "multi_phase": "Mode multi : sélectionnez un dossier contenant des jeux.",
        "coffee_title": "☕ Offrir un café :)",
        "coffee_msg": "Cet outil fait travailler le disque pendant image.dat et le CPU pendant .ffpfsc.\nUn café pour le développeur peut rendre la barre de progression plus heureuse 😄",
        "copy": "Copier",
        "copied": "Copié",
        "close": "Fermer",
    },
    "es": {
        "app_title": "Empaquetador PS5 PFS",
        "subtitle": "Convierte una carpeta de juego o imagen exfat al formato ffpfsc.",
        "check_updates": "Buscar actualizaciones",
        "checking_updates": "Comprobando...",
        "app_current": "Aplicación actualizada",
        "new_version": "Nueva versión",
        "buy_coffee": "Invitar un café :)",
        "single_tab": "Convertir un juego",
        "multi_tab": "Convertir varios juegos",
        "source_path": "Ruta de origen:",
        "main_folder": "Carpeta principal:",
        "output_folder": "Carpeta de salida:",
        "file_name": "Nombre de archivo:",
        "temp_folder": "Carpeta temporal:",
        "select": "Elegir",
        "get_titleid": "Obtener TitleID",
        "test_sound": "Probar sonido",
        "cpu": "CPU:",
        "compression": "Compresión:",
        "keep_dat": "Conservar image.dat",
        "extra_verify": "Verificación / comparación extra",
        "delete_game_folder": "Eliminar carpeta del juego",
        "play_sound": "Reproducir sonido al terminar",
        "single_start": "Convertir juego",
        "multi_start": "Convertir juegos",
        "single_running": "Convirtiendo juego...",
        "multi_running": "Convirtiendo juegos...",
        "cancel": "Cancelar",
        "ready": "Listo",
        "waiting": "Esperando",
        "last_none": "Último trabajo: ninguno",
        "language": "Idioma:",
        "single_phase": "Modo individual: selecciona una carpeta de juego o archivo .exfat.",
        "multi_phase": "Modo múltiple: selecciona una carpeta principal con juegos.",
        "coffee_title": "☕ Invitar un café :)",
        "coffee_msg": "Esta herramienta hace sudar al disco con image.dat y usa el CPU con .ffpfsc.\nUn café para el desarrollador puede alegrar la barra de progreso 😄",
        "copy": "Copiar",
        "copied": "Copiado",
        "close": "Cerrar",
    },
    "it": {
        "app_title": "Pacchettizzatore PS5 PFS",
        "subtitle": "Converti una cartella gioco o immagine exfat in formato ffpfsc.",
        "check_updates": "Controlla aggiornamenti",
        "checking_updates": "Controllo...",
        "app_current": "App aggiornata",
        "new_version": "Nuova versione",
        "buy_coffee": "Offri un caffè :)",
        "single_tab": "Converti gioco singolo",
        "multi_tab": "Converti più giochi",
        "source_path": "Percorso sorgente:",
        "main_folder": "Cartella principale:",
        "output_folder": "Cartella output:",
        "file_name": "Nome file:",
        "temp_folder": "Cartella temp:",
        "select": "Seleziona",
        "get_titleid": "Prendi TitleID",
        "test_sound": "Test audio",
        "cpu": "CPU:",
        "compression": "Compressione:",
        "keep_dat": "Mantieni image.dat",
        "extra_verify": "Verifica / confronto extra",
        "delete_game_folder": "Elimina cartella gioco",
        "play_sound": "Suono alla fine",
        "single_start": "Converti gioco",
        "multi_start": "Converti giochi",
        "single_running": "Gioco in conversione...",
        "multi_running": "Giochi in conversione...",
        "cancel": "Annulla",
        "ready": "Pronto",
        "waiting": "In attesa",
        "last_none": "Ultimo lavoro: nessuno",
        "language": "Lingua:",
        "single_phase": "Modalità singola: seleziona una cartella gioco o file .exfat.",
        "multi_phase": "Modalità multipla: seleziona una cartella con giochi.",
        "coffee_title": "☕ Offri un caffè :)",
        "coffee_msg": "Questo strumento fa lavorare il disco con image.dat e la CPU con .ffpfsc.\nUn caffè allo sviluppatore può rendere più felice la barra di avanzamento 😄",
        "copy": "Copia",
        "copied": "Copiato",
        "close": "Chiudi",
    },
    "de": {
        "app_title": "PS5 PFS-Packer",
        "subtitle": "Spielordner oder exfat-Image in das ffpfsc-Format konvertieren.",
        "check_updates": "Updates prüfen",
        "checking_updates": "Prüfe...",
        "app_current": "App aktuell",
        "new_version": "Neue Version",
        "buy_coffee": "Kaffee spendieren :)",
        "single_tab": "Ein Spiel konvertieren",
        "multi_tab": "Mehrere Spiele konvertieren",
        "source_path": "Quellpfad:",
        "main_folder": "Hauptordner:",
        "output_folder": "Ausgabeordner:",
        "file_name": "Dateiname:",
        "temp_folder": "Temp-Ordner:",
        "select": "Auswählen",
        "get_titleid": "TitleID holen",
        "test_sound": "Ton testen",
        "cpu": "CPU:",
        "compression": "Kompression:",
        "keep_dat": "image.dat behalten",
        "extra_verify": "Zusätzliche Prüfung / Vergleich",
        "delete_game_folder": "Spielordner löschen",
        "play_sound": "Ton nach Abschluss",
        "single_start": "Spiel konvertieren",
        "multi_start": "Spiele konvertieren",
        "single_running": "Spiel wird konvertiert...",
        "multi_running": "Spiele werden konvertiert...",
        "cancel": "Abbrechen",
        "ready": "Bereit",
        "waiting": "Warten",
        "last_none": "Letzter Job: keiner",
        "language": "Sprache:",
        "single_phase": "Einzelmodus: Spielordner oder .exfat-Datei auswählen.",
        "multi_phase": "Mehrfachmodus: Hauptordner mit Spielordnern auswählen.",
        "coffee_title": "☕ Kaffee spendieren :)",
        "coffee_msg": "Dieses Tool bringt beim Schreiben von image.dat die Festplatte und bei .ffpfsc die CPU ins Schwitzen.\nEin Kaffee für den Entwickler macht den Fortschrittsbalken glücklicher 😄",
        "copy": "Kopieren",
        "copied": "Kopiert",
        "close": "Schließen",
    },
    "el": {
        "app_title": "PS5 PFS Packager",
        "subtitle": "Μετατρέψτε φάκελο παιχνιδιού ή εικόνα exfat σε μορφή ffpfsc.",
        "check_updates": "Έλεγχος ενημερώσεων",
        "checking_updates": "Έλεγχος...",
        "app_current": "Η εφαρμογή είναι ενημερωμένη",
        "new_version": "Νέα έκδοση",
        "buy_coffee": "Κέρασε καφέ :)",
        "single_tab": "Μετατροπή ενός παιχνιδιού",
        "multi_tab": "Μετατροπή πολλών παιχνιδιών",
        "source_path": "Πηγή:",
        "main_folder": "Κύριος φάκελος:",
        "output_folder": "Φάκελος εξόδου:",
        "file_name": "Όνομα αρχείου:",
        "temp_folder": "Προσωρινός φάκελος:",
        "select": "Επιλογή",
        "get_titleid": "Λήψη TitleID",
        "test_sound": "Δοκιμή ήχου",
        "cpu": "CPU:",
        "compression": "Συμπίεση:",
        "keep_dat": "Διατήρηση image.dat",
        "extra_verify": "Επιπλέον επαλήθευση / σύγκριση",
        "delete_game_folder": "Διαγραφή φακέλου παιχνιδιού",
        "play_sound": "Ήχος στο τέλος",
        "single_start": "Μετατροπή παιχνιδιού",
        "multi_start": "Μετατροπή παιχνιδιών",
        "single_running": "Μετατροπή παιχνιδιού...",
        "multi_running": "Μετατροπή παιχνιδιών...",
        "cancel": "Άκυρο",
        "ready": "Έτοιμο",
        "waiting": "Αναμονή",
        "last_none": "Τελευταία εργασία: καμία",
        "language": "Γλώσσα:",
        "single_phase": "Μονή λειτουργία: επιλέξτε φάκελο παιχνιδιού ή αρχείο .exfat.",
        "multi_phase": "Πολλαπλή λειτουργία: επιλέξτε κύριο φάκελο με παιχνίδια.",
        "coffee_title": "☕ Κέρασε καφέ :)",
        "coffee_msg": "Το εργαλείο δουλεύει τον δίσκο με image.dat και την CPU με .ffpfsc.\nΈνας καφές για τον developer κάνει τη μπάρα προόδου πιο χαρούμενη 😄",
        "copy": "Αντιγραφή",
        "copied": "Αντιγράφηκε",
        "close": "Κλείσιμο",
    },
    "ko": {
        "app_title": "PS5 PFS 패키저",
        "subtitle": "게임 폴더 또는 exfat 이미지를 ffpfsc 형식으로 변환합니다.",
        "check_updates": "업데이트 확인",
        "checking_updates": "확인 중...",
        "app_current": "최신 버전",
        "new_version": "새 버전",
        "buy_coffee": "커피 후원 :)",
        "single_tab": "단일 게임 변환",
        "multi_tab": "여러 게임 변환",
        "source_path": "소스 경로:",
        "main_folder": "상위 폴더:",
        "output_folder": "출력 폴더:",
        "file_name": "파일 이름:",
        "temp_folder": "임시 폴더:",
        "select": "선택",
        "get_titleid": "TitleID 가져오기",
        "test_sound": "사운드 테스트",
        "cpu": "CPU:",
        "compression": "압축:",
        "keep_dat": "image.dat 유지",
        "extra_verify": "추가 검증 / 비교",
        "delete_game_folder": "게임 폴더 삭제",
        "play_sound": "완료 시 소리",
        "single_start": "게임 변환",
        "multi_start": "게임들 변환",
        "single_running": "게임 변환 중...",
        "multi_running": "게임들 변환 중...",
        "cancel": "취소",
        "ready": "준비됨",
        "waiting": "대기 중",
        "last_none": "마지막 작업: 없음",
        "language": "언어:",
        "single_phase": "단일 모드: 게임 폴더 또는 .exfat 파일을 선택하세요.",
        "multi_phase": "다중 모드: 게임 폴더가 들어있는 상위 폴더를 선택하세요.",
        "coffee_title": "☕ 커피 후원 :)",
        "coffee_msg": "이 도구는 image.dat 작성 시 디스크를, .ffpfsc 생성 시 CPU를 열심히 사용합니다.\n개발자에게 커피 한 잔은 진행 바를 더 행복하게 만들 수 있어요 😄",
        "copy": "복사",
        "copied": "복사됨",
        "close": "닫기",
    },
    "ja": {
        "app_title": "PS5 PFS パッケージャー",
        "subtitle": "ゲームフォルダまたは exfat イメージを ffpfsc 形式に変換します。",
        "check_updates": "更新を確認",
        "checking_updates": "確認中...",
        "app_current": "最新です",
        "new_version": "新しいバージョン",
        "buy_coffee": "コーヒーを送る :)",
        "single_tab": "1本のゲームを変換",
        "multi_tab": "複数ゲームを変換",
        "source_path": "ソースパス:",
        "main_folder": "メインフォルダ:",
        "output_folder": "出力フォルダ:",
        "file_name": "ファイル名:",
        "temp_folder": "一時フォルダ:",
        "select": "選択",
        "get_titleid": "TitleID 取得",
        "test_sound": "音をテスト",
        "cpu": "CPU:",
        "compression": "圧縮:",
        "keep_dat": "image.dat を保持",
        "extra_verify": "追加検証 / 比較",
        "delete_game_folder": "ゲームフォルダを削除",
        "play_sound": "完了時に音を鳴らす",
        "single_start": "ゲームを変換",
        "multi_start": "ゲームを一括変換",
        "single_running": "ゲーム変換中...",
        "multi_running": "ゲーム変換中...",
        "cancel": "キャンセル",
        "ready": "準備完了",
        "waiting": "待機中",
        "last_none": "最後の処理: なし",
        "language": "言語:",
        "single_phase": "単体モード: ゲームフォルダまたは .exfat ファイルを選択してください。",
        "multi_phase": "一括モード: ゲームフォルダを含む親フォルダを選択してください。",
        "coffee_title": "☕ コーヒーを送る :)",
        "coffee_msg": "このツールは image.dat 作成でディスクを、.ffpfsc 作成で CPU を使います。\n開発者へのコーヒーで進捗バーが少し幸せになります 😄",
        "copy": "コピー",
        "copied": "コピー済み",
        "close": "閉じる",
    },
    "pt": {
        "app_title": "Empacotador PS5 PFS",
        "subtitle": "Converta uma pasta de jogo ou imagem exfat para o formato ffpfsc.",
        "check_updates": "Verificar atualizações",
        "checking_updates": "Verificando...",
        "app_current": "App atualizado",
        "new_version": "Nova versão",
        "buy_coffee": "Pagar um café :)",
        "single_tab": "Converter um jogo",
        "multi_tab": "Converter vários jogos",
        "source_path": "Caminho de origem:",
        "main_folder": "Pasta principal:",
        "output_folder": "Pasta de saída:",
        "file_name": "Nome do arquivo:",
        "temp_folder": "Pasta temporária:",
        "select": "Selecionar",
        "get_titleid": "Obter TitleID",
        "test_sound": "Testar som",
        "cpu": "CPU:",
        "compression": "Compressão:",
        "keep_dat": "Manter image.dat",
        "extra_verify": "Verificação / comparação extra",
        "delete_game_folder": "Excluir pasta do jogo",
        "play_sound": "Tocar som ao concluir",
        "single_start": "Converter jogo",
        "multi_start": "Converter jogos",
        "single_running": "Convertendo jogo...",
        "multi_running": "Convertendo jogos...",
        "cancel": "Cancelar",
        "ready": "Pronto",
        "waiting": "Aguardando",
        "last_none": "Último trabalho: nenhum",
        "language": "Idioma:",
        "single_phase": "Modo único: selecione uma pasta de jogo ou arquivo .exfat.",
        "multi_phase": "Modo múltiplo: selecione uma pasta principal com jogos.",
        "coffee_title": "☕ Pagar um café :)",
        "coffee_msg": "Esta ferramenta usa o disco no image.dat e a CPU no .ffpfsc.\nUm café para o desenvolvedor pode deixar a barra de progresso mais feliz 😄",
        "copy": "Copiar",
        "copied": "Copiado",
        "close": "Fechar",
    },
    "ru": {
        "app_title": "PS5 PFS Packager",
        "subtitle": "Преобразуйте папку игры или образ exfat в формат ffpfsc.",
        "check_updates": "Проверить обновления",
        "checking_updates": "Проверка...",
        "app_current": "Приложение обновлено",
        "new_version": "Новая версия",
        "buy_coffee": "Купить кофе :)",
        "single_tab": "Конвертировать одну игру",
        "multi_tab": "Конвертировать несколько игр",
        "source_path": "Источник:",
        "main_folder": "Главная папка:",
        "output_folder": "Папка вывода:",
        "file_name": "Имя файла:",
        "temp_folder": "Временная папка:",
        "select": "Выбрать",
        "get_titleid": "Получить TitleID",
        "test_sound": "Проверить звук",
        "cpu": "CPU:",
        "compression": "Сжатие:",
        "keep_dat": "Сохранить image.dat",
        "extra_verify": "Доп. проверка / сравнение",
        "delete_game_folder": "Удалить папку игры",
        "play_sound": "Звук после завершения",
        "single_start": "Конвертировать игру",
        "multi_start": "Конвертировать игры",
        "single_running": "Игра конвертируется...",
        "multi_running": "Игры конвертируются...",
        "cancel": "Отмена",
        "ready": "Готово",
        "waiting": "Ожидание",
        "last_none": "Последняя задача: нет",
        "language": "Язык:",
        "single_phase": "Одиночный режим: выберите папку игры или файл .exfat.",
        "multi_phase": "Мульти-режим: выберите главную папку с играми.",
        "coffee_title": "☕ Купить кофе :)",
        "coffee_msg": "Инструмент нагружает диск при image.dat и CPU при .ffpfsc.\nКофе для разработчика может сделать прогресс-бар счастливее 😄",
        "copy": "Копировать",
        "copied": "Скопировано",
        "close": "Закрыть",
    },
    "zh": {
        "app_title": "PS5 PFS 打包器",
        "subtitle": "将游戏文件夹或 exfat 镜像转换为 ffpfsc 格式。",
        "check_updates": "检查更新",
        "checking_updates": "检查中...",
        "app_current": "已是最新",
        "new_version": "发现新版本",
        "buy_coffee": "请喝咖啡 :)",
        "single_tab": "转换单个游戏",
        "multi_tab": "转换多个游戏",
        "source_path": "源路径:",
        "main_folder": "主文件夹:",
        "output_folder": "输出文件夹:",
        "file_name": "文件名:",
        "temp_folder": "临时文件夹:",
        "select": "选择",
        "get_titleid": "获取 TitleID",
        "test_sound": "测试声音",
        "cpu": "CPU:",
        "compression": "压缩:",
        "keep_dat": "保留 image.dat",
        "extra_verify": "额外验证 / 比较",
        "delete_game_folder": "删除游戏文件夹",
        "play_sound": "完成后播放声音",
        "single_start": "转换游戏",
        "multi_start": "转换游戏",
        "single_running": "正在转换游戏...",
        "multi_running": "正在转换游戏...",
        "cancel": "取消",
        "ready": "就绪",
        "waiting": "等待中",
        "last_none": "上次任务: 无",
        "language": "语言:",
        "single_phase": "单个模式: 选择游戏文件夹或 .exfat 文件。",
        "multi_phase": "多个模式: 选择包含游戏文件夹的主文件夹。",
        "coffee_title": "☕ 请喝咖啡 :)",
        "coffee_msg": "该工具在写入 image.dat 时使用磁盘，在创建 .ffpfsc 时使用 CPU。\n给开发者一杯咖啡，进度条会更开心 😄",
        "copy": "复制",
        "copied": "已复制",
        "close": "关闭",
    },
    "ar": {
        "app_title": "حازم PS5 PFS",
        "subtitle": "حوّل مجلد اللعبة أو صورة exfat إلى صيغة ffpfsc.",
        "check_updates": "التحقق من التحديثات",
        "checking_updates": "جارٍ التحقق...",
        "app_current": "التطبيق محدث",
        "new_version": "إصدار جديد",
        "buy_coffee": "اشترِ قهوة :)",
        "single_tab": "تحويل لعبة واحدة",
        "multi_tab": "تحويل عدة ألعاب",
        "source_path": "مسار المصدر:",
        "main_folder": "المجلد الرئيسي:",
        "output_folder": "مجلد الإخراج:",
        "file_name": "اسم الملف:",
        "temp_folder": "مجلد مؤقت:",
        "select": "اختيار",
        "get_titleid": "جلب TitleID",
        "test_sound": "اختبار الصوت",
        "cpu": "CPU:",
        "compression": "الضغط:",
        "keep_dat": "الاحتفاظ بـ image.dat",
        "extra_verify": "تحقق / مقارنة إضافية",
        "delete_game_folder": "حذف مجلد اللعبة",
        "play_sound": "تشغيل صوت عند الانتهاء",
        "single_start": "تحويل اللعبة",
        "multi_start": "تحويل الألعاب",
        "single_running": "جارٍ تحويل اللعبة...",
        "multi_running": "جارٍ تحويل الألعاب...",
        "cancel": "إلغاء",
        "ready": "جاهز",
        "waiting": "انتظار",
        "last_none": "آخر مهمة: لا يوجد",
        "language": "اللغة:",
        "single_phase": "وضع لعبة واحدة: اختر مجلد اللعبة أو ملف .exfat.",
        "multi_phase": "وضع متعدد: اختر مجلداً رئيسياً يحتوي على الألعاب.",
        "coffee_title": "☕ اشترِ قهوة :)",
        "coffee_msg": "هذه الأداة تُشغل القرص مع image.dat والمعالج مع .ffpfsc.\nقهوة للمطور قد تجعل شريط التقدم أكثر سعادة 😄",
        "copy": "نسخ",
        "copied": "تم النسخ",
        "close": "إغلاق",
    },
    "nl": {
        "app_title": "PS5 PFS Packager",
        "subtitle": "Converteer een gamemap of exfat-image naar ffpfsc-formaat.",
        "check_updates": "Updates controleren",
        "checking_updates": "Controleren...",
        "app_current": "App is actueel",
        "new_version": "Nieuwe versie",
        "buy_coffee": "Trakteer op koffie :)",
        "single_tab": "Eén game converteren",
        "multi_tab": "Meerdere games converteren",
        "source_path": "Bronpad:",
        "main_folder": "Hoofdmap:",
        "output_folder": "Uitvoermap:",
        "file_name": "Bestandsnaam:",
        "temp_folder": "Tempmap:",
        "select": "Kiezen",
        "get_titleid": "TitleID ophalen",
        "test_sound": "Geluid testen",
        "cpu": "CPU:",
        "compression": "Compressie:",
        "keep_dat": "image.dat bewaren",
        "extra_verify": "Extra verificatie / vergelijking",
        "delete_game_folder": "Gamemap verwijderen",
        "play_sound": "Geluid na voltooiing",
        "single_start": "Game converteren",
        "multi_start": "Games converteren",
        "single_running": "Game wordt geconverteerd...",
        "multi_running": "Games worden geconverteerd...",
        "cancel": "Annuleren",
        "ready": "Gereed",
        "waiting": "Wachten",
        "last_none": "Laatste taak: geen",
        "language": "Taal:",
        "single_phase": "Enkele modus: selecteer een gamemap of .exfat-bestand.",
        "multi_phase": "Meervoudige modus: selecteer een hoofdmap met games.",
        "coffee_title": "☕ Trakteer op koffie :)",
        "coffee_msg": "Deze tool laat de schijf werken bij image.dat en de CPU bij .ffpfsc.\nEen koffie voor de ontwikkelaar maakt de voortgangsbalk blijer 😄",
        "copy": "Kopiëren",
        "copied": "Gekopieerd",
        "close": "Sluiten",
    },
    "pl": {
        "app_title": "PS5 PFS Packager",
        "subtitle": "Konwertuj folder gry lub obraz exfat do formatu ffpfsc.",
        "check_updates": "Sprawdź aktualizacje",
        "checking_updates": "Sprawdzanie...",
        "app_current": "Aplikacja aktualna",
        "new_version": "Nowa wersja",
        "buy_coffee": "Postaw kawę :)",
        "single_tab": "Konwertuj jedną grę",
        "multi_tab": "Konwertuj wiele gier",
        "source_path": "Ścieżka źródła:",
        "main_folder": "Folder główny:",
        "output_folder": "Folder wyjściowy:",
        "file_name": "Nazwa pliku:",
        "temp_folder": "Folder tymczasowy:",
        "select": "Wybierz",
        "get_titleid": "Pobierz TitleID",
        "test_sound": "Test dźwięku",
        "cpu": "CPU:",
        "compression": "Kompresja:",
        "keep_dat": "Zachowaj image.dat",
        "extra_verify": "Dodatkowa weryfikacja / porównanie",
        "delete_game_folder": "Usuń folder gry",
        "play_sound": "Odtwórz dźwięk po zakończeniu",
        "single_start": "Konwertuj grę",
        "multi_start": "Konwertuj gry",
        "single_running": "Konwersja gry...",
        "multi_running": "Konwersja gier...",
        "cancel": "Anuluj",
        "ready": "Gotowe",
        "waiting": "Oczekiwanie",
        "last_none": "Ostatnie zadanie: brak",
        "language": "Język:",
        "single_phase": "Tryb pojedynczy: wybierz folder gry lub plik .exfat.",
        "multi_phase": "Tryb wielu gier: wybierz główny folder z grami.",
        "coffee_title": "☕ Postaw kawę :)",
        "coffee_msg": "To narzędzie obciąża dysk przy image.dat i CPU przy .ffpfsc.\nKawa dla dewelopera może uszczęśliwić pasek postępu 😄",
        "copy": "Kopiuj",
        "copied": "Skopiowano",
        "close": "Zamknij",
    },
}

# Fill missing translations from English so any unsupported key safely falls back.
for _lang, _data in list(_I18N.items()):
    merged = dict(_I18N["en"])
    merged.update(_data)
    _I18N[_lang] = merged

_UPDATE_LOG_TEXT = {
    "en": {
        "update_checking_log": "Checking for updates...",
        "update_failed_log": "Update check failed: {error}",
        "remote_version_log": "Server version: {version}",
        "current_version_log": "Current version: {version}",
        "app_up_to_date_log": "App is up to date.",
        "new_version_downloading_log": "New version found. Downloading update package...",
        "save_location_log": "Save location: {path}",
        "update_downloaded_log": "Update downloaded: {path}",
        "update_download_failed_log": "Update download failed: {error}",
        "update_title": "Update",
        "new_version_downloaded_msg": "New version downloaded:\n{path}",
    },
    "tr": {
        "update_checking_log": "Güncelleme kontrol ediliyor...",
        "update_failed_log": "Güncelleme kontrolü başarısız: {error}",
        "remote_version_log": "Sunucudaki sürüm: {version}",
        "current_version_log": "Mevcut sürüm: {version}",
        "app_up_to_date_log": "Uygulama güncel.",
        "new_version_downloading_log": "Yeni sürüm bulundu. Güncelleme paketi indiriliyor...",
        "save_location_log": "Kaydedilecek yer: {path}",
        "update_downloaded_log": "Güncelleme indirildi: {path}",
        "update_download_failed_log": "Güncelleme indirilemedi: {error}",
        "update_title": "Güncelleme",
        "new_version_downloaded_msg": "Yeni sürüm indirildi:\n{path}",
    },
    "fr": {
        "update_checking_log": "Vérification des mises à jour...",
        "update_failed_log": "Échec de la vérification : {error}",
        "remote_version_log": "Version serveur : {version}",
        "current_version_log": "Version actuelle : {version}",
        "app_up_to_date_log": "L’application est à jour.",
        "new_version_downloading_log": "Nouvelle version trouvée. Téléchargement du paquet...",
        "save_location_log": "Emplacement : {path}",
        "update_downloaded_log": "Mise à jour téléchargée : {path}",
        "update_download_failed_log": "Téléchargement échoué : {error}",
        "update_title": "Mise à jour",
        "new_version_downloaded_msg": "Nouvelle version téléchargée :\n{path}",
    },
    "es": {
        "update_checking_log": "Buscando actualizaciones...",
        "update_failed_log": "Error al comprobar actualizaciones: {error}",
        "remote_version_log": "Versión del servidor: {version}",
        "current_version_log": "Versión actual: {version}",
        "app_up_to_date_log": "La aplicación está actualizada.",
        "new_version_downloading_log": "Nueva versión encontrada. Descargando paquete...",
        "save_location_log": "Ubicación de guardado: {path}",
        "update_downloaded_log": "Actualización descargada: {path}",
        "update_download_failed_log": "No se pudo descargar: {error}",
        "update_title": "Actualización",
        "new_version_downloaded_msg": "Nueva versión descargada:\n{path}",
    },
    "it": {
        "update_checking_log": "Controllo aggiornamenti...",
        "update_failed_log": "Controllo aggiornamenti non riuscito: {error}",
        "remote_version_log": "Versione server: {version}",
        "current_version_log": "Versione attuale: {version}",
        "app_up_to_date_log": "L’app è aggiornata.",
        "new_version_downloading_log": "Nuova versione trovata. Download del pacchetto...",
        "save_location_log": "Percorso salvataggio: {path}",
        "update_downloaded_log": "Aggiornamento scaricato: {path}",
        "update_download_failed_log": "Download non riuscito: {error}",
        "update_title": "Aggiornamento",
        "new_version_downloaded_msg": "Nuova versione scaricata:\n{path}",
    },
    "de": {
        "update_checking_log": "Updates werden geprüft...",
        "update_failed_log": "Updateprüfung fehlgeschlagen: {error}",
        "remote_version_log": "Serverversion: {version}",
        "current_version_log": "Aktuelle Version: {version}",
        "app_up_to_date_log": "Die App ist aktuell.",
        "new_version_downloading_log": "Neue Version gefunden. Updatepaket wird heruntergeladen...",
        "save_location_log": "Speicherort: {path}",
        "update_downloaded_log": "Update heruntergeladen: {path}",
        "update_download_failed_log": "Download fehlgeschlagen: {error}",
        "update_title": "Update",
        "new_version_downloaded_msg": "Neue Version heruntergeladen:\n{path}",
    },
    "el": {
        "update_checking_log": "Έλεγχος ενημερώσεων...",
        "update_failed_log": "Ο έλεγχος απέτυχε: {error}",
        "remote_version_log": "Έκδοση διακομιστή: {version}",
        "current_version_log": "Τρέχουσα έκδοση: {version}",
        "app_up_to_date_log": "Η εφαρμογή είναι ενημερωμένη.",
        "new_version_downloading_log": "Βρέθηκε νέα έκδοση. Γίνεται λήψη...",
        "save_location_log": "Τοποθεσία αποθήκευσης: {path}",
        "update_downloaded_log": "Η ενημέρωση λήφθηκε: {path}",
        "update_download_failed_log": "Αποτυχία λήψης: {error}",
        "update_title": "Ενημέρωση",
        "new_version_downloaded_msg": "Η νέα έκδοση λήφθηκε:\n{path}",
    },
    "ko": {
        "update_checking_log": "업데이트 확인 중...",
        "update_failed_log": "업데이트 확인 실패: {error}",
        "remote_version_log": "서버 버전: {version}",
        "current_version_log": "현재 버전: {version}",
        "app_up_to_date_log": "앱이 최신 버전입니다.",
        "new_version_downloading_log": "새 버전을 찾았습니다. 업데이트 패키지 다운로드 중...",
        "save_location_log": "저장 위치: {path}",
        "update_downloaded_log": "업데이트 다운로드됨: {path}",
        "update_download_failed_log": "업데이트 다운로드 실패: {error}",
        "update_title": "업데이트",
        "new_version_downloaded_msg": "새 버전이 다운로드되었습니다:\n{path}",
    },
    "ja": {
        "update_checking_log": "更新を確認中...",
        "update_failed_log": "更新確認に失敗しました: {error}",
        "remote_version_log": "サーバーバージョン: {version}",
        "current_version_log": "現在のバージョン: {version}",
        "app_up_to_date_log": "アプリは最新です。",
        "new_version_downloading_log": "新しいバージョンが見つかりました。更新パッケージをダウンロード中...",
        "save_location_log": "保存先: {path}",
        "update_downloaded_log": "更新をダウンロードしました: {path}",
        "update_download_failed_log": "更新のダウンロードに失敗しました: {error}",
        "update_title": "更新",
        "new_version_downloaded_msg": "新しいバージョンをダウンロードしました:\n{path}",
    },
    "pt": {
        "update_checking_log": "Verificando atualizações...",
        "update_failed_log": "Falha na verificação: {error}",
        "remote_version_log": "Versão do servidor: {version}",
        "current_version_log": "Versão atual: {version}",
        "app_up_to_date_log": "O app está atualizado.",
        "new_version_downloading_log": "Nova versão encontrada. Baixando pacote...",
        "save_location_log": "Local de salvamento: {path}",
        "update_downloaded_log": "Atualização baixada: {path}",
        "update_download_failed_log": "Falha no download: {error}",
        "update_title": "Atualização",
        "new_version_downloaded_msg": "Nova versão baixada:\n{path}",
    },
    "ru": {
        "update_checking_log": "Проверка обновлений...",
        "update_failed_log": "Проверка обновлений не удалась: {error}",
        "remote_version_log": "Версия на сервере: {version}",
        "current_version_log": "Текущая версия: {version}",
        "app_up_to_date_log": "Приложение обновлено.",
        "new_version_downloading_log": "Найдена новая версия. Загрузка пакета...",
        "save_location_log": "Место сохранения: {path}",
        "update_downloaded_log": "Обновление загружено: {path}",
        "update_download_failed_log": "Ошибка загрузки: {error}",
        "update_title": "Обновление",
        "new_version_downloaded_msg": "Новая версия загружена:\n{path}",
    },
    "zh": {
        "update_checking_log": "正在检查更新...",
        "update_failed_log": "检查更新失败: {error}",
        "remote_version_log": "服务器版本: {version}",
        "current_version_log": "当前版本: {version}",
        "app_up_to_date_log": "应用已是最新。",
        "new_version_downloading_log": "发现新版本。正在下载更新包...",
        "save_location_log": "保存位置: {path}",
        "update_downloaded_log": "更新已下载: {path}",
        "update_download_failed_log": "下载更新失败: {error}",
        "update_title": "更新",
        "new_version_downloaded_msg": "新版本已下载:\n{path}",
    },
    "ar": {
        "update_checking_log": "جارٍ التحقق من التحديثات...",
        "update_failed_log": "فشل التحقق من التحديث: {error}",
        "remote_version_log": "إصدار الخادم: {version}",
        "current_version_log": "الإصدار الحالي: {version}",
        "app_up_to_date_log": "التطبيق محدث.",
        "new_version_downloading_log": "تم العثور على إصدار جديد. جارٍ التنزيل...",
        "save_location_log": "مكان الحفظ: {path}",
        "update_downloaded_log": "تم تنزيل التحديث: {path}",
        "update_download_failed_log": "فشل تنزيل التحديث: {error}",
        "update_title": "تحديث",
        "new_version_downloaded_msg": "تم تنزيل الإصدار الجديد:\n{path}",
    },
    "nl": {
        "update_checking_log": "Updates controleren...",
        "update_failed_log": "Updatecontrole mislukt: {error}",
        "remote_version_log": "Serverversie: {version}",
        "current_version_log": "Huidige versie: {version}",
        "app_up_to_date_log": "De app is actueel.",
        "new_version_downloading_log": "Nieuwe versie gevonden. Updatepakket downloaden...",
        "save_location_log": "Opslaglocatie: {path}",
        "update_downloaded_log": "Update gedownload: {path}",
        "update_download_failed_log": "Download mislukt: {error}",
        "update_title": "Update",
        "new_version_downloaded_msg": "Nieuwe versie gedownload:\n{path}",
    },
    "pl": {
        "update_checking_log": "Sprawdzanie aktualizacji...",
        "update_failed_log": "Sprawdzanie nie powiodło się: {error}",
        "remote_version_log": "Wersja serwera: {version}",
        "current_version_log": "Aktualna wersja: {version}",
        "app_up_to_date_log": "Aplikacja jest aktualna.",
        "new_version_downloading_log": "Znaleziono nową wersję. Pobieranie pakietu...",
        "save_location_log": "Miejsce zapisu: {path}",
        "update_downloaded_log": "Aktualizacja pobrana: {path}",
        "update_download_failed_log": "Pobieranie nie powiodło się: {error}",
        "update_title": "Aktualizacja",
        "new_version_downloaded_msg": "Nowa wersja pobrana:\n{path}",
    },
}
for _lang, _data in _UPDATE_LOG_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)

_GAME_COUNTER_TEXT = {
    "en": "Game {current}/{total}",
    "tr": "Oyun {current}/{total}",
    "fr": "Jeu {current}/{total}",
    "es": "Juego {current}/{total}",
    "it": "Gioco {current}/{total}",
    "el": "Παιχνίδι {current}/{total}",
    "ko": "게임 {current}/{total}",
    "ja": "ゲーム {current}/{total}",
    "de": "Spiel {current}/{total}",
    "pt": "Jogo {current}/{total}",
    "ru": "Игра {current}/{total}",
    "zh": "游戏 {current}/{total}",
    "ar": "اللعبة {current}/{total}",
    "nl": "Game {current}/{total}",
    "pl": "Gra {current}/{total}",
}
for _lang, _value in _GAME_COUNTER_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang]["game_counter"] = _value


_APP_RUNTIME_TEXT = {
    "en": {
        "dialog_select_multi_folder": "Select the main folder containing games",
        "dialog_select_game_folder": "Select game folder",
        "dialog_select_exfat": "Select .exfat file",
        "dialog_all_files": "All files",
        "dialog_select_output": "Select output folder",
        "dialog_select_temp": "Select temp folder",
        "missing_info_title": "Missing information",
        "invalid_source": "Select a valid source path.",
        "select_output_warning": "Select an output folder.",
        "output_create_failed": "Output folder could not be created.",
        "select_temp_warning": "Select a temp folder.",
        "temp_create_failed": "Temp folder could not be created.",
        "multi_select_valid": "For multi mode, select a main folder containing game folders or .exfat files.",
        "file_name_empty": "File name cannot be empty.",
        "multi_list_no_main": "Multi list: Main folder not selected.",
        "multi_folder_read_failed": "Multi folder could not be read: {error}",
        "multi_list_no_games": "Multi list: no game folder or .exfat found.",
        "multi_game_list_title": "Multi game list:",
        "multi_list_found": "Multi list: {count} games found.",
        "file_name_detected": "File name detected: {name}",
        "file_name_not_detected": "File name could not be detected: {error}",
        "cancel_requested": "Cancel requested.",
        "status_running": "Running",
        "phase_preparing": "Preparing",
        "method_log": "Method: Folder -> temp pfs_image.dat (--no-compress) -> .ffpfsc (--compress)",
        "version_log": "Version: {version}",
        "cpu_limit_log": "CPU limit: {cpu}",
        "compression_level_log": "Compression level: {level}",
        "temp_log": "Temp: {path}",
        "runner_internal": "MkPFS runner: bundled inside EXE",
        "runner_external": "MkPFS runner: {runner}",
        "runner_not_found": "not found",
        "mkpfs_missing": "Error: MkPFS was not found in this Python environment. Select the correct Python or install MkPFS.",
        "python_recommendation": "Suggestion: run with py -3.11",
        "no_games_found": "No games found to process.",
        "game_index_title": "[{current}/{total}] Game: {game}",
        "source_log": "Source: {path}",
        "output_log": "Output: {path}",
        "previous_size_log": "Previous size: {size}",
        "temp_dat_log": "Temporary DAT: {path}",
        "fakelib_skip": "Fakelib could not be downloaded, this game was skipped.",
        "stage_image_dat_creating": "1/2 creating image.dat",
        "dat_estimate_intro": "If MkPFS does not show percent in the first stage, estimated progress will be shown from DAT size.",
        "dat_estimate_formula": "Formula: pfs_image.dat.tmp size / source size. This stage is 0%-50% of the total bar.",
        "first_stage_failed": "Error: First stage failed. Code: {code}",
        "status_dat_done": "DAT completed",
        "phase_dat_done": "1/2 image.dat completed",
        "image_dat_stage_done": "image.dat stage completed. Moving to compression stage.",
        "output_removed": "Existing output removed, it will be overwritten: {path}",
        "output_path_not_file": "Error: Output path is not a file and cannot be overwritten: {path}",
        "output_remove_failed": "Error: Existing output could not be removed: {error}",
        "output_exists_skipped": "Output file already exists, process skipped: {path}",
        "stage_ffpfsc_creating": "2/2 creating .ffpfsc",
        "second_stage_failed": "Error: Second stage failed. Code: {code}",
        "phase_extra_verify": "Extra verification running",
        "image_dat_kept": "image.dat kept: {path}",
        "status_done": "Completed",
        "phase_done": "Done",
        "completed_log": "COMPLETED: {path}",
        "summary_title": "Process summary:",
        "game_name_log": "Game name: {game}",
        "new_size_log": "New size: {size}",
        "gain_log": "Gain: {size} ({percent:.2f}%)",
        "duration_log": "Process duration: {duration}",
        "log_written": "log.txt written: {path}",
        "log_write_failed": "log.txt could not be written: {error}",
        "last_summary": "Last job: {game} | {previous} → {new} | Gain {percent:.2f}% | Time {duration}",
        "delete_source_phase": "Deleting source game folder",
        "all_done": "All processes finished.",
        "status_ready": "Ready",
        "phase_waiting": "Waiting",
        "unexpected_error": "Unexpected error: {error}",
        "dat_estimate_status": "DAT estimate {percent:.1f}%",
        "dat_writing_status": "Writing DAT",
        "dat_writing_phase_full": "1/2 writing image.dat: {current} / {total}",
        "dat_writing_phase": "1/2 writing image.dat: {current}",
        "mkpfs_started": "MkPFS started",
        "process_start_failed": "Error: process could not be started: {error}",
        "disk_writing": "Writing to disk",
        "disk_write_wait": "Writing file to the hard drive. Please wait...",
        "build_summary_receiving": "Receiving Build Summary",
        "continue_status": "Process is still running",
        "continue_wait": "Process is still running. Please wait...",
        "fakelib_only_folders": "Fakelib can only be added to game folders; skipped for file source.",
        "fakelib_updating": "Updating fakelib: {filename}",
        "fakelib_empty": "Error: {filename} downloaded empty.",
        "fakelib_ready": "Fakelib ready: fakelib\\{filename}",
        "fakelib_update_failed": "Error: fakelib file could not be updated: {filename} -> {error}",
        "delete_skip_not_folder": "Delete game folder is selected, but source is not a folder; delete skipped.",
        "delete_safety_same": "Source folder was not deleted for safety: source is the same as output/temp folder.",
        "delete_safety_inside": "Source folder was not deleted for safety: output/temp folder is inside the source folder.",
        "game_folder_deleted": "Game folder deleted: {path}",
        "game_folder_delete_failed": "Game folder could not be deleted: {error}",
        "summary_game_name": "Game name",
        "summary_previous_size": "Previous size",
        "summary_new_size": "New size",
        "summary_gain": "Gain",
        "summary_duration": "Process duration",
        "summary_output": "Output",
        "duration_hms": "{h} h {m} min {s} sec",
        "duration_ms": "{m} min {s} sec",
        "duration_s": "{s} sec",
    },
    "tr": {
        "dialog_select_multi_folder": "Oyunların bulunduğu ana klasörü seç",
        "dialog_select_game_folder": "Oyun klasörü seç",
        "dialog_select_exfat": ".exfat dosyası seç",
        "dialog_all_files": "Tüm dosyalar",
        "dialog_select_output": "Çıkış klasörü seç",
        "dialog_select_temp": "Temp klasörü seç",
        "missing_info_title": "Eksik bilgi",
        "invalid_source": "Geçerli bir kaynak yolu seç.",
        "select_output_warning": "Çıkış klasörü seç.",
        "output_create_failed": "Çıkış klasörü oluşturulamadı.",
        "select_temp_warning": "Temp klasörü seç.",
        "temp_create_failed": "Temp klasörü oluşturulamadı.",
        "multi_select_valid": "Çoklu mod için içinde oyun klasörleri veya .exfat dosyaları olan bir ana klasör seç.",
        "file_name_empty": "Dosya adı boş olamaz.",
        "multi_list_no_main": "Çoklu liste: Ana klasör seçilmedi.",
        "multi_folder_read_failed": "Çoklu klasör okunamadı: {error}",
        "multi_list_no_games": "Çoklu liste: oyun klasörü veya .exfat bulunamadı.",
        "multi_game_list_title": "Çoklu oyun listesi:",
        "multi_list_found": "Çoklu liste: {count} oyun bulundu.",
        "file_name_detected": "Dosya adı belirlendi: {name}",
        "file_name_not_detected": "Dosya adı alınamadı: {error}",
        "cancel_requested": "İptal istendi.",
        "status_running": "Çalışıyor",
        "phase_preparing": "Hazırlanıyor",
        "method_log": "Yöntem: Klasör -> temp pfs_image.dat (--no-compress) -> .ffpfsc (--compress)",
        "version_log": "Sürüm: {version}",
        "cpu_limit_log": "CPU limiti: {cpu}",
        "compression_level_log": "Sıkıştırma seviyesi: {level}",
        "temp_log": "Temp: {path}",
        "runner_internal": "MkPFS çalıştırıcı: EXE içi paket",
        "runner_external": "MkPFS çalıştırıcı: {runner}",
        "runner_not_found": "bulunamadı",
        "mkpfs_missing": "Hata: Bu Python ortamında MkPFS bulunamadı. Doğru Python'u seç veya MkPFS kur.",
        "python_recommendation": "Öneri: py -3.11 ile çalıştır.",
        "no_games_found": "İşlenecek oyun bulunamadı.",
        "game_index_title": "[{current}/{total}] Oyun: {game}",
        "source_log": "Kaynak: {path}",
        "output_log": "Çıkış: {path}",
        "previous_size_log": "Önceki boyut: {size}",
        "temp_dat_log": "Geçici DAT: {path}",
        "fakelib_skip": "Fakelib indirilemediği için bu oyun atlandı.",
        "stage_image_dat_creating": "1/2 image.dat oluşturuluyor",
        "dat_estimate_intro": "İlk aşamada MkPFS yüzde basmazsa DAT boyutundan tahmini ilerleme gösterilecek.",
        "dat_estimate_formula": "Hesap: pfs_image.dat.tmp boyutu / kaynak boyutu. Bu aşama toplam barın %0-%50 arasıdır.",
        "first_stage_failed": "Hata: İlk aşama başarısız. Kod: {code}",
        "status_dat_done": "DAT tamamlandı",
        "phase_dat_done": "1/2 image.dat tamamlandı",
        "image_dat_stage_done": "image.dat aşaması tamamlandı. Sıkıştırma aşamasına geçiliyor.",
        "output_removed": "Mevcut çıktı silindi, üzerine yazılacak: {path}",
        "output_path_not_file": "Hata: Çıkış yolu dosya değil, üzerine yazılamaz: {path}",
        "output_remove_failed": "Hata: Mevcut çıktı silinemedi: {error}",
        "output_exists_skipped": "Çıkış dosyası zaten var, işlem atlandı: {path}",
        "stage_ffpfsc_creating": "2/2 .ffpfsc oluşturuluyor",
        "second_stage_failed": "Hata: İkinci aşama başarısız. Kod: {code}",
        "phase_extra_verify": "Ek doğrulama çalışıyor",
        "image_dat_kept": "image.dat saklandı: {path}",
        "status_done": "Tamamlandı",
        "phase_done": "Bitti",
        "completed_log": "TAMAMLANDI: {path}",
        "summary_title": "İşlem özeti:",
        "game_name_log": "Oyun adı: {game}",
        "new_size_log": "Yeni boyut: {size}",
        "gain_log": "Kazanım: {size} (%{percent:.2f})",
        "duration_log": "İşlem süresi: {duration}",
        "log_written": "log.txt yazıldı: {path}",
        "log_write_failed": "log.txt yazılamadı: {error}",
        "last_summary": "Son işlem: {game} | {previous} → {new} | Kazanım %{percent:.2f} | Süre {duration}",
        "delete_source_phase": "Kaynak oyun klasörü siliniyor",
        "all_done": "Tüm işlemler bitti.",
        "status_ready": "Hazır",
        "phase_waiting": "Bekliyor",
        "unexpected_error": "Beklenmeyen hata: {error}",
        "dat_estimate_status": "DAT tahmini %{percent:.1f}",
        "dat_writing_status": "DAT yazılıyor",
        "dat_writing_phase_full": "1/2 image.dat yazılıyor: {current} / {total}",
        "dat_writing_phase": "1/2 image.dat yazılıyor: {current}",
        "mkpfs_started": "MkPFS başladı",
        "process_start_failed": "Hata: işlem başlatılamadı: {error}",
        "disk_writing": "Diske yazılıyor",
        "disk_write_wait": "Dosya harddiske yazılıyor. Lütfen bekleyiniz...",
        "build_summary_receiving": "Build Summary alınıyor",
        "continue_status": "İşlem devam ediyor",
        "continue_wait": "İşlem devam ediyor. Lütfen bekleyiniz...",
        "fakelib_only_folders": "Fakelib yalnızca oyun klasörlerine eklenebilir; dosya kaynağı için atlandı.",
        "fakelib_updating": "Fakelib güncelleniyor: {filename}",
        "fakelib_empty": "Hata: {filename} boş indi.",
        "fakelib_ready": "Fakelib hazır: fakelib\\{filename}",
        "fakelib_update_failed": "Hata: fakelib dosyası güncellenemedi: {filename} -> {error}",
        "delete_skip_not_folder": "Oyun klasörü sil seçili ama kaynak klasör değil; silme atlandı.",
        "delete_safety_same": "Güvenlik nedeniyle kaynak klasörü silinmedi: kaynak, çıkış/temp klasörüyle aynı.",
        "delete_safety_inside": "Güvenlik nedeniyle kaynak klasörü silinmedi: çıkış/temp klasörü kaynak klasörün içinde.",
        "game_folder_deleted": "Oyun klasörü silindi: {path}",
        "game_folder_delete_failed": "Oyun klasörü silinemedi: {error}",
        "summary_game_name": "Oyun adı",
        "summary_previous_size": "Önceki boyut",
        "summary_new_size": "Yeni boyut",
        "summary_gain": "Kazanım",
        "summary_duration": "İşlem süresi",
        "summary_output": "Çıkış",
        "duration_hms": "{h} sa {m} dk {s} sn",
        "duration_ms": "{m} dk {s} sn",
        "duration_s": "{s} sn",
    },
}
for _lang, _data in _APP_RUNTIME_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)

_FINAL_PUBLIC_TEXT = {
    "en": {
        "checking_updates": "Checking...",
        "app_current": "MkPFS Up to Date",
        "new_version": "New MkPFS Version",
        "mkpfs_update_checking_log": "Checking MkPFS updates...",
        "mkpfs_update_source_log": "Source: {url}",
        "mkpfs_update_failed_log": "MkPFS update check failed: {error}",
        "current_mkpfs_version_log": "Bundled MkPFS version: {version}",
        "latest_mkpfs_version_log": "GitHub latest MkPFS version: {version}",
        "mkpfs_up_to_date_log": "MkPFS is up to date.",
        "mkpfs_latest_unknown_log": "Could not read the latest MkPFS version.",
        "mkpfs_new_version_log": "New MkPFS version found: {version}",
        "packager_github_note": "Note: Check the new PS5-PFS-Packager version on Github.",
        "fakelib_skip": "Fakelib could not be added, this game was skipped.",
        "fakelib_updating": "Adding fakelib: {filename}",
        "fakelib_missing_embedded": "Error: embedded fakelib file not found: fakelib\\{filename}",
        "fakelib_build_hint": "Make sure the EXE is built with --add-data \"fakelib;fakelib\" and the fakelib folder is included.",
        "fakelib_ready": "Fakelib ready: fakelib\\{filename}",
        "fakelib_update_failed": "Error: fakelib file could not be added: {filename} -> {error}",
    },
    "tr": {
        "checking_updates": "Kontrol ediliyor...",
        "app_current": "MkPFS Güncel",
        "new_version": "Yeni MkPFS Sürümü",
        "mkpfs_update_checking_log": "MkPFS güncelleme kontrolü yapılıyor...",
        "mkpfs_update_source_log": "Kaynak: {url}",
        "mkpfs_update_failed_log": "MkPFS güncelleme kontrolü başarısız: {error}",
        "current_mkpfs_version_log": "EXE içindeki MkPFS sürümü: {version}",
        "latest_mkpfs_version_log": "GitHub son MkPFS sürümü: {version}",
        "mkpfs_up_to_date_log": "MkPFS güncel.",
        "mkpfs_latest_unknown_log": "MkPFS son sürüm bilgisi alınamadı.",
        "mkpfs_new_version_log": "MkPFS yeni versiyon bulundu: {version}",
        "packager_github_note": "Not: PS5-PFS-Packager yeni sürümünü Github üzerinden kontrol edin.",
        "fakelib_skip": "Fakelib eklenemediği için bu oyun atlandı.",
        "fakelib_updating": "Fakelib ekleniyor: {filename}",
        "fakelib_missing_embedded": "Hata: EXE içindeki fakelib dosyası bulunamadı: fakelib\\{filename}",
        "fakelib_build_hint": "Build alırken --add-data \"fakelib;fakelib\" ekli olduğundan ve fakelib klasörünün EXE ile paketlendiğinden emin ol.",
        "fakelib_ready": "Fakelib hazır: fakelib\\{filename}",
        "fakelib_update_failed": "Hata: fakelib dosyası eklenemedi: {filename} -> {error}",
    },
    "fr": {
        "checking_updates": "Vérification...",
        "app_current": "MkPFS à jour",
        "new_version": "Nouvelle version MkPFS",
        "mkpfs_update_checking_log": "Vérification des mises à jour MkPFS...",
        "mkpfs_update_source_log": "Source : {url}",
        "mkpfs_update_failed_log": "Échec de la vérification MkPFS : {error}",
        "current_mkpfs_version_log": "Version MkPFS intégrée : {version}",
        "latest_mkpfs_version_log": "Dernière version MkPFS sur GitHub : {version}",
        "mkpfs_up_to_date_log": "MkPFS est à jour.",
        "mkpfs_latest_unknown_log": "Impossible de lire la dernière version de MkPFS.",
        "mkpfs_new_version_log": "Nouvelle version MkPFS trouvée : {version}",
        "packager_github_note": "Remarque : vérifiez la nouvelle version de PS5-PFS-Packager sur Github.",
        "fakelib_skip": "Fakelib n’a pas pu être ajouté, ce jeu a été ignoré.",
        "fakelib_updating": "Ajout de fakelib : {filename}",
        "fakelib_missing_embedded": "Erreur : fichier fakelib intégré introuvable : fakelib\\{filename}",
        "fakelib_build_hint": "Assurez-vous que l’EXE est compilé avec --add-data \"fakelib;fakelib\" et que le dossier fakelib est inclus.",
        "fakelib_ready": "Fakelib prêt : fakelib\\{filename}",
        "fakelib_update_failed": "Erreur : impossible d’ajouter le fichier fakelib : {filename} -> {error}",
    },
    "es": {
        "checking_updates": "Comprobando...",
        "app_current": "MkPFS actualizado",
        "new_version": "Nueva versión de MkPFS",
        "mkpfs_update_checking_log": "Comprobando actualizaciones de MkPFS...",
        "mkpfs_update_source_log": "Fuente: {url}",
        "mkpfs_update_failed_log": "Error al comprobar MkPFS: {error}",
        "current_mkpfs_version_log": "Versión MkPFS integrada: {version}",
        "latest_mkpfs_version_log": "Última versión MkPFS en GitHub: {version}",
        "mkpfs_up_to_date_log": "MkPFS está actualizado.",
        "mkpfs_latest_unknown_log": "No se pudo leer la última versión de MkPFS.",
        "mkpfs_new_version_log": "Nueva versión de MkPFS encontrada: {version}",
        "packager_github_note": "Nota: compruebe la nueva versión de PS5-PFS-Packager en Github.",
        "fakelib_skip": "No se pudo añadir fakelib, se omitió este juego.",
        "fakelib_updating": "Añadiendo fakelib: {filename}",
        "fakelib_missing_embedded": "Error: archivo fakelib incrustado no encontrado: fakelib\\{filename}",
        "fakelib_build_hint": "Asegúrese de compilar el EXE con --add-data \"fakelib;fakelib\" e incluir la carpeta fakelib.",
        "fakelib_ready": "Fakelib listo: fakelib\\{filename}",
        "fakelib_update_failed": "Error: no se pudo añadir el archivo fakelib: {filename} -> {error}",
    },
    "it": {
        "checking_updates": "Controllo...",
        "app_current": "MkPFS aggiornato",
        "new_version": "Nuova versione MkPFS",
        "mkpfs_update_checking_log": "Controllo aggiornamenti MkPFS...",
        "mkpfs_update_source_log": "Fonte: {url}",
        "mkpfs_update_failed_log": "Controllo aggiornamenti MkPFS non riuscito: {error}",
        "current_mkpfs_version_log": "Versione MkPFS integrata: {version}",
        "latest_mkpfs_version_log": "Ultima versione MkPFS su GitHub: {version}",
        "mkpfs_up_to_date_log": "MkPFS è aggiornato.",
        "mkpfs_latest_unknown_log": "Impossibile leggere l’ultima versione di MkPFS.",
        "mkpfs_new_version_log": "Nuova versione MkPFS trovata: {version}",
        "packager_github_note": "Nota: controlla la nuova versione di PS5-PFS-Packager su Github.",
        "fakelib_skip": "Impossibile aggiungere fakelib, questo gioco è stato saltato.",
        "fakelib_updating": "Aggiunta fakelib: {filename}",
        "fakelib_missing_embedded": "Errore: file fakelib incorporato non trovato: fakelib\\{filename}",
        "fakelib_build_hint": "Assicurati che l’EXE sia compilato con --add-data \"fakelib;fakelib\" e che la cartella fakelib sia inclusa.",
        "fakelib_ready": "Fakelib pronto: fakelib\\{filename}",
        "fakelib_update_failed": "Errore: impossibile aggiungere il file fakelib: {filename} -> {error}",
    },
    "de": {
        "checking_updates": "Prüfe...",
        "app_current": "MkPFS aktuell",
        "new_version": "Neue MkPFS-Version",
        "mkpfs_update_checking_log": "MkPFS-Updates werden geprüft...",
        "mkpfs_update_source_log": "Quelle: {url}",
        "mkpfs_update_failed_log": "MkPFS-Updateprüfung fehlgeschlagen: {error}",
        "current_mkpfs_version_log": "Gebündelte MkPFS-Version: {version}",
        "latest_mkpfs_version_log": "Neueste MkPFS-Version auf GitHub: {version}",
        "mkpfs_up_to_date_log": "MkPFS ist aktuell.",
        "mkpfs_latest_unknown_log": "Neueste MkPFS-Version konnte nicht gelesen werden.",
        "mkpfs_new_version_log": "Neue MkPFS-Version gefunden: {version}",
        "packager_github_note": "Hinweis: Prüfen Sie die neue PS5-PFS-Packager-Version auf Github.",
        "fakelib_skip": "Fakelib konnte nicht hinzugefügt werden, dieses Spiel wurde übersprungen.",
        "fakelib_updating": "Fakelib wird hinzugefügt: {filename}",
        "fakelib_missing_embedded": "Fehler: eingebettete fakelib-Datei nicht gefunden: fakelib\\{filename}",
        "fakelib_build_hint": "Stellen Sie sicher, dass die EXE mit --add-data \"fakelib;fakelib\" erstellt wurde und der fakelib-Ordner enthalten ist.",
        "fakelib_ready": "Fakelib bereit: fakelib\\{filename}",
        "fakelib_update_failed": "Fehler: fakelib-Datei konnte nicht hinzugefügt werden: {filename} -> {error}",
    },
    "el": {
        "checking_updates": "Έλεγχος...",
        "app_current": "Το MkPFS είναι ενημερωμένο",
        "new_version": "Νέα έκδοση MkPFS",
        "mkpfs_update_checking_log": "Έλεγχος ενημερώσεων MkPFS...",
        "mkpfs_update_source_log": "Πηγή: {url}",
        "mkpfs_update_failed_log": "Ο έλεγχος ενημέρωσης MkPFS απέτυχε: {error}",
        "current_mkpfs_version_log": "Ενσωματωμένη έκδοση MkPFS: {version}",
        "latest_mkpfs_version_log": "Τελευταία έκδοση MkPFS στο GitHub: {version}",
        "mkpfs_up_to_date_log": "Το MkPFS είναι ενημερωμένο.",
        "mkpfs_latest_unknown_log": "Δεν ήταν δυνατή η ανάγνωση της τελευταίας έκδοσης MkPFS.",
        "mkpfs_new_version_log": "Βρέθηκε νέα έκδοση MkPFS: {version}",
        "packager_github_note": "Σημείωση: ελέγξτε τη νέα έκδοση του PS5-PFS-Packager στο Github.",
        "fakelib_skip": "Δεν ήταν δυνατή η προσθήκη fakelib, αυτό το παιχνίδι παραλείφθηκε.",
        "fakelib_updating": "Προσθήκη fakelib: {filename}",
        "fakelib_missing_embedded": "Σφάλμα: το ενσωματωμένο αρχείο fakelib δεν βρέθηκε: fakelib\\{filename}",
        "fakelib_build_hint": "Βεβαιωθείτε ότι το EXE δημιουργήθηκε με --add-data \"fakelib;fakelib\" και ότι περιλαμβάνεται ο φάκελος fakelib.",
        "fakelib_ready": "Fakelib έτοιμο: fakelib\\{filename}",
        "fakelib_update_failed": "Σφάλμα: δεν ήταν δυνατή η προσθήκη του αρχείου fakelib: {filename} -> {error}",
    },
    "ko": {
        "checking_updates": "확인 중...",
        "app_current": "MkPFS 최신",
        "new_version": "새 MkPFS 버전",
        "mkpfs_update_checking_log": "MkPFS 업데이트 확인 중...",
        "mkpfs_update_source_log": "소스: {url}",
        "mkpfs_update_failed_log": "MkPFS 업데이트 확인 실패: {error}",
        "current_mkpfs_version_log": "내장 MkPFS 버전: {version}",
        "latest_mkpfs_version_log": "GitHub 최신 MkPFS 버전: {version}",
        "mkpfs_up_to_date_log": "MkPFS가 최신입니다.",
        "mkpfs_latest_unknown_log": "최신 MkPFS 버전을 읽을 수 없습니다.",
        "mkpfs_new_version_log": "새 MkPFS 버전 발견: {version}",
        "packager_github_note": "참고: Github에서 새 PS5-PFS-Packager 버전을 확인하세요.",
        "fakelib_skip": "fakelib을 추가할 수 없어 이 게임을 건너뜁니다.",
        "fakelib_updating": "fakelib 추가 중: {filename}",
        "fakelib_missing_embedded": "오류: 내장 fakelib 파일을 찾을 수 없습니다: fakelib\\{filename}",
        "fakelib_build_hint": "EXE가 --add-data \"fakelib;fakelib\"로 빌드되었고 fakelib 폴더가 포함되었는지 확인하세요.",
        "fakelib_ready": "Fakelib 준비됨: fakelib\\{filename}",
        "fakelib_update_failed": "오류: fakelib 파일을 추가할 수 없습니다: {filename} -> {error}",
    },
    "ja": {
        "checking_updates": "確認中...",
        "app_current": "MkPFS は最新です",
        "new_version": "新しい MkPFS バージョン",
        "mkpfs_update_checking_log": "MkPFS の更新を確認中...",
        "mkpfs_update_source_log": "ソース: {url}",
        "mkpfs_update_failed_log": "MkPFS 更新確認に失敗しました: {error}",
        "current_mkpfs_version_log": "内蔵 MkPFS バージョン: {version}",
        "latest_mkpfs_version_log": "GitHub 最新 MkPFS バージョン: {version}",
        "mkpfs_up_to_date_log": "MkPFS は最新です。",
        "mkpfs_latest_unknown_log": "最新の MkPFS バージョンを読み取れませんでした。",
        "mkpfs_new_version_log": "新しい MkPFS バージョンが見つかりました: {version}",
        "packager_github_note": "注意: Github で新しい PS5-PFS-Packager バージョンを確認してください。",
        "fakelib_skip": "fakelib を追加できなかったため、このゲームはスキップされました。",
        "fakelib_updating": "fakelib を追加中: {filename}",
        "fakelib_missing_embedded": "エラー: 内蔵 fakelib ファイルが見つかりません: fakelib\\{filename}",
        "fakelib_build_hint": "EXE が --add-data \"fakelib;fakelib\" でビルドされ、fakelib フォルダが含まれていることを確認してください。",
        "fakelib_ready": "Fakelib 準備完了: fakelib\\{filename}",
        "fakelib_update_failed": "エラー: fakelib ファイルを追加できませんでした: {filename} -> {error}",
    },
    "pt": {
        "checking_updates": "Verificando...",
        "app_current": "MkPFS atualizado",
        "new_version": "Nova versão MkPFS",
        "mkpfs_update_checking_log": "Verificando atualizações do MkPFS...",
        "mkpfs_update_source_log": "Fonte: {url}",
        "mkpfs_update_failed_log": "Falha ao verificar MkPFS: {error}",
        "current_mkpfs_version_log": "Versão MkPFS embutida: {version}",
        "latest_mkpfs_version_log": "Última versão MkPFS no GitHub: {version}",
        "mkpfs_up_to_date_log": "MkPFS está atualizado.",
        "mkpfs_latest_unknown_log": "Não foi possível ler a última versão do MkPFS.",
        "mkpfs_new_version_log": "Nova versão do MkPFS encontrada: {version}",
        "packager_github_note": "Nota: verifique a nova versão do PS5-PFS-Packager no Github.",
        "fakelib_skip": "Não foi possível adicionar fakelib, este jogo foi ignorado.",
        "fakelib_updating": "Adicionando fakelib: {filename}",
        "fakelib_missing_embedded": "Erro: arquivo fakelib embutido não encontrado: fakelib\\{filename}",
        "fakelib_build_hint": "Certifique-se de que o EXE foi compilado com --add-data \"fakelib;fakelib\" e que a pasta fakelib foi incluída.",
        "fakelib_ready": "Fakelib pronto: fakelib\\{filename}",
        "fakelib_update_failed": "Erro: não foi possível adicionar o arquivo fakelib: {filename} -> {error}",
    },
    "ru": {
        "checking_updates": "Проверка...",
        "app_current": "MkPFS обновлён",
        "new_version": "Новая версия MkPFS",
        "mkpfs_update_checking_log": "Проверка обновлений MkPFS...",
        "mkpfs_update_source_log": "Источник: {url}",
        "mkpfs_update_failed_log": "Проверка MkPFS не удалась: {error}",
        "current_mkpfs_version_log": "Встроенная версия MkPFS: {version}",
        "latest_mkpfs_version_log": "Последняя версия MkPFS на GitHub: {version}",
        "mkpfs_up_to_date_log": "MkPFS обновлён.",
        "mkpfs_latest_unknown_log": "Не удалось прочитать последнюю версию MkPFS.",
        "mkpfs_new_version_log": "Найдена новая версия MkPFS: {version}",
        "packager_github_note": "Примечание: проверьте новую версию PS5-PFS-Packager на Github.",
        "fakelib_skip": "Не удалось добавить fakelib, эта игра пропущена.",
        "fakelib_updating": "Добавление fakelib: {filename}",
        "fakelib_missing_embedded": "Ошибка: встроенный файл fakelib не найден: fakelib\\{filename}",
        "fakelib_build_hint": "Убедитесь, что EXE собран с --add-data \"fakelib;fakelib\" и папка fakelib включена.",
        "fakelib_ready": "Fakelib готов: fakelib\\{filename}",
        "fakelib_update_failed": "Ошибка: не удалось добавить файл fakelib: {filename} -> {error}",
    },
    "zh": {
        "checking_updates": "检查中...",
        "app_current": "MkPFS 已是最新",
        "new_version": "新的 MkPFS 版本",
        "mkpfs_update_checking_log": "正在检查 MkPFS 更新...",
        "mkpfs_update_source_log": "来源: {url}",
        "mkpfs_update_failed_log": "MkPFS 更新检查失败: {error}",
        "current_mkpfs_version_log": "内置 MkPFS 版本: {version}",
        "latest_mkpfs_version_log": "GitHub 最新 MkPFS 版本: {version}",
        "mkpfs_up_to_date_log": "MkPFS 已是最新。",
        "mkpfs_latest_unknown_log": "无法读取最新的 MkPFS 版本。",
        "mkpfs_new_version_log": "发现新的 MkPFS 版本: {version}",
        "packager_github_note": "注意：请在 Github 上检查新的 PS5-PFS-Packager 版本。",
        "fakelib_skip": "无法添加 fakelib，已跳过此游戏。",
        "fakelib_updating": "正在添加 fakelib: {filename}",
        "fakelib_missing_embedded": "错误：找不到内置 fakelib 文件: fakelib\\{filename}",
        "fakelib_build_hint": "请确认 EXE 使用 --add-data \"fakelib;fakelib\" 构建，并包含 fakelib 文件夹。",
        "fakelib_ready": "Fakelib 就绪: fakelib\\{filename}",
        "fakelib_update_failed": "错误：无法添加 fakelib 文件: {filename} -> {error}",
    },
    "ar": {
        "checking_updates": "جارٍ التحقق...",
        "app_current": "MkPFS محدث",
        "new_version": "إصدار MkPFS جديد",
        "mkpfs_update_checking_log": "جارٍ التحقق من تحديثات MkPFS...",
        "mkpfs_update_source_log": "المصدر: {url}",
        "mkpfs_update_failed_log": "فشل التحقق من تحديث MkPFS: {error}",
        "current_mkpfs_version_log": "إصدار MkPFS المضمن: {version}",
        "latest_mkpfs_version_log": "آخر إصدار MkPFS على GitHub: {version}",
        "mkpfs_up_to_date_log": "MkPFS محدث.",
        "mkpfs_latest_unknown_log": "تعذر قراءة آخر إصدار من MkPFS.",
        "mkpfs_new_version_log": "تم العثور على إصدار MkPFS جديد: {version}",
        "packager_github_note": "ملاحظة: تحقق من إصدار PS5-PFS-Packager الجديد على Github.",
        "fakelib_skip": "تعذرت إضافة fakelib، تم تخطي هذه اللعبة.",
        "fakelib_updating": "جارٍ إضافة fakelib: {filename}",
        "fakelib_missing_embedded": "خطأ: لم يتم العثور على ملف fakelib المضمن: fakelib\\{filename}",
        "fakelib_build_hint": "تأكد من بناء EXE باستخدام --add-data \"fakelib;fakelib\" وأن مجلد fakelib مضمن.",
        "fakelib_ready": "Fakelib جاهز: fakelib\\{filename}",
        "fakelib_update_failed": "خطأ: تعذرت إضافة ملف fakelib: {filename} -> {error}",
    },
    "nl": {
        "checking_updates": "Controleren...",
        "app_current": "MkPFS actueel",
        "new_version": "Nieuwe MkPFS-versie",
        "mkpfs_update_checking_log": "MkPFS-updates controleren...",
        "mkpfs_update_source_log": "Bron: {url}",
        "mkpfs_update_failed_log": "MkPFS-updatecontrole mislukt: {error}",
        "current_mkpfs_version_log": "Ingebouwde MkPFS-versie: {version}",
        "latest_mkpfs_version_log": "Nieuwste MkPFS-versie op GitHub: {version}",
        "mkpfs_up_to_date_log": "MkPFS is actueel.",
        "mkpfs_latest_unknown_log": "Kon de nieuwste MkPFS-versie niet lezen.",
        "mkpfs_new_version_log": "Nieuwe MkPFS-versie gevonden: {version}",
        "packager_github_note": "Opmerking: controleer de nieuwe PS5-PFS-Packager-versie op Github.",
        "fakelib_skip": "Fakelib kon niet worden toegevoegd, deze game is overgeslagen.",
        "fakelib_updating": "Fakelib toevoegen: {filename}",
        "fakelib_missing_embedded": "Fout: ingebed fakelib-bestand niet gevonden: fakelib\\{filename}",
        "fakelib_build_hint": "Zorg ervoor dat de EXE is gebouwd met --add-data \"fakelib;fakelib\" en dat de fakelib-map is inbegrepen.",
        "fakelib_ready": "Fakelib gereed: fakelib\\{filename}",
        "fakelib_update_failed": "Fout: fakelib-bestand kon niet worden toegevoegd: {filename} -> {error}",
    },
    "pl": {
        "checking_updates": "Sprawdzanie...",
        "app_current": "MkPFS aktualny",
        "new_version": "Nowa wersja MkPFS",
        "mkpfs_update_checking_log": "Sprawdzanie aktualizacji MkPFS...",
        "mkpfs_update_source_log": "Źródło: {url}",
        "mkpfs_update_failed_log": "Sprawdzanie MkPFS nie powiodło się: {error}",
        "current_mkpfs_version_log": "Wbudowana wersja MkPFS: {version}",
        "latest_mkpfs_version_log": "Najnowsza wersja MkPFS na GitHub: {version}",
        "mkpfs_up_to_date_log": "MkPFS jest aktualny.",
        "mkpfs_latest_unknown_log": "Nie można odczytać najnowszej wersji MkPFS.",
        "mkpfs_new_version_log": "Znaleziono nową wersję MkPFS: {version}",
        "packager_github_note": "Uwaga: sprawdź nową wersję PS5-PFS-Packager na Github.",
        "fakelib_skip": "Nie można dodać fakelib, ta gra została pominięta.",
        "fakelib_updating": "Dodawanie fakelib: {filename}",
        "fakelib_missing_embedded": "Błąd: nie znaleziono wbudowanego pliku fakelib: fakelib\\{filename}",
        "fakelib_build_hint": "Upewnij się, że EXE zbudowano z --add-data \"fakelib;fakelib\" i że folder fakelib jest dołączony.",
        "fakelib_ready": "Fakelib gotowy: fakelib\\{filename}",
        "fakelib_update_failed": "Błąd: nie można dodać pliku fakelib: {filename} -> {error}",
    },
}
for _lang, _data in _FINAL_PUBLIC_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)

_ADD_FAKELIB_TEXT = {
    "en": "Add fakelib files",
    "tr": "Fakelib dosyalarını ekle",
    "fr": "Ajouter les fichiers fakelib",
    "es": "Añadir archivos fakelib",
    "it": "Aggiungi file fakelib",
    "el": "Προσθήκη αρχείων fakelib",
    "ko": "fakelib 파일 추가",
    "ja": "fakelib ファイルを追加",
    "de": "fakelib-Dateien hinzufügen",
    "pt": "Adicionar arquivos fakelib",
    "ru": "Добавить файлы fakelib",
    "zh": "添加 fakelib 文件",
    "ar": "إضافة ملفات fakelib",
    "nl": "fakelib-bestanden toevoegen",
    "pl": "Dodaj pliki fakelib",
}
for _lang, _value in _ADD_FAKELIB_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang]["add_fakelib"] = _value

_EXTERNAL_FAKELIB_TEXT = {
    "en": {
        "fakelib_skip": "Fakelib could not be copied, this game was skipped.",
        "fakelib_updating": "Copying fakelib: {filename}",
        "fakelib_ready": "Fakelib copied: fakelib\\{filename}",
        "fakelib_update_failed": "Error: fakelib file could not be copied: {filename} -> {error}",
        "fakelib_external_folder_missing": "Fakelib folder not found next to the program, skipped: {path}",
        "fakelib_external_file_missing": "Fakelib file not found, skipped: {filename}",
        "fakelib_no_files_copied": "No fakelib files were copied; conversion will continue.",
    },
    "tr": {
        "fakelib_skip": "Fakelib kopyalanamadığı için bu oyun atlandı.",
        "fakelib_updating": "Fakelib kopyalanıyor: {filename}",
        "fakelib_ready": "Fakelib kopyalandı: fakelib\\{filename}",
        "fakelib_update_failed": "Hata: fakelib dosyası kopyalanamadı: {filename} -> {error}",
        "fakelib_external_folder_missing": "Programın yanında fakelib klasörü bulunamadı, atlandı: {path}",
        "fakelib_external_file_missing": "Fakelib dosyası bulunamadı, atlandı: {filename}",
        "fakelib_no_files_copied": "Hiç fakelib dosyası kopyalanmadı; dönüştürme devam edecek.",
    },
    "fr": {
        "fakelib_skip": "Fakelib n’a pas pu être copié, ce jeu a été ignoré.",
        "fakelib_updating": "Copie de fakelib : {filename}",
        "fakelib_ready": "Fakelib copié : fakelib\\{filename}",
        "fakelib_update_failed": "Erreur : impossible de copier le fichier fakelib : {filename} -> {error}",
        "fakelib_external_folder_missing": "Dossier fakelib introuvable à côté du programme, ignoré : {path}",
        "fakelib_external_file_missing": "Fichier fakelib introuvable, ignoré : {filename}",
        "fakelib_no_files_copied": "Aucun fichier fakelib copié ; la conversion continue.",
    },
    "es": {
        "fakelib_skip": "No se pudo copiar fakelib, se omitió este juego.",
        "fakelib_updating": "Copiando fakelib: {filename}",
        "fakelib_ready": "Fakelib copiado: fakelib\\{filename}",
        "fakelib_update_failed": "Error: no se pudo copiar el archivo fakelib: {filename} -> {error}",
        "fakelib_external_folder_missing": "No se encontró la carpeta fakelib junto al programa, se omite: {path}",
        "fakelib_external_file_missing": "Archivo fakelib no encontrado, se omite: {filename}",
        "fakelib_no_files_copied": "No se copiaron archivos fakelib; la conversión continuará.",
    },
    "it": {
        "fakelib_skip": "Impossibile copiare fakelib, questo gioco è stato saltato.",
        "fakelib_updating": "Copia fakelib: {filename}",
        "fakelib_ready": "Fakelib copiato: fakelib\\{filename}",
        "fakelib_update_failed": "Errore: impossibile copiare il file fakelib: {filename} -> {error}",
        "fakelib_external_folder_missing": "Cartella fakelib non trovata accanto al programma, saltata: {path}",
        "fakelib_external_file_missing": "File fakelib non trovato, saltato: {filename}",
        "fakelib_no_files_copied": "Nessun file fakelib copiato; la conversione continuerà.",
    },
    "de": {
        "fakelib_skip": "Fakelib konnte nicht kopiert werden, dieses Spiel wurde übersprungen.",
        "fakelib_updating": "Fakelib wird kopiert: {filename}",
        "fakelib_ready": "Fakelib kopiert: fakelib\\{filename}",
        "fakelib_update_failed": "Fehler: fakelib-Datei konnte nicht kopiert werden: {filename} -> {error}",
        "fakelib_external_folder_missing": "Fakelib-Ordner neben dem Programm nicht gefunden, übersprungen: {path}",
        "fakelib_external_file_missing": "Fakelib-Datei nicht gefunden, übersprungen: {filename}",
        "fakelib_no_files_copied": "Keine fakelib-Dateien kopiert; die Konvertierung wird fortgesetzt.",
    },
    "el": {
        "fakelib_skip": "Δεν ήταν δυνατή η αντιγραφή του fakelib, αυτό το παιχνίδι παραλείφθηκε.",
        "fakelib_updating": "Αντιγραφή fakelib: {filename}",
        "fakelib_ready": "Το fakelib αντιγράφηκε: fakelib\\{filename}",
        "fakelib_update_failed": "Σφάλμα: δεν ήταν δυνατή η αντιγραφή του αρχείου fakelib: {filename} -> {error}",
        "fakelib_external_folder_missing": "Ο φάκελος fakelib δεν βρέθηκε δίπλα στο πρόγραμμα, παραλείφθηκε: {path}",
        "fakelib_external_file_missing": "Το αρχείο fakelib δεν βρέθηκε, παραλείφθηκε: {filename}",
        "fakelib_no_files_copied": "Δεν αντιγράφηκαν αρχεία fakelib· η μετατροπή θα συνεχιστεί.",
    },
    "ko": {
        "fakelib_skip": "fakelib을 복사할 수 없어 이 게임을 건너뜁니다.",
        "fakelib_updating": "fakelib 복사 중: {filename}",
        "fakelib_ready": "fakelib 복사됨: fakelib\\{filename}",
        "fakelib_update_failed": "오류: fakelib 파일을 복사할 수 없습니다: {filename} -> {error}",
        "fakelib_external_folder_missing": "프로그램 옆에 fakelib 폴더가 없어 건너뜁니다: {path}",
        "fakelib_external_file_missing": "fakelib 파일을 찾을 수 없어 건너뜁니다: {filename}",
        "fakelib_no_files_copied": "복사된 fakelib 파일이 없습니다. 변환은 계속됩니다.",
    },
    "ja": {
        "fakelib_skip": "fakelib をコピーできなかったため、このゲームはスキップされました。",
        "fakelib_updating": "fakelib をコピー中: {filename}",
        "fakelib_ready": "fakelib をコピーしました: fakelib\\{filename}",
        "fakelib_update_failed": "エラー: fakelib ファイルをコピーできませんでした: {filename} -> {error}",
        "fakelib_external_folder_missing": "プログラム横に fakelib フォルダが見つからないためスキップ: {path}",
        "fakelib_external_file_missing": "fakelib ファイルが見つからないためスキップ: {filename}",
        "fakelib_no_files_copied": "fakelib ファイルはコピーされませんでした。変換は続行します。",
    },
    "pt": {
        "fakelib_skip": "Não foi possível copiar fakelib, este jogo foi ignorado.",
        "fakelib_updating": "Copiando fakelib: {filename}",
        "fakelib_ready": "Fakelib copiado: fakelib\\{filename}",
        "fakelib_update_failed": "Erro: não foi possível copiar o arquivo fakelib: {filename} -> {error}",
        "fakelib_external_folder_missing": "Pasta fakelib não encontrada ao lado do programa, ignorada: {path}",
        "fakelib_external_file_missing": "Arquivo fakelib não encontrado, ignorado: {filename}",
        "fakelib_no_files_copied": "Nenhum arquivo fakelib foi copiado; a conversão continuará.",
    },
    "ru": {
        "fakelib_skip": "Не удалось скопировать fakelib, эта игра пропущена.",
        "fakelib_updating": "Копирование fakelib: {filename}",
        "fakelib_ready": "Fakelib скопирован: fakelib\\{filename}",
        "fakelib_update_failed": "Ошибка: не удалось скопировать файл fakelib: {filename} -> {error}",
        "fakelib_external_folder_missing": "Папка fakelib рядом с программой не найдена, пропуск: {path}",
        "fakelib_external_file_missing": "Файл fakelib не найден, пропуск: {filename}",
        "fakelib_no_files_copied": "Файлы fakelib не скопированы; конвертация продолжится.",
    },
    "zh": {
        "fakelib_skip": "无法复制 fakelib，已跳过此游戏。",
        "fakelib_updating": "正在复制 fakelib: {filename}",
        "fakelib_ready": "Fakelib 已复制: fakelib\\{filename}",
        "fakelib_update_failed": "错误：无法复制 fakelib 文件: {filename} -> {error}",
        "fakelib_external_folder_missing": "程序旁未找到 fakelib 文件夹，已跳过: {path}",
        "fakelib_external_file_missing": "未找到 fakelib 文件，已跳过: {filename}",
        "fakelib_no_files_copied": "未复制任何 fakelib 文件；转换将继续。",
    },
    "ar": {
        "fakelib_skip": "تعذر نسخ fakelib، تم تخطي هذه اللعبة.",
        "fakelib_updating": "جارٍ نسخ fakelib: {filename}",
        "fakelib_ready": "تم نسخ Fakelib: fakelib\\{filename}",
        "fakelib_update_failed": "خطأ: تعذر نسخ ملف fakelib: {filename} -> {error}",
        "fakelib_external_folder_missing": "لم يتم العثور على مجلد fakelib بجانب البرنامج، تم التخطي: {path}",
        "fakelib_external_file_missing": "لم يتم العثور على ملف fakelib، تم التخطي: {filename}",
        "fakelib_no_files_copied": "لم يتم نسخ أي ملفات fakelib؛ ستستمر عملية التحويل.",
    },
    "nl": {
        "fakelib_skip": "Fakelib kon niet worden gekopieerd, deze game is overgeslagen.",
        "fakelib_updating": "Fakelib kopiëren: {filename}",
        "fakelib_ready": "Fakelib gekopieerd: fakelib\\{filename}",
        "fakelib_update_failed": "Fout: fakelib-bestand kon niet worden gekopieerd: {filename} -> {error}",
        "fakelib_external_folder_missing": "Fakelib-map naast het programma niet gevonden, overgeslagen: {path}",
        "fakelib_external_file_missing": "Fakelib-bestand niet gevonden, overgeslagen: {filename}",
        "fakelib_no_files_copied": "Er zijn geen fakelib-bestanden gekopieerd; conversie gaat door.",
    },
    "pl": {
        "fakelib_skip": "Nie można skopiować fakelib, ta gra została pominięta.",
        "fakelib_updating": "Kopiowanie fakelib: {filename}",
        "fakelib_ready": "Fakelib skopiowany: fakelib\\{filename}",
        "fakelib_update_failed": "Błąd: nie można skopiować pliku fakelib: {filename} -> {error}",
        "fakelib_external_folder_missing": "Nie znaleziono folderu fakelib obok programu, pominięto: {path}",
        "fakelib_external_file_missing": "Nie znaleziono pliku fakelib, pominięto: {filename}",
        "fakelib_no_files_copied": "Nie skopiowano żadnych plików fakelib; konwersja będzie kontynuowana.",
    },
}
for _lang, _data in _EXTERNAL_FAKELIB_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)

_HTML_LOG_CONFIG_TEXT = {
    "en": {"log_written": "HTML log written: {path}", "log_write_failed": "HTML log could not be written: {error}"},
    "tr": {"log_written": "HTML log yazıldı: {path}", "log_write_failed": "HTML log yazılamadı: {error}"},
    "fr": {"log_written": "Journal HTML écrit : {path}", "log_write_failed": "Impossible d’écrire le journal HTML : {error}"},
    "es": {"log_written": "Log HTML escrito: {path}", "log_write_failed": "No se pudo escribir el log HTML: {error}"},
    "it": {"log_written": "Log HTML scritto: {path}", "log_write_failed": "Impossibile scrivere il log HTML: {error}"},
    "de": {"log_written": "HTML-Log geschrieben: {path}", "log_write_failed": "HTML-Log konnte nicht geschrieben werden: {error}"},
    "el": {"log_written": "Το HTML log γράφτηκε: {path}", "log_write_failed": "Δεν ήταν δυνατή η εγγραφή του HTML log: {error}"},
    "ko": {"log_written": "HTML 로그 작성됨: {path}", "log_write_failed": "HTML 로그를 쓸 수 없습니다: {error}"},
    "ja": {"log_written": "HTML ログを書き込みました: {path}", "log_write_failed": "HTML ログを書き込めませんでした: {error}"},
    "pt": {"log_written": "Log HTML gravado: {path}", "log_write_failed": "Não foi possível gravar o log HTML: {error}"},
    "ru": {"log_written": "HTML-лог записан: {path}", "log_write_failed": "Не удалось записать HTML-лог: {error}"},
    "zh": {"log_written": "HTML 日志已写入: {path}", "log_write_failed": "无法写入 HTML 日志: {error}"},
    "ar": {"log_written": "تمت كتابة سجل HTML: {path}", "log_write_failed": "تعذرت كتابة سجل HTML: {error}"},
    "nl": {"log_written": "HTML-log geschreven: {path}", "log_write_failed": "HTML-log kon niet worden geschreven: {error}"},
    "pl": {"log_written": "Log HTML zapisany: {path}", "log_write_failed": "Nie można zapisać logu HTML: {error}"},
}
for _lang, _data in _HTML_LOG_CONFIG_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)

_SOURCE_MODAL_TIMER_TEXT = {
    "en": {
        "source_choice_title": "Select Source Type",
        "source_choice_message": "What type of source do you want to select?",
        "choose_game_folder": "Select Game Folder",
        "choose_exfat_file": "Select Exfat",
        "elapsed_only": "Elapsed: {elapsed}",
        "elapsed_remaining": "Elapsed: {elapsed} | Estimated remaining: {remaining}",
    },
    "tr": {
        "source_choice_title": "Kaynak Türünü Seç",
        "source_choice_message": "Hangi kaynak türünü seçmek istiyorsunuz?",
        "choose_game_folder": "Oyun klasörü seç",
        "choose_exfat_file": "Exfat seç",
        "elapsed_only": "Geçen: {elapsed}",
        "elapsed_remaining": "Geçen: {elapsed} | Tahmini kalan: {remaining}",
    },
    "fr": {
        "source_choice_title": "Sélectionner le type de source",
        "source_choice_message": "Quel type de source souhaitez-vous sélectionner ?",
        "choose_game_folder": "Sélectionner le dossier du jeu",
        "choose_exfat_file": "Sélectionner Exfat",
        "elapsed_only": "Écoulé : {elapsed}",
        "elapsed_remaining": "Écoulé : {elapsed} | Temps restant estimé : {remaining}",
    },
    "es": {
        "source_choice_title": "Seleccionar tipo de origen",
        "source_choice_message": "¿Qué tipo de origen deseas seleccionar?",
        "choose_game_folder": "Seleccionar carpeta del juego",
        "choose_exfat_file": "Seleccionar Exfat",
        "elapsed_only": "Transcurrido: {elapsed}",
        "elapsed_remaining": "Transcurrido: {elapsed} | Restante estimado: {remaining}",
    },
    "it": {
        "source_choice_title": "Seleziona il tipo di origine",
        "source_choice_message": "Quale tipo di origine vuoi selezionare?",
        "choose_game_folder": "Seleziona cartella gioco",
        "choose_exfat_file": "Seleziona Exfat",
        "elapsed_only": "Trascorso: {elapsed}",
        "elapsed_remaining": "Trascorso: {elapsed} | Rimanente stimato: {remaining}",
    },
    "de": {
        "source_choice_title": "Quelltyp auswählen",
        "source_choice_message": "Welchen Quelltyp möchten Sie auswählen?",
        "choose_game_folder": "Spielordner auswählen",
        "choose_exfat_file": "Exfat auswählen",
        "elapsed_only": "Vergangen: {elapsed}",
        "elapsed_remaining": "Vergangen: {elapsed} | Geschätzt verbleibend: {remaining}",
    },
    "el": {
        "source_choice_title": "Επιλογή τύπου πηγής",
        "source_choice_message": "Ποιον τύπο πηγής θέλετε να επιλέξετε;",
        "choose_game_folder": "Επιλογή φακέλου παιχνιδιού",
        "choose_exfat_file": "Επιλογή Exfat",
        "elapsed_only": "Χρόνος που πέρασε: {elapsed}",
        "elapsed_remaining": "Χρόνος που πέρασε: {elapsed} | Εκτιμώμενος υπόλοιπος: {remaining}",
    },
    "ko": {
        "source_choice_title": "소스 유형 선택",
        "source_choice_message": "어떤 소스 유형을 선택하시겠습니까?",
        "choose_game_folder": "게임 폴더 선택",
        "choose_exfat_file": "Exfat 선택",
        "elapsed_only": "경과: {elapsed}",
        "elapsed_remaining": "경과: {elapsed} | 예상 남은 시간: {remaining}",
    },
    "ja": {
        "source_choice_title": "ソースの種類を選択",
        "source_choice_message": "選択するソースの種類を指定してください。",
        "choose_game_folder": "ゲームフォルダを選択",
        "choose_exfat_file": "Exfat を選択",
        "elapsed_only": "経過: {elapsed}",
        "elapsed_remaining": "経過: {elapsed} | 推定残り時間: {remaining}",
    },
    "pt": {
        "source_choice_title": "Selecionar tipo de origem",
        "source_choice_message": "Qual tipo de origem deseja selecionar?",
        "choose_game_folder": "Selecionar pasta do jogo",
        "choose_exfat_file": "Selecionar Exfat",
        "elapsed_only": "Decorrido: {elapsed}",
        "elapsed_remaining": "Decorrido: {elapsed} | Restante estimado: {remaining}",
    },
    "ru": {
        "source_choice_title": "Выберите тип источника",
        "source_choice_message": "Какой тип источника вы хотите выбрать?",
        "choose_game_folder": "Выбрать папку игры",
        "choose_exfat_file": "Выбрать Exfat",
        "elapsed_only": "Прошло: {elapsed}",
        "elapsed_remaining": "Прошло: {elapsed} | Осталось примерно: {remaining}",
    },
    "zh": {
        "source_choice_title": "选择源类型",
        "source_choice_message": "请选择要使用的源类型。",
        "choose_game_folder": "选择游戏文件夹",
        "choose_exfat_file": "选择 Exfat",
        "elapsed_only": "已用时间: {elapsed}",
        "elapsed_remaining": "已用时间: {elapsed} | 预计剩余: {remaining}",
    },
    "ar": {
        "source_choice_title": "اختر نوع المصدر",
        "source_choice_message": "ما نوع المصدر الذي تريد اختياره؟",
        "choose_game_folder": "اختر مجلد اللعبة",
        "choose_exfat_file": "اختر Exfat",
        "elapsed_only": "المنقضي: {elapsed}",
        "elapsed_remaining": "المنقضي: {elapsed} | المتبقي التقديري: {remaining}",
    },
    "nl": {
        "source_choice_title": "Brontype selecteren",
        "source_choice_message": "Welk type bron wilt u selecteren?",
        "choose_game_folder": "Gamemap selecteren",
        "choose_exfat_file": "Exfat selecteren",
        "elapsed_only": "Verstreken: {elapsed}",
        "elapsed_remaining": "Verstreken: {elapsed} | Geschat resterend: {remaining}",
    },
    "pl": {
        "source_choice_title": "Wybierz typ źródła",
        "source_choice_message": "Jaki typ źródła chcesz wybrać?",
        "choose_game_folder": "Wybierz folder gry",
        "choose_exfat_file": "Wybierz Exfat",
        "elapsed_only": "Upłynęło: {elapsed}",
        "elapsed_remaining": "Upłynęło: {elapsed} | Szacowany pozostały czas: {remaining}",
    },
}
for _lang, _data in _SOURCE_MODAL_TIMER_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)

_SHUTDOWN_TEXT = {
    'en': {"shutdown_pc": 'Shut down PC when finished', "shutdown_scheduled": 'All operations completed. The PC will shut down in 30 seconds.', "shutdown_failed": 'PC shutdown could not be scheduled: {error}', "shutdown_unsupported": 'Automatic shutdown is supported only on Windows.'},
    'tr': {"shutdown_pc": "Bitince PC'yi kapat", "shutdown_scheduled": 'Tüm işlemler tamamlandı. Bilgisayar 30 saniye içinde kapatılacak.', "shutdown_failed": 'Bilgisayar kapatma işlemi planlanamadı: {error}', "shutdown_unsupported": "Otomatik kapatma yalnızca Windows'ta desteklenir."},
    'fr': {"shutdown_pc": 'Éteindre le PC à la fin', "shutdown_scheduled": 'Toutes les opérations sont terminées. Le PC s’éteindra dans 30 secondes.', "shutdown_failed": 'Impossible de programmer l’arrêt du PC : {error}', "shutdown_unsupported": 'L’arrêt automatique est pris en charge uniquement sous Windows.'},
    'es': {"shutdown_pc": 'Apagar el PC al finalizar', "shutdown_scheduled": 'Todas las operaciones han terminado. El PC se apagará en 30 segundos.', "shutdown_failed": 'No se pudo programar el apagado del PC: {error}', "shutdown_unsupported": 'El apagado automático solo es compatible con Windows.'},
    'it': {"shutdown_pc": 'Spegni il PC al termine', "shutdown_scheduled": 'Tutte le operazioni sono terminate. Il PC si spegnerà tra 30 secondi.', "shutdown_failed": 'Impossibile programmare lo spegnimento del PC: {error}', "shutdown_unsupported": 'Lo spegnimento automatico è supportato solo su Windows.'},
    'de': {"shutdown_pc": 'PC nach Abschluss herunterfahren', "shutdown_scheduled": 'Alle Vorgänge sind abgeschlossen. Der PC wird in 30 Sekunden heruntergefahren.', "shutdown_failed": 'Das Herunterfahren konnte nicht geplant werden: {error}', "shutdown_unsupported": 'Automatisches Herunterfahren wird nur unter Windows unterstützt.'},
    'el': {"shutdown_pc": 'Τερματισμός υπολογιστή στο τέλος', "shutdown_scheduled": 'Όλες οι εργασίες ολοκληρώθηκαν. Ο υπολογιστής θα τερματιστεί σε 30 δευτερόλεπτα.', "shutdown_failed": 'Δεν ήταν δυνατός ο προγραμματισμός τερματισμού: {error}', "shutdown_unsupported": 'Ο αυτόματος τερματισμός υποστηρίζεται μόνο στα Windows.'},
    'ko': {"shutdown_pc": '완료 후 PC 종료', "shutdown_scheduled": '모든 작업이 완료되었습니다. PC가 30초 후 종료됩니다.', "shutdown_failed": 'PC 종료를 예약할 수 없습니다: {error}', "shutdown_unsupported": '자동 종료는 Windows에서만 지원됩니다.'},
    'ja': {"shutdown_pc": '完了後にPCをシャットダウン', "shutdown_scheduled": 'すべての処理が完了しました。PCは30秒後にシャットダウンします。', "shutdown_failed": 'PCのシャットダウンを予約できませんでした: {error}', "shutdown_unsupported": '自動シャットダウンはWindowsのみ対応しています。'},
    'pt': {"shutdown_pc": 'Desligar o PC ao terminar', "shutdown_scheduled": 'Todas as operações terminaram. O PC será desligado em 30 segundos.', "shutdown_failed": 'Não foi possível agendar o desligamento do PC: {error}', "shutdown_unsupported": 'O desligamento automático é suportado apenas no Windows.'},
    'ru': {"shutdown_pc": 'Выключить ПК после завершения', "shutdown_scheduled": 'Все операции завершены. ПК выключится через 30 секунд.', "shutdown_failed": 'Не удалось запланировать выключение ПК: {error}', "shutdown_unsupported": 'Автоматическое выключение поддерживается только в Windows.'},
    'zh': {"shutdown_pc": '完成后关闭电脑', "shutdown_scheduled": '所有操作已完成。电脑将在30秒后关机。', "shutdown_failed": '无法安排电脑关机: {error}', "shutdown_unsupported": '自动关机仅支持 Windows。'},
    'ar': {"shutdown_pc": 'إيقاف تشغيل الكمبيوتر عند الانتهاء', "shutdown_scheduled": 'اكتملت جميع العمليات. سيتم إيقاف تشغيل الكمبيوتر خلال 30 ثانية.', "shutdown_failed": 'تعذر جدولة إيقاف تشغيل الكمبيوتر: {error}', "shutdown_unsupported": 'الإيقاف التلقائي مدعوم على Windows فقط.'},
    'nl': {"shutdown_pc": 'PC uitschakelen na voltooiing', "shutdown_scheduled": 'Alle bewerkingen zijn voltooid. De pc wordt over 30 seconden uitgeschakeld.', "shutdown_failed": 'Het uitschakelen van de pc kon niet worden gepland: {error}', "shutdown_unsupported": 'Automatisch uitschakelen wordt alleen op Windows ondersteund.'},
    'pl': {"shutdown_pc": 'Wyłącz komputer po zakończeniu', "shutdown_scheduled": 'Wszystkie operacje zakończone. Komputer zostanie wyłączony za 30 sekund.', "shutdown_failed": 'Nie można zaplanować wyłączenia komputera: {error}', "shutdown_unsupported": 'Automatyczne wyłączanie jest obsługiwane tylko w Windows.'},
}
for _lang, _data in _SHUTDOWN_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)

_SHORT_KEEP_DAT_TEXT = {
    'en': 'Keep image.dat',
    'tr': 'image.dat tut',
    'fr': 'Garder image.dat',
    'es': 'Guardar image.dat',
    'it': 'Tieni image.dat',
    'de': 'image.dat behalten',
    'el': 'Κράτησε image.dat',
    'ko': 'image.dat 유지',
    'ja': 'image.dat 保持',
    'pt': 'Manter image.dat',
    'ru': 'Хранить image.dat',
    'zh': '保留 image.dat',
    'ar': 'حفظ image.dat',
    'nl': 'image.dat bewaren',
    'pl': 'Zachowaj image.dat',
}
for _lang, _value in _SHORT_KEEP_DAT_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang]["keep_dat"] = _value

_SHORT_EXTRA_VERIFY_TEXT = {
    'en': 'Extra verification',
    'tr': 'Ek doğrulama',
    'fr': 'Vérification',
    'es': 'Verificación extra',
    'it': 'Verifica extra',
    'de': 'Extra-Prüfung',
    'el': 'Επιπλέον επαλήθευση',
    'ko': '추가 검증',
    'ja': '追加検証',
    'pt': 'Verificação extra',
    'ru': 'Доп. проверка',
    'zh': '额外校验',
    'ar': 'تحقق إضافي',
    'nl': 'Extra controle',
    'pl': 'Dodatkowa weryfikacja',
}
for _lang, _value in _SHORT_EXTRA_VERIFY_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang]["extra_verify"] = _value

_EXFAT_ESTIMATE_TEXT = {
    'en': {
        'exfat_estimate_intro': 'If MkPFS does not show percent here, estimated progress will be shown from the output file size.',
        'exfat_estimate_formula': 'Formula: current .ffpfsc size / estimated final size. Estimated final size assumes about 40% space saving.',
        'ffpfsc_estimate_status': 'Estimated .ffpfsc {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 writing .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 writing .ffpfsc: {current}',
    },
    'tr': {
        'exfat_estimate_intro': 'MkPFS burada yüzde basmazsa çıktı dosyası boyutundan tahmini ilerleme gösterilecek.',
        'exfat_estimate_formula': 'Hesap: mevcut .ffpfsc boyutu / tahmini final boyut. Tahmini final boyutta yaklaşık %40 kazanım varsayılır.',
        'ffpfsc_estimate_status': 'Tahmini .ffpfsc %{percent:.1f}',
        'ffpfsc_writing_phase_full': '2/2 .ffpfsc yazılıyor: {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 .ffpfsc yazılıyor: {current}',
    },
    'fr': {
        'exfat_estimate_intro': 'Si MkPFS n’affiche pas de pourcentage ici, une progression estimée sera affichée à partir de la taille du fichier de sortie.',
        'exfat_estimate_formula': 'Formule : taille actuelle du .ffpfsc / taille finale estimée. La taille finale estimée suppose un gain d’environ 40 %.',
        'ffpfsc_estimate_status': '.ffpfsc estimé {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 écriture du .ffpfsc : {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 écriture du .ffpfsc : {current}',
    },
    'es': {
        'exfat_estimate_intro': 'Si MkPFS no muestra porcentaje aquí, se mostrará un progreso estimado según el tamaño del archivo de salida.',
        'exfat_estimate_formula': 'Fórmula: tamaño actual del .ffpfsc / tamaño final estimado. El tamaño final estimado asume un ahorro aproximado del 40 %.',
        'ffpfsc_estimate_status': '.ffpfsc estimado {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 escribiendo .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 escribiendo .ffpfsc: {current}',
    },
    'it': {
        'exfat_estimate_intro': 'Se MkPFS non mostra una percentuale qui, verrà mostrato un avanzamento stimato in base alla dimensione del file di output.',
        'exfat_estimate_formula': 'Formula: dimensione attuale del .ffpfsc / dimensione finale stimata. La dimensione finale stimata presume un risparmio di circa il 40 %.',
        'ffpfsc_estimate_status': '.ffpfsc stimato {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 scrittura .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 scrittura .ffpfsc: {current}',
    },
    'de': {
        'exfat_estimate_intro': 'Wenn MkPFS hier keinen Prozentwert anzeigt, wird ein geschätzter Fortschritt anhand der Ausgabedateigröße gezeigt.',
        'exfat_estimate_formula': 'Formel: aktuelle .ffpfsc-Größe / geschätzte Endgröße. Die geschätzte Endgröße geht von etwa 40 % Platzgewinn aus.',
        'ffpfsc_estimate_status': 'Geschätztes .ffpfsc {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 .ffpfsc wird geschrieben: {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 .ffpfsc wird geschrieben: {current}',
    },
    'el': {
        'exfat_estimate_intro': 'Αν το MkPFS δεν εμφανίσει ποσοστό εδώ, θα εμφανιστεί εκτιμώμενη πρόοδος από το μέγεθος του αρχείου εξόδου.',
        'exfat_estimate_formula': 'Τύπος: τρέχον μέγεθος .ffpfsc / εκτιμώμενο τελικό μέγεθος. Το εκτιμώμενο τελικό μέγεθος υποθέτει περίπου 40% εξοικονόμηση.',
        'ffpfsc_estimate_status': 'Εκτιμώμενο .ffpfsc {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 εγγραφή .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 εγγραφή .ffpfsc: {current}',
    },
    'ko': {
        'exfat_estimate_intro': '여기에서 MkPFS가 퍼센트를 표시하지 않으면 출력 파일 크기를 기준으로 예상 진행률을 표시합니다.',
        'exfat_estimate_formula': '공식: 현재 .ffpfsc 크기 / 예상 최종 크기. 예상 최종 크기는 약 40% 절감으로 계산합니다.',
        'ffpfsc_estimate_status': '예상 .ffpfsc {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 .ffpfsc 작성 중: {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 .ffpfsc 작성 중: {current}',
    },
    'ja': {
        'exfat_estimate_intro': 'ここで MkPFS が進行率を表示しない場合、出力ファイルサイズから推定進行率を表示します。',
        'exfat_estimate_formula': '計算式: 現在の .ffpfsc サイズ / 推定最終サイズ。推定最終サイズは約40%の容量削減を前提にしています。',
        'ffpfsc_estimate_status': '推定 .ffpfsc {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 .ffpfsc 書き込み中: {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 .ffpfsc 書き込み中: {current}',
    },
    'pt': {
        'exfat_estimate_intro': 'Se o MkPFS não mostrar porcentagem aqui, será exibido um progresso estimado com base no tamanho do arquivo de saída.',
        'exfat_estimate_formula': 'Fórmula: tamanho atual do .ffpfsc / tamanho final estimado. O tamanho final estimado assume cerca de 40% de economia.',
        'ffpfsc_estimate_status': '.ffpfsc estimado {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 gravando .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 gravando .ffpfsc: {current}',
    },
    'ru': {
        'exfat_estimate_intro': 'Если MkPFS не показывает процент здесь, будет показан примерный прогресс по размеру выходного файла.',
        'exfat_estimate_formula': 'Формула: текущий размер .ffpfsc / предполагаемый итоговый размер. Итоговый размер рассчитывается с учётом примерно 40% экономии.',
        'ffpfsc_estimate_status': 'Примерный .ffpfsc {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 запись .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 запись .ffpfsc: {current}',
    },
    'zh': {
        'exfat_estimate_intro': '如果 MkPFS 在此不显示百分比，将根据输出文件大小显示估算进度。',
        'exfat_estimate_formula': '公式：当前 .ffpfsc 大小 / 估算最终大小。估算最终大小按约 40% 的空间节省计算。',
        'ffpfsc_estimate_status': '估算 .ffpfsc {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 正在写入 .ffpfsc：{current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 正在写入 .ffpfsc：{current}',
    },
    'ar': {
        'exfat_estimate_intro': 'إذا لم يعرض MkPFS نسبة مئوية هنا، فسيتم عرض تقدم تقديري اعتمادًا على حجم ملف الإخراج.',
        'exfat_estimate_formula': 'المعادلة: حجم .ffpfsc الحالي / الحجم النهائي التقديري. الحجم النهائي التقديري يفترض توفيرًا يقارب 40٪.',
        'ffpfsc_estimate_status': '.ffpfsc تقديري {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 جارٍ كتابة .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 جارٍ كتابة .ffpfsc: {current}',
    },
    'nl': {
        'exfat_estimate_intro': 'Als MkPFS hier geen percentage toont, wordt een geschatte voortgang weergegeven op basis van de grootte van het uitvoerbestand.',
        'exfat_estimate_formula': 'Formule: huidige .ffpfsc-grootte / geschatte eindgrootte. De geschatte eindgrootte gaat uit van ongeveer 40% ruimtewinst.',
        'ffpfsc_estimate_status': 'Geschatte .ffpfsc {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 .ffpfsc schrijven: {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 .ffpfsc schrijven: {current}',
    },
    'pl': {
        'exfat_estimate_intro': 'Jeśli MkPFS nie pokazuje tutaj procentów, zostanie wyświetlony szacowany postęp na podstawie rozmiaru pliku wyjściowego.',
        'exfat_estimate_formula': 'Wzór: bieżący rozmiar .ffpfsc / szacowany rozmiar końcowy. Szacowany rozmiar końcowy zakłada około 40% oszczędności miejsca.',
        'ffpfsc_estimate_status': 'Szacowany .ffpfsc {percent:.1f}%',
        'ffpfsc_writing_phase_full': '2/2 zapisywanie .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': '2/2 zapisywanie .ffpfsc: {current}',
    },
}
for _lang, _data in _EXFAT_ESTIMATE_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)

_EXFAT_DIRECT_TEXT = {
    'en': {
        'stage_exfat_ffpfsc_creating': 'Creating .ffpfsc from Exfat',
        'exfat_direct_failed': 'Exfat conversion failed. Code: {code}',
        'ffpfsc_writing_phase_full': 'Writing .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': 'Writing .ffpfsc: {current}',
        'exfat_method_log': 'Method: Exfat -> .ffpfsc (direct, compressed)',
    },
    'tr': {
        'stage_exfat_ffpfsc_creating': 'Exfat doğrudan .ffpfsc oluşturuluyor',
        'exfat_direct_failed': 'Exfat dönüşümü başarısız. Kod: {code}',
        'ffpfsc_writing_phase_full': '.ffpfsc yazılıyor: {current} / ~{total}',
        'ffpfsc_writing_phase': '.ffpfsc yazılıyor: {current}',
        'exfat_method_log': 'Yöntem: Exfat -> .ffpfsc (doğrudan, sıkıştırılmış)',
    },
    'fr': {
        'stage_exfat_ffpfsc_creating': 'Création directe du .ffpfsc depuis Exfat',
        'exfat_direct_failed': 'La conversion Exfat a échoué. Code : {code}',
        'ffpfsc_writing_phase_full': 'Écriture du .ffpfsc : {current} / ~{total}',
        'ffpfsc_writing_phase': 'Écriture du .ffpfsc : {current}',
        'exfat_method_log': 'Méthode : Exfat -> .ffpfsc (direct, compressé)',
    },
    'es': {
        'stage_exfat_ffpfsc_creating': 'Creando .ffpfsc directamente desde Exfat',
        'exfat_direct_failed': 'La conversión Exfat falló. Código: {code}',
        'ffpfsc_writing_phase_full': 'Escribiendo .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': 'Escribiendo .ffpfsc: {current}',
        'exfat_method_log': 'Método: Exfat -> .ffpfsc (directo, comprimido)',
    },
    'it': {
        'stage_exfat_ffpfsc_creating': 'Creazione diretta di .ffpfsc da Exfat',
        'exfat_direct_failed': 'Conversione Exfat non riuscita. Codice: {code}',
        'ffpfsc_writing_phase_full': 'Scrittura .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': 'Scrittura .ffpfsc: {current}',
        'exfat_method_log': 'Metodo: Exfat -> .ffpfsc (diretto, compresso)',
    },
    'de': {
        'stage_exfat_ffpfsc_creating': '.ffpfsc wird direkt aus Exfat erstellt',
        'exfat_direct_failed': 'Exfat-Konvertierung fehlgeschlagen. Code: {code}',
        'ffpfsc_writing_phase_full': '.ffpfsc wird geschrieben: {current} / ~{total}',
        'ffpfsc_writing_phase': '.ffpfsc wird geschrieben: {current}',
        'exfat_method_log': 'Methode: Exfat -> .ffpfsc (direkt, komprimiert)',
    },
    'el': {
        'stage_exfat_ffpfsc_creating': 'Άμεση δημιουργία .ffpfsc από Exfat',
        'exfat_direct_failed': 'Η μετατροπή Exfat απέτυχε. Κωδικός: {code}',
        'ffpfsc_writing_phase_full': 'Εγγραφή .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': 'Εγγραφή .ffpfsc: {current}',
        'exfat_method_log': 'Μέθοδος: Exfat -> .ffpfsc (άμεσα, συμπιεσμένο)',
    },
    'ko': {
        'stage_exfat_ffpfsc_creating': 'Exfat에서 .ffpfsc 직접 생성 중',
        'exfat_direct_failed': 'Exfat 변환 실패. 코드: {code}',
        'ffpfsc_writing_phase_full': '.ffpfsc 작성 중: {current} / ~{total}',
        'ffpfsc_writing_phase': '.ffpfsc 작성 중: {current}',
        'exfat_method_log': '방식: Exfat -> .ffpfsc (직접, 압축)',
    },
    'ja': {
        'stage_exfat_ffpfsc_creating': 'Exfat から .ffpfsc を直接作成中',
        'exfat_direct_failed': 'Exfat 変換に失敗しました。コード: {code}',
        'ffpfsc_writing_phase_full': '.ffpfsc 書き込み中: {current} / ~{total}',
        'ffpfsc_writing_phase': '.ffpfsc 書き込み中: {current}',
        'exfat_method_log': '方式: Exfat -> .ffpfsc（直接・圧縮）',
    },
    'pt': {
        'stage_exfat_ffpfsc_creating': 'Criando .ffpfsc diretamente do Exfat',
        'exfat_direct_failed': 'A conversão Exfat falhou. Código: {code}',
        'ffpfsc_writing_phase_full': 'Gravando .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': 'Gravando .ffpfsc: {current}',
        'exfat_method_log': 'Método: Exfat -> .ffpfsc (direto, comprimido)',
    },
    'ru': {
        'stage_exfat_ffpfsc_creating': 'Прямое создание .ffpfsc из Exfat',
        'exfat_direct_failed': 'Преобразование Exfat завершилось ошибкой. Код: {code}',
        'ffpfsc_writing_phase_full': 'Запись .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': 'Запись .ffpfsc: {current}',
        'exfat_method_log': 'Метод: Exfat -> .ffpfsc (напрямую, со сжатием)',
    },
    'zh': {
        'stage_exfat_ffpfsc_creating': '正在从 Exfat 直接创建 .ffpfsc',
        'exfat_direct_failed': 'Exfat 转换失败。代码：{code}',
        'ffpfsc_writing_phase_full': '正在写入 .ffpfsc：{current} / ~{total}',
        'ffpfsc_writing_phase': '正在写入 .ffpfsc：{current}',
        'exfat_method_log': '方式：Exfat -> .ffpfsc（直接、压缩）',
    },
    'ar': {
        'stage_exfat_ffpfsc_creating': 'جارٍ إنشاء .ffpfsc مباشرة من Exfat',
        'exfat_direct_failed': 'فشل تحويل Exfat. الرمز: {code}',
        'ffpfsc_writing_phase_full': 'جارٍ كتابة .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': 'جارٍ كتابة .ffpfsc: {current}',
        'exfat_method_log': 'الطريقة: Exfat -> .ffpfsc (مباشر، مضغوط)',
    },
    'nl': {
        'stage_exfat_ffpfsc_creating': '.ffpfsc rechtstreeks uit Exfat maken',
        'exfat_direct_failed': 'Exfat-conversie mislukt. Code: {code}',
        'ffpfsc_writing_phase_full': '.ffpfsc schrijven: {current} / ~{total}',
        'ffpfsc_writing_phase': '.ffpfsc schrijven: {current}',
        'exfat_method_log': 'Methode: Exfat -> .ffpfsc (direct, gecomprimeerd)',
    },
    'pl': {
        'stage_exfat_ffpfsc_creating': 'Bezpośrednie tworzenie .ffpfsc z Exfat',
        'exfat_direct_failed': 'Konwersja Exfat nie powiodła się. Kod: {code}',
        'ffpfsc_writing_phase_full': 'Zapisywanie .ffpfsc: {current} / ~{total}',
        'ffpfsc_writing_phase': 'Zapisywanie .ffpfsc: {current}',
        'exfat_method_log': 'Metoda: Exfat -> .ffpfsc (bezpośrednio, kompresja)',
    },
}
for _lang, _data in _EXFAT_DIRECT_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)

_EXFAT_COMPRESSION_DIAGNOSTIC_TEXT = {
    'en': {
        'exfat_estimate_formula': 'Fallback estimate uses the source size as an upper bound. Actual compression gain cannot be known in advance.',
        'compression_disabled_warning': 'Warning: MkPFS reported compression as disabled. The output may be the same size as the source.',
        'compression_low_gain_warning': 'Compression gain is very low ({gain:.2f}%). The source image may already contain compressed or incompressible data.',
        'compression_same_size_warning': 'Output size is almost the same as the source. MkPFS did run with compression, but the data produced little or no gain.',
        'compression_enabled_confirmed': 'MkPFS compression confirmed: enabled.',
    },
    'tr': {
        'exfat_estimate_formula': 'Yedek tahmin kaynak boyutunu üst sınır kabul eder. Gerçek sıkıştırma kazancı önceden kesin bilinemez.',
        'compression_disabled_warning': 'Uyarı: MkPFS sıkıştırmayı kapalı bildirdi. Çıktı kaynakla aynı boyutta olabilir.',
        'compression_low_gain_warning': 'Sıkıştırma kazancı çok düşük (%{gain:.2f}). Kaynak imaj zaten sıkıştırılmış veya zor sıkışan veri içeriyor olabilir.',
        'compression_same_size_warning': 'Çıktı boyutu kaynakla neredeyse aynı. MkPFS sıkıştırmayı çalıştırdı ancak veriden anlamlı kazanım elde edemedi.',
        'compression_enabled_confirmed': 'MkPFS sıkıştırması doğrulandı: açık.',
    },
    'fr': {
        'exfat_estimate_formula': 'L’estimation de secours utilise la taille source comme limite supérieure. Le gain réel ne peut pas être connu à l’avance.',
        'compression_disabled_warning': 'Avertissement : MkPFS indique que la compression est désactivée. La sortie peut avoir la même taille que la source.',
        'compression_low_gain_warning': 'Le gain de compression est très faible ({gain:.2f} %). L’image source contient peut-être déjà des données compressées ou peu compressibles.',
        'compression_same_size_warning': 'La sortie a presque la même taille que la source. MkPFS a bien compressé, mais le gain est insignifiant.',
        'compression_enabled_confirmed': 'Compression MkPFS confirmée : activée.',
    },
    'es': {
        'exfat_estimate_formula': 'La estimación alternativa usa el tamaño de origen como límite superior. La ganancia real no puede conocerse de antemano.',
        'compression_disabled_warning': 'Advertencia: MkPFS informó que la compresión está desactivada. La salida puede tener el mismo tamaño que el origen.',
        'compression_low_gain_warning': 'La ganancia de compresión es muy baja ({gain:.2f} %). La imagen puede contener datos ya comprimidos o difíciles de comprimir.',
        'compression_same_size_warning': 'La salida tiene casi el mismo tamaño que el origen. MkPFS comprimió, pero obtuvo poca o ninguna ganancia.',
        'compression_enabled_confirmed': 'Compresión MkPFS confirmada: activada.',
    },
    'it': {
        'exfat_estimate_formula': 'La stima di riserva usa la dimensione sorgente come limite massimo. Il guadagno reale non è prevedibile in anticipo.',
        'compression_disabled_warning': 'Avviso: MkPFS ha indicato la compressione come disattivata. L’output può avere la stessa dimensione della sorgente.',
        'compression_low_gain_warning': 'Il guadagno di compressione è molto basso ({gain:.2f}%). L’immagine può contenere dati già compressi o poco comprimibili.',
        'compression_same_size_warning': 'L’output è quasi della stessa dimensione della sorgente. MkPFS ha compresso, ma senza un guadagno significativo.',
        'compression_enabled_confirmed': 'Compressione MkPFS confermata: attiva.',
    },
    'de': {
        'exfat_estimate_formula': 'Die Ersatzschätzung verwendet die Quellgröße als Obergrenze. Der tatsächliche Gewinn ist vorher nicht sicher bekannt.',
        'compression_disabled_warning': 'Warnung: MkPFS meldet die Komprimierung als deaktiviert. Die Ausgabe kann gleich groß wie die Quelle sein.',
        'compression_low_gain_warning': 'Der Komprimierungsgewinn ist sehr gering ({gain:.2f} %). Das Quellabbild enthält möglicherweise bereits komprimierte Daten.',
        'compression_same_size_warning': 'Die Ausgabe ist fast so groß wie die Quelle. MkPFS hat komprimiert, aber kaum Gewinn erzielt.',
        'compression_enabled_confirmed': 'MkPFS-Komprimierung bestätigt: aktiviert.',
    },
    'el': {
        'exfat_estimate_formula': 'Η εφεδρική εκτίμηση χρησιμοποιεί το μέγεθος πηγής ως ανώτατο όριο. Το πραγματικό κέρδος δεν είναι γνωστό εκ των προτέρων.',
        'compression_disabled_warning': 'Προειδοποίηση: Το MkPFS ανέφερε απενεργοποιημένη συμπίεση. Η έξοδος μπορεί να έχει ίδιο μέγεθος με την πηγή.',
        'compression_low_gain_warning': 'Το κέρδος συμπίεσης είναι πολύ χαμηλό ({gain:.2f}%). Η εικόνα ίσως περιέχει ήδη συμπιεσμένα δεδομένα.',
        'compression_same_size_warning': 'Η έξοδος είναι σχεδόν ίδια σε μέγεθος με την πηγή. Η συμπίεση εκτελέστηκε αλλά χωρίς ουσιαστικό κέρδος.',
        'compression_enabled_confirmed': 'Η συμπίεση MkPFS επιβεβαιώθηκε: ενεργή.',
    },
    'ko': {
        'exfat_estimate_formula': '보조 추정은 원본 크기를 상한으로 사용합니다. 실제 압축 절감률은 미리 알 수 없습니다.',
        'compression_disabled_warning': '경고: MkPFS가 압축 비활성화를 보고했습니다. 출력 크기가 원본과 같을 수 있습니다.',
        'compression_low_gain_warning': '압축 절감률이 매우 낮습니다({gain:.2f}%). 원본 이미지가 이미 압축되었거나 압축이 어려운 데이터일 수 있습니다.',
        'compression_same_size_warning': '출력 크기가 원본과 거의 같습니다. MkPFS 압축은 실행됐지만 의미 있는 절감이 없었습니다.',
        'compression_enabled_confirmed': 'MkPFS 압축 확인: 활성.',
    },
    'ja': {
        'exfat_estimate_formula': '予備推定ではソースサイズを上限として使用します。実際の圧縮率は事前には確定できません。',
        'compression_disabled_warning': '警告: MkPFS は圧縮無効を報告しました。出力がソースと同じサイズになる場合があります。',
        'compression_low_gain_warning': '圧縮効果が非常に低いです（{gain:.2f}%）。ソースが既に圧縮済み、または圧縮しにくい可能性があります。',
        'compression_same_size_warning': '出力サイズはソースとほぼ同じです。圧縮は実行されましたが、有効な削減は得られませんでした。',
        'compression_enabled_confirmed': 'MkPFS 圧縮確認: 有効。',
    },
    'pt': {
        'exfat_estimate_formula': 'A estimativa alternativa usa o tamanho da origem como limite superior. O ganho real não pode ser conhecido antes.',
        'compression_disabled_warning': 'Aviso: o MkPFS informou compressão desativada. A saída pode ter o mesmo tamanho da origem.',
        'compression_low_gain_warning': 'O ganho de compressão é muito baixo ({gain:.2f}%). A imagem pode já conter dados comprimidos ou pouco compressíveis.',
        'compression_same_size_warning': 'A saída tem quase o mesmo tamanho da origem. O MkPFS comprimiu, mas obteve pouco ou nenhum ganho.',
        'compression_enabled_confirmed': 'Compressão MkPFS confirmada: ativada.',
    },
    'ru': {
        'exfat_estimate_formula': 'Резервная оценка использует размер источника как верхнюю границу. Реальный выигрыш заранее неизвестен.',
        'compression_disabled_warning': 'Предупреждение: MkPFS сообщил, что сжатие отключено. Выход может быть того же размера, что и источник.',
        'compression_low_gain_warning': 'Выигрыш сжатия очень мал ({gain:.2f}%). Образ может уже содержать сжатые или плохо сжимаемые данные.',
        'compression_same_size_warning': 'Выход почти равен источнику. MkPFS выполнил сжатие, но заметного выигрыша не получил.',
        'compression_enabled_confirmed': 'Сжатие MkPFS подтверждено: включено.',
    },
    'zh': {
        'exfat_estimate_formula': '备用估算使用源文件大小作为上限。实际压缩收益无法提前确定。',
        'compression_disabled_warning': '警告：MkPFS 报告压缩已禁用。输出大小可能与源文件相同。',
        'compression_low_gain_warning': '压缩收益很低（{gain:.2f}%）。源镜像可能已经压缩或包含难以压缩的数据。',
        'compression_same_size_warning': '输出大小几乎与源文件相同。MkPFS 已执行压缩，但没有获得明显收益。',
        'compression_enabled_confirmed': '已确认 MkPFS 压缩：启用。',
    },
    'ar': {
        'exfat_estimate_formula': 'يستخدم التقدير الاحتياطي حجم المصدر كحد أعلى. لا يمكن معرفة مكسب الضغط الحقيقي مسبقًا.',
        'compression_disabled_warning': 'تحذير: أبلغ MkPFS أن الضغط معطل. قد يكون حجم الناتج مساويًا للمصدر.',
        'compression_low_gain_warning': 'مكسب الضغط منخفض جدًا ({gain:.2f}٪). قد تحتوي الصورة على بيانات مضغوطة مسبقًا أو صعبة الضغط.',
        'compression_same_size_warning': 'حجم الناتج قريب جدًا من المصدر. تم تشغيل الضغط لكن دون مكسب ملحوظ.',
        'compression_enabled_confirmed': 'تم تأكيد ضغط MkPFS: مفعّل.',
    },
    'nl': {
        'exfat_estimate_formula': 'De reserve-inschatting gebruikt de brongrootte als bovengrens. De werkelijke winst is vooraf niet bekend.',
        'compression_disabled_warning': 'Waarschuwing: MkPFS meldde dat compressie is uitgeschakeld. De uitvoer kan even groot zijn als de bron.',
        'compression_low_gain_warning': 'De compressiewinst is zeer laag ({gain:.2f}%). De bron kan al gecomprimeerde of moeilijk comprimeerbare data bevatten.',
        'compression_same_size_warning': 'De uitvoer is bijna even groot als de bron. MkPFS heeft gecomprimeerd, maar nauwelijks winst behaald.',
        'compression_enabled_confirmed': 'MkPFS-compressie bevestigd: ingeschakeld.',
    },
    'pl': {
        'exfat_estimate_formula': 'Szacunek awaryjny używa rozmiaru źródła jako górnej granicy. Rzeczywisty zysk nie jest znany z góry.',
        'compression_disabled_warning': 'Ostrzeżenie: MkPFS zgłosił wyłączoną kompresję. Wynik może mieć taki sam rozmiar jak źródło.',
        'compression_low_gain_warning': 'Zysk kompresji jest bardzo niski ({gain:.2f}%). Obraz może zawierać już skompresowane lub trudne do kompresji dane.',
        'compression_same_size_warning': 'Wynik ma prawie taki sam rozmiar jak źródło. MkPFS kompresował, ale bez istotnego zysku.',
        'compression_enabled_confirmed': 'Kompresja MkPFS potwierdzona: włączona.',
    },
}
for _lang, _data in _EXFAT_COMPRESSION_DIAGNOSTIC_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)

_MKPFS_009_WORKFLOW_TEXT = {
    'en': {
        'coffee_msg': 'This tool packs game folders into exFAT-wrapped .ffpfsc images and keeps the CPU busy during compression.\nA coffee for the developer may make the progress bar happier 😄',
        'method_log': 'Method: Folder -> exFAT-wrapped .ffpfsc (one pass) | Exfat -> .ffpfsc',
        'folder_method_log': 'Method: Game folder -> exFAT-wrapped .ffpfsc (one pass, no temporary image)',
        'stage_folder_ffpfsc_creating': 'Creating exFAT-wrapped .ffpfsc',
        'folder_direct_failed': 'Folder conversion failed. Code: {code}',
        'direct_estimate_intro': 'If MkPFS does not show progress, estimated progress will be shown from the output file size.',
        'direct_estimate_formula': 'Fallback estimate uses the source size as an upper bound. Actual compression gain cannot be known in advance.',
    },
    'tr': {
        'coffee_msg': "Bu araç oyun klasörlerini exFAT sarmallı .ffpfsc imajına dönüştürürken CPU'yu terletiyor.\nGeliştirici tarafına bir kahve gönderirsen progress bar daha mutlu akar 😄",
        'method_log': 'Yöntem: Klasör -> exFAT sarmallı .ffpfsc (tek aşama) | Exfat -> .ffpfsc',
        'folder_method_log': 'Yöntem: Oyun klasörü -> exFAT sarmallı .ffpfsc (tek aşama, geçici imaj yok)',
        'stage_folder_ffpfsc_creating': 'exFAT sarmallı .ffpfsc oluşturuluyor',
        'folder_direct_failed': 'Klasör dönüşümü başarısız. Kod: {code}',
        'direct_estimate_intro': 'MkPFS ilerleme yüzdesi basmazsa çıktı dosyası boyutundan tahmini ilerleme gösterilecek.',
        'direct_estimate_formula': 'Yedek tahmin kaynak boyutunu üst sınır kabul eder. Gerçek sıkıştırma kazancı önceden kesin bilinemez.',
    },
    'fr': {
        'coffee_msg': 'Cet outil convertit les dossiers de jeu en images .ffpfsc encapsulées en exFAT et sollicite le CPU pendant la compression.\nUn café pour le développeur peut rendre la barre de progression plus heureuse 😄',
        'method_log': 'Méthode : dossier -> .ffpfsc encapsulé exFAT (une passe) | Exfat -> .ffpfsc',
        'folder_method_log': 'Méthode : dossier de jeu -> .ffpfsc encapsulé exFAT (une passe, sans image temporaire)',
        'stage_folder_ffpfsc_creating': 'Création du .ffpfsc encapsulé exFAT',
        'folder_direct_failed': 'Échec de la conversion du dossier. Code : {code}',
        'direct_estimate_intro': 'Si MkPFS n’affiche pas la progression, une estimation sera calculée à partir de la taille du fichier de sortie.',
        'direct_estimate_formula': 'L’estimation utilise la taille source comme limite supérieure. Le gain réel ne peut pas être connu à l’avance.',
    },
    'es': {
        'coffee_msg': 'Esta herramienta convierte carpetas de juegos en imágenes .ffpfsc envueltas en exFAT y usa el CPU durante la compresión.\nUn café para el desarrollador puede alegrar la barra de progreso 😄',
        'method_log': 'Método: carpeta -> .ffpfsc envuelto en exFAT (una pasada) | Exfat -> .ffpfsc',
        'folder_method_log': 'Método: carpeta de juego -> .ffpfsc envuelto en exFAT (una pasada, sin imagen temporal)',
        'stage_folder_ffpfsc_creating': 'Creando .ffpfsc envuelto en exFAT',
        'folder_direct_failed': 'Falló la conversión de la carpeta. Código: {code}',
        'direct_estimate_intro': 'Si MkPFS no muestra el progreso, se calculará una estimación según el tamaño del archivo de salida.',
        'direct_estimate_formula': 'La estimación usa el tamaño de origen como límite superior. La ganancia real no puede conocerse de antemano.',
    },
    'it': {
        'coffee_msg': 'Questo strumento converte le cartelle di gioco in immagini .ffpfsc avvolte in exFAT e usa la CPU durante la compressione.\nUn caffè allo sviluppatore può rendere più felice la barra di avanzamento 😄',
        'method_log': 'Metodo: cartella -> .ffpfsc avvolto in exFAT (un passaggio) | Exfat -> .ffpfsc',
        'folder_method_log': 'Metodo: cartella gioco -> .ffpfsc avvolto in exFAT (un passaggio, nessuna immagine temporanea)',
        'stage_folder_ffpfsc_creating': 'Creazione .ffpfsc avvolto in exFAT',
        'folder_direct_failed': 'Conversione cartella non riuscita. Codice: {code}',
        'direct_estimate_intro': 'Se MkPFS non mostra l’avanzamento, verrà stimato dalla dimensione del file di output.',
        'direct_estimate_formula': 'La stima usa la dimensione sorgente come limite massimo. Il guadagno reale non è prevedibile in anticipo.',
    },
    'de': {
        'coffee_msg': 'Dieses Tool konvertiert Spielordner in exFAT-umschlossene .ffpfsc-Images und beschäftigt die CPU bei der Komprimierung.\nEin Kaffee für den Entwickler macht den Fortschrittsbalken glücklicher 😄',
        'method_log': 'Methode: Ordner -> exFAT-umschlossenes .ffpfsc (ein Durchlauf) | Exfat -> .ffpfsc',
        'folder_method_log': 'Methode: Spielordner -> exFAT-umschlossenes .ffpfsc (ein Durchlauf, kein temporäres Image)',
        'stage_folder_ffpfsc_creating': 'exFAT-umschlossenes .ffpfsc wird erstellt',
        'folder_direct_failed': 'Ordnerkonvertierung fehlgeschlagen. Code: {code}',
        'direct_estimate_intro': 'Wenn MkPFS keinen Fortschritt anzeigt, wird er anhand der Ausgabedateigröße geschätzt.',
        'direct_estimate_formula': 'Die Schätzung verwendet die Quellgröße als Obergrenze. Der tatsächliche Gewinn ist vorher nicht sicher bekannt.',
    },
    'el': {
        'coffee_msg': 'Το εργαλείο μετατρέπει φακέλους παιχνιδιών σε .ffpfsc με περίβλημα exFAT και χρησιμοποιεί την CPU κατά τη συμπίεση.\nΈνας καφές για τον developer κάνει τη μπάρα προόδου πιο χαρούμενη 😄',
        'method_log': 'Μέθοδος: φάκελος -> .ffpfsc με περίβλημα exFAT (ένα πέρασμα) | Exfat -> .ffpfsc',
        'folder_method_log': 'Μέθοδος: φάκελος παιχνιδιού -> .ffpfsc με περίβλημα exFAT (ένα πέρασμα, χωρίς προσωρινή εικόνα)',
        'stage_folder_ffpfsc_creating': 'Δημιουργία .ffpfsc με περίβλημα exFAT',
        'folder_direct_failed': 'Η μετατροπή φακέλου απέτυχε. Κωδικός: {code}',
        'direct_estimate_intro': 'Αν το MkPFS δεν εμφανίσει πρόοδο, θα γίνει εκτίμηση από το μέγεθος του αρχείου εξόδου.',
        'direct_estimate_formula': 'Η εκτίμηση χρησιμοποιεί το μέγεθος πηγής ως ανώτατο όριο. Το πραγματικό κέρδος δεν είναι γνωστό εκ των προτέρων.',
    },
    'ko': {
        'coffee_msg': '이 도구는 게임 폴더를 exFAT 래핑 .ffpfsc 이미지로 변환하며 압축 중 CPU를 사용합니다.\n개발자에게 커피 한 잔은 진행 바를 더 행복하게 만들 수 있어요 😄',
        'method_log': '방식: 폴더 -> exFAT 래핑 .ffpfsc (단일 패스) | Exfat -> .ffpfsc',
        'folder_method_log': '방식: 게임 폴더 -> exFAT 래핑 .ffpfsc (단일 패스, 임시 이미지 없음)',
        'stage_folder_ffpfsc_creating': 'exFAT 래핑 .ffpfsc 생성 중',
        'folder_direct_failed': '폴더 변환 실패. 코드: {code}',
        'direct_estimate_intro': 'MkPFS가 진행률을 표시하지 않으면 출력 파일 크기로 예상 진행률을 계산합니다.',
        'direct_estimate_formula': '예상치는 원본 크기를 상한으로 사용합니다. 실제 압축 절감률은 미리 알 수 없습니다.',
    },
    'ja': {
        'coffee_msg': 'このツールはゲームフォルダを exFAT ラップ .ffpfsc イメージへ変換し、圧縮中に CPU を使用します。\n開発者へのコーヒーで進捗バーが少し幸せになります 😄',
        'method_log': '方式: フォルダ -> exFAT ラップ .ffpfsc（1パス）| Exfat -> .ffpfsc',
        'folder_method_log': '方式: ゲームフォルダ -> exFAT ラップ .ffpfsc（1パス、一時イメージなし）',
        'stage_folder_ffpfsc_creating': 'exFAT ラップ .ffpfsc を作成中',
        'folder_direct_failed': 'フォルダ変換に失敗しました。コード: {code}',
        'direct_estimate_intro': 'MkPFS が進行率を表示しない場合、出力ファイルサイズから推定します。',
        'direct_estimate_formula': '推定ではソースサイズを上限として使用します。実際の圧縮率は事前には確定できません。',
    },
    'pt': {
        'coffee_msg': 'Esta ferramenta converte pastas de jogos em imagens .ffpfsc envolvidas em exFAT e usa a CPU durante a compressão.\nUm café para o desenvolvedor pode deixar a barra de progresso mais feliz 😄',
        'method_log': 'Método: pasta -> .ffpfsc envolvido em exFAT (uma passagem) | Exfat -> .ffpfsc',
        'folder_method_log': 'Método: pasta do jogo -> .ffpfsc envolvido em exFAT (uma passagem, sem imagem temporária)',
        'stage_folder_ffpfsc_creating': 'Criando .ffpfsc envolvido em exFAT',
        'folder_direct_failed': 'Falha na conversão da pasta. Código: {code}',
        'direct_estimate_intro': 'Se o MkPFS não mostrar progresso, será calculada uma estimativa pelo tamanho do arquivo de saída.',
        'direct_estimate_formula': 'A estimativa usa o tamanho da origem como limite superior. O ganho real não pode ser conhecido antes.',
    },
    'ru': {
        'coffee_msg': 'Инструмент преобразует папки игр в обёрнутые exFAT образы .ffpfsc и использует CPU при сжатии.\nКофе для разработчика может сделать прогресс-бар счастливее 😄',
        'method_log': 'Метод: папка -> .ffpfsc в обёртке exFAT (один проход) | Exfat -> .ffpfsc',
        'folder_method_log': 'Метод: папка игры -> .ffpfsc в обёртке exFAT (один проход, без временного образа)',
        'stage_folder_ffpfsc_creating': 'Создание .ffpfsc в обёртке exFAT',
        'folder_direct_failed': 'Ошибка преобразования папки. Код: {code}',
        'direct_estimate_intro': 'Если MkPFS не показывает прогресс, он будет оценён по размеру выходного файла.',
        'direct_estimate_formula': 'Оценка использует размер источника как верхнюю границу. Реальный выигрыш заранее неизвестен.',
    },
    'zh': {
        'coffee_msg': '该工具将游戏文件夹转换为 exFAT 封装的 .ffpfsc 镜像，并在压缩时使用 CPU。\n给开发者一杯咖啡，进度条会更开心 😄',
        'method_log': '方式：文件夹 -> exFAT 封装 .ffpfsc（单次处理）| Exfat -> .ffpfsc',
        'folder_method_log': '方式：游戏文件夹 -> exFAT 封装 .ffpfsc（单次处理，无临时镜像）',
        'stage_folder_ffpfsc_creating': '正在创建 exFAT 封装 .ffpfsc',
        'folder_direct_failed': '文件夹转换失败。代码：{code}',
        'direct_estimate_intro': '如果 MkPFS 不显示进度，将根据输出文件大小进行估算。',
        'direct_estimate_formula': '估算使用源大小作为上限。实际压缩收益无法提前确定。',
    },
    'ar': {
        'coffee_msg': 'تحوّل هذه الأداة مجلدات الألعاب إلى صور .ffpfsc مغلفة بـ exFAT وتستخدم المعالج أثناء الضغط.\nقهوة للمطور قد تجعل شريط التقدم أكثر سعادة 😄',
        'method_log': 'الطريقة: مجلد -> .ffpfsc مغلف بـ exFAT (مرحلة واحدة) | Exfat -> .ffpfsc',
        'folder_method_log': 'الطريقة: مجلد اللعبة -> .ffpfsc مغلف بـ exFAT (مرحلة واحدة، دون صورة مؤقتة)',
        'stage_folder_ffpfsc_creating': 'جارٍ إنشاء .ffpfsc مغلف بـ exFAT',
        'folder_direct_failed': 'فشل تحويل المجلد. الرمز: {code}',
        'direct_estimate_intro': 'إذا لم يعرض MkPFS التقدم، فسيتم تقديره من حجم ملف الإخراج.',
        'direct_estimate_formula': 'يستخدم التقدير حجم المصدر كحد أعلى. لا يمكن معرفة مكسب الضغط الحقيقي مسبقًا.',
    },
    'nl': {
        'coffee_msg': 'Deze tool zet gamemappen om naar exFAT-omwikkelde .ffpfsc-images en gebruikt de CPU tijdens compressie.\nEen koffie voor de ontwikkelaar maakt de voortgangsbalk blijer 😄',
        'method_log': 'Methode: map -> exFAT-omwikkelde .ffpfsc (één doorgang) | Exfat -> .ffpfsc',
        'folder_method_log': 'Methode: gamemap -> exFAT-omwikkelde .ffpfsc (één doorgang, geen tijdelijk image)',
        'stage_folder_ffpfsc_creating': 'exFAT-omwikkelde .ffpfsc maken',
        'folder_direct_failed': 'Mapconversie mislukt. Code: {code}',
        'direct_estimate_intro': 'Als MkPFS geen voortgang toont, wordt deze geschat via de grootte van het uitvoerbestand.',
        'direct_estimate_formula': 'De schatting gebruikt de brongrootte als bovengrens. De werkelijke winst is vooraf niet bekend.',
    },
    'pl': {
        'coffee_msg': 'To narzędzie konwertuje foldery gier do obrazów .ffpfsc opakowanych w exFAT i używa CPU podczas kompresji.\nKawa dla dewelopera może uszczęśliwić pasek postępu 😄',
        'method_log': 'Metoda: folder -> .ffpfsc opakowany w exFAT (jeden przebieg) | Exfat -> .ffpfsc',
        'folder_method_log': 'Metoda: folder gry -> .ffpfsc opakowany w exFAT (jeden przebieg, bez obrazu tymczasowego)',
        'stage_folder_ffpfsc_creating': 'Tworzenie .ffpfsc opakowanego w exFAT',
        'folder_direct_failed': 'Konwersja folderu nie powiodła się. Kod: {code}',
        'direct_estimate_intro': 'Jeśli MkPFS nie pokazuje postępu, zostanie on oszacowany na podstawie rozmiaru pliku wyjściowego.',
        'direct_estimate_formula': 'Szacunek używa rozmiaru źródła jako górnej granicy. Rzeczywisty zysk nie jest znany z góry.',
    },
}
for _lang, _data in _MKPFS_009_WORKFLOW_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)

_MOUNT_WORKSPACE_TEXT = {'en': {'mount_image_button': 'Open Exfat/Ffpfsc', 'mount_image_busy': 'Opening Image...', 'mount_save_busy': 'Saving Image...', 'mount_session_button': 'U: Save / Close', 'mount_choice_title': 'Open Image as U: Drive', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': 'Open Exfat file', 'mount_open_ffpfsc': 'Open Ffpfsc file', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': 'Open U: drive', 'mount_save_close': 'Save changes and close', 'mount_discard_close': 'Close without saving', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}, 'tr': {'mount_image_button': 'Exfat/Ffpfsc Aç', 'mount_image_busy': 'İmaj Açılıyor...', 'mount_save_busy': 'İmaj Kaydediliyor...', 'mount_session_button': 'U: Kaydet / Kapat', 'mount_choice_title': 'İmajı U: Sürücüsü Olarak Aç', 'mount_choice_message': 'İmaj yazılabilir bir çalışma klasörüne çıkarılır ve U: olarak bağlanır. Değişiklikler Kaydet / Kapat seçildiğinde yeni bir imaja yazılır.', 'mount_open_exfat': 'Exfat dosyası aç', 'mount_open_ffpfsc': 'Ffpfsc dosyası aç', 'mount_dialog_exfat': 'Exfat imajı seç', 'mount_dialog_ffpfsc': 'Ffpfsc imajı seç', 'mount_u_in_use_title': 'U: sürücüsü kullanımda', 'mount_u_in_use': 'U: harfi zaten kullanılıyor. Mevcut U: sürücüsünü kaldırıp yeniden dene.', 'mount_windows_only': 'Bu özellik yalnızca Windows üzerinde kullanılabilir.', 'mount_temp_missing': 'İmajı açmadan önce geçerli bir temp klasörü seç.', 'mount_open_started': 'İmaj yazılabilir U: çalışma sürücüsü olarak açılıyor', 'mount_source_log': 'İmaj: {path}', 'mount_workspace_log': 'Çalışma klasörü: {path}', 'mount_extracting_exfat': 'Exfat imajı çıkarılıyor', 'mount_extracting_ffpfsc': 'Ffpfsc imajı çıkarılıyor (uzun sürebilir)', 'mount_extract_failed': 'İmaj çıkarılamadı. Kod: {code}', 'mount_mapping_failed': 'U: sürücüsü oluşturulamadı: {error}', 'mount_opened': 'U: sürücüsü hazır. Dosya ekleyebilir, değiştirebilir veya silebilirsin.', 'mount_opened_phase': 'U: yazılabilir durumda. İşin bitince U: Kaydet / Kapat düğmesine bas.', 'mount_session_title': 'Yazılabilir U: Oturumu', 'mount_session_message': 'Kaydetmeden önce U: içinden açık dosyaları kapat. İmaj yeniden oluşturulana kadar değişiklikler çalışma klasöründedir.', 'mount_open_drive': 'U: sürücüsünü aç', 'mount_save_close': 'Değişiklikleri kaydet ve kapat', 'mount_discard_close': 'Kaydetmeden kapat', 'mount_output_dialog': 'Değiştirilmiş imajı kaydet', 'mount_same_output_title': 'Başka bir dosya adı seç', 'mount_same_output': 'Güvenlik için değiştirilmiş imajı farklı bir adla kaydet. Orijinal imajın üzerine yazılmayacak.', 'mount_output_exists_title': 'Dosyanın üzerine yazılsın mı?', 'mount_output_exists': 'Seçilen çıktı zaten var. Üzerine yazılsın mı?', 'mount_unmount_failed': 'U: sürücüsü kaldırılamadı: {error}', 'mount_saving_exfat': 'Değiştirilmiş Exfat imajı yeniden oluşturuluyor', 'mount_saving_ffpfsc': 'Değiştirilmiş Ffpfsc imajı yeniden oluşturuluyor', 'mount_save_failed': 'Değiştirilmiş imaj kaydedilemedi. Kod: {code}', 'mount_remounted_after_error': 'Kaydetme başarısız oldu; U: yeniden bağlandı ve çalışma klasörün korundu.', 'mount_workspace_preserved': 'Çalışma klasörü korundu: {path}', 'mount_saved': 'Değiştirilmiş imaj kaydedildi: {path}', 'mount_closed': 'U: sürücüsü kapatıldı.', 'mount_discard_confirm_title': 'Değişiklikler silinsin mi?', 'mount_discard_confirm': 'U: kapatılsın ve yazılabilir çalışma klasörü kaydedilmeden silinsin mi?', 'mount_cleanup_failed': 'Çalışma klasörü silinemedi: {error}', 'mount_close_app_title': 'U: sürücüsü açık', 'mount_close_app_message': 'U: bağlantısı kaldırılacak. Çalışma klasörü şu konumda korunacak:\n{path}\n\nUygulamadan çıkılsın mı?', 'mount_operation_running_title': 'İşlem devam ediyor', 'mount_operation_running': 'Mevcut işlemin bitmesini bekle veya önce iptal et.', 'mount_cancelled': 'İmaj işlemi iptal edildi.', 'mount_invalid_file': 'Geçerli bir {kind} dosyası seç.', 'mount_no_session': 'Aktif bir yazılabilir U: oturumu yok.', 'mount_subst_note': 'Yazılabilir U: çalışma modu: düzenlemeler çıkarılan dosyalara uygulanır ve yeni imaj oluşturularak kaydedilir.'}, 'fr': {'mount_image_button': 'Ouvrir Exfat/Ffpfsc', 'mount_image_busy': 'Ouverture...', 'mount_save_busy': 'Enregistrement...', 'mount_session_button': 'U: Enregistrer / Fermer', 'mount_choice_title': 'Ouvrir l’image comme lecteur U:', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': 'Ouvrir un fichier Exfat', 'mount_open_ffpfsc': 'Ouvrir un fichier Ffpfsc', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': 'Ouvrir le lecteur U:', 'mount_save_close': 'Enregistrer et fermer', 'mount_discard_close': 'Fermer sans enregistrer', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}, 'es': {'mount_image_button': 'Abrir Exfat/Ffpfsc', 'mount_image_busy': 'Abriendo imagen...', 'mount_save_busy': 'Guardando imagen...', 'mount_session_button': 'U: Guardar / Cerrar', 'mount_choice_title': 'Abrir imagen como unidad U:', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': 'Abrir archivo Exfat', 'mount_open_ffpfsc': 'Abrir archivo Ffpfsc', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': 'Abrir unidad U:', 'mount_save_close': 'Guardar y cerrar', 'mount_discard_close': 'Cerrar sin guardar', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}, 'it': {'mount_image_button': 'Apri Exfat/Ffpfsc', 'mount_image_busy': 'Apertura immagine...', 'mount_save_busy': 'Salvataggio immagine...', 'mount_session_button': 'U: Salva / Chiudi', 'mount_choice_title': 'Apri immagine come unità U:', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': 'Apri file Exfat', 'mount_open_ffpfsc': 'Apri file Ffpfsc', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': 'Apri unità U:', 'mount_save_close': 'Salva e chiudi', 'mount_discard_close': 'Chiudi senza salvare', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}, 'de': {'mount_image_button': 'Exfat/Ffpfsc öffnen', 'mount_image_busy': 'Image wird geöffnet...', 'mount_save_busy': 'Image wird gespeichert...', 'mount_session_button': 'U: Speichern / Schließen', 'mount_choice_title': 'Image als Laufwerk U: öffnen', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': 'Exfat-Datei öffnen', 'mount_open_ffpfsc': 'Ffpfsc-Datei öffnen', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': 'Laufwerk U: öffnen', 'mount_save_close': 'Speichern und schließen', 'mount_discard_close': 'Ohne Speichern schließen', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}, 'el': {'mount_image_button': 'Άνοιγμα Exfat/Ffpfsc', 'mount_image_busy': 'Άνοιγμα εικόνας...', 'mount_save_busy': 'Αποθήκευση εικόνας...', 'mount_session_button': 'U: Αποθήκευση / Κλείσιμο', 'mount_choice_title': 'Άνοιγμα εικόνας ως μονάδα U:', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': 'Άνοιγμα αρχείου Exfat', 'mount_open_ffpfsc': 'Άνοιγμα αρχείου Ffpfsc', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': 'Άνοιγμα μονάδας U:', 'mount_save_close': 'Αποθήκευση και κλείσιμο', 'mount_discard_close': 'Κλείσιμο χωρίς αποθήκευση', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}, 'ko': {'mount_image_button': 'Exfat/Ffpfsc 열기', 'mount_image_busy': '이미지 여는 중...', 'mount_save_busy': '이미지 저장 중...', 'mount_session_button': 'U: 저장 / 닫기', 'mount_choice_title': '이미지를 U: 드라이브로 열기', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': 'Exfat 파일 열기', 'mount_open_ffpfsc': 'Ffpfsc 파일 열기', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': 'U: 드라이브 열기', 'mount_save_close': '저장하고 닫기', 'mount_discard_close': '저장하지 않고 닫기', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}, 'ja': {'mount_image_button': 'Exfat/Ffpfsc を開く', 'mount_image_busy': 'イメージを開いています...', 'mount_save_busy': 'イメージを保存しています...', 'mount_session_button': 'U: 保存 / 閉じる', 'mount_choice_title': 'イメージを U: ドライブとして開く', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': 'Exfat ファイルを開く', 'mount_open_ffpfsc': 'Ffpfsc ファイルを開く', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': 'U: ドライブを開く', 'mount_save_close': '保存して閉じる', 'mount_discard_close': '保存せず閉じる', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}, 'pt': {'mount_image_button': 'Abrir Exfat/Ffpfsc', 'mount_image_busy': 'Abrindo imagem...', 'mount_save_busy': 'Salvando imagem...', 'mount_session_button': 'U: Salvar / Fechar', 'mount_choice_title': 'Abrir imagem como unidade U:', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': 'Abrir arquivo Exfat', 'mount_open_ffpfsc': 'Abrir arquivo Ffpfsc', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': 'Abrir unidade U:', 'mount_save_close': 'Salvar e fechar', 'mount_discard_close': 'Fechar sem salvar', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}, 'ru': {'mount_image_button': 'Открыть Exfat/Ffpfsc', 'mount_image_busy': 'Открытие образа...', 'mount_save_busy': 'Сохранение образа...', 'mount_session_button': 'U: Сохранить / Закрыть', 'mount_choice_title': 'Открыть образ как диск U:', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': 'Открыть файл Exfat', 'mount_open_ffpfsc': 'Открыть файл Ffpfsc', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': 'Открыть диск U:', 'mount_save_close': 'Сохранить и закрыть', 'mount_discard_close': 'Закрыть без сохранения', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}, 'zh': {'mount_image_button': '打开 Exfat/Ffpfsc', 'mount_image_busy': '正在打开镜像...', 'mount_save_busy': '正在保存镜像...', 'mount_session_button': 'U: 保存 / 关闭', 'mount_choice_title': '将镜像打开为 U: 驱动器', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': '打开 Exfat 文件', 'mount_open_ffpfsc': '打开 Ffpfsc 文件', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': '打开 U: 驱动器', 'mount_save_close': '保存并关闭', 'mount_discard_close': '不保存关闭', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}, 'ar': {'mount_image_button': 'فتح Exfat/Ffpfsc', 'mount_image_busy': 'جارٍ فتح الصورة...', 'mount_save_busy': 'جارٍ حفظ الصورة...', 'mount_session_button': 'U: حفظ / إغلاق', 'mount_choice_title': 'فتح الصورة كمحرك U:', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': 'فتح ملف Exfat', 'mount_open_ffpfsc': 'فتح ملف Ffpfsc', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': 'فتح محرك U:', 'mount_save_close': 'حفظ وإغلاق', 'mount_discard_close': 'إغلاق دون حفظ', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}, 'nl': {'mount_image_button': 'Exfat/Ffpfsc openen', 'mount_image_busy': 'Image openen...', 'mount_save_busy': 'Image opslaan...', 'mount_session_button': 'U: Opslaan / Sluiten', 'mount_choice_title': 'Image als U:-station openen', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': 'Exfat-bestand openen', 'mount_open_ffpfsc': 'Ffpfsc-bestand openen', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': 'U:-station openen', 'mount_save_close': 'Opslaan en sluiten', 'mount_discard_close': 'Sluiten zonder opslaan', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}, 'pl': {'mount_image_button': 'Otwórz Exfat/Ffpfsc', 'mount_image_busy': 'Otwieranie obrazu...', 'mount_save_busy': 'Zapisywanie obrazu...', 'mount_session_button': 'U: Zapisz / Zamknij', 'mount_choice_title': 'Otwórz obraz jako dysk U:', 'mount_choice_message': 'The image is extracted to a writable workspace and mapped as U:. Changes are written to a new image when you choose Save / Close.', 'mount_open_exfat': 'Otwórz plik Exfat', 'mount_open_ffpfsc': 'Otwórz plik Ffpfsc', 'mount_dialog_exfat': 'Select an Exfat image', 'mount_dialog_ffpfsc': 'Select an Ffpfsc image', 'mount_u_in_use_title': 'U: drive is in use', 'mount_u_in_use': 'U: is already assigned. Remove or disconnect the existing U: drive and try again.', 'mount_windows_only': 'This feature is available only on Windows.', 'mount_temp_missing': 'Select a valid temp folder before opening an image.', 'mount_open_started': 'Opening image as writable U: workspace', 'mount_source_log': 'Image: {path}', 'mount_workspace_log': 'Workspace: {path}', 'mount_extracting_exfat': 'Extracting Exfat image', 'mount_extracting_ffpfsc': 'Extracting Ffpfsc image (this can take time)', 'mount_extract_failed': 'Image extraction failed. Code: {code}', 'mount_mapping_failed': 'U: drive could not be created: {error}', 'mount_opened': 'U: drive is ready. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Click U: Save / Close when finished.', 'mount_session_title': 'Writable U: Session', 'mount_session_message': 'Close any files opened from U: before saving. Changes exist in the workspace until the image is rebuilt.', 'mount_open_drive': 'Otwórz dysk U:', 'mount_save_close': 'Zapisz i zamknij', 'mount_discard_close': 'Zamknij bez zapisu', 'mount_output_dialog': 'Save modified image', 'mount_same_output_title': 'Choose another file name', 'mount_same_output': 'For safety, save the modified image with a different name. The original image will not be overwritten.', 'mount_output_exists_title': 'Overwrite file?', 'mount_output_exists': 'The selected output already exists. Overwrite it?', 'mount_unmount_failed': 'U: drive could not be disconnected: {error}', 'mount_saving_exfat': 'Rebuilding modified Exfat image', 'mount_saving_ffpfsc': 'Rebuilding modified Ffpfsc image', 'mount_save_failed': 'Modified image could not be saved. Code: {code}', 'mount_remounted_after_error': 'Saving failed; U: was mounted again and your workspace was preserved.', 'mount_workspace_preserved': 'Workspace was preserved at: {path}', 'mount_saved': 'Modified image saved: {path}', 'mount_closed': 'U: drive was closed.', 'mount_discard_confirm_title': 'Discard changes?', 'mount_discard_confirm': 'Close U: and delete the writable workspace without saving?', 'mount_cleanup_failed': 'Workspace could not be deleted: {error}', 'mount_close_app_title': 'U: drive is open', 'mount_close_app_message': 'U: will be disconnected. The workspace will be preserved at:\n{path}\n\nExit the application?', 'mount_operation_running_title': 'Operation in progress', 'mount_operation_running': 'Wait for the current operation to finish or cancel it first.', 'mount_cancelled': 'Image operation was cancelled.', 'mount_invalid_file': 'Select a valid {kind} file.', 'mount_no_session': 'No writable U: session is active.', 'mount_subst_note': 'Writable U: workspace mode: edits are applied to extracted files and saved by rebuilding a new image.'}}
for _lang, _data in _MOUNT_WORKSPACE_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)

_IMDISK_DIRECT_MOUNT_TEXT = {'en': {'mount_choice_message': 'EXFAT is mounted directly and writable on U: without extraction. FFPFSC is first converted to a temporary EXFAT image, mounted on U:, then saved back as a new FFPFSC.', 'mount_image_button': 'Open Exfat/Ffpfsc', 'mount_session_button': 'U: Save / Close', 'mount_installing_driver': 'Installing bundled ImDisk driver', 'mount_driver_ready': 'ImDisk virtual disk driver is ready.', 'mount_driver_missing': 'The bundled ImDisk installer was not found. Rebuild the application with build_nuitka_onefile.bat so the driver is embedded.', 'mount_driver_install_failed': 'ImDisk driver installation failed: {error}', 'mount_admin_required': 'Administrator permission is required to install and use the virtual disk driver.', 'mount_direct_warning_title': 'Original EXFAT will be modified', 'mount_direct_warning': 'This EXFAT image will be mounted read/write. File additions, replacements and deletions will modify the original image directly. Make a backup first.\n\nContinue?', 'mount_open_started': 'Preparing writable U: virtual drive', 'mount_source_log': 'Source image: {path}', 'mount_direct_exfat_log': 'EXFAT mode: direct read/write mount; no temp image is used.', 'mount_ffpfsc_temp_log': 'FFPFSC work image: {path}', 'mount_extracting_ffpfsc': 'Converting FFPFSC to temporary EXFAT (this can take time)', 'mount_extract_failed': 'FFPFSC could not be converted to EXFAT. Code: {code}', 'mount_inner_exfat_missing': 'No mountable EXFAT payload was found inside the FFPFSC image.', 'mount_legacy_rebuild': 'Wrapped EXFAT was not found. Rebuilding a temporary EXFAT from the extracted file tree.', 'mount_mapping_failed': 'U: virtual drive could not be mounted: {error}', 'mount_opened': 'U: is ready and writable. You can add, replace or delete files.', 'mount_opened_phase': 'U: is writable. Close open files before Save / Close.', 'mount_session_exfat_message': 'This is a direct writable EXFAT mount. Changes are written to the original EXFAT image and finalized when U: is disconnected.', 'mount_session_ffpfsc_message': 'You are editing a temporary EXFAT extracted from the FFPFSC. Save / Close rebuilds a new FFPFSC image.', 'mount_close_exfat': 'Save EXFAT and disconnect U:', 'mount_save_ffpfsc': 'Save as FFPFSC and disconnect', 'mount_discard_ffpfsc': 'Discard changes and disconnect', 'mount_saving_ffpfsc': 'Compressing modified EXFAT back to FFPFSC', 'mount_exfat_closed': 'U: was safely disconnected. Changes remain in the original EXFAT.', 'mount_saved': 'Modified FFPFSC saved: {path}', 'mount_unmount_failed': 'U: could not be safely disconnected. Close every file and Explorer window using U:, then try again.\n\n{error}', 'mount_remounted_after_error': 'Saving failed. The temporary EXFAT was mounted again on U: and your changes were preserved.', 'mount_workspace_preserved': 'Temporary EXFAT was preserved at: {path}', 'mount_discard_confirm': 'Disconnect U: and permanently delete the temporary EXFAT without creating a new FFPFSC?', 'mount_close_app_exfat': 'U: will be safely disconnected. Changes already made will remain in the original EXFAT.\n\nExit?', 'mount_close_app_ffpfsc': 'U: will be disconnected without rebuilding FFPFSC. The temporary EXFAT will be preserved at:\n{path}\n\nExit?', 'mount_temp_missing': 'Select a valid temp folder before opening an FFPFSC image.', 'mount_direct_note': 'Virtual drive: bundled ImDisk driver. EXFAT is mounted directly; FFPFSC uses a temporary EXFAT.', 'mount_imdisk_command': 'ImDisk command: {command}', 'mount_imdisk_not_writable': 'The image file is not writable: {path}', 'mount_waiting_drive': 'Waiting for Windows to attach U:...', 'mount_ffpfsc_output_note': 'The original FFPFSC is preserved. Choose a new output file for the modified image.', 'mount_no_exfat_payload': 'The extracted payload is not an EXFAT image.'}, 'tr': {'mount_choice_message': "EXFAT temp kullanmadan doğrudan ve yazılabilir şekilde U: sürücüsüne bağlanır. FFPFSC önce temp klasöründe EXFAT'a dönüştürülür, U: üzerinde düzenlenir ve sonunda yeni bir FFPFSC olarak kaydedilir.", 'mount_image_button': 'Exfat/Ffpfsc Aç', 'mount_session_button': 'U: Kaydet / Kapat', 'mount_installing_driver': 'Paket içindeki ImDisk sürücüsü kuruluyor', 'mount_driver_ready': 'ImDisk sanal disk sürücüsü hazır.', 'mount_driver_missing': 'Paket içindeki ImDisk kurulum dosyası bulunamadı. Sürücünün EXE içine gömülmesi için projeyi build_nuitka_onefile.bat ile yeniden derle.', 'mount_driver_install_failed': 'ImDisk sürücüsü kurulamadı: {error}', 'mount_admin_required': 'Sanal disk sürücüsünü kurmak ve kullanmak için yönetici yetkisi gerekiyor.', 'mount_direct_warning_title': 'Orijinal EXFAT değiştirilecek', 'mount_direct_warning': 'Bu EXFAT imajı doğrudan yazılabilir bağlanacak. Dosya ekleme, değiştirme ve silme işlemleri orijinal EXFAT dosyasını değiştirecek. Önce yedek alman önerilir.\n\nDevam edilsin mi?', 'mount_open_started': 'Yazılabilir U: sanal sürücüsü hazırlanıyor', 'mount_source_log': 'Kaynak imaj: {path}', 'mount_direct_exfat_log': 'EXFAT modu: doğrudan yazılabilir bağlama; temp imaj kullanılmaz.', 'mount_ffpfsc_temp_log': 'FFPFSC çalışma imajı: {path}', 'mount_extracting_ffpfsc': "FFPFSC geçici EXFAT'a dönüştürülüyor (uzun sürebilir)", 'mount_extract_failed': "FFPFSC, EXFAT'a dönüştürülemedi. Kod: {code}", 'mount_inner_exfat_missing': 'FFPFSC içerisinde bağlanabilir bir EXFAT içeriği bulunamadı.', 'mount_legacy_rebuild': 'Sarmallı EXFAT bulunamadı. Çıkarılan dosya ağacından geçici EXFAT yeniden oluşturuluyor.', 'mount_mapping_failed': 'U: sanal sürücüsü bağlanamadı: {error}', 'mount_opened': 'U: hazır ve yazılabilir. Dosya ekleyebilir, değiştirebilir veya silebilirsin.', 'mount_opened_phase': 'U: yazılabilir durumda. Kaydet / Kapat öncesi açık dosyaları kapat.', 'mount_session_exfat_message': "Bu doğrudan yazılabilir EXFAT bağlantısıdır. Değişiklikler orijinal EXFAT'a yazılır ve U: güvenli biçimde kaldırıldığında tamamlanır.", 'mount_session_ffpfsc_message': 'FFPFSC içinden çıkarılan geçici EXFAT üzerinde çalışıyorsun. Kaydet / Kapat yeni bir FFPFSC oluşturur.', 'mount_close_exfat': "EXFAT'ı kaydet ve U: bağlantısını kapat", 'mount_save_ffpfsc': 'FFPFSC olarak kaydet ve bağlantıyı kapat', 'mount_discard_ffpfsc': 'Değişiklikleri sil ve bağlantıyı kapat', 'mount_saving_ffpfsc': 'Değiştirilmiş EXFAT tekrar FFPFSC olarak sıkıştırılıyor', 'mount_exfat_closed': "U: güvenli biçimde kaldırıldı. Değişiklikler orijinal EXFAT'ta kaldı.", 'mount_saved': 'Değiştirilmiş FFPFSC kaydedildi: {path}', 'mount_unmount_failed': 'U: güvenli biçimde kaldırılamadı. U: kullanan tüm dosyaları ve Gezgin pencerelerini kapatıp yeniden dene.\n\n{error}', 'mount_remounted_after_error': 'Kaydetme başarısız oldu. Geçici EXFAT yeniden U: sürücüsüne bağlandı ve değişikliklerin korundu.', 'mount_workspace_preserved': 'Geçici EXFAT korundu: {path}', 'mount_discard_confirm': 'U: bağlantısı kapatılsın ve yeni FFPFSC oluşturmadan geçici EXFAT kalıcı olarak silinsin mi?', 'mount_close_app_exfat': "U: güvenli biçimde kaldırılacak. Yapılan değişiklikler orijinal EXFAT'ta kalacak.\n\nProgram kapatılsın mı?", 'mount_close_app_ffpfsc': 'U: yeni FFPFSC oluşturulmadan kaldırılacak. Geçici EXFAT şu konumda korunacak:\n{path}\n\nProgram kapatılsın mı?', 'mount_temp_missing': 'FFPFSC açmadan önce geçerli bir temp klasörü seç.', 'mount_direct_note': 'Sanal sürücü: EXE içindeki ImDisk sürücüsü. EXFAT doğrudan, FFPFSC ise geçici EXFAT üzerinden açılır.', 'mount_imdisk_command': 'ImDisk komutu: {command}', 'mount_imdisk_not_writable': 'İmaj dosyası yazılabilir değil: {path}', 'mount_waiting_drive': "Windows'un U: sürücüsünü bağlaması bekleniyor...", 'mount_ffpfsc_output_note': 'Orijinal FFPFSC korunur. Değiştirilmiş imaj için yeni bir çıktı dosyası seç.', 'mount_no_exfat_payload': 'Çıkarılan içerik bir EXFAT imajı değil.'}}
for _lang, _data in _IMDISK_DIRECT_MOUNT_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)


_IMDISK_EMBED_FIX_TEXT = {
    "en": {
        "mount_driver_missing": (
            "The embedded ImDisk installer could not be found. "
            "Rebuild with the included build_nuitka_onefile.bat.\n\n"
            "Checked locations:\n{paths}"
        ),
        "mount_driver_payload_found": "Embedded ImDisk payload found: {path} ({size})",
        "mount_driver_payload_invalid": "Embedded ImDisk payload is invalid: {path}",
    },
    "tr": {
        "mount_driver_missing": (
            "EXE içine gömülü ImDisk kurulum paketi bulunamadı. "
            "Projeyi ZIP içindeki build_nuitka_onefile.bat ile yeniden derle.\n\n"
            "Kontrol edilen konumlar:\n{paths}"
        ),
        "mount_driver_payload_found": "Gömülü ImDisk paketi bulundu: {path} ({size})",
        "mount_driver_payload_invalid": "Gömülü ImDisk paketi geçersiz: {path}",
    },
}
for _lang, _data in _IMDISK_EMBED_FIX_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)


_WINDOWS_NATIVE_VHD_TEXT = {
    "en": {
        "mount_choice_message": (
            "EXFAT is mounted directly and writable on U: with Windows' built-in "
            "virtual-disk system. FFPFSC is first converted to a temporary EXFAT, "
            "mounted on U:, then saved back as a new FFPFSC."
        ),
        "mount_direct_note": (
            "Virtual drive: Windows built-in VHD system. EXFAT is mounted directly; "
            "FFPFSC uses a temporary EXFAT."
        ),
        "mount_admin_required": (
            "Administrator permission is required. The application will restart "
            "with a Windows UAC prompt and automatically open the selected image."
        ),
        "mount_admin_failed": "The application could not be restarted as administrator.",
        "mount_native_prepare": (
            "Windows-native adapter: temporarily preparing the raw EXFAT as a fixed VHD."
        ),
        "mount_native_restore": (
            "Restoring the image to its original raw EXFAT layout."
        ),
        "mount_native_recovery": (
            "An interrupted native mount was detected. Recovering the EXFAT image first."
        ),
        "mount_mapping_failed": "Windows could not mount the image as writable U:: {error}",
        "mount_waiting_drive": "Waiting for Windows to expose the U: drive...",
        "mount_direct_exfat_log": (
            "EXFAT mode: direct read/write mount; no second large image or temp copy is used."
        ),
        "mount_session_exfat_message": (
            "This is a direct writable EXFAT mount using Windows' built-in VHD system. "
            "Changes made on U: are written into the original EXFAT image. Closing U: "
            "restores the temporary boot-sector adaptation while preserving file changes."
        ),
        "mount_session_ffpfsc_message": (
            "You are editing the temporary EXFAT extracted from the FFPFSC. "
            "Save / Close restores the raw EXFAT layout and compresses it into a new FFPFSC."
        ),
        "mount_close_exfat": "Save EXFAT and safely disconnect U:",
        "mount_saving_ffpfsc": "Restoring EXFAT and compressing it back to FFPFSC",
        "mount_exfat_closed": (
            "U: was safely disconnected. The original raw EXFAT layout was restored "
            "and file changes were preserved."
        ),
        "mount_unmount_failed": (
            "U: could not be safely disconnected. Close all files and Explorer windows "
            "using U:, then try again.\n\n{error}"
        ),
        "mount_close_app_exfat": (
            "U: will be safely disconnected and the temporary VHD adaptation will be removed. "
            "File changes will remain in the original EXFAT.\n\nExit?"
        ),
        "mount_close_app_ffpfsc": (
            "U: will be safely disconnected without creating a new FFPFSC. "
            "The restored temporary EXFAT will remain at:\n{path}\n\nExit?"
        ),
        "mount_remounted_after_error": (
            "Saving failed. The temporary EXFAT was mounted again on U: and your changes were preserved."
        ),
        "mount_workspace_preserved": "Temporary EXFAT was preserved at: {path}",
        "mount_source_not_plain": (
            "Windows native mounting requires the image to be on a local NTFS/ReFS drive "
            "and not cloud-only, sparse, compressed or EFS-encrypted."
        ),
    },
    "tr": {
        "mount_choice_message": (
            "EXFAT, Windows'un yerleşik sanal disk altyapısıyla temp kullanmadan doğrudan "
            "ve yazılabilir şekilde U: sürücüsüne bağlanır. FFPFSC önce temp klasöründe "
            "EXFAT'a dönüştürülür, U: üzerinde düzenlenir ve yeni FFPFSC olarak kaydedilir."
        ),
        "mount_direct_note": (
            "Sanal sürücü: Windows yerleşik VHD altyapısı. EXFAT doğrudan, "
            "FFPFSC ise geçici EXFAT üzerinden açılır."
        ),
        "mount_admin_required": (
            "Yönetici yetkisi gerekiyor. Uygulama Windows UAC penceresiyle yönetici olarak "
            "yeniden başlayacak ve seçilen imajı otomatik açacak."
        ),
        "mount_admin_failed": "Uygulama yönetici yetkisiyle yeniden başlatılamadı.",
        "mount_native_prepare": (
            "Windows yerleşik bağlama adaptörü: ham EXFAT geçici olarak sabit VHD düzenine hazırlanıyor."
        ),
        "mount_native_restore": (
            "İmaj özgün ham EXFAT düzenine geri döndürülüyor."
        ),
        "mount_native_recovery": (
            "Yarım kalmış bir yerleşik bağlama bulundu. Önce EXFAT güvenli biçimde kurtarılıyor."
        ),
        "mount_mapping_failed": "Windows imajı yazılabilir U: sürücüsüne bağlayamadı: {error}",
        "mount_waiting_drive": "Windows'un U: sürücüsünü göstermesi bekleniyor...",
        "mount_direct_exfat_log": (
            "EXFAT modu: doğrudan yazılabilir bağlama; ikinci büyük imaj veya temp kopyası kullanılmaz."
        ),
        "mount_session_exfat_message": (
            "Bu, Windows yerleşik VHD sistemiyle yapılan doğrudan yazılabilir EXFAT bağlantısıdır. "
            "U: üzerindeki değişiklikler orijinal EXFAT'a yazılır. U: kapatılırken geçici "
            "önyükleme sektörü uyarlaması kaldırılır, dosya değişiklikleri korunur."
        ),
        "mount_session_ffpfsc_message": (
            "FFPFSC içinden çıkarılan geçici EXFAT üzerinde çalışıyorsun. Kaydet / Kapat, "
            "EXFAT'ı ham düzenine geri döndürür ve yeni bir FFPFSC olarak sıkıştırır."
        ),
        "mount_close_exfat": "EXFAT'ı kaydet ve U: bağlantısını güvenli kapat",
        "mount_saving_ffpfsc": "EXFAT geri yüklenip tekrar FFPFSC olarak sıkıştırılıyor",
        "mount_exfat_closed": (
            "U: güvenli biçimde kaldırıldı. Orijinal ham EXFAT düzeni geri yüklendi "
            "ve dosya değişiklikleri korundu."
        ),
        "mount_unmount_failed": (
            "U: güvenli biçimde kaldırılamadı. U: kullanan bütün dosyaları ve Gezgin "
            "pencerelerini kapatıp yeniden dene.\n\n{error}"
        ),
        "mount_close_app_exfat": (
            "U: güvenli biçimde kaldırılacak ve geçici VHD uyarlaması silinecek. "
            "Dosya değişiklikleri orijinal EXFAT'ta kalacak.\n\nProgram kapatılsın mı?"
        ),
        "mount_close_app_ffpfsc": (
            "U: yeni FFPFSC oluşturmadan güvenli biçimde kaldırılacak. Ham düzenine "
            "geri döndürülmüş geçici EXFAT şu konumda korunacak:\n{path}\n\nProgram kapatılsın mı?"
        ),
        "mount_remounted_after_error": (
            "Kaydetme başarısız oldu. Geçici EXFAT yeniden U: sürücüsüne bağlandı ve değişiklikler korundu."
        ),
        "mount_workspace_preserved": "Geçici EXFAT korundu: {path}",
        "mount_source_not_plain": (
            "Windows yerleşik bağlama için imaj yerel bir NTFS/ReFS diskte bulunmalı; "
            "bulut yer tutucusu, sparse, sıkıştırılmış veya EFS şifreli olmamalıdır."
        ),
    },
}
for _lang, _data in _WINDOWS_NATIVE_VHD_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)


_FFPFSC_OVERWRITE_TEXT = {
    "en": {
        "mount_save_ffpfsc": "Save and overwrite original FFPFSC",
        "mount_ffpfsc_overwrite_title": "Overwrite original FFPFSC?",
        "mount_ffpfsc_overwrite_confirm": (
            "The modified image will replace the original FFPFSC file:\n\n"
            "{path}\n\n"
            "The new image is first built as a temporary file. The original is "
            "replaced only after compression and optional verification succeed.\n\nContinue?"
        ),
        "mount_ffpfsc_overwrite_log": "Original FFPFSC will be safely replaced: {path}",
        "mount_saving_ffpfsc": "Rebuilding and replacing the original FFPFSC",
        "mount_saved": "Original FFPFSC successfully updated: {path}",
        "mount_replace_failed": (
            "The rebuilt FFPFSC was created, but the original file could not be replaced: {error}"
        ),
    },
    "tr": {
        "mount_save_ffpfsc": "Kaydet ve orijinal FFPFSC'nin üzerine yaz",
        "mount_ffpfsc_overwrite_title": "Orijinal FFPFSC'nin üzerine yazılsın mı?",
        "mount_ffpfsc_overwrite_confirm": (
            "Değiştirilmiş imaj aşağıdaki orijinal FFPFSC dosyasının üzerine yazılacak:\n\n"
            "{path}\n\n"
            "Yeni imaj önce geçici bir dosya olarak oluşturulur. Sıkıştırma ve seçiliyse "
            "doğrulama başarıyla bitmeden orijinal dosya değiştirilmez.\n\nDevam edilsin mi?"
        ),
        "mount_ffpfsc_overwrite_log": "Orijinal FFPFSC güvenli biçimde değiştirilecek: {path}",
        "mount_saving_ffpfsc": "Orijinal FFPFSC yeniden oluşturulup üzerine yazılıyor",
        "mount_saved": "Orijinal FFPFSC başarıyla güncellendi: {path}",
        "mount_replace_failed": (
            "Yeni FFPFSC oluşturuldu ancak orijinal dosyanın üzerine yazılamadı: {error}"
        ),
    },
}
for _lang, _data in _FFPFSC_OVERWRITE_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)


_V28_MOUNT_UI_TEXT = {
    "en": {
        "mount_save_ffpfsc": "Save and overwrite original FFPFSC",
        "mount_discard_ffpfsc": "Discard changes and disconnect",
        "mount_admin_required": (
            "Administrator permission is required. Start the application as administrator."
        ),
        "mount_ffpfsc_overwrite_log": "Original FFPFSC will be safely replaced: {path}",
        "mount_sessions_cleaned": "Temporary mount session files were deleted.",
    },
    "tr": {
        "mount_save_ffpfsc": "Kaydet ve orijinal FFPFSC'nin üzerine yaz",
        "mount_discard_ffpfsc": "Değişiklikleri sil ve bağlantıyı kapat",
        "mount_admin_required": (
            "Yönetici yetkisi gerekiyor. Uygulamayı yönetici olarak çalıştır."
        ),
        "mount_ffpfsc_overwrite_log": "Orijinal FFPFSC güvenli biçimde değiştirilecek: {path}",
        "mount_sessions_cleaned": "Geçici sanal sürücü çalışma dosyaları silindi.",
    },
}
for _lang, _data in _V28_MOUNT_UI_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)


_PRO_FEATURES_TEXT = {
    "en": {
        "preset": "Profile:",
        "platform": "Platform:",
        "platform_log": "Target platform: {value}",
        "preset_custom": "Custom",
        "preset_fast": "Fast",
        "preset_balanced": "Balanced",
        "preset_max": "Max Compression",
        "preset_low_ram": "Low RAM",
        "block_size": "Block:",
        "auto_memory_retry": "Retry automatically on memory error",
        "preflight_title": "Pre-flight storage check:",
        "preflight_source": "Source size: {size}",
        "preflight_output": "Output drive: {free} free | Filesystem: {fs} | Type: {drive_type}",
        "preflight_temp": "Temp drive: {free} free | Filesystem: {fs} | Type: {drive_type}",
        "preflight_required": "Estimated minimum free space: Output {output} | Temp {temp}",
        "preflight_same_drive": "Temp and output are on the same drive. Combined estimated requirement: {required}",
        "preflight_output_low": "Not enough free space on the output drive. Required approximately {required}, available {free}.",
        "preflight_temp_low": "Temp drive may not have enough free space. Required approximately {required}, available {free}.",
        "preflight_fat32": "FAT32 cannot store a large FFPFSC file. Select an NTFS or exFAT output drive.",
        "preflight_temp_fs_warning": "Temp is on {fs}. NTFS is recommended for links and large temporary files.",
        "preflight_hdd_warning": "Temp is on a mechanical HDD. SSD/NVMe is strongly recommended.",
        "preflight_ok": "Pre-flight check passed.",
        "block_size_log": "Block size: {value}",
        "preset_log": "Compression profile: {value}",
        "memory_retry_enabled_log": "Automatic memory-error retry: enabled",
        "memory_retry_start": "Memory error detected. Retrying once with CPU {cpu}, compression level {level}, block {block}.",
        "memory_retry_success": "Automatic low-memory retry completed successfully.",
        "memory_retry_failed": "Automatic low-memory retry also failed.",
        "friendly_error_title": "Suggested solution:",
        "friendly_error_memory": "The process ran out of memory. Lower CPU cores to 2 or 1, use compression level 5, and close other applications.",
        "friendly_error_space": "A drive ran out of free space. Check both the output and temp folders.",
        "friendly_error_permission": "Access was denied. Confirm that the locations are writable and not locked by another application.",
        "friendly_error_link": "The temp drive could not create the required link/staging file. Use a local NTFS temp folder.",
        "friendly_error_fat32": "The destination may be FAT32 or another filesystem with a file-size limitation. Use NTFS or exFAT.",
        "friendly_error_missing": "A required source file was not found. Check that the game dump is complete.",
        "friendly_error_generic": "Review the final MkPFS lines above and verify source, output and temp paths.",
        "recursive_scan_log": "Recursive batch scan: up to 3 levels; only valid PS5 folders and EXFAT images are included.",
        "compression_rating": "Compression result: {rating}",
        "rating_excellent": "Excellent",
        "rating_good": "Good",
        "rating_okay": "Moderate",
        "rating_poor": "Low gain",
    },
    "tr": {
        "preset": "Profil:",
        "platform": "Platform:",
        "platform_log": "Hedef platform: {value}",
        "preset_custom": "Özel",
        "preset_fast": "Hızlı",
        "preset_balanced": "Dengeli",
        "preset_max": "Maksimum",
        "preset_low_ram": "Düşük RAM",
        "block_size": "Blok:",
        "auto_memory_retry": "Bellek hatasında otomatik tekrar",
        "preflight_title": "İşlem öncesi depolama kontrolü:",
        "preflight_source": "Kaynak boyutu: {size}",
        "preflight_output": "Çıkış diski: {free} boş | Dosya sistemi: {fs} | Tür: {drive_type}",
        "preflight_temp": "Temp diski: {free} boş | Dosya sistemi: {fs} | Tür: {drive_type}",
        "preflight_required": "Tahmini minimum boş alan: Çıkış {output} | Temp {temp}",
        "preflight_same_drive": "Temp ve çıkış aynı diskte. Birleşik tahmini gereksinim: {required}",
        "preflight_output_low": "Çıkış diskinde yeterli boş alan yok. Yaklaşık gereken {required}, mevcut {free}.",
        "preflight_temp_low": "Temp diskindeki boş alan yetersiz kalabilir. Yaklaşık gereken {required}, mevcut {free}.",
        "preflight_fat32": "FAT32 büyük FFPFSC dosyasını saklayamaz. NTFS veya exFAT çıkış diski seç.",
        "preflight_temp_fs_warning": "Temp diski {fs}. Bağlantılar ve büyük geçici dosyalar için NTFS önerilir.",
        "preflight_hdd_warning": "Temp mekanik HDD üzerinde. SSD/NVMe kullanılması kuvvetle önerilir.",
        "preflight_ok": "İşlem öncesi kontrol başarılı.",
        "block_size_log": "Blok boyutu: {value}",
        "preset_log": "Sıkıştırma profili: {value}",
        "memory_retry_enabled_log": "Bellek hatasında otomatik tekrar: açık",
        "memory_retry_start": "Bellek hatası algılandı. CPU {cpu}, sıkıştırma {level}, blok {block} ile bir kez yeniden deneniyor.",
        "memory_retry_success": "Düşük bellek ayarlarıyla otomatik tekrar başarıyla tamamlandı.",
        "memory_retry_failed": "Düşük bellek ayarlarıyla otomatik tekrar da başarısız oldu.",
        "friendly_error_title": "Önerilen çözüm:",
        "friendly_error_memory": "İşlem belleği tüketti. CPU çekirdeğini 2 veya 1'e indir, sıkıştırma seviyesini 5 yap ve diğer uygulamaları kapat.",
        "friendly_error_space": "Disklerden birinde boş alan bitti. Çıkış ve temp klasörlerinin ikisini de kontrol et.",
        "friendly_error_permission": "Erişim reddedildi. Konumların yazılabilir olduğunu ve başka uygulama tarafından kilitlenmediğini kontrol et.",
        "friendly_error_link": "Temp diskinde gerekli bağlantı/geçici dosya oluşturulamadı. Yerel NTFS temp klasörü kullan.",
        "friendly_error_fat32": "Hedef FAT32 veya dosya boyutu sınırı olan başka bir dosya sistemi olabilir. NTFS ya da exFAT kullan.",
        "friendly_error_missing": "Gerekli kaynak dosyalardan biri bulunamadı. Oyun dökümünün eksiksiz olduğunu kontrol et.",
        "friendly_error_generic": "Yukarıdaki son MkPFS satırlarını incele; kaynak, çıkış ve temp yollarını kontrol et.",
        "recursive_scan_log": "Alt klasör taraması: 3 seviyeye kadar; yalnızca geçerli PS5 klasörleri ve EXFAT imajları eklenir.",
        "compression_rating": "Sıkıştırma sonucu: {rating}",
        "rating_excellent": "Mükemmel",
        "rating_good": "İyi",
        "rating_okay": "Orta",
        "rating_poor": "Düşük kazanım",
    },
}
for _lang, _data in _PRO_FEATURES_TEXT.items():
    if _lang in _I18N:
        _I18N[_lang].update(_data)

for _lang, _data in list(_I18N.items()):
    _merged = dict(_I18N["en"])
    _merged.update(_data)
    _I18N[_lang] = _merged

_TEXT_TO_KEY = {}
for _lang, _data in _I18N.items():
    for _key, _value in _data.items():
        _TEXT_TO_KEY.setdefault(_value, _key)


def detect_system_language() -> str:
    """Detect Windows/macOS/Linux UI language; unsupported languages fall back to English."""
    try:
        loc = locale.getlocale()[0] or ""
    except Exception:
        loc = ""
    loc = loc.lower().replace("-", "_")
    if loc.startswith("zh"):
        return "zh"
    code = loc.split("_")[0]
    return code if code in LANGUAGE_DISPLAY else "en"


def translate_value(lang_code: str, key_or_text: str) -> str:
    key = key_or_text if key_or_text in _I18N["en"] else _TEXT_TO_KEY.get(key_or_text, key_or_text)
    return _I18N.get(lang_code, _I18N["en"]).get(key, _I18N["en"].get(key, key_or_text))


def is_frozen() -> bool:
    """PyInstaller veya Nuitka ile derlenmiş çalışma zamanını algıla."""
    return getattr(sys, "frozen", False) is True or "__compiled__" in globals()


def compiled_executable_path() -> str:
    """Kullanıcının çalıştırdığı gerçek EXE yolunu döndür."""
    compiled_info = globals().get("__compiled__")
    if compiled_info is not None:
        original_argv0 = getattr(compiled_info, "original_argv0", None)
        if original_argv0:
            return os.path.abspath(str(original_argv0))
    return os.path.abspath(sys.executable)


def resource_path(relative: str) -> str:
    """Normal Python, PyInstaller ve Nuitka onefile kaynak yolunu döndür."""
    relative = str(relative).replace("/", os.sep).replace("\\", os.sep)

    candidates = []

    pyinstaller_base = getattr(sys, "_MEIPASS", None)
    if pyinstaller_base:
        candidates.append(os.path.join(pyinstaller_base, relative))

    # Nuitka onefile data files are extracted beside the compiled main module.
    candidates.append(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)
    )

    # Development/sidecar fallback beside the real executable.
    try:
        candidates.append(
            os.path.join(
                os.path.dirname(compiled_executable_path()),
                relative,
            )
        )
    except Exception:
        pass

    for candidate in candidates:
        if os.path.exists(candidate):
            return os.path.abspath(candidate)

    # Return the primary expected location for useful diagnostics.
    return os.path.abspath(candidates[0])




def run_no_console(args, **kwargs):
    """
    subprocess.run için CMD penceresi göstermeyen yardımcı.
    """
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        kwargs.setdefault("startupinfo", startupinfo)
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
    return subprocess.run(args, **kwargs)

def normalize_path(path: str) -> str:
    if not path:
        return ""
    return os.path.normpath(path)


def command_to_text(cmd: list[str]) -> str:
    return " ".join(cmd)


def mkpfs_prefix_works(prefix: list[str]) -> bool:
    """Return True if the given command prefix can run MkPFS."""
    try:
        p = subprocess.run(
            prefix + ["-V"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=12,
        )
        out = p.stdout or ""
        return p.returncode == 0 or "MkPFS" in out or "mkpfs" in out.lower()
    except Exception:
        return False


def detect_mkpfs_prefix() -> list[str] | None:
    """
    Detect a Python/MkPFS runner for source-code mode.
    This fixes the Microsoft Store Python alias problem:
    the GUI may run with WindowsApps Python while MkPFS is installed in real Python311.
    """
    candidates: list[list[str]] = []

    # Current interpreter first.
    candidates.append([sys.executable, "-m", "mkpfs"])

    # Python launcher candidates.
    candidates.append(["py", "-3.11", "-m", "mkpfs"])
    candidates.append(["py", "-3.12", "-m", "mkpfs"])
    candidates.append(["py", "-3.10", "-m", "mkpfs"])
    candidates.append(["py", "-3", "-m", "mkpfs"])

    # Common per-user install paths.
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        for ver in ("Python311", "Python312", "Python310", "Python313"):
            p = os.path.join(local_app, "Programs", "Python", ver, "python.exe")
            if os.path.exists(p):
                candidates.append([p, "-m", "mkpfs"])

    # Deduplicate
    seen = set()
    unique = []
    for c in candidates:
        key = tuple(c)
        if key not in seen:
            seen.add(key)
            unique.append(c)

    for prefix in unique:
        if mkpfs_prefix_works(prefix):
            return prefix

    return None


def parse_version_value(value: str) -> tuple[int, ...]:
    """Convert version text like 1, 1.1, 1.2.3 to a comparable tuple."""
    value = (value or "").strip()
    parts = re.findall(r"\d+", value)
    if not parts:
        return (0,)
    return tuple(int(p) for p in parts)


def is_remote_version_newer(remote: str, local: str) -> bool:
    r = list(parse_version_value(remote))
    l = list(parse_version_value(local))
    max_len = max(len(r), len(l))
    r += [0] * (max_len - len(r))
    l += [0] * (max_len - len(l))
    return tuple(r) > tuple(l)


def safe_download_path(folder: str, filename: str) -> str:
    os.makedirs(folder, exist_ok=True)
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(folder, filename)
    i = 2
    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{base}_{i}{ext}")
        i += 1
    return candidate


def app_base_dir() -> str:
    """EXE ise gerçek EXE klasörü; Python ise .py dosyasının klasörü."""
    compiled_info = globals().get("__compiled__")
    if compiled_info is not None:
        containing_dir = getattr(compiled_info, "containing_dir", None)
        if containing_dir:
            return os.path.abspath(str(containing_dir))
        return os.path.dirname(compiled_executable_path())

    if getattr(sys, "frozen", False) is True:
        return os.path.dirname(os.path.abspath(sys.executable))

    return os.path.dirname(os.path.abspath(__file__))


def get_process_log_path() -> str:
    return os.path.join(app_base_dir(), "ps5-pfs-log.html")


def get_config_path() -> str:
    return os.path.join(app_base_dir(), "ps5-pfs-config.ini")


def get_path_size(path: str) -> int:
    """Dosya veya klasör toplam boyutunu byte cinsinden döndürür."""
    path = normalize_path(path)
    if not os.path.exists(path):
        return 0
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    total = 0
    for root, dirs, files in os.walk(path):
        for filename in files:
            fp = os.path.join(root, filename)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def format_bytes(size: int) -> str:
    size = float(size or 0)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024


def format_duration(seconds: float) -> str:
    seconds = int(round(seconds or 0))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} sa {m} dk {s} sn"
    if m:
        return f"{m} dk {s} sn"
    return f"{s} sn"



def _existing_path_for_disk(path: str) -> str:
    candidate = Path(normalize_path(path))
    while not candidate.exists() and candidate.parent != candidate:
        candidate = candidate.parent
    return str(candidate)


def get_free_space_bytes(path: str) -> int:
    try:
        return int(shutil.disk_usage(_existing_path_for_disk(path)).free)
    except Exception:
        return 0


def same_storage_volume(path_a: str, path_b: str) -> bool:
    try:
        a = Path(_existing_path_for_disk(path_a)).resolve().drive.lower()
        b = Path(_existing_path_for_disk(path_b)).resolve().drive.lower()
        return bool(a and b and a == b)
    except Exception:
        return os.path.splitdrive(path_a)[0].lower() == os.path.splitdrive(path_b)[0].lower()


def get_filesystem_type(path: str) -> str:
    if os.name != "nt":
        return "Unknown"
    try:
        import ctypes
        existing = _existing_path_for_disk(path)
        drive = os.path.splitdrive(os.path.abspath(existing))[0] + "\\"
        if not drive.strip("\\"):
            return "Unknown"
        fs_buf = ctypes.create_unicode_buffer(64)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            drive, None, 0, None, None, None, fs_buf, len(fs_buf)
        )
        return fs_buf.value.strip() if ok and fs_buf.value else "Unknown"
    except Exception:
        return "Unknown"


def get_drive_media_type(path: str) -> str:
    if os.name != "nt":
        return "Unknown"
    try:
        drive = os.path.splitdrive(
            os.path.abspath(_existing_path_for_disk(path))
        )[0].rstrip(":\\")
        if not drive:
            return "Unknown"
        command = (
            f"$p=Get-Partition -DriveLetter '{drive}' -ErrorAction Stop;"
            "$d=$p|Get-Disk;"
            "Write-Output ($d.MediaType.ToString()+'|'+$d.BusType.ToString())"
        )
        result = run_no_console(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=7,
            check=False,
        )
        text = (result.stdout or "").strip().upper()
        if "SSD" in text or "NVME" in text:
            return "SSD/NVMe"
        if "HDD" in text:
            return "HDD"
    except Exception:
        pass
    return "Unknown"


def is_valid_ps5_game_folder(path: str) -> bool:
    path = normalize_path(path)
    return (
        os.path.isdir(path)
        and os.path.isfile(os.path.join(path, "eboot.bin"))
        and os.path.isfile(os.path.join(path, "sce_sys", "param.json"))
    )


def discover_conversion_targets(root: str, max_depth: int = 3) -> list[str]:
    root = normalize_path(root)
    if not os.path.isdir(root):
        return []

    found: list[str] = []

    def scan(folder: str, depth: int) -> None:
        if depth > max_depth:
            return
        if is_valid_ps5_game_folder(folder):
            found.append(normalize_path(folder))
            return
        try:
            entries = sorted(os.scandir(folder), key=lambda e: e.name.lower())
        except (OSError, PermissionError):
            return
        for entry in entries:
            try:
                if entry.is_file() and entry.name.lower().endswith(".exfat"):
                    found.append(normalize_path(entry.path))
                elif entry.is_dir(follow_symlinks=False) and not entry.name.startswith("."):
                    scan(entry.path, depth + 1)
            except (OSError, PermissionError):
                continue

    scan(root, 0)

    unique = []
    seen = set()
    for item in found:
        key = os.path.normcase(os.path.abspath(item))
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def set_cli_option(args: list[str], option: str, value: str) -> list[str]:
    result = list(args)
    if option in result:
        idx = result.index(option)
        if idx + 1 < len(result):
            result[idx + 1] = str(value)
    else:
        insert_at = max(0, len(result) - 2)
        result[insert_at:insert_at] = [option, str(value)]
    return result


def classify_mkpfs_failure(output_text: str) -> str:
    text = (output_text or "").lower()
    patterns = [
        ("memory", ("memoryerror", "out of memory", "cannot allocate memory", "not enough memory", "bad_alloc")),
        ("space", ("no space left", "disk full", "not enough space", "insufficient disk space", "errno 28")),
        ("permission", ("permission denied", "access is denied", "winerror 5", "errno 13")),
        ("link", ("hard link and symlink both failed", "unable to stage source file", "hardlink", "symlink")),
        ("fat32", ("file too large", "errno 27", "invalid argument", "winerror 22")),
        ("missing", ("no such file or directory", "file not found", "winerror 2")),
    ]
    for kind, needles in patterns:
        if any(needle in text for needle in needles):
            return kind
    return "generic"


def compression_rating_key(saved_percent: float) -> str:
    if saved_percent >= 25:
        return "rating_excellent"
    if saved_percent >= 10:
        return "rating_good"
    if saved_percent >= 5:
        return "rating_okay"
    return "rating_poor"


def read_game_title_from_param(folder: str) -> str | None:
    """param.json içinden okunabilir oyun adını bulmaya çalışır."""
    if not os.path.isdir(folder):
        return None

    candidates = [
        os.path.join(folder, "sce_sys", "param.json"),
        os.path.join(folder, "sce_sys", "param.JSON"),
    ]

    for p in candidates:
        if not os.path.isfile(p):
            continue

        for enc in ("utf-8-sig", "utf-8", "cp1254", "latin-1"):
            try:
                with open(p, "r", encoding=enc) as f:
                    data = json.load(f)

                for key in ("titleName", "title_name", "name"):
                    value = data.get(key)
                    if value:
                        return str(value).strip()

                localized = data.get("localizedParameters") or data.get("localized_parameters")
                if isinstance(localized, dict):
                    # Önce Türkçe/varsayılan alanları dene, sonra herhangi bir titleName.
                    preferred_keys = ["tr-TR", "tr", "default", "en-US", "en"]
                    for loc_key in preferred_keys + list(localized.keys()):
                        loc = localized.get(loc_key)
                        if isinstance(loc, dict):
                            value = loc.get("titleName") or loc.get("name") or loc.get("title")
                            if value:
                                return str(value).strip()
            except Exception:
                continue

    return None


def derive_game_display_name(source: str, out_name: str | None = None) -> str:
    title = read_game_title_from_param(source)
    title_id = read_title_id_from_game_folder(source) if os.path.isdir(source) else None

    if title and title_id:
        return f"{title} ({title_id})"
    if title:
        return title
    if title_id:
        return title_id
    if out_name:
        return os.path.splitext(os.path.basename(out_name))[0]
    return os.path.basename(source.rstrip("\\/")) or "Bilinmeyen oyun"


def append_process_summary_log(
    game_name: str,
    previous_size: int,
    new_size: int,
    elapsed_seconds: float,
    out_path: str,
    labels: dict[str, str] | None = None,
    duration_text: str | None = None,
) -> str:
    # Append the process summary to ps5-pfs-log.html using the current UI language labels.
    log_path = get_process_log_path()
    gain = previous_size - new_size
    gain_percent = (gain / previous_size * 100.0) if previous_size > 0 else 0.0

    labels = labels or {
        "game_name": "Game name",
        "previous_size": "Previous size",
        "new_size": "New size",
        "gain": "Gain",
        "duration": "Process duration",
        "output": "Output",
    }
    duration_text = duration_text or format_duration(elapsed_seconds)

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry_id = f"log-{int(time.time() * 1000)}"
    gain_class = "success" if gain >= 0 else "warning"
    gain_sign = "" if gain >= 0 else "-"

    def esc(value) -> str:
        return html_lib.escape(str(value), quote=True)

    entry = f'''
        <div class="card log-card shadow-sm border-0 mb-3" id="{esc(entry_id)}">
            <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
                <div>
                    <span class="badge text-bg-primary me-2">PS5-PFS</span>
                    <strong>{esc(game_name)}</strong>
                </div>
                <span class="text-secondary small">{esc(timestamp)}</span>
            </div>
            <div class="card-body">
                <div class="row g-3">
                    <div class="col-12 col-md-6 col-xl-3">
                        <div class="metric-box">
                            <div class="metric-label">{esc(labels['previous_size'])}</div>
                            <div class="metric-value">{esc(format_bytes(previous_size))}</div>
                        </div>
                    </div>
                    <div class="col-12 col-md-6 col-xl-3">
                        <div class="metric-box">
                            <div class="metric-label">{esc(labels['new_size'])}</div>
                            <div class="metric-value">{esc(format_bytes(new_size))}</div>
                        </div>
                    </div>
                    <div class="col-12 col-md-6 col-xl-3">
                        <div class="metric-box metric-{esc(gain_class)}">
                            <div class="metric-label">{esc(labels['gain'])}</div>
                            <div class="metric-value">{esc(gain_sign + format_bytes(abs(gain)))} <small>({gain_percent:.2f}%)</small></div>
                        </div>
                    </div>
                    <div class="col-12 col-md-6 col-xl-3">
                        <div class="metric-box">
                            <div class="metric-label">{esc(labels['duration'])}</div>
                            <div class="metric-value">{esc(duration_text)}</div>
                        </div>
                    </div>
                </div>
                <div class="output-path mt-3">
                    <div class="metric-label">{esc(labels['output'])}</div>
                    <code>{esc(out_path)}</code>
                </div>
            </div>
        </div>
'''

    marker = "<!-- PS5_PFS_LOG_ENTRIES_END -->"
    footer = f'''
        {marker}
    </main>
    <footer class="container py-4 text-center text-secondary small">
        Generated by PS5-PFS-Packager
    </footer>
</body>
</html>
'''

    header = f'''<!doctype html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PS5-PFS Log</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background: radial-gradient(circle at top left, #1e3a8a 0, #111827 34%, #09090b 100%);
            color: #e5e7eb;
            min-height: 100vh;
        }}
        .hero {{
            border: 1px solid rgba(255,255,255,.12);
            background: rgba(15, 23, 42, .72);
            backdrop-filter: blur(10px);
            border-radius: 22px;
        }}
        .log-card {{
            background: rgba(255, 255, 255, .95);
            color: #111827;
            border-radius: 18px;
            overflow: hidden;
        }}
        .log-card .card-header {{
            background: #f8fafc;
            border-bottom: 1px solid #e5e7eb;
        }}
        .metric-box {{
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 14px 16px;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            min-height: 86px;
        }}
        .metric-success {{
            border-color: #bbf7d0;
            background: linear-gradient(180deg, #f0fdf4 0%, #dcfce7 100%);
        }}
        .metric-warning {{
            border-color: #fde68a;
            background: linear-gradient(180deg, #fffbeb 0%, #fef3c7 100%);
        }}
        .metric-label {{
            color: #64748b;
            font-size: .78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .04em;
            margin-bottom: 4px;
        }}
        .metric-value {{
            color: #0f172a;
            font-size: 1.15rem;
            font-weight: 800;
        }}
        .output-path {{
            background: #0f172a;
            border-radius: 16px;
            padding: 14px 16px;
        }}
        .output-path .metric-label {{
            color: #94a3b8;
        }}
        .output-path code {{
            color: #bfdbfe;
            white-space: pre-wrap;
            word-break: break-all;
        }}
    </style>
</head>
<body>
    <main class="container py-4 py-lg-5">
        <section class="hero p-4 p-lg-5 mb-4 shadow">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-3">
                <div>
                    <h1 class="display-6 fw-bold mb-1">PS5-PFS-Packager Log</h1>
                    <p class="text-secondary mb-0">ffpfsc conversion history</p>
                </div>
                <span class="badge rounded-pill text-bg-success px-3 py-2">HTML Log</span>
            </div>
        </section>
'''

    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            content = ""

        # Eski sürümden kalan görünür \\n metinlerini gerçek satır sonuna çevir.
        content = content.replace("\\n        ", "\n        ")

        if marker in content:
            content = content.replace(marker, entry + "\n        " + marker, 1)
        else:
            content = header + entry + footer
    else:
        content = header + entry + footer

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(content)

    return log_path

def safe_delete_game_folder(path: str, output_dir: str, temp_dir: str, log_func, t=None, tf=None) -> bool:
    """Delete the source game folder after successful pack, with basic safety checks."""
    t = t or (lambda key: key)
    tf = tf or (lambda key, **kwargs: t(key).format(**kwargs))

    path = normalize_path(path)
    output_dir = normalize_path(output_dir)
    temp_dir = normalize_path(temp_dir)

    if not os.path.isdir(path):
        log_func(t("delete_skip_not_folder"), "warn")
        return True

    # Safety: do not delete output/temp roots.
    try:
        p_real = os.path.realpath(path)
        out_real = os.path.realpath(output_dir)
        tmp_real = os.path.realpath(temp_dir)
        if p_real in (out_real, tmp_real):
            log_func(t("delete_safety_same"), "error")
            return False
        if out_real.startswith(p_real + os.sep) or tmp_real.startswith(p_real + os.sep):
            log_func(t("delete_safety_inside"), "error")
            return False
    except Exception:
        pass

    try:
        shutil.rmtree(path)
        log_func(tf("game_folder_deleted", path=path), "success")
        return True
    except Exception as exc:
        log_func(tf("game_folder_delete_failed", error=exc), "error")
        return False


def safe_filename(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "output"


def read_title_id_from_game_folder(folder: str) -> str | None:
    """Read titleId from sce_sys/param.json when available."""
    candidates = [
        os.path.join(folder, "sce_sys", "param.json"),
        os.path.join(folder, "sce_sys", "param.JSON"),
    ]
    for p in candidates:
        if not os.path.isfile(p):
            continue
        # Try common encodings
        for enc in ("utf-8-sig", "utf-8", "cp1254", "latin-1"):
            try:
                with open(p, "r", encoding=enc) as f:
                    data = json.load(f)
                value = data.get("titleId") or data.get("title_id") or data.get("titleID")
                if value:
                    value = str(value).strip()
                    # Keep common title id format clean.
                    m = re.search(r"[A-Z]{4}\d{5}", value.upper())
                    return m.group(0) if m else safe_filename(value)
            except Exception:
                continue
    return None


def derive_output_name(source: str) -> str:
    source = normalize_path(source)
    if os.path.isdir(source):
        title_id = read_title_id_from_game_folder(source)
        if title_id:
            return f"{title_id}.ffpfsc"
        base = os.path.basename(source.rstrip("\\/"))
        # Common folders like PPSA17330-app0 -> PPSA17330.ffpfsc
        m = re.search(r"(PPSA\d{5})", base.upper())
        if m:
            return f"{m.group(1)}.ffpfsc"
        return f"{safe_filename(base)}.ffpfsc"
    else:
        base = os.path.splitext(os.path.basename(source))[0]
        m = re.search(r"(PPSA\d{5})", base.upper())
        if m:
            return f"{m.group(1)}.ffpfsc"
        return f"{safe_filename(base)}.ffpfsc"


def ensure_fakelib_files(game_folder: str, log_func, t=None, tf=None) -> bool:
    """
    Copy fakelib files from the application's external fakelib folder into game_folder/fakelib.
    If the external fakelib folder does not exist, skip silently enough and continue the conversion.
    """
    t = t or (lambda key: key)
    tf = tf or (lambda key, **kwargs: t(key).format(**kwargs))

    if not os.path.isdir(game_folder):
        log_func(t("fakelib_only_folders"), "warn")
        return True

    source_fakelib_dir = os.path.join(app_base_dir(), "fakelib")
    if not os.path.isdir(source_fakelib_dir):
        log_func(tf("fakelib_external_folder_missing", path=source_fakelib_dir), "warn")
        return True

    fake_dir = os.path.join(game_folder, "fakelib")
    os.makedirs(fake_dir, exist_ok=True)

    copied_any = False
    for filename in FAKELIB_FILES:
        src = os.path.join(source_fakelib_dir, filename)
        dest = os.path.join(fake_dir, filename)

        if not os.path.isfile(src):
            log_func(tf("fakelib_external_file_missing", filename=filename), "warn")
            continue

        log_func(tf("fakelib_updating", filename=filename), "info")
        try:
            tmp_dest = dest + ".tmp"
            shutil.copy2(src, tmp_dest)
            os.replace(tmp_dest, dest)
            copied_any = True
            log_func(tf("fakelib_ready", filename=filename), "success")
        except Exception as exc:
            try:
                tmp_dest = dest + ".tmp"
                if os.path.exists(tmp_dest):
                    os.remove(tmp_dest)
            except Exception:
                pass
            log_func(tf("fakelib_update_failed", filename=filename, error=exc), "error")
            return False

    if not copied_any:
        log_func(t("fakelib_no_files_copied"), "warn")

    return True

def fetch_latest_mkpfs_version() -> str | None:
    """Read the latest MkPFS release version from GitHub."""
    req = urllib.request.Request(
        MKPFS_LATEST_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "PS5-PFS-Packager",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))

    tag = str(data.get("tag_name") or data.get("name") or "").strip()
    if not tag:
        return None

    m = re.search(r"\d+(?:\.\d+)+", tag)
    return m.group(0) if m else tag.lstrip("vV").strip()


def detect_current_mkpfs_version(prefix: list[str] | None = None) -> str:
    """Detect current/bundled MkPFS version from -V output."""
    candidates: list[list[str]] = []

    if prefix:
        candidates.append(prefix)
    else:
        if is_frozen():
            candidates.append([compiled_executable_path(), "--internal-mkpfs"])
        else:
            detected = detect_mkpfs_prefix()
            if detected:
                candidates.append(detected)
            candidates.append([sys.executable, "-m", "mkpfs"])

    for pref in candidates:
        try:
            p = run_no_console(
                pref + ["-V"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=12,
            )
            out = (p.stdout or "").strip()
            m = re.search(r"\d+(?:\.\d+)+", out)
            if m:
                return m.group(0)
        except Exception:
            pass

    return BUNDLED_MKPFS_VERSION

def _ensure_child_standard_streams():
    """
    GUI-subsystem EXE alt işlem olarak PIPE ile başlatıldığında stdout/stderr
    nesneleri boş kalırsa Windows standart tanıtıcılarından yeniden oluştur.
    """
    if os.name != "nt":
        return

    try:
        import ctypes
        import msvcrt

        kernel32 = ctypes.windll.kernel32
        invalid_handle = ctypes.c_void_p(-1).value

        def restore_stream(stream_name: str, std_handle_id: int, fd_mode: int):
            current = getattr(sys, stream_name, None)
            if current is not None:
                return

            handle = kernel32.GetStdHandle(std_handle_id)
            if handle in (0, invalid_handle):
                return

            fd = msvcrt.open_osfhandle(handle, fd_mode)
            stream = os.fdopen(
                fd,
                "w",
                buffering=1,
                encoding="utf-8",
                errors="replace",
            )
            setattr(sys, stream_name, stream)

        restore_stream("stdout", -11, os.O_WRONLY)  # STD_OUTPUT_HANDLE
        restore_stream("stderr", -12, os.O_WRONLY)  # STD_ERROR_HANDLE
    except Exception:
        pass


def run_internal_mkpfs(args: list[str]) -> int:
    """
    Run MkPFS inside the child EXE process through its official CLI entrypoint.

    Nuitka'nın derlenmiş modül yükleyicisinde modülü betik gibi yeniden çalıştırmak
    yerine resmi mkpfs.cli giriş noktası doğrudan çağrılır.
    """
    _ensure_child_standard_streams()

    try:
        if sys.stdout is not None:
            sys.stdout.reconfigure(line_buffering=True, write_through=True)
        if sys.stderr is not None:
            sys.stderr.reconfigure(line_buffering=True, write_through=True)
    except Exception:
        pass

    try:
        from mkpfs.cli import cli_mkpfs_main

        result = cli_mkpfs_main(args)
        return int(result or 0)
    except SystemExit as exc:
        exit_code = exc.code
        if exit_code is None:
            return 0
        if isinstance(exit_code, int):
            return exit_code
        if sys.stderr is not None:
            print(exit_code, file=sys.stderr, flush=True)
        return 1
    except Exception as exc:
        if sys.stderr is not None:
            print(f"Internal MkPFS error: {exc}", file=sys.stderr, flush=True)
        return 1


from upgrade_features import inspect_game, validate_preflight, recommended_block_size

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("1250x780")
        self.minsize(1120, 720)
        self.after(50, self.center_window)

        try:
            self.iconbitmap(resource_path("appicon.ico"))
        except Exception:
            pass

        self.queue: queue.Queue = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.cancel_requested = False
        self.is_running = False
        self.current_process: subprocess.Popen | None = None
        self._mkpfs_prefix: list[str] | None = None

        # Writable U: image session.
        # EXFAT is mounted directly with the bundled ImDisk driver.
        # FFPFSC is unpacked to a temporary EXFAT and repacked after editing.
        self.mount_drive = "U:"
        self.mount_session: dict | None = None
        self.mount_busy = False
        self.mount_action = ""
        self._last_dat_progress_text = ""
        self._last_multi_preview_key = ""

        self.source_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=normalize_path(os.path.join(Path.home(), "Downloads")))
        self.file_name_var = tk.StringVar(value="PPSA00000.ffpfsc")
        self.temp_dir_var = tk.StringVar(value=normalize_path(os.path.join(Path.home(), "Downloads")))
        self.logical_cpu_count = detect_logical_cpu_count()
        default_cpu_count = min(5, self.logical_cpu_count)
        self.cpu_var = tk.StringVar(value=str(default_cpu_count))
        self.compression_level_var = tk.StringVar(value="7")
        self.block_size_var = tk.StringVar(value="auto")
        self.platform_var = tk.StringVar(value="PS5")
        self.preset_var = tk.StringVar(value="balanced")
        self.preset_display_var = tk.StringVar(value="")
        self._preset_applying = False
        self.batch_var = tk.BooleanVar(value=False)
        self.extra_verify_var = tk.BooleanVar(value=False)
        self.shutdown_var = tk.BooleanVar(value=False)
        self.fakelib_var = tk.BooleanVar(value=False)
        self.delete_source_var = tk.BooleanVar(value=False)
        self.overwrite_output_var = tk.BooleanVar(value=True)

        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="Hazır")
        self.phase_var = tk.StringVar(value="Bekliyor")
        self.time_info_var = tk.StringVar(value="")
        self._progress_value = 0.0
        self._operation_timer_generation = 0
        self._mkpfs_compression_enabled = None
        self._mkpfs_actual_gain = None
        self._mkpfs_last_output_text = ""
        self._mkpfs_failure_kind = "generic"
        self.cpu_usage_var = tk.StringVar(value="CPU: --")
        self.ram_usage_var = tk.StringVar(value="RAM: --")
        self.last_summary_var = tk.StringVar(value="Son işlem: Henüz işlem yok")
        self.game_counter_var = tk.StringVar(value="")
        self._game_counter_state = (0, 0)
        self.language_display_var = tk.StringVar(value=LANGUAGE_DISPLAY.get(detect_system_language(), "English"))
        self._config_ready = False
        self.load_config()

        self._setup_style()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)
        self.after(100, self._process_queue)
        self.after(1000, self._update_system_stats)

    def lang_code(self) -> str:
        return LANGUAGE_CODE_BY_DISPLAY.get(self.language_display_var.get(), "en")

    def tr(self, key_or_text: str) -> str:
        return translate_value(self.lang_code(), key_or_text)

    def tr_format(self, key_or_text: str, **kwargs) -> str:
        try:
            return self.tr(key_or_text).format(**kwargs)
        except Exception:
            return self.tr(key_or_text)

    def format_duration_local(self, seconds: float) -> str:
        seconds = int(round(seconds or 0))
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return self.tr_format("duration_hms", h=h, m=m, s=s)
        if m:
            return self.tr_format("duration_ms", m=m, s=s)
        return self.tr_format("duration_s", s=s)

    def summary_log_labels(self) -> dict[str, str]:
        return {
            "game_name": self.tr("summary_game_name"),
            "previous_size": self.tr("summary_previous_size"),
            "new_size": self.tr("summary_new_size"),
            "gain": self.tr("summary_gain"),
            "duration": self.tr("summary_duration"),
            "output": self.tr("summary_output"),
        }

    def load_config(self):
        """Load ps5-pfs-config.ini if it exists. Defaults remain active when the file is missing."""
        path = get_config_path()
        if not os.path.isfile(path):
            return

        parser = configparser.ConfigParser()
        try:
            parser.read(path, encoding="utf-8")
            settings = parser["settings"] if parser.has_section("settings") else {}

            def get_text(key: str, default: str) -> str:
                try:
                    return str(settings.get(key, default)).strip()
                except Exception:
                    return default

            def get_bool(key: str, default: bool) -> bool:
                value = get_text(key, "1" if default else "0").lower()
                return value in ("1", "true", "yes", "on")

            cpu = get_text("cpu", self.cpu_var.get())
            if cpu.lower() == "auto" or cpu == "0":
                self.cpu_var.set("Auto")
            elif cpu.isdigit():
                cpu_i = max(1, min(self.logical_cpu_count, int(cpu)))
                self.cpu_var.set(str(cpu_i))

            compression = get_text("compression", self.compression_level_var.get())
            if compression.isdigit():
                comp_i = max(0, min(9, int(compression)))
                self.compression_level_var.set(str(comp_i))

            platform = get_text("platform", self.platform_var.get()).upper()
            if platform in ("PS4", "PS5"):
                self.platform_var.set(platform)

            block_size = get_text("block_size", self.block_size_var.get()).lower()
            if block_size in ("auto", "auto-fit", "16384", "32768", "65536"):
                self.block_size_var.set(block_size)

            preset = get_text("preset", self.preset_var.get()).lower()
            if preset in ("custom", "fast", "balanced", "max", "low_ram"):
                self.preset_var.set(preset)

            self.batch_var.set(get_bool("batch_mode", self.batch_var.get()))
            self.extra_verify_var.set(get_bool("extra_verify", self.extra_verify_var.get()))
            self.shutdown_var.set(get_bool("shutdown_pc", self.shutdown_var.get()))
            self.fakelib_var.set(get_bool("add_fakelib", self.fakelib_var.get()))
            self.delete_source_var.set(get_bool("delete_source", self.delete_source_var.get()))

            language = get_text("language", "")
            if language in LANGUAGE_DISPLAY:
                self.language_display_var.set(LANGUAGE_DISPLAY[language])
            elif language in LANGUAGE_CODE_BY_DISPLAY:
                self.language_display_var.set(language)
        except Exception:
            pass

    def save_config(self):
        """Save current user settings to ps5-pfs-config.ini."""
        if not getattr(self, "_config_ready", False):
            return

        parser = configparser.ConfigParser()
        parser["settings"] = {
            "cpu": "auto" if str(self.cpu_var.get()).strip().lower() == "auto" else str(self.cpu_var.get()),
            "compression": str(self.compression_level_var.get()),
            "platform": str(self.platform_var.get()),
            "block_size": str(self.block_size_var.get()),
            "preset": str(self.preset_var.get()),
            "batch_mode": "1" if self.batch_var.get() else "0",
            "extra_verify": "1" if self.extra_verify_var.get() else "0",
            "add_fakelib": "1" if self.fakelib_var.get() else "0",
            "delete_source": "1" if self.delete_source_var.get() else "0",
            "shutdown_pc": "1" if self.shutdown_var.get() else "0",
            "language": self.lang_code(),
        }

        try:
            with open(get_config_path(), "w", encoding="utf-8") as f:
                parser.write(f)
        except Exception:
            pass

    def _setup_config_traces(self):
        """Save config whenever a remembered option changes."""
        watched_vars = [
            self.cpu_var,
            self.compression_level_var,
            self.platform_var,
            self.block_size_var,
            self.preset_var,
            self.batch_var,
            self.extra_verify_var,
            self.shutdown_var,
            self.fakelib_var,
            self.delete_source_var,
            self.language_display_var,
        ]
        for var in watched_vars:
            try:
                var.trace_add("write", lambda *_: self.save_config())
            except Exception:
                pass

    def apply_language(self, event=None):
        """Apply selected language to the main UI. MkPFS's own command output is not translated."""
        try:
            self.title(self.tr("app_title"))
        except Exception:
            pass

        def apply_widget(widget):
            try:
                current = widget.cget("text")
                if current:
                    new_text = self.tr(current)
                    if new_text != current:
                        widget.configure(text=new_text)
            except Exception:
                pass

            try:
                for child in widget.winfo_children():
                    apply_widget(child)
            except Exception:
                pass

        apply_widget(self)

        try:
            self.update_button.configure(
                text=self.tr(self.update_button.cget("text")),
                disabledforeground="white",
                activeforeground="white",
            )
        except Exception:
            pass

        try:
            self.language_radio_title.configure(text="Language:")
        except Exception:
            pass

        try:
            self.status_var.set(self.tr(self.status_var.get()))
            self.phase_var.set(self.tr(self.phase_var.get()))
            self.last_summary_var.set(self.tr(self.last_summary_var.get()))
            self._refresh_progress_status_label()
        except Exception:
            pass

        self._refresh_tuning_controls()
        self.on_mode_changed()
        self._refresh_mount_button()
        self.after_idle(self._align_options_row)

    def center_window(self):
        """Ana pencereyi ekranın ortasına al."""
        try:
            self.update_idletasks()
            w = self.winfo_width() or 1250
            h = self.winfo_height() or 780
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _setup_style(self):
        self.configure(bg="#151515")
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Green.Horizontal.TProgressbar",
            troughcolor="#2b2b2b",
            background="#22c55e",
            bordercolor="#2b2b2b",
            lightcolor="#22c55e",
            darkcolor="#16a34a",
        )
        style.configure(
            "Dark.TCheckbutton",
            background="#151515",
            foreground="#e8e8e8",
            focuscolor="#151515",
        )
        style.map(
            "Dark.TCheckbutton",
            background=[("active", "#151515")],
            foreground=[("active", "#ffffff")],
        )

        style.configure(
            "Dark.TNotebook",
            background="#151515",
            borderwidth=0,
        )
        style.configure(
            "Dark.TNotebook.Tab",
            background="#263244",
            foreground="#e5e7eb",
            padding=(18, 8),
            width=24,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", "#2563eb"), ("active", "#334155")],
            foreground=[("selected", "#ffffff"), ("active", "#ffffff")],
        )

    def _mk_label(self, parent, text, row):
        lbl = tk.Label(parent, text=text, bg="#202020", fg="#d7d7d7", font=("Segoe UI", 11, "bold"))
        lbl.grid(row=row, column=0, sticky="e", padx=(18, 12), pady=10)
        return lbl

    def _build_ui(self):
        header = tk.Frame(self, bg="#151515")
        header.pack(fill="x", padx=34, pady=(24, 12))

        self.title_label = tk.Label(header, text=self.tr("app_title"), bg="#151515", fg="white", font=("Segoe UI", 28, "bold"))
        self.title_label.pack(side="left")

        self.subtitle_label = tk.Label(
            header,
            text=self.tr("subtitle"),
            bg="#151515",
            fg="#b8c0cc",
            font=("Segoe UI", 11, "italic"),
        )
        self.subtitle_label.pack(side="left", padx=(32, 0), pady=(12, 0))

        self.update_button = tk.Button(
            header,
            text=self.tr("check_updates"),
            command=self.check_updates,
            bg="#334155",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=20,
        )
        self.update_button.pack(side="right", pady=(8, 0))

        tk.Button(
            header,
            text=self.tr("buy_coffee"),
            command=self.show_coffee_modal,
            bg="#92400e",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=16,
        ).pack(side="right", padx=(0, 10), pady=(8, 0))

        self.game_preview_label = tk.Label(self, text="Game preview: choose a source folder", bg="#151515", fg="#a7f3d0", anchor="w", font=("Segoe UI", 10))
        self.game_preview_label.pack(fill="x", padx=34, pady=(0, 5))
        self.game_preview_image = None

        self.mode_tab_frame = tk.Frame(self, bg="#151515")
        self.mode_tab_frame.pack(fill="x", padx=34, pady=(0, 10))

        self.single_tab_button = tk.Button(
            self.mode_tab_frame,
            text=self.tr("single_tab"),
            command=lambda: self.set_mode(False),
            bg="#2563eb",
            fg="white",
            activebackground="#2563eb",
            activeforeground="white",
            font=("Segoe UI", 10, "bold"),
            width=28,
            relief="flat",
            bd=0,
            highlightthickness=0,
            takefocus=0,
            pady=8,
        )
        self.single_tab_button.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.multi_tab_button = tk.Button(
            self.mode_tab_frame,
            text=self.tr("multi_tab"),
            command=lambda: self.set_mode(True),
            bg="#263244",
            fg="#e5e7eb",
            activebackground="#334155",
            activeforeground="white",
            font=("Segoe UI", 10, "bold"),
            width=28,
            relief="flat",
            bd=0,
            highlightthickness=0,
            takefocus=0,
            pady=8,
        )
        self.multi_tab_button.pack(side="left", fill="x", expand=True, padx=(2, 0))

        form = tk.Frame(self, bg="#202020")
        form.pack(fill="x", padx=34, pady=(0, 12))
        self.form_frame = form

        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(2, minsize=130)

        self.source_label = self._mk_label(form, self.tr("source_path"), 0)
        source_entry = tk.Entry(form, textvariable=self.source_var, font=("Segoe UI", 11))
        source_entry.grid(row=0, column=1, sticky="ew", pady=10)
        tk.Button(form, text=self.tr("select"), command=self.pick_source, width=12, bg="#2563eb", fg="white").grid(row=0, column=2, padx=14, pady=10)

        self.output_label = self._mk_label(form, self.tr("output_folder"), 1)
        output_entry = tk.Entry(form, textvariable=self.output_dir_var, font=("Segoe UI", 11))
        output_entry.grid(row=1, column=1, sticky="ew", pady=10)
        tk.Button(form, text=self.tr("select"), command=self.pick_output_dir, width=12, bg="#2563eb", fg="white").grid(row=1, column=2, padx=14, pady=10)

        self.file_name_label = self._mk_label(form, self.tr("file_name"), 2)
        self.filename_entry = tk.Entry(form, textvariable=self.file_name_var, font=("Segoe UI", 11))
        self.filename_entry.grid(row=2, column=1, sticky="ew", pady=10)
        self.titleid_button = tk.Button(form, text=self.tr("get_titleid"), command=self.auto_file_name, width=12, bg="#3b82f6", fg="white")
        self.titleid_button.grid(row=2, column=2, padx=14, pady=10)

        self.temp_label = self._mk_label(form, self.tr("temp_folder"), 3)
        temp_entry = tk.Entry(form, textvariable=self.temp_dir_var, font=("Segoe UI", 11))
        temp_entry.grid(row=3, column=1, sticky="ew", pady=10)
        tk.Button(form, text=self.tr("select"), command=self.pick_temp_dir, width=12, bg="#2563eb", fg="white").grid(row=3, column=2, padx=14, pady=10)

        tk.Button(form, text=self.tr("test_sound"), command=self.play_completion_sound, width=12, bg="#475569", fg="white").grid(row=4, column=2, padx=14, pady=(0, 12))

        self.options_wrap = tk.Frame(form, bg="#202020")
        self.options_wrap.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 8),
        )

        platform_group = tk.Frame(self.options_wrap, bg="#202020")
        platform_group.pack(side="left", padx=(0, 28), anchor="w")

        self.platform_label = tk.Label(
            platform_group,
            text=self.tr("platform"),
            bg="#202020",
            fg="#d7d7d7",
            font=("Segoe UI", 10, "bold"),
        )
        self.platform_label.pack(side="left", padx=(0, 8))

        self.platform_combo = ttk.Combobox(
            platform_group,
            values=["PS5", "PS4"],
            textvariable=self.platform_var,
            width=5,
            state="readonly",
            font=("Segoe UI", 10),
        )
        self.platform_combo.pack(side="left")

        preset_group = tk.Frame(self.options_wrap, bg="#202020")
        preset_group.pack(side="left", padx=(0, 28), anchor="w")

        self.preset_label = tk.Label(
            preset_group,
            text=self.tr("preset"),
            bg="#202020",
            fg="#d7d7d7",
            font=("Segoe UI", 10, "bold"),
        )
        self.preset_label.pack(side="left", padx=(0, 8))

        self.preset_combo = ttk.Combobox(
            preset_group,
            textvariable=self.preset_display_var,
            width=17,
            state="readonly",
            font=("Segoe UI", 10),
        )
        self.preset_combo.pack(side="left")
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)

        block_group = tk.Frame(self.options_wrap, bg="#202020")
        block_group.pack(side="left", padx=(0, 28), anchor="w")

        self.block_size_label = tk.Label(
            block_group,
            text=self.tr("block_size"),
            bg="#202020",
            fg="#d7d7d7",
            font=("Segoe UI", 10, "bold"),
        )
        self.block_size_label.pack(side="left", padx=(0, 8))

        self.block_size_combo = ttk.Combobox(
            block_group,
            values=["auto", "auto-fit", "16384", "32768", "65536"],
            textvariable=self.block_size_var,
            width=10,
            state="readonly",
            font=("Segoe UI", 10),
        )
        self.block_size_combo.pack(side="left")
        self.block_size_combo.bind("<<ComboboxSelected>>", self._on_manual_tuning_change)

        cpu_group = tk.Frame(self.options_wrap, bg="#202020")
        cpu_group.pack(side="left", padx=(0, 28), anchor="w")

        tk.Label(
            cpu_group,
            text=self.tr("cpu"),
            bg="#202020",
            fg="#d7d7d7",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=(0, 8))

        self.cpu_combo = ttk.Combobox(
            cpu_group,
            values=["Auto"] + [str(i) for i in range(1, self.logical_cpu_count + 1)],
            textvariable=self.cpu_var,
            width=6,
            state="readonly",
            font=("Segoe UI", 10),
        )
        self.cpu_combo.pack(side="left")

        compression_group = tk.Frame(self.options_wrap, bg="#202020")
        compression_group.pack(side="left", anchor="w")

        tk.Label(
            compression_group,
            text=self.tr("compression"),
            bg="#202020",
            fg="#d7d7d7",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=(0, 8))

        self.compression_combo = ttk.Combobox(
            compression_group,
            values=[str(i) for i in range(0, 10)],
            textvariable=self.compression_level_var,
            width=4,
            state="readonly",
            font=("Segoe UI", 10),
        )
        self.compression_combo.pack(side="left")

        self.options_separator = tk.Frame(
            form,
            bg="#4b5563",
            height=1,
            bd=0,
            highlightthickness=0,
        )
        self.options_separator.grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(2, 10),
        )
        self.options_separator.grid_propagate(False)

        self.tuning_wrap = tk.Frame(form, bg="#202020")
        self.tuning_wrap.grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(0, 12),
        )

        self.extra_verify_check = ttk.Checkbutton(
            self.tuning_wrap,
            text=self.tr("extra_verify"),
            variable=self.extra_verify_var,
            style="Dark.TCheckbutton",
        )
        self.extra_verify_check.pack(side="left", padx=(0, 26), anchor="w")

        self.add_fakelib_check = ttk.Checkbutton(
            self.tuning_wrap,
            text=self.tr("add_fakelib"),
            variable=self.fakelib_var,
            style="Dark.TCheckbutton",
        )
        self.add_fakelib_check.pack(side="left", padx=(0, 26), anchor="w")

        self.delete_source_check = ttk.Checkbutton(
            self.tuning_wrap,
            text=self.tr("delete_game_folder"),
            variable=self.delete_source_var,
            style="Dark.TCheckbutton",
        )
        self.delete_source_check.pack(side="left", padx=(0, 26), anchor="w")

        self.shutdown_check = ttk.Checkbutton(
            self.tuning_wrap,
            text=self.tr("shutdown_pc"),
            variable=self.shutdown_var,
            style="Dark.TCheckbutton",
        )
        self.shutdown_check.pack(side="left", anchor="w")

        self.platform_combo.bind("<<ComboboxSelected>>", lambda event=None: self.save_config())
        self.cpu_combo.bind("<<ComboboxSelected>>", self._on_manual_tuning_change)
        self.compression_combo.bind("<<ComboboxSelected>>", self._on_manual_tuning_change)
        self._refresh_tuning_controls()

        controls = tk.Frame(self, bg="#151515")
        controls.pack(fill="x", padx=34, pady=(2, 10))

        self.mount_button = tk.Button(
            controls,
            text=self.tr("mount_image_button"),
            command=self.show_mount_choice_or_session,
            bg="#0f766e",
            fg="white",
            activebackground="#115e59",
            activeforeground="white",
            disabledforeground="white",
            font=("Segoe UI", 11, "bold"),
            width=20,
        )
        self.mount_button.pack(side="left")

        self.start_button = tk.Button(
            controls,
            text=self.tr("single_start"),
            command=self.start,
            bg="#16a34a",
            fg="white",
            activeforeground="white",
            disabledforeground="white",
            font=("Segoe UI", 12, "bold"),
            width=20,
            state="disabled",
        )
        self.start_button.pack(side="right", padx=(8, 0))

        self.cancel_button = tk.Button(controls, text=self.tr("cancel"), command=self.cancel, bg="#7f1d1d", fg="white", font=("Segoe UI", 12, "bold"), width=12, state="disabled")
        self.cancel_button.pack(side="right")

        progress_frame = tk.Frame(self, bg="#151515")
        progress_frame.pack(fill="x", padx=34, pady=(0, 10))
        self.progress_bar = ttk.Progressbar(progress_frame, style="Green.Horizontal.TProgressbar", variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True)

        self.game_counter_label = tk.Label(
            progress_frame,
            textvariable=self.game_counter_var,
            bg="#0f172a",
            fg="#fde68a",
            font=("Segoe UI", 11, "bold"),
            width=14,
            anchor="center",
            padx=8,
        )
        self.game_counter_label.pack(side="left", padx=(14, 0))

        self.status_label = tk.Label(progress_frame, textvariable=self.status_var, bg="#151515", fg="#d7d7d7", font=("Segoe UI", 11, "bold"), width=20, anchor="e")
        self.status_label.pack(side="left", padx=(10, 0))

        self.time_info_label = tk.Label(
            progress_frame,
            textvariable=self.time_info_var,
            bg="#0f172a",
            fg="#fde68a",
            font=("Segoe UI", 9, "bold"),
            width=42,
            anchor="center",
            padx=8,
        )
        self.time_info_label.pack(side="left", padx=(10, 0))

        self.phase_label = tk.Label(self, textvariable=self.phase_var, bg="#151515", fg="#9ca3af", font=("Segoe UI", 10), anchor="w")
        self.phase_label.pack(fill="x", padx=36, pady=(0, 6))

        stats_frame = tk.Frame(self, bg="#151515")
        stats_frame.pack(fill="x", padx=34, pady=(0, 8))

        tk.Label(stats_frame, textvariable=self.cpu_usage_var, bg="#0f172a", fg="#a7f3d0", font=("Segoe UI", 10, "bold"), padx=12, pady=5).pack(side="left", padx=(0, 8))
        tk.Label(stats_frame, textvariable=self.ram_usage_var, bg="#0f172a", fg="#bfdbfe", font=("Segoe UI", 10, "bold"), padx=12, pady=5).pack(side="left", padx=(0, 8))
        tk.Label(stats_frame, textvariable=self.last_summary_var, bg="#202020", fg="#e5e7eb", font=("Segoe UI", 10, "bold"), padx=12, pady=5, anchor="w").pack(side="left", fill="x", expand=True)

        self.language_radio_frame = tk.Frame(self, bg="#151515")
        self.language_radio_frame.pack(side="bottom", fill="x", padx=34, pady=(4, 10))

        self.language_radio_title = tk.Label(
            self.language_radio_frame,
            text="Language:",
            bg="#151515",
            fg="#d7d7d7",
            font=("Segoe UI", 9, "bold"),
        )
        self.language_radio_title.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 3))

        self.language_radio_buttons = []
        for i, display_name in enumerate(LANGUAGE_DISPLAY.values()):
            rb = tk.Radiobutton(
                self.language_radio_frame,
                text=display_name,
                value=display_name,
                variable=self.language_display_var,
                command=self.apply_language,
                bg="#151515",
                fg="#e5e7eb",
                activebackground="#151515",
                activeforeground="white",
                selectcolor="#2563eb",
                font=("Segoe UI", 8, "bold"),
                indicatoron=True,
                takefocus=0,
                highlightthickness=0,
                bd=0,
                padx=3,
                pady=1,
            )
            row = 0
            col = i + 1
            rb.grid(row=row, column=col, sticky="w", padx=(0, 7), pady=(0, 3))
            self.language_radio_buttons.append(rb)

        log_frame = tk.Frame(self, bg="#202020")
        log_frame.pack(fill="both", expand=True, padx=34, pady=(0, 6))

        self.log_text = tk.Text(
            log_frame,
            bg="#101010",
            fg="#d8d8d8",
            insertbackground="white",
            font=("Consolas", 10),
            wrap="word",
            height=20,
            relief="flat",
            padx=10,
            pady=10,
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scroll.set)

        self.log_text.tag_configure("title", foreground="#ffffff", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("cmd", foreground="#93c5fd")
        self.log_text.tag_configure("success", foreground="#22c55e", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("error", foreground="#ef4444", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("warn", foreground="#f59e0b")
        self.log_text.tag_configure("progress", foreground="#a7f3d0")
        self.log_text.tag_configure("muted", foreground="#9ca3af")
        self.log_text.tag_configure("info", foreground="#e5e7eb")

        self.source_var.trace_add("write", lambda *_: self._on_source_changed())
        self.output_dir_var.trace_add("write", lambda *_: self._update_start_button_state())
        self.temp_dir_var.trace_add("write", lambda *_: self._update_start_button_state())
        self.file_name_var.trace_add("write", lambda *_: self._update_start_button_state())
        self._setup_config_traces()
        self._config_ready = True
        self.after(200, self._update_start_button_state)
        self.after(250, self.on_mode_changed)
        self.after(300, self.apply_language)
        self.after(360, self._align_options_row)



    def _preset_display_map(self) -> dict[str, str]:
        return {
            "custom": self.tr("preset_custom"),
            "fast": self.tr("preset_fast"),
            "balanced": self.tr("preset_balanced"),
            "max": self.tr("preset_max"),
            "low_ram": self.tr("preset_low_ram"),
        }

    def _refresh_tuning_controls(self):
        try:
            display_map = self._preset_display_map()
            self.platform_label.configure(text=self.tr("platform"))
            self.preset_combo.configure(values=list(display_map.values()))
            self.preset_display_var.set(
                display_map.get(self.preset_var.get(), display_map["custom"])
            )
            self.preset_label.configure(text=self.tr("preset"))
            self.block_size_label.configure(text=self.tr("block_size"))
        except Exception:
            pass

    def _on_preset_selected(self, event=None):
        display = self.preset_display_var.get()
        reverse = {value: key for key, value in self._preset_display_map().items()}
        preset = reverse.get(display, "custom")
        self.preset_var.set(preset)
        if preset == "custom":
            return

        profiles = {
            "fast": {
                "cpu": str(max(1, min(8, self.logical_cpu_count))),
                "compression": "3",
                "block": "65536",
            },
            "balanced": {
                "cpu": str(max(1, min(5, self.logical_cpu_count))),
                "compression": "7",
                "block": "auto",
            },
            "max": {
                "cpu": str(max(1, min(8, self.logical_cpu_count))),
                "compression": "9",
                "block": "auto-fit",
            },
            "low_ram": {
                "cpu": str(max(1, min(2, self.logical_cpu_count))),
                "compression": "5",
                "block": "65536",
            },
        }
        values = profiles.get(preset)
        if not values:
            return

        self._preset_applying = True
        try:
            self.cpu_var.set(values["cpu"])
            self.compression_level_var.set(values["compression"])
            self.block_size_var.set(values["block"])
        finally:
            self._preset_applying = False
        self.save_config()

    def _on_manual_tuning_change(self, event=None):
        if self._preset_applying:
            return
        self.preset_var.set("custom")
        try:
            self.preset_display_var.set(self.tr("preset_custom"))
        except Exception:
            pass

    def _preflight_check(
        self,
        source: str,
        output_path: str,
        temp_dir: str,
        source_size: int,
        block_size: str,
    ) -> bool:
        self._qlog(self.tr("preflight_title"), "title")

        output_free = get_free_space_bytes(output_path)
        temp_free = get_free_space_bytes(temp_dir)
        output_fs = get_filesystem_type(output_path)
        temp_fs = get_filesystem_type(temp_dir)
        output_type = get_drive_media_type(output_path)
        temp_type = get_drive_media_type(temp_dir)

        output_required = max(512 * 1024 * 1024, int(source_size * 1.03))
        if str(block_size).lower() == "auto-fit":
            temp_required = max(2 * 1024**3, int(source_size * 1.05))
        elif os.path.isdir(source):
            temp_required = max(1 * 1024**3, int(source_size * 0.12))
        else:
            temp_required = max(512 * 1024**2, int(source_size * 0.05))

        same_drive = same_storage_volume(output_path, temp_dir)

        self._qlog(
            self.tr_format("preflight_source", size=format_bytes(source_size)),
            "info",
        )
        self._qlog(
            self.tr_format(
                "preflight_output",
                free=format_bytes(output_free),
                fs=output_fs,
                drive_type=output_type,
            ),
            "info",
        )
        self._qlog(
            self.tr_format(
                "preflight_temp",
                free=format_bytes(temp_free),
                fs=temp_fs,
                drive_type=temp_type,
            ),
            "info",
        )
        self._qlog(
            self.tr_format(
                "preflight_required",
                output=format_bytes(output_required),
                temp=format_bytes(temp_required),
            ),
            "muted",
        )

        if output_fs.upper() == "FAT32" and output_required > (4 * 1024**3 - 1):
            self._qlog(self.tr("preflight_fat32"), "error")
            return False

        if same_drive:
            combined = output_required + temp_required
            self._qlog(
                self.tr_format(
                    "preflight_same_drive",
                    required=format_bytes(combined),
                ),
                "muted",
            )
            if output_free and output_free < combined:
                self._qlog(
                    self.tr_format(
                        "preflight_output_low",
                        required=format_bytes(combined),
                        free=format_bytes(output_free),
                    ),
                    "error",
                )
                return False
        else:
            if output_free and output_free < output_required:
                self._qlog(
                    self.tr_format(
                        "preflight_output_low",
                        required=format_bytes(output_required),
                        free=format_bytes(output_free),
                    ),
                    "error",
                )
                return False
            if temp_free and temp_free < temp_required:
                self._qlog(
                    self.tr_format(
                        "preflight_temp_low",
                        required=format_bytes(temp_required),
                        free=format_bytes(temp_free),
                    ),
                    "error",
                )
                return False

        if temp_fs.upper() in {"EXFAT", "FAT32", "FAT"}:
            self._qlog(
                self.tr_format("preflight_temp_fs_warning", fs=temp_fs),
                "warn",
            )
        if temp_type == "HDD":
            self._qlog(self.tr("preflight_hdd_warning"), "warn")

        self._qlog(self.tr("preflight_ok"), "success")
        return True

    def _friendly_failure_message(self) -> str:
        key_map = {
            "memory": "friendly_error_memory",
            "space": "friendly_error_space",
            "permission": "friendly_error_permission",
            "link": "friendly_error_link",
            "fat32": "friendly_error_fat32",
            "missing": "friendly_error_missing",
            "generic": "friendly_error_generic",
        }
        return self.tr(key_map.get(self._mkpfs_failure_kind, "friendly_error_generic"))

    def set_mode(self, is_multi: bool):
        self.batch_var.set(bool(is_multi))
        self.on_mode_changed()

    def _paint_mode_tabs(self):
        try:
            if self.batch_var.get():
                self.single_tab_button.configure(text=self.tr("single_tab"), bg="#263244", fg="#e5e7eb", activebackground="#334155")
                self.multi_tab_button.configure(text=self.tr("multi_tab"), bg="#2563eb", fg="white", activebackground="#2563eb")
            else:
                self.single_tab_button.configure(text=self.tr("single_tab"), bg="#2563eb", fg="white", activebackground="#2563eb")
                self.multi_tab_button.configure(text=self.tr("multi_tab"), bg="#263244", fg="#e5e7eb", activebackground="#334155")
        except Exception:
            pass

    def _refresh_game_preview(self):
        """Display source title, title ID and available PNG icon; no network fetch."""
        try:
            info = inspect_game(self.source_var.get().strip())
            details = " | ".join(x for x in (info["title"], info["title_id"]) if x)
            try:
                ram_gib = (psutil.virtual_memory().total / 1024**3) if psutil else 8
                size_gib = os.path.getsize(self.source_var.get().strip()) / 1024**3 if os.path.isfile(self.source_var.get().strip()) else 0
                if os.path.isdir(self.source_var.get().strip()):
                    details += " | Suggested block: " + recommended_block_size(ram_gib, size_gib) + " (auto remains default)"
            except (OSError, AttributeError):
                pass
            self.game_preview_label.configure(text="Game: " + details, image="", compound="left")
            self.game_preview_image = None
            if info["icon"]:
                try:
                    pic = tk.PhotoImage(file=info["icon"])
                    factor = max(1, (max(pic.width(), pic.height()) + 47) // 48)
                    self.game_preview_image = pic.subsample(factor, factor)
                    self.game_preview_label.configure(image=self.game_preview_image, compound="left")
                except tk.TclError:
                    pass
        except Exception:
            pass

    def _on_source_changed(self):
        self._refresh_game_preview()
        if self.batch_var.get():
            self.update_batch_preview()
        else:
            self.auto_file_name(silent=True)
        self._update_start_button_state()

    def _align_options_row(self):
        """Ayar satırını, ayırıcı çizgiyi ve checkbox satırını sola hizala."""
        try:
            self.update_idletasks()
            left_padding = max(
                0,
                self.source_label.winfo_rootx() - self.form_frame.winfo_rootx(),
            )
            self.options_wrap.grid_configure(padx=(left_padding, 0))
            self.options_separator.grid_configure(padx=(left_padding, 0))
            self.tuning_wrap.grid_configure(padx=(left_padding, 0))
        except Exception:
            pass

    def _refresh_progress_status_label(self):
        """
        Tekli mod:
          Hazır / Compress %10 / Read %20

        Çoklu mod:
          Hazır
          veya Oyun 5/6 • Compress %10
        """
        try:
            status_text = str(self.status_var.get()).strip()
            current, total = self._game_counter_state

            if self.batch_var.get() and current and total:
                counter_text = self.tr_format(
                    "game_counter",
                    current=current,
                    total=total,
                )
                if status_text:
                    display_text = f"{counter_text} • {status_text}"
                else:
                    display_text = counter_text
            else:
                display_text = status_text

            self.game_counter_var.set(display_text)
        except Exception:
            pass

    def _update_progress_row_layout(self):
        """Tekli ve çoklu modda aynı progress/status/süre düzenini kullan."""
        try:
            if self.status_label.winfo_manager():
                self.status_label.pack_forget()

            self.game_counter_label.configure(width=26)
            self.time_info_label.configure(width=58)
            self._refresh_progress_status_label()
        except Exception:
            pass

    def on_mode_changed(self, event=None):
        is_multi = bool(self.batch_var.get())
        self._paint_mode_tabs()

        if is_multi:
            if not self.is_running:
                self._game_counter_state = (0, 0)
                self.game_counter_var.set(self.status_var.get())
            self.source_label.configure(text=self.tr("main_folder"))
            self.file_name_label.configure(text=self.tr("file_name"))
            try:
                self.filename_entry.configure(state="readonly")
                self.titleid_button.configure(state="disabled")
            except Exception:
                pass
            self.update_batch_preview()
            self.phase_var.set(self.tr("multi_phase"))
            try:
                if not self.is_running:
                    self.start_button.configure(text=self.tr("multi_start"))
            except Exception:
                pass
        else:
            if not self.is_running:
                self._game_counter_state = (0, 0)
                self.game_counter_var.set(self.status_var.get())
            self.source_label.configure(text=self.tr("source_path"))
            try:
                self.filename_entry.configure(state="normal")
                self.titleid_button.configure(state="normal")
            except Exception:
                pass
            self.auto_file_name(silent=True)
            self.phase_var.set(self.tr("single_phase"))
            try:
                if not self.is_running:
                    self.start_button.configure(text=self.tr("single_start"))
            except Exception:
                pass

        self._update_progress_row_layout()
        self.after_idle(self._align_options_row)
        self._update_start_button_state()

    def _has_multi_targets(self, src: str) -> bool:
        return bool(discover_conversion_targets(src, max_depth=3))

    def _is_ready_to_start(self) -> bool:
        if self.mount_busy or self.mount_session is not None:
            return False

        src = normalize_path(self.source_var.get().strip())
        out_dir = normalize_path(self.output_dir_var.get().strip())
        temp_dir = normalize_path(self.temp_dir_var.get().strip())

        if not out_dir or not temp_dir:
            return False

        if self.batch_var.get():
            return bool(src and os.path.isdir(src) and self._has_multi_targets(src))

        file_name = self.file_name_var.get().strip()
        return bool(src and os.path.exists(src) and file_name)

    def _update_start_button_state(self):
        try:
            if self.is_running or self.mount_busy:
                running_text = self.tr("multi_running") if self.batch_var.get() else self.tr("single_running")
                self.start_button.configure(
                    text=running_text,
                    state="disabled",
                    fg="white",
                    disabledforeground="white",
                    activeforeground="white",
                )
                return
            if self._is_ready_to_start():
                self.start_button.configure(state="normal")
            else:
                self.start_button.configure(state="disabled")
        except Exception:
            pass

    def update_batch_preview(self):
        src = normalize_path(self.source_var.get().strip())

        if not src:
            self.file_name_var.set("")
            self._last_multi_preview_key = ""
            self._update_start_button_state()
            return

        if not os.path.isdir(src):
            self.file_name_var.set("")
            self._qsummary(self.tr("multi_list_no_main"))
            self._last_multi_preview_key = ""
            self._update_start_button_state()
            return

        targets = []
        try:
            targets = discover_conversion_targets(src, max_depth=3)
        except Exception as exc:
            self.file_name_var.set("")
            self._qlog(self.tr_format("multi_folder_read_failed", error=exc), "error")
            self._last_multi_preview_key = ""
            self._update_start_button_state()
            return

        if not targets:
            self.file_name_var.set("")
            self._qsummary(self.tr("multi_list_no_games"))
            self._last_multi_preview_key = ""
            self._update_start_button_state()
            return

        lines = []
        out_names = []

        for i, target in enumerate(targets, start=1):
            try:
                out_name = derive_output_name(target)
                game_name = derive_game_display_name(target, out_name)
                out_names.append(out_name)
                lines.append(f"{i:02d}) {game_name} -> {out_name}")
            except Exception:
                base = os.path.basename(target.rstrip("\\/"))
                out_names.append(derive_output_name(target))
                lines.append(f"{i:02d}) {base} -> {derive_output_name(target)}")

        self.file_name_var.set(", ".join(out_names))

        preview_key = src + "|" + "|".join(out_names)
        if preview_key != self._last_multi_preview_key:
            self._last_multi_preview_key = preview_key
            self._qlog(self.tr("multi_game_list_title"), "title")
            for line in lines:
                self._qlog(line, "info")

        self._qsummary(self.tr_format("multi_list_found", count=len(targets)))
        self._update_start_button_state()


    # ------------------------------------------------------------------
    # Writable EXFAT / FFPFSC image mount using Windows native VHD:
    # ------------------------------------------------------------------
    def _drive_letter_in_use(self, drive: str = "U:") -> bool:
        drive = str(drive or "U:").upper().rstrip("\\")
        if os.name != "nt":
            return False
        try:
            import ctypes

            letter = drive[0]
            mask = int(ctypes.windll.kernel32.GetLogicalDrives())
            return bool(mask & (1 << (ord(letter) - ord("A"))))
        except Exception:
            return os.path.exists(drive + "\\")

    def _is_admin(self) -> bool:
        if os.name != "nt":
            return False
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _restart_as_admin_for_mount(self, kind: str, image_path: str) -> bool:
        if os.name != "nt":
            return False
        try:
            import ctypes

            if is_frozen():
                executable = compiled_executable_path()
                args = ["--open-image", kind, image_path]
            else:
                executable = sys.executable
                args = [
                    os.path.abspath(__file__),
                    "--open-image",
                    kind,
                    image_path,
                ]

            params = subprocess.list2cmdline(args)
            shell_execute = ctypes.windll.shell32.ShellExecuteW
            shell_execute.restype = ctypes.c_void_p
            result = shell_execute(
                None,
                "runas",
                executable,
                params,
                app_base_dir(),
                1,
            )
            return bool(result and int(result) > 32)
        except Exception:
            return False

    def _mount_native_image(self, image_path: str) -> tuple[bool, str]:
        image_path = normalize_path(image_path)
        try:
            if native_exfat.has_recovery_sidecar(image_path):
                self._qlog(self.tr("mount_native_recovery"), "warn")
                native_exfat.recover_image(image_path, "U")

            self._qlog(self.tr("mount_native_prepare"), "info")
            native_exfat.mount_image(image_path, "U")

            deadline = time.time() + 25
            while time.time() < deadline:
                try:
                    if (
                        self._drive_letter_in_use(self.mount_drive)
                        and os.path.isdir(self.mount_drive + "\\")
                    ):
                        os.listdir(self.mount_drive + "\\")
                        return True, ""
                except OSError:
                    pass
                time.sleep(0.25)

            raise RuntimeError(
                "Windows created the virtual disk but U: did not become accessible."
            )
        except Exception as exc:
            return False, str(exc)

    def _unmount_native_image(self, image_path: str) -> tuple[bool, str]:
        image_path = normalize_path(image_path)
        if not image_path:
            return True, ""

        try:
            if (
                native_exfat.has_recovery_sidecar(image_path)
                or native_exfat.is_attached(image_path)
            ):
                self._qlog(self.tr("mount_native_restore"), "info")
                native_exfat.unmount_image(image_path, "U")
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def _open_u_drive_in_explorer(self):
        if os.name != "nt":
            return
        try:
            if not self._drive_letter_in_use(self.mount_drive):
                raise RuntimeError("U: is not mounted.")
            os.startfile(self.mount_drive + "\\")
        except Exception as exc:
            self._log(str(exc), "warn")

    def _looks_like_exfat(self, path: str) -> bool:
        try:
            if not os.path.isfile(path):
                return False
            with open(path, "rb") as f:
                header = f.read(16)
            return len(header) >= 11 and header[3:11] == b"EXFAT   "
        except Exception:
            return False

    def _find_exfat_payload(self, root: str) -> str:
        matches: list[str] = []
        for current_root, _, files in os.walk(root):
            for name in files:
                path = os.path.join(current_root, name)
                if name.lower().endswith(".exfat") or self._looks_like_exfat(path):
                    matches.append(path)

        if not matches:
            return ""

        matches.sort(
            key=lambda p: os.path.getsize(p) if os.path.isfile(p) else 0,
            reverse=True,
        )
        return normalize_path(matches[0])

    def _cleanup_mount_session_paths(self, session: dict | None) -> None:
        """Delete the current FFPFSC working folder and its empty parent."""
        if not session:
            return

        session_root = normalize_path(str(session.get("session_root", "") or ""))
        sessions_root = normalize_path(str(session.get("sessions_root", "") or ""))

        if session_root:
            try:
                shutil.rmtree(session_root, ignore_errors=False)
            except FileNotFoundError:
                pass
            except Exception as exc:
                self._qlog(
                    self.tr_format("mount_cleanup_failed", error=exc),
                    "warn",
                )

        # Delete PS5PFS-MountSessions itself when our session was the last one.
        if sessions_root:
            try:
                if (
                    os.path.isdir(sessions_root)
                    and not os.listdir(sessions_root)
                ):
                    os.rmdir(sessions_root)
                    self._qlog(
                        self.tr("mount_sessions_cleaned"),
                        "muted",
                    )
            except FileNotFoundError:
                pass
            except Exception as exc:
                self._qlog(
                    self.tr_format("mount_cleanup_failed", error=exc),
                    "warn",
                )

    def _refresh_mount_button(self):
        try:
            if self.mount_busy:
                key = (
                    "mount_save_busy"
                    if self.mount_action in {"save", "close"}
                    else "mount_image_busy"
                )
                self.mount_button.configure(
                    text=self.tr(key),
                    state="disabled",
                    bg="#475569",
                )
            elif self.mount_session is not None:
                self.mount_button.configure(
                    text=self.tr("mount_session_button"),
                    state="normal",
                    bg="#b45309",
                    activebackground="#92400e",
                )
            elif self.is_running:
                self.mount_button.configure(
                    text=self.tr("mount_image_button"),
                    state="disabled",
                    bg="#475569",
                )
            else:
                self.mount_button.configure(
                    text=self.tr("mount_image_button"),
                    state="normal",
                    bg="#0f766e",
                    activebackground="#115e59",
                )
        except Exception:
            pass

    def _set_mount_busy(self, busy: bool, action: str = ""):
        self.mount_busy = bool(busy)
        self.mount_action = action if busy else ""
        self.is_running = bool(busy)

        if busy:
            self.cancel_requested = False
            self.start_button.configure(state="disabled")
            self.cancel_button.configure(state="normal")
        else:
            self.cancel_button.configure(state="disabled")
            self.current_process = None
            self.cancel_requested = False

            # U: açma/kaydetme işlemi sırasında ana düğme
            # "Oyun Dönüştürülüyor..." metnine geçiyor. İşlem bittiğinde
            # yalnızca state değil, normal metin de mutlaka geri yüklenmeli.
            try:
                normal_text = (
                    self.tr("multi_start")
                    if self.batch_var.get()
                    else self.tr("single_start")
                )
                self.start_button.configure(
                    text=normal_text,
                    fg="white",
                    disabledforeground="white",
                    activeforeground="white",
                )
            except Exception:
                pass

        self._update_start_button_state()
        self._refresh_mount_button()

    def _center_modal(self, modal: tk.Toplevel, width: int, height: int):
        self.update_idletasks()
        modal.update_idletasks()
        try:
            x = self.winfo_rootx() + max(
                0,
                (self.winfo_width() - width) // 2,
            )
            y = self.winfo_rooty() + max(
                0,
                (self.winfo_height() - height) // 2,
            )
        except Exception:
            x = max(0, (modal.winfo_screenwidth() - width) // 2)
            y = max(0, (modal.winfo_screenheight() - height) // 2)
        modal.geometry(f"{width}x{height}+{x}+{y}")

    def show_mount_choice_or_session(self):
        if self.mount_busy or (
            self.is_running and self.mount_session is None
        ):
            messagebox.showwarning(
                self.tr("mount_operation_running_title"),
                self.tr("mount_operation_running"),
                parent=self,
            )
            return

        if self.mount_session is not None:
            self.show_mount_session_modal()
        else:
            self.show_mount_choice_modal()

    def show_mount_choice_modal(self):
        if os.name != "nt":
            messagebox.showwarning(
                self.tr("mount_choice_title"),
                self.tr("mount_windows_only"),
                parent=self,
            )
            return

        if self._drive_letter_in_use(self.mount_drive):
            messagebox.showwarning(
                self.tr("mount_u_in_use_title"),
                self.tr("mount_u_in_use"),
                parent=self,
            )
            return

        modal = tk.Toplevel(self)
        modal.withdraw()
        modal.title(self.tr("mount_choice_title"))
        modal.configure(bg="#151515")
        modal.resizable(False, False)
        modal.transient(self)

        try:
            modal.iconbitmap(resource_path("appicon.ico"))
        except Exception:
            pass

        self._center_modal(modal, 610, 365)

        tk.Label(
            modal,
            text=self.tr("mount_choice_title"),
            bg="#151515",
            fg="white",
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(26, 8))

        tk.Label(
            modal,
            text=self.tr("mount_choice_message"),
            bg="#151515",
            fg="#cbd5e1",
            font=("Segoe UI", 10),
            justify="center",
            wraplength=550,
        ).pack(padx=24, pady=(0, 20))

        button_frame = tk.Frame(modal, bg="#151515")
        button_frame.pack(fill="x", padx=42)

        def close_and_select(kind: str):
            try:
                modal.grab_release()
            except Exception:
                pass
            modal.destroy()
            self.after(80, lambda: self._select_image_for_mount(kind))

        tk.Button(
            button_frame,
            text="💿  " + self.tr("mount_open_exfat"),
            command=lambda: close_and_select("exfat"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            cursor="hand2",
            height=3,
        ).pack(fill="x", pady=(0, 10))

        tk.Button(
            button_frame,
            text="📦  " + self.tr("mount_open_ffpfsc"),
            command=lambda: close_and_select("ffpfsc"),
            bg="#7c3aed",
            fg="white",
            activebackground="#6d28d9",
            activeforeground="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            cursor="hand2",
            height=3,
        ).pack(fill="x")

        tk.Button(
            modal,
            text=self.tr("cancel"),
            command=modal.destroy,
            bg="#334155",
            fg="white",
            activebackground="#475569",
            activeforeground="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            width=13,
        ).pack(pady=(16, 0))

        modal.protocol("WM_DELETE_WINDOW", modal.destroy)
        modal.deiconify()
        modal.lift()
        modal.focus_force()
        modal.grab_set()

    def _select_image_for_mount(self, kind: str):
        if kind == "exfat":
            title = self.tr("mount_dialog_exfat")
            filetypes = [
                ("exFAT image", "*.exfat"),
                (self.tr("dialog_all_files"), "*.*"),
            ]
        else:
            title = self.tr("mount_dialog_ffpfsc")
            filetypes = [
                ("FFPFSC image", "*.ffpfsc"),
                ("PFS images", "*.ffpfs;*.ffpfsc"),
                (self.tr("dialog_all_files"), "*.*"),
            ]

        path = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            parent=self,
        )
        if path:
            self._start_mount_for_path(kind, path)

    def _start_mount_for_path(self, kind: str, path: str):
        path = normalize_path(path)
        expected_ext = (
            ".exfat"
            if kind == "exfat"
            else (".ffpfsc", ".ffpfs")
        )
        if (
            not os.path.isfile(path)
            or not path.lower().endswith(expected_ext)
        ):
            messagebox.showwarning(
                self.tr("missing_info_title"),
                self.tr_format("mount_invalid_file", kind=kind),
                parent=self,
            )
            return

        if not self._is_admin():
            messagebox.showerror(
                self.tr("mount_choice_title"),
                self.tr("mount_admin_required"),
                parent=self,
            )
            return

        recovery_allowed = (
            kind == "exfat"
            and native_exfat.has_recovery_sidecar(path)
        )
        if self._drive_letter_in_use(self.mount_drive) and not recovery_allowed:
            messagebox.showwarning(
                self.tr("mount_u_in_use_title"),
                self.tr("mount_u_in_use"),
                parent=self,
            )
            return

        if kind == "exfat":
            if not os.access(path, os.W_OK):
                messagebox.showerror(
                    self.tr("mount_choice_title"),
                    self.tr_format(
                        "mount_imdisk_not_writable",
                        path=path,
                    ),
                    parent=self,
                )
                return

            # EXFAT doğrudan yazılabilir olarak açılır.
            # Kullanıcı isteği doğrultusunda ek onay penceresi gösterilmez.
            session_root = ""
            mounted_image = path
        else:
            temp_dir = normalize_path(self.temp_dir_var.get().strip())
            if not temp_dir:
                messagebox.showwarning(
                    self.tr("missing_info_title"),
                    self.tr("mount_temp_missing"),
                    parent=self,
                )
                return
            try:
                os.makedirs(temp_dir, exist_ok=True)
            except Exception:
                messagebox.showwarning(
                    self.tr("missing_info_title"),
                    self.tr("temp_create_failed"),
                    parent=self,
                )
                return

            safe_stem = re.sub(
                r"[^A-Za-z0-9._-]+",
                "_",
                Path(path).stem,
            ).strip("._") or "image"
            sessions_root = normalize_path(
                os.path.join(temp_dir, "PS5PFS-MountSessions")
            )
            session_root = normalize_path(
                os.path.join(
                    sessions_root,
                    f"{safe_stem}_{int(time.time())}",
                )
            )
            mounted_image = ""
            os.makedirs(session_root, exist_ok=True)

        if kind == "exfat":
            sessions_root = ""

        session = {
            "source": path,
            "kind": kind,
            "sessions_root": sessions_root,
            "session_root": session_root,
            "mounted_image": mounted_image,
            "drive": self.mount_drive,
            "created_at": time.time(),
        }

        self.log_text.delete("1.0", "end")
        self._qlog(self.tr("app_title"), "title")
        self._qlog(self.tr("mount_direct_note"), "warn")
        self._qlog(self.tr("mount_open_started"), "title")
        self._qlog(
            self.tr_format("mount_source_log", path=path),
            "info",
        )
        if kind == "exfat":
            self._qlog(self.tr("mount_direct_exfat_log"), "success")

        self._qprogress(0)
        self._qstatus(self.tr("status_running"))
        self._qphase(
            self.tr("mount_waiting_drive")
            if kind == "exfat"
            else self.tr("mount_extracting_ffpfsc")
        )

        self._set_mount_busy(True, "open")
        started_at = time.perf_counter()
        self._start_operation_timer(started_at)

        threading.Thread(
            target=self._mount_open_worker,
            args=(session, started_at),
            daemon=True,
        ).start()

    def _mount_open_worker(self, session: dict, started_at: float):
        kind = session["kind"]
        source = session["source"]
        preserved_path = ""

        try:
            if kind == "exfat":
                mounted_image = source
            else:
                session_root = session["session_root"]
                outer_dir = normalize_path(
                    os.path.join(session_root, "outer")
                )
                os.makedirs(outer_dir, exist_ok=True)

                self._qphase(self.tr("mount_extracting_ffpfsc"))
                rc = self._run_mkpfs(
                    [
                        "unpack",
                        "--overwrite",
                        source,
                        outer_dir,
                    ],
                    progress_offset=0,
                    progress_scale=90,
                )

                if self.cancel_requested:
                    self._cleanup_mount_session_paths(session)
                    self._stop_operation_timer(
                        time.perf_counter() - started_at
                    )
                    self.queue.put(
                        (
                            "mount_open_failure",
                            self.tr("mount_cancelled"),
                            "",
                        )
                    )
                    return

                if rc != 0:
                    self._cleanup_mount_session_paths(session)
                    self._stop_operation_timer(
                        time.perf_counter() - started_at
                    )
                    self.queue.put(
                        (
                            "mount_open_failure",
                            self.tr_format(
                                "mount_extract_failed",
                                code=rc,
                            ),
                            "",
                        )
                    )
                    return

                mounted_image = self._find_exfat_payload(outer_dir)

                # Fallback for raw/legacy PFS outputs that do not contain
                # a wrapped EXFAT payload.
                if not mounted_image:
                    self._qlog(
                        self.tr("mount_legacy_rebuild"),
                        "warn",
                    )
                    fallback_exfat = normalize_path(
                        os.path.join(
                            session_root,
                            Path(source).stem + "_work.exfat",
                        )
                    )
                    rc = self._run_mkpfs(
                        [
                            "pack",
                            "exfat",
                            "--overwrite",
                            outer_dir,
                            fallback_exfat,
                        ],
                        progress_offset=90,
                        progress_scale=10,
                    )
                    if rc == 0 and self._looks_like_exfat(
                        fallback_exfat
                    ):
                        mounted_image = fallback_exfat

                if not mounted_image:
                    self._cleanup_mount_session_paths(session)
                    preserved_path = ""
                    self._stop_operation_timer(
                        time.perf_counter() - started_at
                    )
                    self.queue.put(
                        (
                            "mount_open_failure",
                            self.tr("mount_inner_exfat_missing"),
                            "",
                        )
                    )
                    return

                session["mounted_image"] = mounted_image
                preserved_path = mounted_image
                self._qlog(
                    self.tr_format(
                        "mount_ffpfsc_temp_log",
                        path=mounted_image,
                    ),
                    "info",
                )

            ok, error = self._mount_native_image(mounted_image)
            elapsed = time.perf_counter() - started_at
            self._stop_operation_timer(elapsed)

            if not ok:
                if kind == "ffpfsc":
                    self._cleanup_mount_session_paths(session)
                    preserved_path = ""
                self.queue.put(
                    (
                        "mount_open_failure",
                        self.tr_format(
                            "mount_mapping_failed",
                            error=error,
                        ),
                        preserved_path,
                    )
                )
                return

            session["mounted_image"] = mounted_image
            self.queue.put(("mount_open_success", session))
        except Exception as exc:
            if kind == "ffpfsc":
                self._cleanup_mount_session_paths(session)
                preserved_path = ""
            self._stop_operation_timer(
                time.perf_counter() - started_at
            )
            self.queue.put(
                (
                    "mount_open_failure",
                    str(exc),
                    preserved_path,
                )
            )

    def _handle_mount_open_success(self, session: dict):
        self.mount_session = session
        self._set_mount_busy(False)
        self._qprogress(100)
        self.status_var.set(self.tr("status_ready"))
        self.phase_var.set(self.tr("mount_opened_phase"))
        self._refresh_progress_status_label()
        self._log(self.tr("mount_opened"), "success")
        if session["kind"] == "ffpfsc":
            self._log(
                self.tr_format(
                    "mount_ffpfsc_temp_log",
                    path=session["mounted_image"],
                ),
                "muted",
            )
        self._open_u_drive_in_explorer()
        self._refresh_mount_button()

    def _handle_mount_open_failure(
        self,
        message: str,
        preserved_workspace: str = "",
    ):
        self._set_mount_busy(False)
        self.status_var.set(self.tr("status_ready"))
        self.phase_var.set(self.tr("phase_waiting"))
        self._refresh_progress_status_label()
        self._log(message, "error")
        if preserved_workspace:
            self._log(
                self.tr_format(
                    "mount_workspace_preserved",
                    path=preserved_workspace,
                ),
                "warn",
            )
        self.play_error_sound()

    def show_mount_session_modal(self):
        session = self.mount_session
        if not session:
            messagebox.showinfo(
                self.tr("mount_session_title"),
                self.tr("mount_no_session"),
                parent=self,
            )
            return

        kind = session["kind"]
        modal = tk.Toplevel(self)
        modal.withdraw()
        modal.title(self.tr("mount_session_title"))
        modal.configure(bg="#151515")
        modal.resizable(False, False)
        modal.transient(self)

        try:
            modal.iconbitmap(resource_path("appicon.ico"))
        except Exception:
            pass

        height = 390 if kind == "exfat" else 465
        self._center_modal(modal, 650, height)

        tk.Label(
            modal,
            text=self.tr("mount_session_title"),
            bg="#151515",
            fg="white",
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(24, 8))

        message_key = (
            "mount_session_exfat_message"
            if kind == "exfat"
            else "mount_session_ffpfsc_message"
        )
        tk.Label(
            modal,
            text=self.tr(message_key),
            bg="#151515",
            fg="#cbd5e1",
            font=("Segoe UI", 10),
            justify="center",
            wraplength=585,
        ).pack(padx=24, pady=(0, 12))

        tk.Label(
            modal,
            text=(
                f"{self.mount_drive}\\  →  "
                f"{session['mounted_image']}"
            ),
            bg="#0f172a",
            fg="#fde68a",
            font=("Consolas", 9, "bold"),
            padx=12,
            pady=9,
            wraplength=575,
        ).pack(fill="x", padx=30, pady=(0, 16))

        buttons = tk.Frame(modal, bg="#151515")
        buttons.pack(fill="x", padx=42)

        def close_then(callback):
            try:
                modal.grab_release()
            except Exception:
                pass
            modal.destroy()
            self.after(80, callback)

        tk.Button(
            buttons,
            text="📂  " + self.tr("mount_open_drive"),
            command=lambda: close_then(
                self._open_u_drive_in_explorer
            ),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            height=2,
        ).pack(fill="x", pady=(0, 9))

        if kind == "exfat":
            tk.Button(
                buttons,
                text="💾  " + self.tr("mount_close_exfat"),
                command=lambda: close_then(
                    self._start_direct_exfat_close
                ),
                bg="#16a34a",
                fg="white",
                activebackground="#15803d",
                activeforeground="white",
                font=("Segoe UI", 11, "bold"),
                relief="flat",
                height=2,
            ).pack(fill="x")
        else:
            tk.Button(
                buttons,
                text="💾  " + self.tr("mount_save_ffpfsc"),
                command=lambda: close_then(
                    self._choose_ffpfsc_save_output
                ),
                bg="#16a34a",
                fg="white",
                activebackground="#15803d",
                activeforeground="white",
                font=("Segoe UI", 11, "bold"),
                relief="flat",
                height=2,
            ).pack(fill="x", pady=(0, 9))

            tk.Button(
                buttons,
                text="🗑  " + self.tr("mount_discard_ffpfsc"),
                command=lambda: close_then(
                    self._confirm_discard_mount
                ),
                bg="#991b1b",
                fg="white",
                activebackground="#7f1d1d",
                activeforeground="white",
                font=("Segoe UI", 10, "bold"),
                relief="flat",
                height=2,
            ).pack(fill="x")

        tk.Button(
            modal,
            text=self.tr("close"),
            command=modal.destroy,
            bg="#334155",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=12,
        ).pack(pady=(12, 8))

        modal.protocol("WM_DELETE_WINDOW", modal.destroy)
        modal.deiconify()
        modal.lift()
        modal.focus_force()
        modal.grab_set()

    def _start_direct_exfat_close(self):
        if not self.mount_session:
            return
        self._qstatus(self.tr("status_running"))
        self._qphase(self.tr("mount_close_exfat"))
        self._set_mount_busy(True, "close")
        threading.Thread(
            target=self._direct_exfat_close_worker,
            daemon=True,
        ).start()

    def _direct_exfat_close_worker(self):
        session = self.mount_session or {}
        image_path = session.get("mounted_image", "")
        ok, error = self._unmount_native_image(image_path)
        if not ok:
            self.queue.put(("mount_close_failure", error))
            return
        self.queue.put(("mount_close_success",))

    def _choose_ffpfsc_save_output(self):
        session = self.mount_session
        if not session or session["kind"] != "ffpfsc":
            return

        output = normalize_path(session["source"])
        self._log(
            self.tr_format(
                "mount_ffpfsc_overwrite_log",
                path=output,
            ),
            "warn",
        )
        self._start_ffpfsc_save(output)

    def _start_ffpfsc_save(self, output: str):
        session = self.mount_session
        if not session or session["kind"] != "ffpfsc":
            return

        self._qlog("-" * 78, "muted")
        self._qlog(self.tr("mount_saving_ffpfsc"), "title")
        self._qlog(
            self.tr_format("output_log", path=output),
            "info",
        )
        self._qprogress(0)
        self._qstatus(self.tr("status_running"))
        self._qphase(self.tr("mount_saving_ffpfsc"))

        self._set_mount_busy(True, "save")
        started_at = time.perf_counter()
        self._start_operation_timer(started_at)

        threading.Thread(
            target=self._ffpfsc_save_worker,
            args=(dict(session), output, started_at),
            daemon=True,
        ).start()

    def _ffpfsc_save_worker(
        self,
        session: dict,
        output: str,
        started_at: float,
    ):
        mounted_image = session["mounted_image"]
        rebuild_output = ""

        unmounted, error = self._unmount_native_image(mounted_image)
        if not unmounted:
            self._stop_operation_timer(
                time.perf_counter() - started_at
            )
            self.queue.put(
                ("mount_save_failure", error, True)
            )
            return

        cpu_text = str(self.cpu_var.get()).strip()
        cpu = (
            0
            if cpu_text.lower() == "auto"
            else max(
                1,
                min(self.logical_cpu_count, int(cpu_text)),
            )
        )
        compression_level = max(
            0,
            min(9, int(self.compression_level_var.get())),
        )
        platform = str(self.platform_var.get()).strip().upper()
        if platform not in ("PS4", "PS5"):
            platform = "PS5"
        block_size = str(self.block_size_var.get()).strip().lower()
        if block_size not in ("auto", "auto-fit", "16384", "32768", "65536"):
            block_size = "auto"
        temp_dir = normalize_path(self.temp_dir_var.get().strip())

        try:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Build on the same volume as the original so os.replace() can
            # atomically swap the completed file into place. The original
            # remains untouched if compression, verification or cancellation fails.
            fd, rebuild_output = tempfile.mkstemp(
                prefix=f".{output_path.stem}_rebuild_",
                suffix=".ffpfsc",
                dir=str(output_path.parent),
            )
            os.close(fd)
            os.remove(rebuild_output)
            rebuild_output = normalize_path(rebuild_output)

            args = [
                "pack",
                "file",
                "--compress",
                "--threshold-gain",
                "0",
                "--max-compressed-ratio",
                "100",
                "--version",
                platform,
                "--inode-bits",
                "32",
                "--temp-folder",
                temp_dir,
                "--cpu-count",
                str(cpu),
                "--compression-level",
                str(compression_level),
                "--block-size",
                block_size,
                "--no-verify-structure",
                mounted_image,
                rebuild_output,
            ]

            rc = self._run_mkpfs(
                args,
                progress_offset=0,
                progress_scale=95
                if self.extra_verify_var.get()
                else 100,
            )

            if rc == 0 and self.extra_verify_var.get():
                rc = self._run_mkpfs(
                    [
                        "verify",
                        rebuild_output,
                        "--source-file",
                        mounted_image,
                    ],
                    progress_offset=95,
                    progress_scale=5,
                )

            if self.cancel_requested or rc != 0:
                try:
                    if rebuild_output and os.path.exists(rebuild_output):
                        os.remove(rebuild_output)
                except Exception:
                    pass

                elapsed = time.perf_counter() - started_at
                self._stop_operation_timer(elapsed)

                remounted, _ = self._mount_native_image(
                    mounted_image
                )
                message = (
                    self.tr("mount_cancelled")
                    if self.cancel_requested
                    else self.tr_format(
                        "mount_save_failed",
                        code=rc,
                    )
                )
                self.queue.put(
                    (
                        "mount_save_failure",
                        message,
                        remounted,
                    )
                )
                return

            try:
                os.replace(rebuild_output, output)
                rebuild_output = ""
            except Exception as exc:
                elapsed = time.perf_counter() - started_at
                self._stop_operation_timer(elapsed)

                remounted, _ = self._mount_native_image(
                    mounted_image
                )
                self.queue.put(
                    (
                        "mount_save_failure",
                        self.tr_format(
                            "mount_replace_failed",
                            error=exc,
                        ),
                        remounted,
                    )
                )
                return

            elapsed = time.perf_counter() - started_at
            self._stop_operation_timer(elapsed)

            self._cleanup_mount_session_paths(session)
            self.queue.put(("mount_save_success", output))
        except Exception as exc:
            try:
                if rebuild_output and os.path.exists(rebuild_output):
                    os.remove(rebuild_output)
            except Exception:
                pass

            remounted, _ = self._mount_native_image(
                mounted_image
            )
            self._stop_operation_timer(
                time.perf_counter() - started_at
            )
            self.queue.put(
                (
                    "mount_save_failure",
                    str(exc),
                    remounted,
                )
            )

    def _handle_mount_save_success(self, output: str):
        self.mount_session = None
        self._set_mount_busy(False)
        self._qprogress(100)
        self.status_var.set(self.tr("status_done"))
        self.phase_var.set(self.tr("phase_done"))
        self._refresh_progress_status_label()
        self._log(
            self.tr_format("mount_saved", path=output),
            "success",
        )
        self.play_completion_sound()
        self._refresh_mount_button()

    def _handle_mount_save_failure(
        self,
        message: str,
        remounted: bool,
    ):
        self._set_mount_busy(False)
        self.status_var.set(self.tr("status_ready"))
        self.phase_var.set(
            self.tr("mount_opened_phase")
            if remounted
            else self.tr("phase_waiting")
        )
        self._refresh_progress_status_label()
        self._log(message, "error")
        if remounted:
            self._log(
                self.tr("mount_remounted_after_error"),
                "warn",
            )
            self._open_u_drive_in_explorer()
        elif self.mount_session:
            self._log(
                self.tr_format(
                    "mount_workspace_preserved",
                    path=self.mount_session["mounted_image"],
                ),
                "warn",
            )
        self.play_error_sound()
        self._refresh_mount_button()

    def _confirm_discard_mount(self):
        session = self.mount_session
        if not session or session["kind"] != "ffpfsc":
            return

        self._set_mount_busy(True, "close")
        threading.Thread(
            target=self._discard_ffpfsc_worker,
            args=(dict(session),),
            daemon=True,
        ).start()

    def _discard_ffpfsc_worker(self, session: dict):
        image_path = session.get("mounted_image", "")
        ok, error = self._unmount_native_image(image_path)
        if not ok:
            self.queue.put(("mount_close_failure", error))
            return

        self._cleanup_mount_session_paths(session)
        self.queue.put(("mount_close_success",))

    def _handle_mount_close_success(self):
        was_exfat = bool(
            self.mount_session
            and self.mount_session.get("kind") == "exfat"
        )
        self.mount_session = None
        self._set_mount_busy(False)
        self.status_var.set(self.tr("status_ready"))
        self.phase_var.set(self.tr("phase_waiting"))
        self._refresh_progress_status_label()
        self._log(
            self.tr(
                "mount_exfat_closed"
                if was_exfat
                else "mount_closed"
            ),
            "success",
        )
        self._refresh_mount_button()

    def _handle_mount_close_failure(self, message: str):
        self._set_mount_busy(False)
        self.status_var.set(self.tr("status_ready"))
        self.phase_var.set(self.tr("mount_opened_phase"))
        self._refresh_progress_status_label()
        self._log(message, "error")
        self.play_error_sound()
        self._refresh_mount_button()

    def _on_app_close(self):
        if self.mount_busy:
            messagebox.showwarning(
                self.tr("mount_operation_running_title"),
                self.tr("mount_operation_running"),
                parent=self,
            )
            return

        if self.is_running and self.mount_session is None:
            if not messagebox.askyesno(
                self.tr("mount_operation_running_title"),
                self.tr("mount_operation_running"),
                parent=self,
            ):
                return
            self.cancel_requested = True
            try:
                if (
                    self.current_process
                    and self.current_process.poll() is None
                ):
                    self.current_process.terminate()
            except Exception:
                pass
            return

        if self.mount_session is not None:
            session = self.mount_session
            if session["kind"] == "exfat":
                message = self.tr("mount_close_app_exfat")
            else:
                message = self.tr_format(
                    "mount_close_app_ffpfsc",
                    path=session["mounted_image"],
                )

            if not messagebox.askyesno(
                self.tr("mount_close_app_title"),
                message,
                parent=self,
            ):
                return

            ok, error = self._unmount_native_image(
                session.get("mounted_image", "")
            )
            if not ok:
                messagebox.showerror(
                    self.tr("mount_close_app_title"),
                    error,
                    parent=self,
                )
                return

            if session.get("kind") == "ffpfsc":
                self._cleanup_mount_session_paths(session)

        try:
            self.save_config()
        except Exception:
            pass
        self.destroy()

    def show_coffee_modal(self):
        addresses = {
            f"{self.tr('usdt')} (TRC20)": "TNYdNNEHWw4kyftkAZViG3fzpHB7hYRC71",
            f"{self.tr('btc')} (Bitcoin)": "37iQfhCWPt6FWWcoSarbrB9k4QVSyDPi2x",
            f"{self.tr('eth')} (ERC20)": "0x4d202af852112f87ac736e13d81a828706d25688",
        }

        modal = tk.Toplevel(self)
        modal.withdraw()
        modal.title("Kahve Ismarla :)")
        modal.configure(bg="#151515")
        modal.resizable(False, False)
        modal.transient(self)

        try:
            modal.iconbitmap(resource_path("appicon.ico"))
        except Exception:
            pass

        w, h = 640, 340
        self.update_idletasks()
        modal.update_idletasks()

        # İlk açılışta sol üstte görünmesin; önce konumu hesapla, sonra göster.
        try:
            x = self.winfo_rootx() + max(0, (self.winfo_width() - w) // 2)
            y = self.winfo_rooty() + max(0, (self.winfo_height() - h) // 2)
        except Exception:
            x = (modal.winfo_screenwidth() - w) // 2
            y = (modal.winfo_screenheight() - h) // 2
        modal.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(
            modal,
            text=self.tr("coffee_title"),
            bg="#151515",
            fg="white",
            font=("Segoe UI", 21, "bold"),
        ).pack(pady=(24, 8))

        msg = self.tr("coffee_msg")
        tk.Label(
            modal,
            text=msg,
            bg="#151515",
            fg="#d1d5db",
            font=("Segoe UI", 10),
            justify="center",
            wraplength=570,
        ).pack(padx=24, pady=(0, 16))

        rows = tk.Frame(modal, bg="#151515")
        rows.pack(fill="x", padx=26, pady=(0, 10))
        rows.grid_columnconfigure(1, weight=1)

        def copy_address(value: str, btn: tk.Button):
            self.clipboard_clear()
            self.clipboard_append(value)
            btn.configure(text=self.tr("copied"))
            modal.after(1400, lambda: btn.configure(text=self.tr("copy")))

        for row_index, (label, value) in enumerate(addresses.items()):
            tk.Label(
                rows,
                text=label + ":",
                bg="#151515",
                fg="#e5e7eb",
                font=("Segoe UI", 10, "bold"),
                width=12,
                anchor="w",
            ).grid(row=row_index, column=0, sticky="w", pady=7)

            entry = tk.Entry(
                rows,
                font=("Consolas", 10, "bold"),
                bg="#0f172a",
                fg="#a7f3d0",
                readonlybackground="#0f172a",
                insertbackground="white",
                relief="flat",
            )
            entry.grid(row=row_index, column=1, sticky="ew", padx=(0, 10), ipady=7, pady=7)
            entry.insert(0, value)
            entry.configure(state="readonly")

            btn = tk.Button(
                rows,
                text=self.tr("copy"),
                bg="#16a34a",
                fg="white",
                font=("Segoe UI", 9, "bold"),
                width=10,
            )
            btn.configure(command=lambda v=value, b=btn: copy_address(v, b))
            btn.grid(row=row_index, column=2, sticky="e", pady=7)

        tk.Button(
            modal,
            text=self.tr("close"),
            command=modal.destroy,
            bg="#334155",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=12,
        ).pack(pady=(4, 4))

        modal.deiconify()
        modal.lift()
        modal.focus_force()
        modal.grab_set()

    def _pick_single_game_folder(self):
        path = filedialog.askdirectory(title=self.tr("dialog_select_game_folder"), parent=self)
        if path:
            self.source_var.set(normalize_path(path))
            self.auto_file_name(silent=True)

    def _pick_single_exfat_file(self):
        path = filedialog.askopenfilename(
            title=self.tr("dialog_select_exfat"),
            filetypes=[("exFAT image", "*.exfat"), (self.tr("dialog_all_files"), "*.*")],
            parent=self,
        )
        if path:
            self.source_var.set(normalize_path(path))
            self.auto_file_name(silent=True)

    def show_source_choice_modal(self):
        modal = tk.Toplevel(self)
        modal.withdraw()
        modal.title(self.tr("source_choice_title"))
        modal.configure(bg="#151515")
        modal.resizable(False, False)
        modal.transient(self)

        try:
            modal.iconbitmap(resource_path("appicon.ico"))
        except Exception:
            pass

        width, height = 520, 300
        self.update_idletasks()
        modal.update_idletasks()

        try:
            x = self.winfo_rootx() + max(0, (self.winfo_width() - width) // 2)
            y = self.winfo_rooty() + max(0, (self.winfo_height() - height) // 2)
        except Exception:
            x = max(0, (modal.winfo_screenwidth() - width) // 2)
            y = max(0, (modal.winfo_screenheight() - height) // 2)

        modal.geometry(f"{width}x{height}+{x}+{y}")

        tk.Label(
            modal,
            text=self.tr("source_choice_title"),
            bg="#151515",
            fg="white",
            font=("Segoe UI", 21, "bold"),
        ).pack(pady=(28, 8))

        tk.Label(
            modal,
            text=self.tr("source_choice_message"),
            bg="#151515",
            fg="#cbd5e1",
            font=("Segoe UI", 10),
        ).pack(pady=(0, 24))

        button_frame = tk.Frame(modal, bg="#151515")
        button_frame.pack(fill="x", padx=38)

        def close_and_open(callback):
            try:
                modal.grab_release()
            except Exception:
                pass
            modal.destroy()
            self.after(80, callback)

        folder_button = tk.Button(
            button_frame,
            text="📁  " + self.tr("choose_game_folder"),
            command=lambda: close_and_open(self._pick_single_game_folder),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            cursor="hand2",
            height=3,
        )
        folder_button.pack(fill="x", pady=(0, 10))

        exfat_button = tk.Button(
            button_frame,
            text="💿  " + self.tr("choose_exfat_file"),
            command=lambda: close_and_open(self._pick_single_exfat_file),
            bg="#7c3aed",
            fg="white",
            activebackground="#6d28d9",
            activeforeground="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            cursor="hand2",
            height=3,
        )
        exfat_button.pack(fill="x")

        tk.Button(
            modal,
            text=self.tr("cancel"),
            command=modal.destroy,
            bg="#334155",
            fg="white",
            activebackground="#475569",
            activeforeground="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            width=13,
        ).pack(pady=(16, 0))

        modal.protocol("WM_DELETE_WINDOW", modal.destroy)
        modal.deiconify()
        modal.lift()
        modal.focus_force()
        modal.grab_set()

    def pick_source(self):
        if self.batch_var.get():
            path = filedialog.askdirectory(title=self.tr("dialog_select_multi_folder"), parent=self)
            if path:
                self.source_var.set(normalize_path(path))
                self.update_batch_preview()
            return

        self.show_source_choice_modal()

    def pick_output_dir(self):
        path = filedialog.askdirectory(title=self.tr("dialog_select_output"))
        if path:
            self.output_dir_var.set(normalize_path(path))

    def pick_temp_dir(self):
        path = filedialog.askdirectory(title=self.tr("dialog_select_temp"))
        if path:
            self.temp_dir_var.set(normalize_path(path))

    def auto_file_name(self, silent=False):
        src = self.source_var.get().strip()
        if not src or self.batch_var.get():
            return
        try:
            name = derive_output_name(src)
            self.file_name_var.set(name)
            if not silent:
                self._log(self.tr_format("file_name_detected", name=name), "success")
        except Exception as exc:
            if not silent:
                self._log(self.tr_format("file_name_not_detected", error=exc), "warn")

    def _log(self, msg: str, tag: str = "info"):
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")
        self.update_idletasks()

    def _qlog(self, msg: str, tag: str = "info"):
        self.queue.put(("log", msg, tag))

    def _qstatus(self, text: str):
        self.queue.put(("status", text))

    def _qphase(self, text: str):
        self.queue.put(("phase", text))

    def _qprogress(self, value: float):
        try:
            self._progress_value = max(0.0, min(100.0, float(value)))
        except Exception:
            self._progress_value = 0.0
        self.queue.put(("progress", self._progress_value))

    def _qtime_info(self, text: str):
        self.queue.put(("time_info", text))

    def _process_queue(self):
        while True:
            try:
                item = self.queue.get_nowait()
            except queue.Empty:
                break

            kind = item[0]
            if kind == "log":
                _, msg, tag = item
                self._log(msg, tag)
            elif kind == "status":
                status_text = item[1]
                self.status_var.set(status_text)
                self._refresh_progress_status_label()
            elif kind == "phase":
                self.phase_var.set(item[1])
            elif kind == "progress":
                self.progress_var.set(item[1])
            elif kind == "time_info":
                self.time_info_var.set(item[1])
            elif kind == "summary":
                self.last_summary_var.set(item[1])
            elif kind == "game_counter":
                try:
                    current, total = item[1], item[2]
                    self._game_counter_state = (current, total)
                    self._refresh_progress_status_label()
                except Exception:
                    pass
            elif kind == "update_button":
                try:
                    state = item[3] if len(item) > 3 else "normal"
                    fg = item[4] if len(item) > 4 else "white"
                    self.update_button.configure(
                        text=item[1],
                        bg=item[2],
                        fg=fg,
                        activeforeground=fg,
                        disabledforeground=fg,
                        state=state,
                    )
                except Exception:
                    pass
            elif kind == "mount_open_success":
                self._handle_mount_open_success(item[1])
            elif kind == "mount_open_failure":
                self._handle_mount_open_failure(item[1], item[2] if len(item) > 2 else "")
            elif kind == "mount_save_success":
                self._handle_mount_save_success(item[1])
            elif kind == "mount_save_failure":
                self._handle_mount_save_failure(
                    item[1],
                    bool(item[2]) if len(item) > 2 else False,
                )
            elif kind == "mount_close_success":
                self._handle_mount_close_success()
            elif kind == "mount_close_failure":
                self._handle_mount_close_failure(item[1])
            elif kind == "done":
                self._set_running(False)
        self.after(100, self._process_queue)

    def _qsummary(self, text: str):
        self.queue.put(("summary", text))

    def _start_operation_timer(self, started_at: float):
        """
        Show elapsed time for every source type.
        When progress is available, calculate an approximate remaining time.
        This also covers .exfat -> .ffpfsc conversions.
        """
        self._operation_timer_generation += 1
        generation = self._operation_timer_generation

        def worker():
            while generation == self._operation_timer_generation and self.is_running:
                try:
                    elapsed = max(0.0, time.perf_counter() - started_at)
                    progress = max(0.0, min(100.0, float(self._progress_value)))

                    if 1.0 <= progress < 99.5:
                        remaining = elapsed * ((100.0 - progress) / progress)
                        # Çok erken ölçümlerde oluşabilecek aşırı tahminleri sınırlamadan
                        # göstermek yerine, yeterli veri gelene kadar yalnızca geçen süreyi yaz.
                        if elapsed >= 5.0 and remaining >= 0:
                            text = self.tr_format(
                                "elapsed_remaining",
                                elapsed=self.format_duration_local(elapsed),
                                remaining=self.format_duration_local(remaining),
                            )
                        else:
                            text = self.tr_format(
                                "elapsed_only",
                                elapsed=self.format_duration_local(elapsed),
                            )
                    else:
                        text = self.tr_format(
                            "elapsed_only",
                            elapsed=self.format_duration_local(elapsed),
                        )

                    self._qtime_info(text)
                except Exception:
                    pass

                time.sleep(1.0)

        threading.Thread(target=worker, daemon=True).start()

    def _stop_operation_timer(self, final_elapsed: float | None = None, clear: bool = False):
        self._operation_timer_generation += 1
        if clear:
            self._qtime_info("")
        elif final_elapsed is not None:
            self._qtime_info(
                self.tr_format(
                    "elapsed_only",
                    elapsed=self.format_duration_local(final_elapsed),
                )
            )

    def _qgame_counter(self, current: int, total: int):
        self.queue.put(("game_counter", current, total))

    def _update_system_stats(self):
        try:
            if psutil is None:
                self.cpu_usage_var.set("CPU: psutil yok")
                self.ram_usage_var.set("RAM: psutil yok")
            else:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory()
                self.cpu_usage_var.set(f"CPU: %{cpu:.0f}")
                self.ram_usage_var.set(f"RAM: %{ram.percent:.0f} ({format_bytes(ram.used)} / {format_bytes(ram.total)})")

        except Exception:
            self.cpu_usage_var.set("CPU: --")
            self.ram_usage_var.set("RAM: --")

        self.after(1000, self._update_system_stats)

    def _set_running(self, running: bool):
        self.is_running = running
        if running:
            running_text = self.tr("multi_running") if self.batch_var.get() else self.tr("single_running")
            self.start_button.configure(
                text=running_text,
                state="disabled",
                fg="white",
                disabledforeground="white",
                activeforeground="white",
            )
            self.cancel_button.configure(state="normal")
            try:
                self.mount_button.configure(state="disabled")
            except Exception:
                pass
        else:
            self.cancel_button.configure(state="disabled")
            self.current_process = None
            try:
                if self.batch_var.get():
                    self.start_button.configure(text=self.tr("multi_start"), fg="white", disabledforeground="white")
                else:
                    self.start_button.configure(text=self.tr("single_start"), fg="white", disabledforeground="white")
            except Exception:
                pass
            self._update_start_button_state()
            self._refresh_mount_button()

    def cancel(self):
        self.cancel_requested = True
        try:
            if self.current_process and self.current_process.poll() is None:
                self.current_process.terminate()
        except Exception:
            pass
        self._qlog(self.tr("cancel_requested"), "warn")

    def build_targets(self):
        src = normalize_path(self.source_var.get().strip())
        if not self.batch_var.get():
            return [src]
        return discover_conversion_targets(src, max_depth=3)

    def validate(self) -> bool:
        src = normalize_path(self.source_var.get().strip())
        out_dir = normalize_path(self.output_dir_var.get().strip())
        temp_dir = normalize_path(self.temp_dir_var.get().strip())

        if not src or not os.path.exists(src):
            messagebox.showwarning(self.tr("missing_info_title"), self.tr("invalid_source"))
            return False
        if not out_dir:
            messagebox.showwarning(self.tr("missing_info_title"), self.tr("select_output_warning"))
            return False
        if not os.path.isdir(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception:
                messagebox.showwarning(self.tr("missing_info_title"), self.tr("output_create_failed"))
                return False
        if not temp_dir:
            messagebox.showwarning(self.tr("missing_info_title"), self.tr("select_temp_warning"))
            return False
        if not os.path.isdir(temp_dir):
            try:
                os.makedirs(temp_dir, exist_ok=True)
            except Exception:
                messagebox.showwarning(self.tr("missing_info_title"), self.tr("temp_create_failed"))
                return False
        if self.batch_var.get():
            if not os.path.isdir(src) or not self._has_multi_targets(src):
                messagebox.showwarning(self.tr("missing_info_title"), self.tr("multi_select_valid"))
                return False
        elif not self.file_name_var.get().strip():
            messagebox.showwarning(self.tr("missing_info_title"), self.tr("file_name_empty"))
            return False
        return True

    def start(self):
        self.on_mode_changed()
        if not self._is_ready_to_start():
            return
        if not self.validate():
            return

        self.cancel_requested = False
        self._progress_value = 0.0
        self.progress_var.set(0)
        self.time_info_var.set("")
        self.status_var.set(self.tr("status_running"))
        self._refresh_progress_status_label()
        self.phase_var.set(self.tr("phase_preparing"))
        self.log_text.delete("1.0", "end")

        self._set_running(True)
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def _worker(self):
        try:
            targets = self.build_targets()
            out_dir = normalize_path(self.output_dir_var.get().strip())
            temp_dir = normalize_path(self.temp_dir_var.get().strip())
            cpu_text = str(self.cpu_var.get()).strip()
            cpu = (
                0
                if cpu_text.lower() == "auto"
                else max(1, min(self.logical_cpu_count, int(cpu_text)))
            )
            cpu_display = "Auto" if cpu == 0 else str(cpu)
            compression_level = max(0, min(9, int(self.compression_level_var.get())))
            platform = str(self.platform_var.get()).strip().upper()
            if platform not in ("PS4", "PS5"):
                platform = "PS5"
            block_size = str(self.block_size_var.get()).strip().lower()
            if block_size not in ("auto", "auto-fit", "16384", "32768", "65536"):
                block_size = "auto"
            preset_key = str(self.preset_var.get()).strip().lower()
            preset_name = self._preset_display_map().get(
                preset_key,
                self.tr("preset_custom"),
            )
            auto_memory_retry = True
            add_fakelib = self.fakelib_var.get()
            extra_verify = self.extra_verify_var.get()
            delete_source = self.delete_source_var.get()
            overwrite_output = True
            batch = self.batch_var.get()

            error_sound_played = False
            completed_count = 0

            def play_error_once():
                nonlocal error_sound_played
                if not error_sound_played:
                    error_sound_played = True
                    try:
                        self.play_error_sound()
                    except Exception:
                        pass

            self._qgame_counter(0, 0)

            if batch:
                self.update_batch_preview()

            self._qlog(self.tr("app_title"), "title")
            if batch:
                self._qlog(self.tr("recursive_scan_log"), "muted")
            self._qlog(self.tr("method_log"), "muted")
            self._qlog(self.tr_format("version_log", version=APP_VERSION), "muted")
            self._qlog(self.tr_format("cpu_limit_log", cpu=cpu_display), "muted")
            self._qlog(self.tr_format("compression_level_log", level=compression_level), "muted")
            self._qlog(self.tr_format("platform_log", value=platform), "muted")
            self._qlog(self.tr_format("block_size_log", value=block_size), "muted")
            self._qlog(self.tr_format("preset_log", value=preset_name), "muted")
            self._qlog(self.tr("memory_retry_enabled_log"), "muted")
            self._qlog(self.tr_format("temp_log", path=temp_dir), "muted")
            if is_frozen():
                self._qlog(self.tr("runner_internal"), "muted")
            else:
                prefix = self._get_mkpfs_prefix()
                self._qlog(self.tr_format("runner_external", runner=(command_to_text(prefix) if prefix else self.tr("runner_not_found"))), "muted")
                if prefix is None:
                    self._qlog(self.tr("mkpfs_missing"), "error")
                    self._qlog(self.tr("python_recommendation"), "warn")
                    play_error_once()
                    return
            self._qlog("-" * 78, "muted")

            if not targets:
                self._qgame_counter(0, 0)
                self._qlog(self.tr("no_games_found"), "warn")
                return

            for index, target in enumerate(targets, start=1):
                if self.cancel_requested:
                    break

                error_sound_played = False
                target = normalize_path(target)
                if batch:
                    out_name = derive_output_name(target)
                else:
                    out_name = safe_filename(self.file_name_var.get().strip())
                    if not out_name.lower().endswith(".ffpfsc"):
                        out_name += ".ffpfsc"

                out_path = normalize_path(os.path.join(out_dir, out_name))
                game_name = derive_game_display_name(target, out_name)
                if batch:
                    self._qgame_counter(index, len(targets))
                previous_size = get_path_size(target)
                is_folder_source = os.path.isdir(target)
                is_exfat_source = os.path.isfile(target) and target.lower().endswith(".exfat")

                operation_start = time.perf_counter()
                self._qprogress(0)
                self._start_operation_timer(operation_start)

                self._qlog(self.tr_format("game_index_title", current=index, total=len(targets), game=game_name), "title")
                self._qlog(self.tr_format("source_log", path=target), "info")
                self._qlog(self.tr_format("output_log", path=out_path), "info")
                self._qlog(self.tr_format("previous_size_log", size=format_bytes(previous_size)), "info")
                if is_folder_source:
                    self._qlog(self.tr("folder_method_log"), "muted")
                elif is_exfat_source:
                    self._qlog(self.tr("exfat_method_log"), "muted")

                if add_fakelib:
                    if not ensure_fakelib_files(target, self._qlog, self.tr, self.tr_format):
                        self._qlog(self.tr("fakelib_skip"), "error")
                        play_error_once()
                        continue

                os.makedirs(out_dir, exist_ok=True)

                if not self._preflight_check(
                    target,
                    out_path,
                    temp_dir,
                    previous_size,
                    block_size,
                ):
                    play_error_once()
                    self._qlog("-" * 78, "muted")
                    continue

                # MkPFS GUI'den cevap beklemesin diye mevcut çıktıyı önceden kaldır.
                if os.path.exists(out_path):
                    if overwrite_output:
                        try:
                            if os.path.isfile(out_path):
                                os.remove(out_path)
                                self._qlog(
                                    self.tr_format("output_removed", path=out_path),
                                    "warn",
                                )
                            else:
                                self._qlog(
                                    self.tr_format(
                                        "output_path_not_file",
                                        path=out_path,
                                    ),
                                    "error",
                                )
                                play_error_once()
                                continue
                        except Exception as exc:
                            self._qlog(
                                self.tr_format(
                                    "output_remove_failed",
                                    error=exc,
                                ),
                                "error",
                            )
                            play_error_once()
                            continue
                    else:
                        self._qlog(
                            self.tr_format(
                                "output_exists_skipped",
                                path=out_path,
                            ),
                            "warn",
                        )
                        continue

                pack_progress_scale = 95 if extra_verify else 100

                if is_exfat_source:
                    # Hazır .exfat imajını PFSC ile sıkıştır.
                    pack_args = [
                        "pack", "file",
                        "--compress",
                        "--threshold-gain", "0",
                        "--max-compressed-ratio", "100",
                        "--version", platform,
                        "--inode-bits", "32",
                        "--temp-folder", temp_dir,
                        "--cpu-count", str(cpu),
                        "--compression-level", str(compression_level),
                        "--block-size", block_size,
                        "--no-verify-structure",
                        target,
                        out_path,
                    ]
                    self._qphase(
                        self.tr("stage_exfat_ffpfsc_creating")
                    )
                    failure_key = "exfat_direct_failed"

                elif is_folder_source:
                    # MkPFS 1.1.0 varsayılan akışı:
                    # klasörü bellekte exFAT'e sarar ve aynı akışta .ffpfsc üretir.
                    # --raw KULLANILMAZ; diskte geçici image.dat/.exfat oluşmaz.
                    pack_args = [
                        "pack", "folder",
                        "--compress",
                        "--threshold-gain", "0",
                        "--max-compressed-ratio", "100",
                        "--no-adjust-output-file-extension",
                        "--version", platform,
                        "--inode-bits", "32",
                        "--require-game-files",
                        "--temp-folder", temp_dir,
                        "--cpu-count", str(cpu),
                        "--compression-level", str(compression_level),
                        "--block-size", block_size,
                        "--no-verify-structure",
                        target,
                        out_path,
                    ]
                    self._qphase(
                        self.tr("stage_folder_ffpfsc_creating")
                    )
                    failure_key = "folder_direct_failed"

                else:
                    self._qlog(self.tr("invalid_source"), "error")
                    play_error_once()
                    continue

                self._qlog(
                    self.tr("direct_estimate_intro"),
                    "warn",
                )
                self._qlog(
                    self.tr("direct_estimate_formula"),
                    "muted",
                )

                # Gerçek sıkıştırma oranı önceden bilinemez.
                # MkPFS yüzde basmazsa kaynak boyutu güvenli üst sınır kabul edilir.
                expected_final_size = max(1, int(previous_size))
                output_progress_stop = threading.Event()
                output_progress_thread = self._start_output_progress_watcher(
                    out_path,
                    expected_final_size,
                    output_progress_stop,
                    progress_offset=0.0,
                    progress_scale=float(pack_progress_scale),
                )

                try:
                    rc = self._run_mkpfs(
                        pack_args,
                        progress_offset=0,
                        progress_scale=pack_progress_scale,
                    )
                finally:
                    output_progress_stop.set()
                    try:
                        output_progress_thread.join(timeout=2)
                    except Exception:
                        pass

                if (
                    rc != 0
                    and auto_memory_retry
                    and self._mkpfs_failure_kind == "memory"
                    and not self.cancel_requested
                ):
                    retry_cpu = 2 if cpu == 0 or cpu > 2 else 1
                    retry_level = min(compression_level, 5)
                    retry_block = "65536"

                    self._qlog(
                        self.tr_format(
                            "memory_retry_start",
                            cpu=retry_cpu,
                            level=retry_level,
                            block=retry_block,
                        ),
                        "warn",
                    )

                    try:
                        if os.path.isfile(out_path):
                            os.remove(out_path)
                    except Exception:
                        pass

                    retry_args = set_cli_option(pack_args, "--cpu-count", str(retry_cpu))
                    retry_args = set_cli_option(
                        retry_args,
                        "--compression-level",
                        str(retry_level),
                    )
                    retry_args = set_cli_option(
                        retry_args,
                        "--block-size",
                        retry_block,
                    )

                    self._qprogress(0)
                    retry_stop = threading.Event()
                    retry_thread = self._start_output_progress_watcher(
                        out_path,
                        expected_final_size,
                        retry_stop,
                        progress_offset=0.0,
                        progress_scale=float(pack_progress_scale),
                    )
                    try:
                        rc = self._run_mkpfs(
                            retry_args,
                            progress_offset=0,
                            progress_scale=pack_progress_scale,
                        )
                    finally:
                        retry_stop.set()
                        try:
                            retry_thread.join(timeout=2)
                        except Exception:
                            pass

                    if rc == 0:
                        self._qlog(self.tr("memory_retry_success"), "success")
                    else:
                        self._qlog(self.tr("memory_retry_failed"), "error")

                if rc != 0:
                    self._qlog(
                        self.tr_format(failure_key, code=rc),
                        "error",
                    )
                    self._qlog(self.tr("friendly_error_title"), "title")
                    self._qlog(self._friendly_failure_message(), "warn")
                    play_error_once()
                    continue

                if self._mkpfs_compression_enabled is False:
                    self._qlog(
                        self.tr("compression_disabled_warning"),
                        "error",
                    )
                elif self._mkpfs_compression_enabled is True:
                    self._qlog(
                        self.tr("compression_enabled_confirmed"),
                        "success",
                    )

                if (
                    self._mkpfs_actual_gain is not None
                    and self._mkpfs_actual_gain < 1.0
                ):
                    self._qlog(
                        self.tr_format(
                            "compression_low_gain_warning",
                            gain=self._mkpfs_actual_gain,
                        ),
                        "warn",
                    )

                if os.path.exists(out_path) and previous_size > 0:
                    direct_output_size = os.path.getsize(out_path)
                    if direct_output_size >= int(previous_size * 0.99):
                        self._qlog(
                            self.tr("compression_same_size_warning"),
                            "warn",
                        )

                if extra_verify:
                    self._qphase(self.tr("phase_extra_verify"))
                    verify_args = ["verify", out_path]

                    if is_exfat_source:
                        verify_args.extend(["--source-file", target])
                    elif is_folder_source:
                        verify_args.extend(["--source-dir", target])

                    verify_rc = self._run_mkpfs(
                        verify_args,
                        progress_offset=95,
                        progress_scale=5,
                    )
                    if verify_rc != 0:
                        self._qlog(
                            self.tr_format(
                                "unexpected_error",
                                error=f"verify exit code {verify_rc}",
                            ),
                            "error",
                        )
                        self._qlog(self.tr("friendly_error_title"), "title")
                        self._qlog(self._friendly_failure_message(), "warn")
                        play_error_once()
                        continue

                new_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
                elapsed_seconds = time.perf_counter() - operation_start
                self._stop_operation_timer(final_elapsed=elapsed_seconds)
                gain = previous_size - new_size
                gain_percent = (gain / previous_size * 100.0) if previous_size > 0 else 0.0

                self._qprogress(100)
                self._qstatus(self.tr("status_done"))
                self._qphase(self.tr("phase_done"))
                self._qlog(self.tr_format("completed_log", path=out_path), "success")
                self._qlog(self.tr("summary_title"), "title")
                self._qlog(self.tr_format("game_name_log", game=game_name), "info")
                self._qlog(self.tr_format("previous_size_log", size=format_bytes(previous_size)), "info")
                self._qlog(self.tr_format("new_size_log", size=format_bytes(new_size)), "info")
                self._qlog(self.tr_format("gain_log", size=format_bytes(gain), percent=gain_percent), "success" if gain >= 0 else "warn")
                self._qlog(
                    self.tr_format(
                        "compression_rating",
                        rating=self.tr(compression_rating_key(gain_percent)),
                    ),
                    "success" if gain_percent >= 10 else "warn",
                )
                self._qlog(self.tr_format("duration_log", duration=self.format_duration_local(elapsed_seconds)), "info")

                try:
                    log_path = append_process_summary_log(
                        game_name,
                        previous_size,
                        new_size,
                        elapsed_seconds,
                        out_path,
                        labels=self.summary_log_labels(),
                        duration_text=self.format_duration_local(elapsed_seconds),
                    )
                    self._qlog(self.tr_format("log_written", path=log_path), "muted")
                except Exception as exc:
                    self._qlog(self.tr_format("log_write_failed", error=exc), "warn")

                self._qsummary(
                    self.tr_format(
                        "last_summary",
                        game=game_name,
                        previous=format_bytes(previous_size),
                        new=format_bytes(new_size),
                        percent=gain_percent,
                        duration=self.format_duration_local(elapsed_seconds),
                    )
                )

                completed_count += 1

                if delete_source:
                    self._qphase(self.tr("delete_source_phase"))
                    safe_delete_game_folder(target, out_dir, temp_dir, self._qlog, self.tr, self.tr_format)

                self._qlog("-" * 78, "muted")

            self._qlog(self.tr("all_done"), "success")
            self._qstatus(self.tr("status_ready"))
            self._qphase(self.tr("phase_waiting"))

            all_successful = bool(targets) and completed_count == len(targets) and not self.cancel_requested
            if all_successful:
                self.play_completion_sound()
                if self.shutdown_var.get():
                    self.schedule_pc_shutdown()
        except Exception as exc:
            self._qlog(self.tr_format("unexpected_error", error=exc), "error")
            try:
                self.play_error_sound()
            except Exception:
                pass
        finally:
            self._stop_operation_timer(clear=False)
            self.queue.put(("done",))

    def _get_mkpfs_prefix(self) -> list[str] | None:
        if is_frozen():
            return [compiled_executable_path(), "--internal-mkpfs"]

        if self._mkpfs_prefix and mkpfs_prefix_works(self._mkpfs_prefix):
            return self._mkpfs_prefix

        self._mkpfs_prefix = detect_mkpfs_prefix()
        return self._mkpfs_prefix

    def _command_prefix(self) -> list[str]:
        prefix = self._get_mkpfs_prefix()
        if prefix is None:
            # This should already be caught in _worker, but keep a safe fallback.
            return [sys.executable, "-m", "mkpfs"]
        return prefix

    def _start_output_progress_watcher(
        self,
        output_path: str,
        expected_size: int,
        stop_event: threading.Event,
        progress_offset: float = 50.0,
        progress_scale: float = 50.0,
    ):
        """
        Klasör veya .exfat kaynaktan .ffpfsc üretirken MkPFS yüzde üretmiyorsa
        çıktı dosyasının boyutuna bakıp tahmini ilerleme üret.
        """
        def worker():
            while not stop_event.is_set():
                try:
                    if getattr(self, "_real_stage_progress_seen", False):
                        time.sleep(0.30)
                        continue

                    current_size = 0
                    for candidate in (output_path + ".tmp", output_path, output_path + ".part"):
                        if os.path.exists(candidate):
                            size = os.path.getsize(candidate)
                            if size >= current_size:
                                current_size = size

                    if current_size > 0:
                        if expected_size > 0:
                            pct = min(99.0, (current_size / expected_size) * 100.0)
                            mapped = min(progress_offset + progress_scale - 0.5, progress_offset + (pct * progress_scale / 100.0))

                            if mapped >= float(getattr(self, "_progress_value", 0.0)):
                                self._qprogress(mapped)

                            self._qstatus(self.tr_format("ffpfsc_estimate_status", percent=pct))
                            self._qphase(
                                self.tr_format(
                                    "ffpfsc_writing_phase_full",
                                    current=format_bytes(current_size),
                                    total=format_bytes(expected_size),
                                )
                            )
                        else:
                            self._qstatus(self.tr("mkpfs_started"))
                            self._qphase(
                                self.tr_format(
                                    "ffpfsc_writing_phase",
                                    current=format_bytes(current_size),
                                )
                            )
                except Exception:
                    pass

                time.sleep(0.35)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    def _run_mkpfs(self, mkpfs_args: list[str], progress_offset: int = 0, progress_scale: int = 100) -> int:
        if len(mkpfs_args) >= 2 and mkpfs_args[0] == "pack":
            tmp_path = normalize_path(self.temp_dir_var.get().strip())
            output_path = normalize_path(self.output_dir_var.get().strip())
            source_path = normalize_path(self.source_var.get().strip())
            issues = validate_preflight(tmp_path, output_path, source_path)
            if issues:
                for issue in issues:
                    self._qlog("Preflight: " + issue, "error")
                return 1
            if str(self.platform_var.get()).upper() == "PS5" and "--raw" in mkpfs_args:
                self._qlog("Safety check: compressed raw PFS for PS5 is not allowed.", "error")
                return 1
            if str(self.block_size_var.get()) == "auto":
                self._qlog("MkPFS auto block size retained (recommended for compatibility).", "info")
        cmd = self._command_prefix() + mkpfs_args
        self._qlog(">>> " + " ".join(cmd), "cmd")
        self._qstatus(self.tr("mkpfs_started"))

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        # Force child Python/system temporary files to the user's selected work drive.
        selected_temp = normalize_path(self.temp_dir_var.get().strip())
        if selected_temp and os.path.isdir(selected_temp):
            env["TEMP"] = selected_temp
            env["TMP"] = selected_temp
            env["TMPDIR"] = selected_temp

        last_seen: dict[str, int] = {}
        last_mapped_progress = progress_offset
        compress_finalize_wait_logged = False
        self._real_stage_progress_seen = False
        self._mkpfs_compression_enabled = None
        self._mkpfs_actual_gain = None
        self._mkpfs_last_output_text = ""
        self._mkpfs_failure_kind = "generic"
        recent_lines: list[str] = []
        try:
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                bufsize=0,
            )
        except Exception as exc:
            self._qlog(self.tr_format("process_start_failed", error=exc), "error")
            return 1

        buffer = ""
        assert self.current_process.stdout is not None

        def handle_line(raw_line: str):
            nonlocal compress_finalize_wait_logged

            line = raw_line.strip()
            if not line:
                return

            recent_lines.append(line)
            if len(recent_lines) > 300:
                del recent_lines[:100]

            upper = line.upper()

            if upper.startswith("COMPRESSION:"):
                if "ENABLED" in upper:
                    self._mkpfs_compression_enabled = True
                elif "DISABLED" in upper:
                    self._mkpfs_compression_enabled = False

            gain_match = re.search(r"ACTUAL GAIN ACHIEVED:\s*([-+]?[0-9]+(?:\.[0-9]+)?)%", upper)
            if gain_match:
                try:
                    self._mkpfs_actual_gain = float(gain_match.group(1))
                except Exception:
                    self._mkpfs_actual_gain = None

            # Throughput, Build Summary'nin son satırlarından biridir.
            # Pack komutunda --no-verify-structure kullanıldığı için burada
            # varsayılan hızlı yapı doğrulaması kapalıdır.
            if upper.startswith("THROUGHPUT:"):
                self._qlog(line, "info")
                self._qphase(self.tr("build_summary_receiving"))
                return

            if upper.startswith("BUILD SUMMARY"):
                self._qphase(self.tr("build_summary_receiving"))
                self._qlog(line, "title")
                return

            # Filter MkPFS repeated progress. Log only when percent increases.
            # MkPFS bazen "[...] 12% read", bazen de "scan %12" / "read %12" formatında yazar.
            m = re.search(r"\]\s+(\d+)%\s+([A-Za-z_]+)(.*)$", line)
            m_simple = re.match(r"^([A-Za-z_]+)\s+%(\d+)(.*)$", line)
            if m or m_simple:
                nonlocal last_mapped_progress
                self._real_stage_progress_seen = True

                if m:
                    pct = int(m.group(1))
                    phase = m.group(2).lower()
                    rest = m.group(3).strip()
                else:
                    phase = m_simple.group(1).lower()
                    pct = int(m_simple.group(2))
                    rest = m_simple.group(3).strip()

                prev = last_seen.get(phase, -1)
                mapped = min(100, progress_offset + (pct * progress_scale / 100.0))

                if mapped >= last_mapped_progress:
                    last_mapped_progress = mapped
                    self._qprogress(mapped)

                self._qstatus(f"{phase} %{pct}")
                if pct > prev:
                    last_seen[phase] = pct

                    # scan/read gibi çok satır üreten fazlarda log alanını doldurma.
                    # Sadece %10 aralıklarla kısa bilgi yaz.
                    if phase in ("scan", "read"):
                        if pct in (0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100):
                            self._qlog(f"{phase} %{pct}", "progress")
                    else:
                        short = f"{phase} %{pct}"
                        speed = re.search(r"@\s+([^@]+)$", rest)
                        if speed:
                            short += " @ " + speed.group(1).strip()
                        self._qlog(short, "progress")

                    # compress %100 sonrası MkPFS bazen Build Summary / final dosya yazımı için bekletebilir.
                    # Program dondu sanılmasın diye net uyarı ver.
                    if phase == "compress" and pct >= 100 and not compress_finalize_wait_logged:
                        compress_finalize_wait_logged = True
                        self._qstatus(self.tr("continue_status"))
                        self._qphase(self.tr("continue_wait"))
                        self._qlog(self.tr("continue_wait"), "warn")
                return

            if line.startswith(">>>"):
                self._qlog(line, "cmd")
            elif "ERROR" in upper or "HATA" in upper or "FAILED" in upper or "TRACEBACK" in upper:
                self._qlog(line, "error")
            elif "WARN" in upper or "UYARI" in upper:
                self._qlog(line, "warn")
            elif "SUCCESSFULLY" in upper or "TAMAMLANDI" in upper or "ERRORS:                0" in upper:
                self._qlog(line, "success")
            elif (
                "COMPRESSION SETUP" in upper
                or "COMPRESSION:" in upper
                or "CPU CORES" in upper
                or "TOTAL FILES" in upper
                or "TOTAL UNCOMPRESSED SIZE" in upper
                or "TOTAL STORED SIZE" in upper
                or "ACTUAL GAIN ACHIEVED" in upper
                or "ALL-PFSC GAIN" in upper
                or "ELAPSED TIME" in upper
                or "THROUGHPUT" in upper
            ):
                self._qlog(line, "info")
            elif line.startswith("=") or line.startswith("-"):
                self._qlog(line, "muted")
            else:
                # Keep the output readable; skip super noisy empty-style progress fragments.
                self._qlog(line, "muted")

        # Eski sürümde stdout.read(4096) kullanılıyordu.
        # Büyük oyunlarda MkPFS ilk 4096 karakter dolana kadar GUI'ye progress düşmeyebiliyordu.
        # Burada karakter karakter okuyup \r / \n gördükçe satırı işliyoruz.
        while True:
            if self.cancel_requested:
                try:
                    self.current_process.terminate()
                except Exception:
                    pass

            ch = self.current_process.stdout.read(1)

            if ch == "":
                if self.current_process.poll() is not None:
                    break
                time.sleep(0.05)
                continue

            if ch in ("\n", "\r"):
                if buffer.strip():
                    handle_line(buffer)
                buffer = ""
            else:
                buffer += ch

        if buffer.strip():
            handle_line(buffer)

        return_code = self.current_process.wait()
        self._mkpfs_last_output_text = "\n".join(recent_lines[-300:])
        self._mkpfs_failure_kind = classify_mkpfs_failure(
            self._mkpfs_last_output_text
        )
        return return_code

    def check_updates(self):
        """Check latest MkPFS release on GitHub and print the result to the terminal."""
        try:
            self.update_button.configure(
                text=self.tr("checking_updates"),
                bg="#475569",
                fg="white",
                activeforeground="white",
                disabledforeground="white",
                state="disabled",
            )
        except Exception:
            pass
        threading.Thread(target=self._check_updates_worker, daemon=True).start()

    def _check_updates_worker(self):
        self._qlog(self.tr("mkpfs_update_checking_log"), "info")
        self._qlog(self.tr_format("mkpfs_update_source_log", url=MKPFS_RELEASES_URL), "muted")

        try:
            current_version = detect_current_mkpfs_version(self._get_mkpfs_prefix())
        except Exception:
            current_version = BUNDLED_MKPFS_VERSION

        try:
            latest_version = fetch_latest_mkpfs_version()
        except Exception as exc:
            self._qlog(self.tr_format("mkpfs_update_failed_log", error=exc), "error")
            self.queue.put(("update_button", self.tr("check_updates"), "#334155", "normal", "white"))
            return

        if not latest_version:
            self._qlog(self.tr("mkpfs_latest_unknown_log"), "warn")
            self.queue.put(("update_button", self.tr("check_updates"), "#334155", "normal", "white"))
            return

        self._qlog(self.tr_format("current_mkpfs_version_log", version=current_version), "muted")
        self._qlog(self.tr_format("latest_mkpfs_version_log", version=latest_version), "info")

        if is_remote_version_newer(latest_version, current_version):
            self._qlog(self.tr_format("mkpfs_new_version_log", version=latest_version), "warn")
            self._qlog(self.tr("packager_github_note"), "muted")
            self.queue.put(("update_button", self.tr("new_version"), "#b45309", "normal", "white"))
        else:
            self._qlog(self.tr("mkpfs_up_to_date_log"), "success")
            self.queue.put(("update_button", self.tr("app_current"), "#166534", "normal", "white"))

    def _play_mp3_resource(self, filename: str, fallback_error: bool = False):
        """
        Paket içindeki MP3'ü Windows WinMM/MCI API ile çalar.
        Komut yorumlayıcısı, PowerShell veya harici medya oynatıcısı kullanılmaz.
        """
        def worker():
            path = resource_path(filename)
            alias = f"ps5pfs_{threading.get_ident()}_{int(time.time() * 1000)}"

            try:
                if os.name != "nt" or not os.path.isfile(path):
                    raise FileNotFoundError(path)

                import ctypes

                winmm = ctypes.windll.winmm
                mci_send = winmm.mciSendStringW
                mci_send.argtypes = [
                    ctypes.c_wchar_p,
                    ctypes.c_wchar_p,
                    ctypes.c_uint,
                    ctypes.c_void_p,
                ]
                mci_send.restype = ctypes.c_uint

                def mci(command: str):
                    error_code = int(mci_send(command, None, 0, None))
                    if error_code:
                        raise OSError(f"MCI error {error_code}")

                safe_path = path.replace('"', "")
                mci(f'open "{safe_path}" type mpegvideo alias {alias}')
                try:
                    mci(f"play {alias} wait")
                finally:
                    try:
                        mci(f"close {alias}")
                    except Exception:
                        pass
                return
            except Exception:
                # MP3 çalınamazsa sessiz kalmak yerine yerleşik Windows sesi kullan.
                try:
                    import winsound

                    if fallback_error:
                        winsound.MessageBeep(winsound.MB_ICONHAND)
                    else:
                        for frequency, duration in ((660, 150), (880, 180), (1047, 260)):
                            winsound.Beep(frequency, duration)
                except Exception:
                    try:
                        self.bell()
                    except Exception:
                        pass

        threading.Thread(target=worker, daemon=True).start()

    def play_completion_sound(self):
        self._play_mp3_resource("completion.mp3", fallback_error=False)

    def play_error_sound(self):
        self._play_mp3_resource("error.mp3", fallback_error=True)


    def schedule_pc_shutdown(self):
        """Tüm hedefler başarıyla bittiyse Windows kapatmasını 30 saniye gecikmeyle planlar."""
        if os.name != "nt":
            self._qlog(self.tr("shutdown_unsupported"), "warn")
            return

        try:
            shutdown_exe = os.path.join(
                os.environ.get("SystemRoot", r"C:\Windows"),
                "System32",
                "shutdown.exe",
            )
            result = run_no_console(
                [
                    shutdown_exe,
                    "/s",
                    "/t",
                    "30",
                    "/c",
                    "PS5-PFS-Packager: all operations completed.",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                check=False,
            )

            if result.returncode == 0:
                self._qlog(self.tr("shutdown_scheduled"), "warn")
            else:
                self._qlog(
                    self.tr_format("shutdown_failed", error=f"exit code {result.returncode}"),
                    "error",
                )
        except Exception as exc:
            self._qlog(self.tr_format("shutdown_failed", error=exc), "error")


def main():
    multiprocessing.freeze_support()

    # Child mode used by the already elevated GUI to run MkPFS internally.
    if len(sys.argv) >= 2 and sys.argv[1] == "--internal-mkpfs":
        sys.exit(run_internal_mkpfs(sys.argv[2:]))

    # The compiled EXE also carries a requireAdministrator manifest.
    # This fallback keeps direct Python launches consistent: elevation
    # happens once at startup, never while opening EXFAT/FFPFSC.
    if os.name == "nt":
        try:
            import ctypes

            if not bool(ctypes.windll.shell32.IsUserAnAdmin()):
                if is_frozen():
                    executable = compiled_executable_path()
                    args = list(sys.argv[1:])
                else:
                    executable = sys.executable
                    args = [os.path.abspath(__file__), *sys.argv[1:]]

                result = ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",
                    executable,
                    subprocess.list2cmdline(args),
                    app_base_dir(),
                    1,
                )
                if result and int(result) > 32:
                    return
                raise RuntimeError("UAC elevation was cancelled or failed.")
        except Exception as exc:
            try:
                messagebox.showerror(
                    APP_TITLE,
                    f"Yönetici yetkisi alınamadı:\n{exc}",
                )
            except Exception:
                pass
            return

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
