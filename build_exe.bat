@echo off
REM ============================================================
REM  Compilation du bot en un .exe autonome (Windows)
REM  A lancer dans le dossier du projet : double-clic ou
REM  depuis PowerShell :  .\build_exe.bat
REM ============================================================

echo.
echo === Installation de PyInstaller et des dependances ===
pip install -r requirements.txt
pip install pyinstaller

echo.
echo === Compilation de l'exe ===
REM --onedir : cree un dossier (plus rapide a lancer, permet d'embarquer Tesseract)
REM --windowed : pas de console noire derriere l'interface
pyinstaller --noconfirm --onedir --windowed ^
    --name "GTA_Farm_Bot" ^
    --collect-all cv2 ^
    --collect-all mss ^
    --collect-all pytesseract ^
    --collect-all keyboard ^
    farm_gui.py

echo.
echo === Copie de Tesseract dans le dossier de l'exe ===
REM Embarque Tesseract pour que l'utilisateur final n'ait RIEN a installer.
REM Adapte le chemin source si ton Tesseract est ailleurs.
set TESS_SRC=C:\Program Files\Tesseract-OCR
set DEST=dist\GTA_Farm_Bot\Tesseract-OCR

if exist "%TESS_SRC%" (
    echo Copie de %TESS_SRC% ...
    xcopy /E /I /Y "%TESS_SRC%" "%DEST%" >nul
    echo Tesseract embarque avec succes.
) else (
    echo ATTENTION : Tesseract introuvable dans %TESS_SRC%
    echo L'exe fonctionnera seulement si Tesseract est installe sur la machine.
)

echo.
echo ============================================================
echo  TERMINE !
echo  L'application se trouve dans :  dist\GTA_Farm_Bot\
echo  Lance :  dist\GTA_Farm_Bot\GTA_Farm_Bot.exe
echo  Tu peux zipper et distribuer tout le dossier GTA_Farm_Bot.
echo ============================================================
pause
