#!/bin/bash
#
# سكربت تحديث نظام إدارة طلبات المواد
# Material Requests System Update Script
#
# الاستخدام: ./update.sh
#

set -e

# ألوان للطباعة
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       نظام إدارة طلبات المواد - تحديث النظام              ║${NC}"
echo -e "${BLUE}║       Material Requests System - Update Script            ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# التحقق من وجود Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker غير مثبت. يرجى تثبيت Docker أولاً.${NC}"
    exit 1
fi

# التحقق من وجود docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose غير مثبت. يرجى تثبيت Docker Compose أولاً.${NC}"
    exit 1
fi

# الحصول على المسار الحالي
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# التحقق من وجود ملف docker-compose.prod.yml
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}❌ لم يتم العثور على ملف docker-compose${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 معلومات التحديث:${NC}"
echo -e "   المسار: $PROJECT_DIR"
echo -e "   ملف Docker: $COMPOSE_FILE"
echo ""

# عرض الإصدار الحالي
echo -e "${YELLOW}📌 الإصدار الحالي:${NC}"
docker images | grep -E "material|backend|frontend" | head -5 || echo "   لا توجد صور محلية"
echo ""

# تأكيد التحديث
read -p "هل تريد المتابعة مع التحديث؟ (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠️ تم إلغاء التحديث${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}🔄 الخطوة 1/4: إنشاء نسخة احتياطية من قاعدة البيانات...${NC}"
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
docker exec material_requests_db pg_dump -U app_user material_requests > "$PROJECT_DIR/$BACKUP_FILE" 2>/dev/null || echo -e "${YELLOW}   ⚠️ لم يتم إنشاء نسخة احتياطية (قد تكون قاعدة البيانات خارجية)${NC}"
if [ -f "$PROJECT_DIR/$BACKUP_FILE" ]; then
    echo -e "${GREEN}   ✅ تم إنشاء نسخة احتياطية: $BACKUP_FILE${NC}"
fi

echo ""
echo -e "${BLUE}🔄 الخطوة 2/4: تحميل الصور الجديدة...${NC}"
cd "$PROJECT_DIR"
docker-compose -f "$COMPOSE_FILE" pull
echo -e "${GREEN}   ✅ تم تحميل الصور الجديدة${NC}"

echo ""
echo -e "${BLUE}🔄 الخطوة 3/4: إيقاف الخدمات الحالية...${NC}"
docker-compose -f "$COMPOSE_FILE" down
echo -e "${GREEN}   ✅ تم إيقاف الخدمات${NC}"

echo ""
echo -e "${BLUE}🔄 الخطوة 4/4: تشغيل الخدمات بالإصدار الجديد...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d
echo -e "${GREEN}   ✅ تم تشغيل الخدمات${NC}"

echo ""
echo -e "${BLUE}⏳ انتظار بدء الخدمات...${NC}"
sleep 10

# التحقق من حالة الخدمات
echo ""
echo -e "${BLUE}📊 حالة الخدمات:${NC}"
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ تم التحديث بنجاح!                         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📝 ملاحظات:${NC}"
echo -e "   - النسخة الاحتياطية: $BACKUP_FILE"
echo -e "   - للتراجع: docker-compose -f $COMPOSE_FILE down && استعادة النسخة الاحتياطية"
echo -e "   - لعرض السجلات: docker-compose -f $COMPOSE_FILE logs -f"
echo ""
