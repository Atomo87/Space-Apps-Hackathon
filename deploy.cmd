@echo off
rem Envia para a Hostinger o que mudou desde o ultimo deploy.
rem Opcoes: -DryRun -Yes -SkipTests -SkipBuild -Seed Classe -Baseline
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\deploy.ps1" %*
