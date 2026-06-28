"""
GTA Seed Farming Bot
====================
Résolution cible : 2560x1440
Touche ramassage : E
Clavier : AZERTY (ZQSD)
OS : Windows

Détecte le texte "Vous n'avez pas assez de place" par OCR sur la ligne exacte.

Dépendances : pip install -r requirements.txt
Tesseract requis : https://github.com/UB-Mannheim/tesseract/wiki (avec pack French)
"""

import sys
import time
import threading
import winsound
import random
import ctypes

import keyboard
import mss
import numpy as np
import cv2
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─────────────────────────────────────────────
# ENVOI DE TOUCHES (scan codes, indépendant du layout AZERTY/QWERTY)
# ─────────────────────────────────────────────

KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP    = 0x0002

SCAN_CODES = {
    "e": 0x12,
    "z": 0x11,
    "q": 0x10,
    "s": 0x1F,
    "d": 0x20,
}

def _send_scan(scan_code: int, up: bool = False):
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0)
    ctypes.windll.user32.keybd_event(0, scan_code, flags, 0)

def press_scan(key: str):
    _send_scan(SCAN_CODES[key])

def release_scan(key: str):
    _send_scan(SCAN_CODES[key], up=True)

def tap_scan(key: str):
    press_scan(key)
    time.sleep(0.05)
    release_scan(key)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

PICKUP_KEY = "e"
PICKUP_DURATION = 5.5
BETWEEN_PICKUP_DELAY = 0.3

# Zone ciblant UNIQUEMENT la ligne de texte "Vous n'avez pas assez de place"
# Calculée depuis screenshot 2560x1440
TEXT_REGION = {
    "top":    1065,
    "left":   65,
    "width":  330,
    "height": 40,
}

# Mot-clé à détecter (distinctif à ce message)
INVENTORY_KEYWORD = "avez pas"

SEARCH_MIN_DURATION = 0.2
SEARCH_MAX_DURATION = 0.6

PAUSE_KEY = "p"
STOP_KEY  = "end"

ALERT_BEEPS = [
    (1200, 300),
    (900,  300),
    (1200, 300),
    (900,  500),
]

# ─────────────────────────────────────────────
# ÉTAT GLOBAL
# ─────────────────────────────────────────────

paused  = False
running = True
_pause_lock = threading.Lock()

# ─────────────────────────────────────────────
# DÉTECTION
# ─────────────────────────────────────────────

def play_alert():
    for freq, duration in ALERT_BEEPS:
        winsound.Beep(freq, duration)
        time.sleep(0.05)


def capture_region(region: dict) -> np.ndarray:
    with mss.mss() as sct:
        shot = sct.grab(region)
        arr = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)
        return arr[:, :, :3]  # BGR


def preprocess(bgr: np.ndarray) -> Image.Image:
    """
    Texte blanc sur fond sombre :
    1. Niveaux de gris
    2. Inversion (texte blanc → noir)
    3. Seuillage pour nettoyer le bruit
    4. Agrandissement x3 pour améliorer l'OCR sur petite police
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    inv  = cv2.bitwise_not(gray)
    _, thresh = cv2.threshold(inv, 160, 255, cv2.THRESH_BINARY)
    h, w = thresh.shape
    big  = cv2.resize(thresh, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
    return Image.fromarray(big)


def is_inventory_full() -> bool:
    try:
        bgr = capture_region(TEXT_REGION)
        img = preprocess(bgr)
        # psm 7 = ligne de texte unique, idéal pour notre zone étroite
        text = pytesseract.image_to_string(img, lang="fra", config="--psm 7").lower()
        return INVENTORY_KEYWORD in text
    except Exception as e:
        print(f"[WARN] OCR : {e}")
        return False


def safe_sleep(duration: float):
    end = time.time() + duration
    while time.time() < end:
        if not running:
            return
        time.sleep(0.05)


def micro_search():
    key = random.choice(["q", "d"])
    duration = random.uniform(SEARCH_MIN_DURATION, SEARCH_MAX_DURATION)
    press_scan(key)
    safe_sleep(duration)
    release_scan(key)

# ─────────────────────────────────────────────
# HOTKEYS
# ─────────────────────────────────────────────

def setup_hotkeys():
    global paused, running

    def on_pause():
        global paused
        with _pause_lock:
            paused = not paused
        print(f"\n[BOT] {'PAUSE' if paused else 'REPRISE'} — [{PAUSE_KEY.upper()}] pour basculer.")

    def on_stop():
        global running
        running = False
        print("\n[BOT] Arrêt demandé.")

    keyboard.add_hotkey(PAUSE_KEY, on_pause, suppress=False)
    keyboard.add_hotkey(STOP_KEY,  on_stop,  suppress=False)

# ─────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ─────────────────────────────────────────────

def alert_and_pause():
    global paused
    paused = True
    print("\n" + "=" * 52)
    print("  !! INVENTAIRE PLEIN !!")
    print("  Va vider ton inventaire dans le jeu,")
    print(f"  puis appuie sur [{PAUSE_KEY.upper()}] pour reprendre.")
    print("=" * 52 + "\n")
    threading.Thread(target=play_alert, daemon=True).start()


def main():
    global running, paused

    print("=" * 52)
    print("  GTA SEED FARMING BOT  —  2560x1440")
    print(f"  Ramassage : [{PICKUP_KEY.upper()}]   Pause : [{PAUSE_KEY.upper()}]   Stop : [END]")
    print("=" * 52)
    print("\nPositionne-toi dans la zone de farm.")
    print("Lancement dans 5 secondes — clique sur GTA !\n")
    time.sleep(5)

    setup_hotkeys()

    cycle = 0
    while running:
        if paused:
            time.sleep(0.2)
            continue

        cycle += 1
        print(f"[BOT] Cycle #{cycle}")

        if is_inventory_full():
            alert_and_pause()
            continue

        tap_scan(PICKUP_KEY)
        safe_sleep(PICKUP_DURATION)

        if not running:
            break

        if is_inventory_full():
            alert_and_pause()
            continue

        if not paused and running:
            micro_search()
            safe_sleep(BETWEEN_PICKUP_DELAY)

    print("[BOT] Arrêté. À bientôt !")
    sys.exit(0)


if __name__ == "__main__":
    main()
