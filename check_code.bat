@echo off
setlocal
chcp 65001 >nul
color 0A
title Prometheus Core: Проверка кода

goto :start

:: ==========================================
:: СТИЛИЗОВАННЫЙ ЗАГОЛОВОК
:: ==========================================
:header
cls
echo.
echo  ==============================================================
echo.
echo     ######  ######   ###   #   # ###### ##### #   # ######  #### 
echo     #     # #     # #   #  ## ## #      #      #   # #      #     
echo     ######  ######  #   #  # # # #####  ####   #####  #####   ### 
echo     #       #   #   #   #  #   # #      #      #   # #          # 
echo     #       #    #   ###   #   # ###### ##### #   # ###### ####  
echo.
echo  ==============================================================
echo.
goto :eof

:: ==========================================
:: ЧЕЛОВЕЧЕК (успех)
:: ==========================================
:person_ok
echo.
echo           .-""""-.
echo          /  ^   ^  \
echo         ^|    ^     ^|
echo         ^|   '-'    ^|
echo          \        /
echo           '-....-'
echo           /^|    ^|^\
echo          / ^|    ^| ^\
echo            ^|    ^|
echo           /      \
echo          /        \
echo.
goto :eof

:: ==========================================
:: ЧЕЛОВЕЧЕК (ошибка)
:: ==========================================
:person_fail
echo.
echo           .-""""-.
echo          /  x   x  \
echo         ^|    ^     ^|
echo         ^|   'o'    ^|
echo          \        /
echo           '-....-'
echo           /^|    ^|^\
echo          / ^|    ^| ^\
echo            ^|    ^|
echo           /      \
echo          /        \
echo.
goto :eof

:: ==========================================
:: ЗАПУСК
:: ==========================================
:start
where python >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Python не найден в PATH!
    pause
    exit /b 1
)

:: АНИМАЦИЯ ЗЕМЛИ (1 ОБОРОТ)
call :earth_pass

:: --- ПРОВЕРКИ ---
call :header
echo [1/5] Проверка синтаксиса Python...
for %%f in (app.py physics.py update_materials.py check_consistency.py) do (
    python -m py_compile %%f
    if errorlevel 1 goto error
)
echo   Синтаксис в порядке.
echo.

echo [2/5] Проверка наличия файлов данных...
if not exist "data\materials.json" (echo   [НЕТ] data\materials.json & goto error)
if not exist "data\isotopes.json"  (echo   [НЕТ] data\isotopes.json  & goto error)
echo   Файлы на месте.
echo.

echo [3/5] Проверка JSON-файлов...
python -c "import json; json.load(open('data/materials.json', encoding='utf-8')); json.load(open('data/isotopes.json', encoding='utf-8')); print('  JSON валиден.')"
if errorlevel 1 goto error
echo.

echo [4/5] Проверка согласованности сечений...
python check_consistency.py
if errorlevel 1 goto error
echo.

echo [5/5] Проверка импорта модулей...
python -c "import numpy, matplotlib, numba, PySide6; print('  Зависимости OK.')"
if errorlevel 1 goto error
python -c "import physics; print('  physics.py OK.')"
if errorlevel 1 goto error
python -c "import app; print('  app.py OK.')"
if errorlevel 1 goto error
echo.

:: --- УСПЕХ ---
call :header
call :person_ok
echo ====================================================
echo   ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Код готов к сборке.
echo ====================================================
echo.
pause
exit /b 0

:error
call :header
call :person_fail
echo ====================================================
echo   ПРОВЕРКА НЕ ПРОЙДЕНА. Исправьте ошибки.
echo ====================================================
echo.
pause
exit /b 1

