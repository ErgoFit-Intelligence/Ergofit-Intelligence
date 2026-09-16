@echo off
title Replace ErgoFit Logo
echo.
echo  Replacing logo.png with transparentlogo.png ...
echo.

set "SRC=C:\Users\kriti\AppData\Roaming\Claude\local-agent-mode-sessions\1d5a954b-de11-475f-bc3f-83bbeb97bcbd\7fb099bf-29ba-4982-8a48-e1480ff31e32\local_57f5a66f-b137-4af1-868b-67a0bcc63170\uploads\transparentlogo.png"
set "DST=C:\Users\kriti\Desktop\Claude\Claude Projects\Ergonomic App\logo.png"

if not exist "%SRC%" (
    echo  [ERROR] Source file not found:
    echo  %SRC%
    echo.
    pause
    exit /b
)

copy /Y "%SRC%" "%DST%"

if errorlevel 1 (
    echo.
    echo  [ERROR] Copy failed.
    pause
    exit /b
)

echo.
echo  ============================================
echo   Logo replaced successfully!
echo   You can now delete this .bat file.
echo  ============================================
echo.
pause
