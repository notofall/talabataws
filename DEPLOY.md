# ============================================
# دليل النشر على الخادم (Deployment Guide)
# ============================================

## 📋 متطلبات الخادم
- Ubuntu 20.04+ أو أي توزيعة Linux
- Docker و Docker Compose
- 2GB RAM على الأقل

## 🚀 التثبيت لأول مرة

### 1. استنسخ المشروع:
```bash
git clone https://github.com/YOUR_REPO/talabat.git
cd talabat
```

### 2. شغّل التطبيق:
```bash
chmod +x start.sh
./start.sh
```

**أو يدوياً:**
```bash
# احصل على IP الخادم
export SERVER_IP="http://$(curl -s ifconfig.me):8001"

# شغّل
docker-compose up -d --build
```

### 3. افتح في المتصفح:
```
http://[IP_الخادم]:3000
```

---

## 🔄 التحديث

```bash
cd ~/talabat
git pull origin main
./start.sh
```

**البيانات محفوظة في:**
- `./postgres_data/` - قاعدة البيانات
- `./backend/data/` - إعدادات التطبيق

---

## 👤 إنشاء مستخدم Admin يدوياً

```bash
docker exec -it talabat_db psql -U admin -d talabat_db -c "
INSERT INTO users (id, name, email, password, role, is_active, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  'مدير النظام',
  'admin@system.com',
  '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G4WxJnqLxWCJmK',
  'system_admin',
  true,
  NOW(),
  NOW()
) ON CONFLICT (email) DO NOTHING;
"
```

**بيانات الدخول:**
- البريد: admin@system.com
- كلمة المرور: 123456

---

## 🛠️ أوامر مفيدة

```bash
# حالة الخدمات
docker-compose ps

# سجلات Backend
docker logs talabat_backend --tail=50

# دخول قاعدة البيانات
docker exec -it talabat_db psql -U admin -d talabat_db

# إعادة تشغيل
docker-compose restart

# إيقاف
docker-compose down
```