:: ==========================================
:: ЗЕМЛЯ (12 КАДРОВ, 1 ОБОРОТ)
:: ==========================================
:earth_pass
call :header
echo.
echo               .-+ooo+/-.
echo           .:+oyhhhhhhhyo+:.
echo         -oyhhhyso+++osyhhhyo-
echo       :shhhyo/.        ./+ohhhs:
echo      +hhho/                /+ohhh+
echo    .shh+:                    :+hhs.
echo   .yhho-                      -ohhy.
echo   +hh+                          +hh+
echo  /hho.                          .ohh/
echo  .yh+      .+oooo+.              +hy.
echo  +hy      /hhhhhhhh+             .yh+
echo  .yh.    /hhhhhhhhhh+             hy.
echo   /hy.   :hhhhhhhhyh/           .yh/
echo    +hh+   +hhhhhhhh/           +hh+
echo    .yhho-  :hhhhhh+          -ohhy.
echo     .shh+:                  :+hhs.
echo       +hhho/.            ./+ohhh+
echo        :shhhyso+++++osyhhhhyo-
echo          -oyhhhhhhhhhhhyo-
echo            .:+osyhyo+:.
echo               .-+oo+-.
choice /c x /t 1 /d x >nul

call :header
echo.
echo               .-+ooo+/-.
echo           .:+oyhhhhhhhyo+:.
echo         -oyhhhyso+++osyhhhyo-
echo       :shhhyo/.        ./+ohhhs:
echo      +hhho/                /+ohhh+
echo    .shh+:                    :+hhs.
echo   .yhho-                      -ohhy.
echo   +hh+                          +hh+
echo  /hho.        .+oooo+.          .ohh/
echo  .yh+        /hhhhhhhh+          +hy.
echo  +hy        /hhhhhhhhhh+         .yh+
echo  .yh.      :hhhhhhhhyh/           hy.
echo   /hy.      +hhhhhhhh/          .yh/
echo    +hh+      :hhhhhh+          +hh+
echo    .yhho-     .+oo+.          -ohhy.
echo     .shh+:                  :+hhs.
echo       +hhho/.            ./+ohhh+
echo        :shhhyso+++++osyhhhhyo-
echo          -oyhhhhhhhhhhhyo-
echo            .:+osyhyo+:.
echo               .-+oo+-.
choice /c x /t 1 /d x >nul

call :header
echo.
echo               .-+ooo+/-.
echo           .:+oyhhhhhhhyo+:.
echo         -oyhhhyso+++osyhhhyo-
echo       :shhhyo/.        ./+ohhhs:
echo      +hhho/                /+ohhh+
echo    .shh+:                    :+hhs.
echo   .yhho-                      -ohhy.
echo   +hh+                          +hh+
echo  /hho.               .+oooo+.    .ohh/
echo  .yh+               /hhhhhhhh+    +hy.
echo  +hy               /hhhhhhhhhh+   .yh+
echo  .yh.             :hhhhhhhhyh/     hy.
echo   /hy.            +hhhhhhhh/    .yh/
echo    +hh+            :hhhhhh+    +hh+
echo    .yhho-           .+oo+.    -ohhy.
echo     .shh+:                  :+hhs.
echo       +hhho/.            ./+ohhh+
echo        :shhhyso+++++osyhhhhyo-
echo          -oyhhhhhhhhhhhyo-
echo            .:+osyhyo+:.
echo               .-+oo+-.
choice /c x /t 1 /d x >nul

call :header
echo.
echo               .-+ooo+/-.
echo           .:+oyhhhhhhhyo+:.
echo         -oyhhhyso+++osyhhhyo-
echo       :shhhyo/.        ./+ohhhs:
echo      +hhho/                /+ohhh+
echo    .shh+:      .+oooo+.      :+hhs.
echo   .yhho-      /hhhhhhhh+      -ohhy.
echo   +hh+       /hhhhhhhhhh+      +hh+
echo  /hho.      :hhhhhhhhyh/        .ohh/
echo  .yh+        +hhhhhhhh/          +hy.
echo  +hy          :hhhhhh+           .yh+
echo  .yh.          .+oo+.             hy.
echo   /hy.                           .yh/
echo    +hh+                         +hh+
echo    .yhho-                     -ohhy.
echo     .shh+:                  :+hhs.
echo       +hhho/.            ./+ohhh+
echo        :shhhyso+++++osyhhhhyo-
echo          -oyhhhhhhhhhhhyo-
echo            .:+osyhyo+:.
echo               .-+oo+-.
choice /c x /t 1 /d x >nul

