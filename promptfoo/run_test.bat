@echo off
title VerificAI PromptFoo Test Runner
color 0A

echo ========================================
echo   VerificAI PromptFoo Test Runner
echo ========================================
echo.

REM Setup environment
set GEMINI_API_KEY=%GEMINI_API_KEY%
set VERIFICAI_ROOT=C:\Users\gobli\Desktop\verificai

echo [INFO] Environment variables set
echo [INFO] Current directory: %CD%

REM Check for existing PromptFoo
if exist "node_modules\.bin\promptfoo.cmd" (
    echo [INFO] Using local PromptFoo
    set PROMPTFOO_CMD=node_modules\.bin\promptfoo.cmd
) else if exist "%APPDATA%\npm\promptfoo.cmd" (
    echo [INFO] Using global PromptFoo
    set PROMPTFOO_CMD=%APPDATA%\npm\promptfoo.cmd
) else (
    echo [INFO] Using npx (may install first time)
    set PROMPTFOO_CMD="C:\Program Files\nodejs\npx.cmd"
)

echo.
echo [MENU] Choose test:
echo   1. Test titles only (3 tests)
echo   2. Full test suite (12 tests)
echo   3. Custom filter
echo   4. Check configuration only
echo.

set /p choice="Enter choice (1-4): "

if "%choice%"=="1" (
    echo [RUN] Testing titles only...
    set FILTER=--filter-description "Titolo"
) else if "%choice%"=="2" (
    echo [RUN] Full test suite...
    set FILTER=
) else if "%choice%"=="3" (
    set /p custom_filter="Enter filter: "
    echo [RUN] Custom filter: %custom_filter%
    set FILTER=--filter-description "%custom_filter%"
) else if "%choice%"=="4" (
    echo [RUN] Configuration check...
    python test_assertions.py
    python test_provider.py
    pause
    exit /b 0
) else (
    echo [ERROR] Invalid choice
    pause
    exit /b 1
)

echo.
echo [EXEC] %PROMPTFOO_CMD% promptfoo@latest eval -j 1 %FILTER%
echo.

REM Execute test
if "%PROMPTFOO_CMD%"=="\"C:\Program Files\nodejs\npx.cmd\"" (
    %PROMPTFOO_CMD% promptfoo@latest eval -j 1 %FILTER%
) else (
    %PROMPTFOO_CMD% eval -j 1 %FILTER%
)

echo.
echo [DONE] Test completed!
pause
