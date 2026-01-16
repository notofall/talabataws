#!/bin/bash
# ============================================
# سكربت النشر والتحديث - نظام طلبات المواد
# Deploy & Update Script
# ============================================
#
# الاستخدام:
#   ./deploy.sh           - تحديث وإعادة بناء
#   ./deploy.sh start     - تشغيل فقط
#   ./deploy.sh stop      - إيقاف فقط
#   ./deploy.sh restart   - إعادة تشغيل
#   ./deploy.sh logs      - عرض السجلات
#   ./deploy.sh status    - حالة الخدمات
#
# ============================================

set -e

# ألوان للطباعة
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# طباعة ملونة
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# التحقق من وجود Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker غير مثبت!"
        exit 1
    fi
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose غير مثبت!"
        exit 1
    fi
}

# التحقق من ملف .env
check_env() {
    if [ ! -f .env ]; then
        print_warning "ملف .env غير موجود"
        if [ -f .env.example ]; then
            print_info "إنشاء .env من .env.example..."
            cp .env.example .env
            print_success "تم إنشاء .env - يرجى تعديل القيم حسب بيئتك"
        fi
    fi
}

# تحديد أمر docker-compose
get_compose_cmd() {
    if docker compose version &> /dev/null 2>&1; then
        echo "docker compose"
    else
        echo "docker-compose"
    fi
}

COMPOSE_CMD=$(get_compose_cmd)

# الأوامر
start() {
    print_info "تشغيل الخدمات..."
    $COMPOSE_CMD up -d
    print_success "تم تشغيل الخدمات"
    status
}

stop() {
    print_info "إيقاف الخدمات..."
    $COMPOSE_CMD down
    print_success "تم إيقاف الخدمات"
}

restart() {
    print_info "إعادة تشغيل الخدمات..."
    $COMPOSE_CMD restart
    print_success "تم إعادة تشغيل الخدمات"
}

build() {
    print_info "بناء الصور..."
    $COMPOSE_CMD build --no-cache
    print_success "تم بناء الصور"
}

update() {
    print_info "جلب آخر التحديثات من Git..."
    git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || print_warning "فشل جلب التحديثات من Git"
    
    print_info "إعادة بناء وتشغيل الخدمات..."
    $COMPOSE_CMD up -d --build
    
    print_success "تم التحديث بنجاح!"
    status
}

logs() {
    print_info "عرض السجلات (Ctrl+C للخروج)..."
    $COMPOSE_CMD logs -f
}

status() {
    echo ""
    print_info "حالة الخدمات:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    $COMPOSE_CMD ps
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # عرض الروابط
    BACKEND_URL=$(grep BACKEND_URL .env 2>/dev/null | cut -d '=' -f2 || echo "http://localhost:8001")
    FRONTEND_PORT=$(grep FRONTEND_PORT .env 2>/dev/null | cut -d '=' -f2 || echo "3000")
    
    echo ""
    print_info "الروابط:"
    echo "  🌐 الواجهة: http://localhost:$FRONTEND_PORT"
    echo "  🔧 API: $BACKEND_URL"
    echo ""
}

help() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  سكربت النشر - نظام طلبات المواد"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "الاستخدام: ./deploy.sh [أمر]"
    echo ""
    echo "الأوامر:"
    echo "  (بدون أمر)   تحديث كامل (git pull + build + start)"
    echo "  start        تشغيل الخدمات"
    echo "  stop         إيقاف الخدمات"
    echo "  restart      إعادة تشغيل"
    echo "  build        بناء الصور فقط"
    echo "  logs         عرض السجلات"
    echo "  status       حالة الخدمات"
    echo "  help         عرض المساعدة"
    echo ""
}

# التنفيذ الرئيسي
main() {
    check_docker
    check_env
    
    case "${1:-update}" in
        start)   start ;;
        stop)    stop ;;
        restart) restart ;;
        build)   build ;;
        update)  update ;;
        logs)    logs ;;
        status)  status ;;
        help|--help|-h) help ;;
        *)
            print_error "أمر غير معروف: $1"
            help
            exit 1
            ;;
    esac
}

main "$@"
