"""
Outil de calibration.

  python calibrate.py          → affiche position de la souris
  python calibrate.py capture  → capture la zone texte et tente l'OCR
  python calibrate.py watch    → surveille en temps réel
"""

import sys
import time
import numpy as np
import cv2
import mss
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

TEXT_REGION = {
    "top":    1065,
    "left":   65,
    "width":  330,
    "height": 40,
}

INVENTORY_KEYWORD = "n'avez"


def capture():
    with mss.mss() as sct:
        shot = sct.grab(TEXT_REGION)
        arr = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)
        return arr[:, :, :3]


def preprocess(bgr):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    inv  = cv2.bitwise_not(gray)
    _, thresh = cv2.threshold(inv, 160, 255, cv2.THRESH_BINARY)
    h, w = thresh.shape
    big  = cv2.resize(thresh, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
    return Image.fromarray(big)


def ocr(img):
    return pytesseract.image_to_string(img, lang="fra", config="--psm 7").strip()


def single_capture():
    bgr = capture()
    img = preprocess(bgr)
    cv2.imwrite("calibration_capture.png", bgr)
    img.save("calibration_thresh.png")
    text = ocr(img)
    print(f"\nTexte OCR : '{text}'")
    if INVENTORY_KEYWORD in text.lower():
        print("✓ DÉTECTÉ — calibration correcte !")
    else:
        print("✗ Non détecté.")
        print("  → Assure-toi que le message est visible dans GTA au moment de la capture.")
        print("  → Ouvre calibration_capture.png pour voir la zone capturée.")


def watch_mode():
    print("Mode surveillance — Ctrl+C pour quitter")
    try:
        while True:
            bgr = capture()
            img = preprocess(bgr)
            text = ocr(img)
            detected = INVENTORY_KEYWORD in text.lower()
            status = "✓ DÉTECTÉ" if detected else "✗ absent  "
            display = text[:40].replace("\n", " ")
            print(f"  {status}  |  '{display}'", end="\r" + " "*80 + "\r")
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nTerminé.")


def live_mouse():
    try:
        import pyautogui
        print("Position de la souris — Ctrl+C pour quitter")
        while True:
            x, y = pyautogui.position()
            print(f"  x={x:4d}  y={y:4d}", end="\r")
            time.sleep(0.05)
    except ImportError:
        print("pyautogui non installé. Installe-le avec: pip install pyautogui")
    except KeyboardInterrupt:
        print("\nTerminé.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "capture":
        single_capture()
    elif cmd == "watch":
        watch_mode()
    else:
        live_mouse()
