"""
GTA Seed Farming Bot — Interface graphique
==========================================
Lance avec : python farm_gui.py

- Keybinder : clique sur un bouton de touche puis appuie sur la touche voulue
- Configure : touche utiliser, pause, stop, durées, zone OCR
- Détection du message inventaire plein par OCR (Tesseract)
- Alerte sonore + pause auto quand l'inventaire est plein
"""

import json
import os
import sys
import time
import threading
import random
import ctypes

import tkinter as tk
from tkinter import ttk, messagebox

import winsound
import mss
import numpy as np
import cv2
import pytesseract
from PIL import Image

# ─────────────────────────────────────────────
# CONFIG PERSISTANTE
# ─────────────────────────────────────────────

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    "pickup_key": "e",
    "pause_key": "p",
    "stop_key": "end",
    "pickup_duration": 5.5,
    "between_delay": 0.3,
    "search_enabled": True,
    "search_min": 0.2,
    "search_max": 0.6,
    "region_top": 1065,
    "region_left": 65,
    "region_width": 330,
    "region_height": 40,
    "keyword": "avez pas",
    "start_delay": 5,
}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
# ENVOI DE TOUCHES (scan codes, indépendant AZERTY/QWERTY)
# ─────────────────────────────────────────────

KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP    = 0x0002

# Table nom de touche → scan code physique
SCAN_CODES = {
    "a": 0x1E, "b": 0x30, "c": 0x2E, "d": 0x20, "e": 0x12, "f": 0x21,
    "g": 0x22, "h": 0x23, "i": 0x17, "j": 0x24, "k": 0x25, "l": 0x26,
    "m": 0x32, "n": 0x31, "o": 0x18, "p": 0x19, "q": 0x10, "r": 0x13,
    "s": 0x1F, "t": 0x14, "u": 0x16, "v": 0x2F, "w": 0x11, "x": 0x2D,
    "y": 0x15, "z": 0x2C,
    "0": 0x0B, "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05,
    "5": 0x06, "6": 0x07, "7": 0x08, "8": 0x09, "9": 0x0A,
    "space": 0x39, "enter": 0x1C, "tab": 0x0F, "shift": 0x2A,
    "ctrl": 0x1D, "alt": 0x38, "esc": 0x01,
    "f1": 0x3B, "f2": 0x3C, "f3": 0x3D, "f4": 0x3E, "f5": 0x3F,
    "f6": 0x40, "f7": 0x41, "f8": 0x42, "f9": 0x43, "f10": 0x44,
    "f11": 0x57, "f12": 0x58,
    "up": 0x48, "down": 0x50, "left": 0x4B, "right": 0x4D,
}


def _send_scan(scan_code: int, up: bool = False):
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0)
    ctypes.windll.user32.keybd_event(0, scan_code, flags, 0)


def press_scan(key: str):
    code = SCAN_CODES.get(key.lower())
    if code:
        _send_scan(code)


def release_scan(key: str):
    code = SCAN_CODES.get(key.lower())
    if code:
        _send_scan(code, up=True)


def tap_scan(key: str):
    press_scan(key)
    time.sleep(0.05)
    release_scan(key)


# ─────────────────────────────────────────────
# MOTEUR DU BOT (thread séparé)
# ─────────────────────────────────────────────

