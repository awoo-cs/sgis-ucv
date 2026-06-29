@echo off
REM Lanza el kit de demo del SGIS-UCV con la politica de ejecucion correcta.
REM (Doble clic en este archivo. No requiere instalar nada para Atacante/Operador.)
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0Launcher.ps1"
