"""
GTA Seed Farming Bot
====================
Résolution cible : 2560x1440
Touche ramassage : E
Clavier : AZERTY (ZQSD)
OS : Windows

Détecte la notification Unity RP par couleur (rapide, sans OCR).

Dépendances : pip install -r requirements.txt
"""

import sys
import time
import threading
import winsound
import random

import pyautogui
import keyboard
import mss
import numpy as np
import cv2
from PIL import Image

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

# Touche de ramassage
PICKUP_KEY = "e"

# Durée de l'animation de ramassage (secondes)
PICKUP_DURATION = 5.5

# Délai entre la fin de l'animation et le prochain ramassage
BETWEEN_PICKUP_DELAY = 0.3

# Zone contenant la notification Unity RP (bas-gauche, 2560x1440)
NOTIF_REGION = {
    "top": 990,
    "left": 60,
    "width": 380,
    "height": 110,
}

# Couleur rouge du logo Unity RP (BGR) — plage de détection
# Rouge vif : R>150, G<80, B<80
RED_MIN = np.array([0,   0,   150], dtype=np.uint8)   # BGR min
RED_MAX = np.array([80,  80,  255], dtype=np.uint8)   # BGR max

# Nombre minimum de pixels rouges pour valider la détection
RED_PIXEL_THRESHOLD = 30

# Micro-mouvement entre graines
SEARCH_MIN_DURATION = 0.2
SEARCH_MAX_DURATION = 0.6

# Touches
PAUSE_KEY = "p"
STOP_KEY  = "end"

# Alerte sonore
ALERT_BEEPS = [
    (1200, 300),
    (900,  300),
    (1200, 300),
    (900,  500),
]

# ─────────────────────────────────────────────
# ÉTAT GLOBAL
# ─────────────────────────────────────────────

paused = False
running = True
_pause_lock = threading.Lock()

# ─────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────

def play_alert():
    for freq, duration in ALERT_BEEPS:
        winsound.Beep(freq, duration)
        time.sleep(0.05)


def capture_region(region: dict) -> np.ndarray:
    """Capture une région et retourne un tableau BGR (format OpenCV)."""
    with mss.mss() as sct:
        shot = sct.grab(region)
        arr = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)
        return arr[:, :, :3]  # drop alpha → BGR


def is_inventory_full() -> bool:
    """
    Détecte la notification Unity RP en cherchant les pixels rouges du logo.
    Rapide (~5ms), sans OCR.
    """
    try:
        bgr = capture_region(NOTIF_REGION)
        mask = cv2.inRange(bgr, RED_MIN, RED_MAX)
        red_pixels = cv2.countNonZero(mask)
        return red_pixels >= RED_PIXEL_THRESHOLD
    except Exception as e:
        print(f"[WARN] Erreur détection : {e}")
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
    keyboard.press(key)
    safe_sleep(duration)
    keyboard.release(key)

# ─────────────────────────────────────────────
# GESTION DES TOUCHES
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
    print("Lancement dans 5 secondes...\n")
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

        keyboard.send(PICKUP_KEY)
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