class FarmBot:
    def __init__(self, cfg, log_cb, status_cb, alert_cb):
        self.cfg = cfg
        self.log = log_cb
        self.set_status = status_cb
        self.alert = alert_cb
        self.running = False
        self.paused = False
        self._thread = None
        pytesseract.pytesseract.tesseract_cmd = cfg["tesseract_path"]

    # ---- détection OCR ----
    def _capture(self):
        region = {
            "top": self.cfg["region_top"],
            "left": self.cfg["region_left"],
            "width": self.cfg["region_width"],
            "height": self.cfg["region_height"],
        }
        with mss.mss() as sct:
            shot = sct.grab(region)
            arr = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)
            return arr[:, :, :3]

    def _preprocess(self, bgr):
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        inv = cv2.bitwise_not(gray)
        _, thresh = cv2.threshold(inv, 160, 255, cv2.THRESH_BINARY)
        h, w = thresh.shape
        big = cv2.resize(thresh, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
        return Image.fromarray(big)

    def is_inventory_full(self):
        try:
            bgr = self._capture()
            img = self._preprocess(bgr)
            text = pytesseract.image_to_string(img, lang="fra", config="--psm 7").lower()
            return self.cfg["keyword"].lower() in text
        except Exception as e:
            self.log(f"[WARN] OCR : {e}")
            return False

    # ---- contrôle ----
    def start(self):
        if self.running:
            return
        self.running = True
        self.paused = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def toggle_pause(self):
        self.paused = not self.paused
        self.set_status("PAUSE" if self.paused else "EN COURS")
        self.log(f"[BOT] {'Pause' if self.paused else 'Reprise'}")

    def _safe_sleep(self, duration):
        end = time.time() + duration
        while time.time() < end:
            if not self.running:
                return
            time.sleep(0.05)

    def _micro_search(self):
        if not self.cfg["search_enabled"]:
            return
        key = random.choice(["q", "d"])
        duration = random.uniform(self.cfg["search_min"], self.cfg["search_max"])
        press_scan(key)
        self._safe_sleep(duration)
        release_scan(key)

    def _loop(self):
        delay = self.cfg["start_delay"]
        self.log(f"[BOT] Démarrage dans {delay}s — clique sur GTA !")
        for i in range(delay, 0, -1):
            if not self.running:
                return
            self.set_status(f"Démarre dans {i}s...")
            time.sleep(1)

        self.set_status("EN COURS")
        cycle = 0
        while self.running:
            if self.paused:
                time.sleep(0.2)
                continue

            cycle += 1
            self.log(f"[BOT] Cycle #{cycle}")

            if self.is_inventory_full():
                self._trigger_full()
                continue

            tap_scan(self.cfg["pickup_key"])
            self._safe_sleep(self.cfg["pickup_duration"])

            if not self.running:
                break

            if self.is_inventory_full():
                self._trigger_full()
                continue

            if not self.paused and self.running:
                self._micro_search()
                self._safe_sleep(self.cfg["between_delay"])

        self.set_status("ARRÊTÉ")
        self.log("[BOT] Arrêté.")

    def _trigger_full(self):
        self.paused = True
        self.set_status("INVENTAIRE PLEIN !")
        self.log("=" * 40)
        self.log("  !! INVENTAIRE PLEIN !!")
        self.log("  Vide ton inventaire puis reprends.")
        self.log("=" * 40)
        self.alert()


# ─────────────────────────────────────────────
# INTERFACE GRAPHIQUE
# ─────────────────────────────────────────────

class KeyCaptureButton(ttk.Button):
    """Bouton qui capture la prochaine touche pressée quand on clique dessus."""

    def __init__(self, parent, initial_key, on_change):
        super().__init__(parent, text=initial_key.upper(), command=self._start_capture)
        self.key = initial_key
        self.on_change = on_change
        self._capturing = False

    def _start_capture(self):
        self._capturing = True
        self.config(text="Appuie sur une touche...")
        self.bind_all("<Key>", self._on_key)

    def _on_key(self, event):
        if not self._capturing:
            return
        key = event.keysym.lower()
        # Normalise quelques noms tkinter
        mapping = {
            "return": "enter", "escape": "esc", "control_l": "ctrl",
            "control_r": "ctrl", "shift_l": "shift", "shift_r": "shift",
            "alt_l": "alt", "alt_r": "alt", "prior": "pageup", "next": "pagedown",
        }
        key = mapping.get(key, key)
        if key not in SCAN_CODES and key not in ("end", "home", "delete", "pageup", "pagedown"):
            # touche non supportée → ignore
            self.config(text=self.key.upper())
            self._capturing = False
            self.unbind_all("<Key>")
            messagebox.showwarning("Touche non supportée", f"La touche '{key}' n'est pas gérée.")
            return
        self.key = key
        self.config(text=key.upper())
        self._capturing = False
        self.unbind_all("<Key>")
        self.on_change(key)


class FarmGUI:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.bot = None

        root.title("GTA Seed Farming Bot")
        root.geometry("560x640")
        root.resizable(False, False)

        self._build_ui()
        # Écoute globale des touches pause/stop même hors focus
        self._setup_global_hotkeys()

    # ---------- UI ----------
    def _build_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_main = ttk.Frame(nb)
        self.tab_keys = ttk.Frame(nb)
        self.tab_adv = ttk.Frame(nb)
        nb.add(self.tab_main, text="  Contrôle  ")
        nb.add(self.tab_keys, text="  Touches  ")
        nb.add(self.tab_adv, text="  Avancé  ")

        self._build_main_tab()
        self._build_keys_tab()
        self._build_adv_tab()

    def _build_main_tab(self):
        f = self.tab_main

        self.status_var = tk.StringVar(value="PRÊT")
        status_lbl = ttk.Label(f, textvariable=self.status_var,
                               font=("Segoe UI", 16, "bold"), foreground="#2a7")
        status_lbl.pack(pady=(16, 8))

        btns = ttk.Frame(f)
        btns.pack(pady=8)
        self.btn_start = ttk.Button(btns, text="▶ Démarrer", command=self.on_start, width=14)
        self.btn_start.grid(row=0, column=0, padx=4)
        self.btn_pause = ttk.Button(btns, text="⏸ Pause", command=self.on_pause, width=14, state="disabled")
        self.btn_pause.grid(row=0, column=1, padx=4)
        self.btn_stop = ttk.Button(btns, text="⏹ Stop", command=self.on_stop, width=14, state="disabled")
        self.btn_stop.grid(row=0, column=2, padx=4)

        # Log
        ttk.Label(f, text="Journal :").pack(anchor="w", padx=12, pady=(12, 0))
        log_frame = ttk.Frame(f)
        log_frame.pack(fill="both", expand=True, padx=12, pady=4)
        self.log_text = tk.Text(log_frame, height=14, state="disabled", wrap="word",
                                bg="#1e1e1e", fg="#ddd", font=("Consolas", 9))
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _build_keys_tab(self):
        f = self.tab_keys
        ttk.Label(f, text="Clique sur un bouton puis appuie sur la touche désirée.",
                  font=("Segoe UI", 9, "italic")).pack(pady=(12, 16))

        grid = ttk.Frame(f)
        grid.pack()

        self._add_key_row(grid, 0, "Touche Utiliser (ramasser)", "pickup_key")
        self._add_key_row(grid, 1, "Touche Pause / Reprendre", "pause_key")
        self._add_key_row(grid, 2, "Touche Stop (arrêt)", "stop_key")

        ttk.Label(f, text="Note : Pause et Stop fonctionnent même quand GTA a le focus.",
                  font=("Segoe UI", 8), foreground="#888").pack(pady=20)

    def _add_key_row(self, parent, row, label, cfg_key):
        ttk.Label(parent, text=label, width=30, anchor="w").grid(row=row, column=0, padx=8, pady=8, sticky="w")
        btn = KeyCaptureButton(parent, self.cfg[cfg_key],
                               lambda k, ck=cfg_key: self._on_key_change(ck, k))
        btn.config(width=18)
        btn.grid(row=row, column=1, padx=8, pady=8)

    def _on_key_change(self, cfg_key, new_key):
        self.cfg[cfg_key] = new_key
        save_config(self.cfg)
        self._setup_global_hotkeys()
        self.log(f"[CONFIG] {cfg_key} = {new_key.upper()}")

    def _build_adv_tab(self):
        f = self.tab_adv
        grid = ttk.Frame(f)
        grid.pack(pady=12, padx=12, fill="x")

        self.adv_vars = {}

        def add_field(row, label, key, width=10):
            ttk.Label(grid, text=label, anchor="w").grid(row=row, column=0, sticky="w", pady=4)
            var = tk.StringVar(value=str(self.cfg[key]))
            ent = ttk.Entry(grid, textvariable=var, width=width)
            ent.grid(row=row, column=1, sticky="w", padx=8, pady=4)
            self.adv_vars[key] = var

        add_field(0, "Durée animation ramassage (s)", "pickup_duration")
        add_field(1, "Délai entre ramassages (s)", "between_delay")
        add_field(2, "Délai avant démarrage (s)", "start_delay")
        add_field(3, "Mot-clé détection", "keyword", width=20)

        ttk.Separator(grid, orient="horizontal").grid(row=4, column=0, columnspan=2, sticky="ew", pady=10)
        ttk.Label(grid, text="Zone de détection du texte (pixels)",
                  font=("Segoe UI", 9, "bold")).grid(row=5, column=0, columnspan=2, sticky="w")

        add_field(6, "Position X (left)", "region_left")
        add_field(7, "Position Y (top)", "region_top")
        add_field(8, "Largeur (width)", "region_width")
        add_field(9, "Hauteur (height)", "region_height")

        ttk.Separator(grid, orient="horizontal").grid(row=10, column=0, columnspan=2, sticky="ew", pady=10)
        ttk.Label(grid, text="Chemin Tesseract", anchor="w").grid(row=11, column=0, sticky="w", pady=4)
        self.tess_var = tk.StringVar(value=self.cfg["tesseract_path"])
        ttk.Entry(grid, textvariable=self.tess_var, width=40).grid(row=12, column=0, columnspan=2, sticky="w", pady=4)

        self.search_var = tk.BooleanVar(value=self.cfg["search_enabled"])
        ttk.Checkbutton(grid, text="Activer le micro-déplacement entre graines",
                        variable=self.search_var).grid(row=13, column=0, columnspan=2, sticky="w", pady=8)

        ttk.Button(f, text="💾 Enregistrer les réglages", command=self.save_advanced).pack(pady=8)

    def save_advanced(self):
        try:
            self.cfg["pickup_duration"] = float(self.adv_vars["pickup_duration"].get())
            self.cfg["between_delay"]   = float(self.adv_vars["between_delay"].get())
            self.cfg["start_delay"]     = int(float(self.adv_vars["start_delay"].get()))
            self.cfg["keyword"]         = self.adv_vars["keyword"].get()
            self.cfg["region_left"]     = int(self.adv_vars["region_left"].get())
            self.cfg["region_top"]      = int(self.adv_vars["region_top"].get())
            self.cfg["region_width"]    = int(self.adv_vars["region_width"].get())
            self.cfg["region_height"]   = int(self.adv_vars["region_height"].get())
            self.cfg["tesseract_path"]  = self.tess_var.get()
            self.cfg["search_enabled"]  = self.search_var.get()
            save_config(self.cfg)
            self.log("[CONFIG] Réglages enregistrés.")
            messagebox.showinfo("OK", "Réglages enregistrés.")
        except ValueError as e:
            messagebox.showerror("Erreur", f"Valeur invalide : {e}")

    # ---------- hotkeys globaux ----------
    def _setup_global_hotkeys(self):
        try:
            import keyboard as kb
            kb.unhook_all_hotkeys()
            kb.add_hotkey(self.cfg["pause_key"], self._hotkey_pause)
            kb.add_hotkey(self.cfg["stop_key"], self._hotkey_stop)
        except Exception as e:
            self.log(f"[WARN] Hotkeys : {e}")

    def _hotkey_pause(self):
        if self.bot and self.bot.running:
            self.bot.toggle_pause()
            self._refresh_buttons()

    def _hotkey_stop(self):
        if self.bot and self.bot.running:
            self.on_stop()

    # ---------- callbacks bot ----------
    def log(self, msg):
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(0, _append)

    def set_status(self, txt):
        self.root.after(0, lambda: self.status_var.set(txt))

    def alert(self):
        def _beep():
            for freq, dur in [(1200, 300), (900, 300), (1200, 300), (900, 500)]:
                winsound.Beep(freq, dur)
                time.sleep(0.05)
        threading.Thread(target=_beep, daemon=True).start()
        self.root.after(0, self._refresh_buttons)

    # ---------- boutons ----------
    def on_start(self):
        if not os.path.exists(self.cfg["tesseract_path"]):
            messagebox.showerror("Tesseract introuvable",
                                 f"Chemin invalide :\n{self.cfg['tesseract_path']}\n\n"
                                 "Corrige-le dans l'onglet Avancé.")
            return
        self.bot = FarmBot(self.cfg, self.log, self.set_status, self.alert)
        self.bot.start()
        self._refresh_buttons()

    def on_pause(self):
        if self.bot:
            self.bot.toggle_pause()
            self._refresh_buttons()

    def on_stop(self):
        if self.bot:
            self.bot.stop()
        self.root.after(300, self._refresh_buttons)

    def _refresh_buttons(self):
        running = self.bot and self.bot.running
        self.btn_start.config(state="disabled" if running else "normal")
        self.btn_pause.config(state="normal" if running else "disabled")
        self.btn_stop.config(state="normal" if running else "disabled")
        if self.bot:
            self.btn_pause.config(text="▶ Reprendre" if self.bot.paused else "⏸ Pause")


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass
    app = FarmGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
