@echo off
chcp 65001 >nul
title نظام إدارة طلبات المواد - التشغيل

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║          نظام إدارة طلبات المواد                          ║
echo ║          Material Requests Management System               ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

:: Check if Docker is installed
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

echo [✓] Docker مثبت
echo.

:: Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [خطأ] Docker غير مُشغّل!
    echo.
    echo يرجى تشغيل Docker Desktop والانتظار حتى يكتمل التحميل
    echo.
    pause
    exit /b 1
)

echo [✓] Docker يعمل
echo.

echo جاري تشغيل التطبيق...
echo (قد يستغرق هذا بضع دقائق في المرة الأولى)
echo.

:: Start the application
docker-compose -f docker-compose.windows.yml up -d --build

if errorlevel 1 (
    echo.
    echo [خطأ] فشل في تشغيل التطبيق
    echo.
    pause
    exit /b 1
)

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                    تم التشغيل بنجاح! ✓                     ║
echo ╠════════════════════════════════════════════════════════════╣
echo ║                                                            ║
echo ║  افتح المتصفح على الرابط التالي:                          ║
echo ║                                                            ║
echo ║         http://localhost                                   ║
echo ║                                                            ║
echo ╠════════════════════════════════════════════════════════════╣
echo ║  لإيقاف التطبيق: شغّل stop.bat                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

:: Open browser
timeout /t 3 >nul
start http://localhost

pause
