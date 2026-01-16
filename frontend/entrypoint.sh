#!/bin/sh
# ============================================
# Frontend Entrypoint Script
# يقوم بتحديث Backend URL قبل تشغيل الخادم
# ============================================

set -e

echo "🔧 تهيئة الواجهة الأمامية..."

# استبدال Backend URL في جميع ملفات JS
if [ -n "$REACT_APP_BACKEND_URL" ]; then
    echo "📝 تحديث Backend URL إلى: $REACT_APP_BACKEND_URL"
    
    # استبدال localhost:8001 بالرابط الجديد
    find /app/build -name '*.js' -type f -exec sed -i "s|http://localhost:8001|$REACT_APP_BACKEND_URL|g" {} \;
    
    # استبدال أي روابط قديمة محتملة
    find /app/build -name '*.js' -type f -exec sed -i "s|REACT_APP_BACKEND_URL_PLACEHOLDER|$REACT_APP_BACKEND_URL|g" {} \;
    
    echo "✅ تم تحديث Backend URL بنجاح"
else
    echo "⚠️ لم يتم تحديد REACT_APP_BACKEND_URL - استخدام القيمة الافتراضية"
fi

echo "🚀 تشغيل الخادم..."
exec serve -s build -l 3000