call :header
echo.
echo               .-+ooo+/-.
echo           .:+oyhhhhhhhyo+:.
echo         -oyhhhyso+++osyhhhyo-
echo       :shhhyo/.        ./+ohhhs:
echo      +hhho/       .+oooo+.  /+ohhh+
echo    .shh+:        /hhhhhhhh+   :+hhs.
echo   .yhho-        /hhhhhhhhhh+   -ohhy.
echo   +hh+         :hhhhhhhhyh/     +hh+
echo  /hho.          +hhhhhhhh/       .ohh/
echo  .yh+            :hhhhhh+         +hy.
echo  +hy              .+oo+.          .yh+
echo  .yh.                              hy.
echo   /hy.                            .yh/
echo    +hh+                          +hh+
echo    .yhho-                      -ohhy.
echo     .shh+:                  :+hhs.
echo       +hhho/.            ./+ohhh+
echo        :shhhyso+++++osyhhhhyo-
echo          -oyhhhhhhhhhhhyo-
echo            .:+osyhyo+:.
echo               .-+oo+-.
choice /c x /t 1 /d x >nul

call :header
echo.
echo               .-+ooo+/-.
echo           .:+oyhhhhhhhyo+:.
echo         -oyhhhyso+++osyhhhyo-
echo       :shhhyo/  .+oooo+.  ./+ohhhs:
echo      +hhho/    /hhhhhhhh+    /+ohhh+
echo    .shh+:     /hhhhhhhhhh+    :+hhs.
echo   .yhho-     :hhhhhhhhyh/      -ohhy.
echo   +hh+       +hhhhhhhh/         +hh+
echo  /hho.        :hhhhhh+           .ohh/
echo  .yh+          .+oo+.             +hy.
echo  +hy                               .yh+
echo  .yh.                               hy.
echo   /hy.                             .yh/
echo    +hh+                           +hh+
echo    .yhho-                       -ohhy.
echo     .shh+:                    :+hhs.
echo       +hhho/.              ./+ohhh+
echo        :shhhyso+++++++osyhhhhyo-
echo          -oyhhhhhhhhhhhhhyo-
echo            .:+osyhyhyo+:.
echo               .-+oooo+-.
choice /c x /t 1 /d x >nul

call :header
echo.
echo               .-+ooo+/-.
echo           .:+oyhhhhhhhyo+:.
echo         -oyhhhyso+++osyhhhyo-
echo       :shhhyo/.        ./+ohhhs:
echo      +hhho/                /+ohhh+
echo    .shh+:                    :+hhs.
echo   .yhho-       .+oooo+.       -ohhy.
echo   +hh+        /hhhhhhhh+       +hh+
echo  /hho.       /hhhhhhhhhh+       .ohh/
echo  .yh+       :hhhhhhhhyh/         +hy.
echo  +hy         +hhhhhhhh/          .yh+
echo  .yh.         :hhhhhh+            hy.
echo   /hy.          .+oo+.           .yh/
echo    +hh+                          +hh+
echo    .yhho-                      -ohhy.
echo     .shh+:                  :+hhs.
echo       +hhho/.            ./+ohhh+
echo        :shhhyso+++++osyhhhhyo-
echo          -oyhhhhhhhhhhhyo-
echo            .:+osyhyo+:.
echo               .-+oo+-.
choice /c x /t 1 /d x >nul

