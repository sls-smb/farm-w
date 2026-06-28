"""
GTA Seed Farming Bot
====================
Résolution cible : 2560x1440
Touche ramassage : E
Message inventaire plein : "Vous n'avez pas assez de place"
Clavier : AZERTY (ZQSD)
OS : Windows

Dépendances : pip install -r requirements.txt
Tesseract OCR requis : https://github.com/UB-Mannheim/tesseract/wiki
  → Installe le pack de langue française lors de l'installation Tesseract
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
import pytesseract

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

# Chemin vers Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Touche de ramassage
PICKUP_KEY = "e"

# Durée de l'animation de ramassage (secondes) — ajuste si besoin
PICKUP_DURATION = 5.5

# Délai entre la fin de l'animation et le prochain ramassage
BETWEEN_PICKUP_DELAY = 0.3

# Zone de détection du message inventaire — bas-gauche en 2560x1440
# "Vous n'avez pas assez de place" apparaît dans cette zone
INVENTORY_REGION = {
    "top": 1300,
    "left": 0,
    "width": 750,
    "height": 100,
}

# Texte à détecter (insensible à la casse, correspondance partielle)
INVENTORY_FULL_TEXT = "assez de place"

# Micro-mouvement aléatoire entre chaque graine (zone petite)
# Le personnage pivote légèrement sur lui-même pour couvrir la zone
SEARCH_MIN_DURATION = 0.2  # secondes de touche maintenue
SEARCH_MAX_DURATION = 0.6

# Touches de déplacement AZERTY
MOVE_KEYS = ["z", "q", "s", "d"]

# Touche pause manuelle / reprise
PAUSE_KEY = "p"

# Touche arrêt complet
STOP_KEY = "end"

# Alerte sonore Windows (fréquence Hz, durée ms, répétitions)
ALERT_BEEPS = [
    (1200, 300),
    (900, 300),
    (1200, 300),
    (900, 500),
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
    """Joue une séquence de bips pour alerter l'utilisateur."""
    for freq, duration in ALERT_BEEPS:
        winsound.Beep(freq, duration)
        time.sleep(0.05)


def capture_region(region: dict) -> Image.Image:
    with mss.mss() as sct:
        shot = sct.grab(region)
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """
    Les messages GTA sont du texte blanc/jaune sur fond semi-transparent.
    On augmente le contraste pour améliorer la détection OCR.
    """
    arr = np.array(img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    # Seuillage Otsu — s'adapte automatiquement à la luminosité
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Agrandissement x2 pour améliorer la précision OCR sur petit texte
    h, w = thresh.shape
    resized = cv2.resize(thresh, (w * 2, h * 2), interpolation=cv2.INTER_LINEAR)
    return Image.fromarray(resized)


def is_inventory_full() -> bool:
    """Retourne True si le message d'inventaire plein est visible."""
    try:
        img = capture_region(INVENTORY_REGION)
        img = preprocess_for_ocr(img)
        text = pytesseract.image_to_string(img, lang="fra").lower()
        return INVENTORY_FULL_TEXT.lower() in text
    except Exception as e:
        print(f"[WARN] Erreur OCR : {e}")
        return False


def safe_sleep(duration: float):
    """Sleep interruptible : s'arrête si paused ou running change."""
    end = time.time() + duration
    while time.time() < end:
        if not running:
            return
        time.sleep(0.05)


def micro_search():
    """Pivote légèrement le personnage pour trouver la graine suivante."""
    key = random.choice(["q", "d"])  # rotation gauche ou droite
    duration = random.uniform(SEARCH_MIN_DURATION, SEARCH_MAX_DURATION)
    pyautogui.keyDown(key)
    safe_sleep(duration)
    pyautogui.keyUp(key)


# ─────────────────────────────────────────────
# GESTION DES TOUCHES
# ─────────────────────────────────────────────

def setup_hotkeys():
    """Configure les raccourcis clavier pause/stop."""
    global paused, running

    def on_pause():
        global paused
        with _pause_lock:
            paused = not paused
        state = "PAUSE" if paused else "REPRISE"
        print(f"\n[BOT] {state} — appuie sur [{PAUSE_KEY.upper()}] pour basculer.")

    def on_stop():
        global running
        running = False
        print("\n[BOT] Arrêt demandé.")

    keyboard.add_hotkey(PAUSE_KEY, on_pause, suppress=False)
    keyboard.add_hotkey(STOP_KEY, on_stop, suppress=False)


# ─────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ─────────────────────────────────────────────

def alert_and_pause():
    """Signale inventaire plein et met le bot en pause."""
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
        # Attente active si en pause
        if paused:
            time.sleep(0.2)
            continue

        cycle += 1
        print(f"[BOT] Cycle #{cycle} — tentative de ramassage...")

        # Vérifie l'inventaire avant d'agir
        if is_inventory_full():
            alert_and_pause()
            continue

        # Appuie sur E pour ramasser
        pyautogui.press(PICKUP_KEY)

        # Attend la fin de l'animation (interruptible)
        safe_sleep(PICKUP_DURATION)

        if not running:
            break

        # Re-vérifie l'inventaire après ramassage
        if is_inventory_full():
            alert_and_pause()
            continue

        # Micro-mouvement pour pointer vers la prochaine graine
        if not paused and running:
            micro_search()
            safe_sleep(BETWEEN_PICKUP_DELAY)

    print("[BOT] Arrêté. À bientôt !")
    sys.exit(0)


if __name__ == "__main__":
    main()
