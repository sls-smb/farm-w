"""
Outil de calibration — Lance AVANT le bot pour vérifier la détection OCR.

  python calibrate.py           → affiche la position de la souris (pour trouver les coordonnées)
  python calibrate.py capture   → capture la région inventaire et tente l'OCR

Si l'OCR ne détecte rien :
  1. Ouvre calibration_capture.png pour voir ce qui est capturé
  2. Ajuste INVENTORY_REGION dans farm_bot.py selon tes coordonnées
  3. Re-lance "python calibrate.py capture" avec le message affiché dans GTA
"""

import sys
import time
import mss
import numpy as np
import cv2
import pytesseract
from PIL import Image

# Doit correspondre à farm_bot.py
INVENTORY_REGION = {
    "top": 990,
    "left": 60,
    "width": 380,
    "height": 110,
}

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def live_mouse():
    """Affiche la position de la souris en temps réel (Ctrl+C pour quitter)."""
    import pyautogui
    print("Position de la souris — Ctrl+C pour quitter")
    print("Déplace la souris vers le message GTA pour trouver ses coordonnées.\n")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"  x={x:4d}  y={y:4d}", end="\r")
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nTerminé.")


def capture_and_ocr():
    """Capture la région et tente l'OCR — affiche le texte détecté."""
    print(f"Capture de la région : {INVENTORY_REGION}")

    with mss.mss() as sct:
        shot = sct.grab(INVENTORY_REGION)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    img.save("calibration_capture.png")
    print("→ Image brute sauvegardée : calibration_capture.png")

    # Prétraitement : texte blanc sur fond sombre → on inverse pour obtenir noir sur blanc
    arr = np.array(img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    # Inversion : texte blanc devient noir, fond sombre devient blanc
    inverted = cv2.bitwise_not(gray)
    # Seuillage pour nettoyer le bruit
    _, thresh = cv2.threshold(inverted, 180, 255, cv2.THRESH_BINARY)
    h, w = thresh.shape
    resized = cv2.resize(thresh, (w * 2, h * 2), interpolation=cv2.INTER_LINEAR)
    thresh_img = Image.fromarray(resized)
    thresh_img.save("calibration_thresh.png")
    print("→ Image seuillée sauvegardée : calibration_thresh.png")

    # Tente l'OCR avec plusieurs configs
    text = ""
    for config in ["--psm 6", "--psm 3", "--psm 11"]:
        t = pytesseract.image_to_string(thresh_img, lang="fra", config=config)
        if t.strip():
            text = t
            break
    if not text.strip():
        text = pytesseract.image_to_string(thresh_img, lang="fra")
    print(f"\nTexte OCR détecté :\n---\n{text.strip()}\n---")

    keyword = "assez de place"
    if keyword.lower() in text.lower():
        print("✓ Message 'inventaire plein' DÉTECTÉ — la calibration est correcte.")
    else:
        print("✗ Message non détecté.")
        print("  → Lance GTA, affiche le message, puis relance cette commande.")
        print("  → Ouvre calibration_capture.png pour vérifier la zone capturée.")
        print("  → Ajuste INVENTORY_REGION dans farm_bot.py si la zone est décalée.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "capture":
        capture_and_ocr()
    else:
        live_mouse()
