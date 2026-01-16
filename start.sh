#!/bin/bash
# ============================================
# سكربت تشغيل نظام إدارة طلبات المواد
# ============================================

# الحصول على IP الخادم تلقائياً
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null)

if [ -z "$SERVER_IP" ]; then
    echo "⚠️ لم يتم العثور على IP الخادم، استخدم localhost"
    SERVER_IP="localhost"
fi

echo "🌐 IP الخادم: $SERVER_IP"

# تصدير المتغير
export SERVER_IP="http://$SERVER_IP:8001"

# تشغيل Docker Compose
docker-compose down
docker-compose up -d --build

echo ""
echo "✅ تم تشغيل التطبيق!"
echo "🔗 افتح: http://$SERVER_IP:3000"
echo ""
