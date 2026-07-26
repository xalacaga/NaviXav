@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
title NaviXav

set "VENV=.venv"
set "PY=%VENV%\Scripts\python.exe"

REM La console est passee en UTF-8 (chcp 65001) : Python doit ecrire dans le
REM meme encodage, sinon les accents du panneau ressortent en mojibake.
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

echo.
echo   ==========================================
echo     NaviXav - Completeur de plan de vol IFR
echo   ==========================================
echo.

REM ---------------------------------------------------------------- Python
if exist "%PY%" goto :ready

echo   Premiere execution : installation de l'environnement.
echo.

set "BOOTSTRAP="
py -3 --version >nul 2>&1 && set "BOOTSTRAP=py -3"
if not defined BOOTSTRAP (
  python --version >nul 2>&1 && set "BOOTSTRAP=python"
)
if not defined BOOTSTRAP (
  echo   [ERREUR] Python introuvable.
  echo   Installe Python 3.11 ou plus recent depuis https://www.python.org
  echo   en cochant "Add python.exe to PATH", puis relance ce fichier.
  goto :fail
)

echo   Creation de l'environnement virtuel...
%BOOTSTRAP% -m venv "%VENV%"
if errorlevel 1 (
  echo   [ERREUR] Creation de l'environnement impossible.
  goto :fail
)

echo   Installation des dependances...
"%PY%" -m pip install --quiet --upgrade pip
"%PY%" -m pip install --quiet -e .
if errorlevel 1 (
  echo   [ERREUR] Installation des dependances impossible.
  goto :fail
)
echo   Environnement pret.
echo.

:ready

REM ------------------------------------------------------------ config .env
if not exist ".env" (
  if exist ".env.example" (
    copy /y ".env.example" ".env" >nul
    echo   Fichier .env cree a partir de .env.example.
    echo   Configure ton compte SimBrief depuis le bouton Parametres,
    echo   ou active le mode Demo dans l'application.
    echo.
  )
)

REM ----------------------------------------------------------------- run
echo   Demarrage de l'application NaviXav...
echo   L'interface s'ouvre dans sa propre fenetre.
echo.

"%PY%" -m navixav.desktop %*
set "CODE=%ERRORLEVEL%"

REM Sorties normales : fermeture de la fenetre ou processus interrompu.
if "%CODE%"=="0" goto :done
if "%CODE%"=="-1073741510" goto :done
if "%CODE%"=="-1" goto :done

echo.
echo   [ERREUR] NaviXav s'est arrete avec le code %CODE%.
goto :fail

:done

endlocal
exit /b 0

:fail
echo.
pause
endlocal
exit /b 1
