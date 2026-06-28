"""
Outil de calibration — Lance AVANT le bot.

  python calibrate.py          → affiche la position de la souris
  python calibrate.py capture  → teste la détection de la notification Unity RP
  python calibrate.py watch    → surveille en temps réel (affiche si notif détectée)
"""

import sys
import time
import numpy as np
import cv2
import mss

# Doit correspondre à farm_bot.py
NOTIF_REGION = {
    "top": 990,
    "left": 60,
    "width": 380,
    "height": 110,
}

RED_MIN = np.array([0,  0,  150], dtype=np.uint8)
RED_MAX = np.array([80, 80, 255], dtype=np.uint8)
RED_PIXEL_THRESHOLD = 30


def capture_region():
    with mss.mss() as sct:
        shot = sct.grab(NOTIF_REGION)
        arr = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)
        return arr[:, :, :3]


def check_notif():
    bgr = capture_region()
    mask = cv2.inRange(bgr, RED_MIN, RED_MAX)
    count = cv2.countNonZero(mask)
    return count, count >= RED_PIXEL_THRESHOLD


def live_mouse():
    import pyautogui
    print("Position de la souris — Ctrl+C pour quitter")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"  x={x:4d}  y={y:4d}", end="\r")
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nTerminé.")


def single_capture():
    bgr = capture_region()
    count, detected = check_notif()

    # Sauvegarde l'image avec les pixels rouges surlignés
    from PIL import Image
    mask = cv2.inRange(bgr, RED_MIN, RED_MAX)
    highlighted = bgr.copy()
    highlighted[mask > 0] = [0, 255, 0]  # colorie les pixels détectés en vert
    cv2.imwrite("calibration_capture.png", bgr)
    cv2.imwrite("calibration_highlight.png", highlighted)

    print(f"\nPixels rouges détectés : {count} (seuil : {RED_PIXEL_THRESHOLD})")
    print("→ Image brute : calibration_capture.png")
    print("→ Pixels détectés surlignés en vert : calibration_highlight.png")

    if detected:
        print("\n✓ Notification Unity RP DÉTECTÉE — calibration correcte !")
    else:
        print("\n✗ Non détecté.")
        print("  → Assure-toi que le message est visible dans GTA au moment de la capture.")
        print(f"  → Pixels trouvés : {count} (minimum requis : {RED_PIXEL_THRESHOLD})")
        if count > 5:
            print(f"  → Essaie de baisser RED_PIXEL_THRESHOLD à {count} dans farm_bot.py et calibrate.py")


def watch_mode():
    print("Mode surveillance — Ctrl+C pour quitter")
    print("Déclenche le message dans GTA pour tester la détection en temps réel.\n")
    try:
        while True:
            count, detected = check_notif()
            status = "✓ DÉTECTÉ" if detected else "✗ absent  "
            print(f"  {status}  (pixels rouges : {count:4d})", end="\r")
            time.sleep(0.2)
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
