@echo off
title 一键恢复文件后缀及隐藏文件夹
echo 按任意键来恢复
pause
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced /v Hidden /t REG_DWORD /d 1 /f
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced /v HideFileExt /t REG_DWORD /d 0 /f
echo 设置完毕，按下F5刷新
pause