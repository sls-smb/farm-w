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

Dans PowerShell, depuis le dossier du projet :

```powershell
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --noconfirm --onedir --windowed --name "GTA_Farm_Bot" --collect-all cv2 --collect-all mss --collect-all pytesseract --collect-all keyboard farm_gui.py
```

Puis copie Tesseract à côté de l'exe pour le rendre autonome :

```powershell
xcopy /E /I /Y "C:\Program Files\Tesseract-OCR" "dist\GTA_Farm_Bot\Tesseract-OCR"
```

Résultat dans `dist\GTA_Farm_Bot\`. Tu peux zipper et distribuer tout
le dossier — l'utilisateur final n'a **rien à installer**, il lance
juste `GTA_Farm_Bot.exe`.

### À propos de Tesseract et du .exe

Python et toutes les bibliothèques (OpenCV, mss, numpy...) sont
embarqués dans l'exe. Tesseract est un **programme externe** : le
script de build le copie dans le dossier `Tesseract-OCR\` à côté de
l'exe, et l'application le détecte automatiquement à cet emplacement.
Aucune installation séparée n'est donc requise sur la machine cible.
