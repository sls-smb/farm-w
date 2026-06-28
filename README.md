# GTA Seed Farming Bot

Bot de farming automatique de graines (FiveM / GTA RP).
Appuie sur la touche **Utiliser** en boucle, détecte le message
*« Vous n'avez pas assez de place »* par OCR et alerte avec un son
quand l'inventaire est plein.

## Lancement (mode développeur)

```powershell
pip install -r requirements.txt
python farm_gui.py
```

Nécessite **Tesseract OCR** installé avec le pack de langue français :
https://github.com/UB-Mannheim/tesseract/wiki

## Interface

- **Onglet Contrôle** : Démarrer / Pause / Stop + journal en temps réel
- **Onglet Touches** : keybinder — clique sur un bouton puis appuie sur
  la touche voulue (touche Utiliser, Pause, Stop)

Les réglages sont sauvegardés dans `config.json`.

## Compiler en .exe autonome

```powershell
pip install -r requirements.txt
pip install pyinstaller
```

### Option A — Un seul fichier .exe (tout-en-un, Tesseract inclus)

```powershell
pyinstaller --noconfirm --onefile --windowed --name "GTA_Farm_Bot" --collect-all cv2 --collect-all mss --collect-all pytesseract --collect-all keyboard --add-data "C:\Program Files\Tesseract-OCR;Tesseract-OCR" farm_gui.py
```

Résultat : **un unique `dist\GTA_Farm_Bot.exe`** contenant Python, toutes
les bibliothèques ET Tesseract. Rien à installer, rien à copier.
L'utilisateur double-clique sur l'exe, point.

> Note : au lancement, l'exe décompresse son contenu dans un dossier
> temporaire (quelques secondes au premier démarrage). C'est normal
> pour le mode tout-en-un.

### Option B — Dossier (démarrage plus rapide)

```powershell
pyinstaller --noconfirm --onedir --windowed --name "GTA_Farm_Bot" --collect-all cv2 --collect-all mss --collect-all pytesseract --collect-all keyboard farm_gui.py
xcopy /E /I /Y "C:\Program Files\Tesseract-OCR" "dist\GTA_Farm_Bot\Tesseract-OCR"
```

Résultat dans `dist\GTA_Farm_Bot\` (dossier à zipper). Démarre plus vite
mais c'est un dossier complet au lieu d'un seul fichier.

### À propos de Tesseract et du .exe

Python et toutes les bibliothèques (OpenCV, mss, numpy...) sont
embarqués dans l'exe. Tesseract est un **programme externe** : le
script de build le copie dans le dossier `Tesseract-OCR\` à côté de
l'exe, et l'application le détecte automatiquement à cet emplacement.
Aucune installation séparée n'est donc requise sur la machine cible.
