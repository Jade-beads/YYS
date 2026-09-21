@echo off
chcp 65001 >nul
rem 在 Windows 上一键打包 YYS.exe。需要先装好 Python 3.12(安装时勾选 Add python.exe to PATH)。
rem 用法:把整个项目文件夹拷到 Windows,双击本文件。产物在 dist\YYS.exe。

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 没找到 python。请先安装 Python 3.12: https://www.python.org/downloads/windows/
  pause
  exit /b 1
)

if not exist .venv-win (
  echo [1/3] 创建虚拟环境 .venv-win ...
  python -m venv .venv-win || goto :fail
)

echo [2/3] 安装依赖(首次约 200MB)...
.venv-win\Scripts\python -m pip install --upgrade pip >nul
.venv-win\Scripts\pip install -r requirements.txt pyinstaller || goto :fail

echo [3/3] 打包 ...
.venv-win\Scripts\pyinstaller --noconfirm YYS_win.spec || goto :fail

copy /y release\config.ini dist\config.ini >nul
copy /y "release\使用说明.txt" "dist\使用说明.txt" >nul
echo.
echo 完成: %cd%\dist\YYS.exe
echo 把 dist 文件夹里的三个文件一起拷走即可(YYS.exe / config.ini / 使用说明.txt)。
pause
exit /b 0

:fail
echo.
echo [失败] 上面有报错信息,请把它发给我。
pause
exit /b 1
