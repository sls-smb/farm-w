# Intégrer le Bot de Farming dans l'app sls-smb

Le bot est désormais exposé comme un **Frame tkinter embarquable**
(`FarmBotFrame`), prêt à devenir un onglet de l'app principale.

## 1. Copier les fichiers dans l'app

Copie dans un sous-dossier de l'app (ex : `features/farm_bot/`) :

- `farm_gui.py`   → contient `FarmBotFrame` (l'UI) et `FarmBot` (le moteur)

Ajoute les dépendances de `requirements.txt` à celles de l'app :
`mss`, `opencv-python`, `numpy`, `keyboard`, `pytesseract`, `Pillow`,
`pyautogui`.

## 2. Ajouter l'onglet (gated par la licence)

Dans le code qui construit le `Notebook` principal de l'app :

```python
from features.farm_bot.farm_gui import FarmBotFrame

# ... après vérification de la licence ...
if license_valid:                      # ta logique de licence existante
    farm_tab = FarmBotFrame(main_notebook)
    main_notebook.add(farm_tab, text="Farm Bot")
```

Si la feature doit être réservée à certaines licences :

```python
if license_has_feature("farm_bot"):
    main_notebook.add(FarmBotFrame(main_notebook), text="Farm Bot")
```

## 3. Libérer les ressources à la fermeture

Le bot installe des raccourcis clavier globaux (pause/stop) et un thread.
Appelle `shutdown()` quand l'app se ferme ou quand l'onglet est retiré :

```python
def on_app_close():
    farm_tab.shutdown()   # arrête le bot + libère les hotkeys
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_app_close)
```

> `FarmBotFrame` appelle aussi `shutdown()` automatiquement quand il est
> détruit (`<Destroy>`), mais l'appel explicite reste recommandé.

## 4. Compilation

Les besoins de build (PyInstaller + Tesseract embarqué) sont déjà gérés
par le code : `resolve_tesseract()` détecte Tesseract en mode `--onefile`
(`sys._MEIPASS`), `--onedir`, ou installé. Reprends les options
`--add-data "...Tesseract-OCR;Tesseract-OCR"` et `--collect-all` du
README dans le build de l'app principale.

## Notes

- Le fichier `config.json` du bot est créé à côté de l'exe de l'app.
  Si l'app a déjà sa propre config, le bot garde la sienne séparée — pas
  de conflit.
- Les hotkeys globaux (pause/stop) utilisent la lib `keyboard`, qui
  nécessite les droits administrateur sur certaines machines pour
  capturer les touches hors focus. À tester selon ton contexte.
```
