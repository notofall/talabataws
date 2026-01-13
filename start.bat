@echo off
chcp 65001 >nul
title نظام إدارة طلبات المواد

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║          نظام إدارة طلبات المواد                          ║
echo ║          Material Requests Management System               ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo [خطأ] Docker غير مثبت!
    echo.
    echo يرجى تثبيت Docker Desktop من:
    echo https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)

echo [OK] Docker مثبت
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [خطأ] Docker غير مشغّل!
    echo.
    echo يرجى تشغيل Docker Desktop والانتظار حتى يكتمل التحميل
    echo ثم أعد تشغيل هذا الملف
    echo.
    pause
    exit /b 1
)

echo [OK] Docker يعمل
echo.
echo جاري تشغيل التطبيق...
echo (قد يستغرق 5-10 دقائق في المرة الأولى)
echo.

REM Start the application
docker-compose up -d --build

if errorlevel 1 (
    echo.
    echo [خطأ] فشل في تشغيل التطبيق
    echo جرب تشغيل: docker-compose logs
    echo.
    pause
    exit /b 1
)

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                تم التشغيل بنجاح!                           ║
echo ╠════════════════════════════════════════════════════════════╣
echo ║                                                            ║
echo ║  افتح المتصفح على:                                        ║
echo ║                                                            ║
echo ║      http://localhost:3000                                 ║
echo ║                                                            ║
echo ╠════════════════════════════════════════════════════════════╣
echo ║  لإيقاف التطبيق: شغّل stop.bat                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Wait a moment then open browser
timeout /t 5 >nul
start http://localhost:3000

pause
