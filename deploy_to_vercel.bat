@echo off
chcp 65001 > nul
echo ========================================================
echo   منظومة الأستاذ NextGen - رفع رفيق المحكمة السحابي إلى Vercel
echo ========================================================
echo.
echo جاري فحص Vercel CLI...
where vercel >nul 2>nul
if %errorlevel% neq 0 (
    echo [تنبيه] لم يتم العثور على أداة vercel مثبتة عالمياً على جهازك.
    echo يمكنك تثبيتها بسهولة عبر تشغيل:
    echo    npm i -g vercel
    echo أو رفع مجلد Al_Oustaz_NextGen_Cloud إلى حسابك على GitHub وربطه بـ Vercel مباشرة.
    echo.
    pause
    exit /b
)

echo.
echo [1/2] تسجيل الدخول والبدء في النشر...
vercel --prod
echo.
echo [2/2] تم الانتهاء بنجاح!
pause