call :header
echo.
echo               .-+ooo+/-.
echo           .:+oyhhhhhhhyo+:.
echo         -oyhhhyso+++osyhhhyo-
echo       :shhhyo/.        ./+ohhhs:
echo      +hhho/                /+ohhh+
echo    .shh+:                    :+hhs.
echo   .yhho-                      -ohhy.
echo   +hh+                          +hh+
echo  /hho.                          .ohh/
echo  .yh+          .+oooo+.          +hy.
echo  +hy          /hhhhhhhh+         .yh+
echo  .yh.        /hhhhhhhhhh+         hy.
echo   /hy.       :hhhhhhhhyh/        .yh/
echo    +hh+       +hhhhhhhh/        +hh+
echo    .yhho-      :hhhhhh+        -ohhy.
echo     .shh+:       .+oo+.       :+hhs.
echo       +hhho/.            ./+ohhh+
echo        :shhhyso+++++osyhhhhyo-
echo          -oyhhhhhhhhhhhyo-
echo            .:+osyhyo+:.
echo               .-+oo+-.
choice /c x /t 1 /d x >nul

call :header
echo.
echo               .-+ooo+/-.
echo           .:+oyhhhhhhhyo+:.
echo         -oyhhhyso+++osyhhhyo-
echo       :shhhyo/.        ./+ohhhs:
echo      +hhho/                /+ohhh+
echo    .shh+:                    :+hhs.
echo   .yhho-                      -ohhy.
echo   +hh+                          +hh+
echo  /hho.                          .ohh/
echo  .yh+                           +hy.
echo  +hy           .+oooo+.         .yh+
echo  .yh.         /hhhhhhhh+          hy.
echo   /hy.       /hhhhhhhhhh+        .yh/
echo    +hh+      :hhhhhhhhyh/        +hh+
echo    .yhho-     +hhhhhhhh/       -ohhy.
echo     .shh+:     :hhhhhh+       :+hhs.
echo       +hhho/.    .+oo+.     ./+ohhh+
echo        :shhhyso+++++++osyhhhhyo-
echo          -oyhhhhhhhhhhhhhyo-
echo            .:+osyhyhyo+:.
echo               .-+oooo+-.
choice /c x /t 1 /d x >nul

call :header
echo.
echo               .-+ooo+/-.
echo           .:+oyhhhhhhhyo+:.
echo         -oyhhhyso+++osyhhhyo-
echo       :shhhyo/.        ./+ohhhs:
echo      +hhho/                /+ohhh+
echo    .shh+:                    :+hhs.
echo   .yhho-                      -ohhy.
echo   +hh+                          +hh+
echo  /hho.                          .ohh/
echo  .yh+                           +hy.
echo  +hy                            .yh+
echo  .yh.                            hy.
echo   /hy.                          .yh/
echo    +hh+         .+oooo+.        +hh+
echo    .yhho-      /hhhhhhhh+      -ohhy.
echo     .shh+:    /hhhhhhhhhh+    :+hhs.
echo       +hhho/. :hhhhhhhhyh/ ./+ohhh+
echo        :shhhyso+hhhhhhhh/osyhhhhyo-
echo          -oyhhhhhhhhhhhhhhhyo-
echo            .:+osyhyhyhyo+:.
echo               .-+ooooo+-.
choice /c x /t 1 /d x >nul

call :header
echo.
echo               .-+ooo+/-.
echo           .:+oyhhhhhhhyo+:.
echo         -oyhhhyso+++osyhhhyo-
echo       :shhhyo/.        ./+ohhhs:
echo      +hhho/                /+ohhh+
echo    .shh+:                    :+hhs.
echo   .yhho-      .+oooo+.        -ohhy.
echo   +hh+       /hhhhhhhh+        +hh+
echo  /hho.      /hhhhhhhhhh+        .ohh/
echo  .yh+      :hhhhhhhhyh/          +hy.
echo  +hy        +hhhhhhhh/           .yh+
echo  .yh.        :hhhhhh+             hy.
echo   /hy.         .+oo+.            .yh/
echo    +hh+                          +hh+
echo    .yhho-                      -ohhy.
echo     .shh+:                  :+hhs.
echo       +hhho/.            ./+ohhh+
echo        :shhhyso+++++osyhhhhyo-
echo          -oyhhhhhhhhhhhyo-
echo            .:+osyhyo+:.
echo               .-+oo+-.
choice /c x /t 1 /d x >nul
goto :eof