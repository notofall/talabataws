# دليل التحديث - نظام إدارة طلبات المواد
# Update Guide - Material Requests System

## 📋 المتطلبات

قبل البدء، تأكد من توفر:
- حساب GitHub
- Docker و Docker Compose مثبتين على الخادم
- صلاحيات الوصول إلى GitHub Container Registry

---

## 🚀 الإعداد الأولي (مرة واحدة)

### 1. رفع المشروع إلى GitHub

```bash
# إنشاء مستودع جديد على GitHub
# ثم:
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO_NAME.git
git push -u origin main
```

### 2. تفعيل GitHub Actions

بمجرد رفع الكود، سيقوم GitHub Actions تلقائياً بـ:
- بناء صور Docker للـ Backend والـ Frontend
- رفعها إلى GitHub Container Registry (ghcr.io)

### 3. إعداد خادم الشركة

```bash
# 1. تثبيت Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. تثبيت Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 3. تسجيل الدخول إلى GitHub Container Registry
docker login ghcr.io -u YOUR_GITHUB_USERNAME
# أدخل Personal Access Token (مع صلاحية read:packages)

# 4. تحميل ملفات الإعداد
mkdir -p /opt/material-requests
cd /opt/material-requests
# انسخ docker-compose.prod.yml و scripts/update.sh
```

### 4. تعديل ملف docker-compose.prod.yml

```bash
# غيّر GITHUB_USERNAME/GITHUB_REPO إلى القيم الصحيحة
nano docker-compose.prod.yml

# مثال:
# image: ghcr.io/ahmed/material-requests/backend:latest
```

### 5. إنشاء ملف البيئة

```bash
cat > .env << EOF
DB_USER=app_user
DB_PASSWORD=كلمة_مرور_قوية_هنا
DB_NAME=material_requests
SECRET_KEY=مفتاح_سري_طويل_وعشوائي
BACKEND_URL=https://your-domain.com
EOF
```

### 6. التشغيل الأول

```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🔄 تحديث النظام

### الطريقة 1: استخدام سكربت التحديث (موصى به)

```bash
cd /opt/material-requests
chmod +x scripts/update.sh
./scripts/update.sh
```

### الطريقة 2: التحديث اليدوي

```bash
# 1. أخذ نسخة احتياطية
docker exec material_requests_db pg_dump -U app_user material_requests > backup.sql

# 2. تحميل الصور الجديدة
docker-compose -f docker-compose.prod.yml pull

# 3. إعادة تشغيل الخدمات
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

---

## 📌 إنشاء إصدار جديد

### على جهاز التطوير:

```bash
# 1. تحديث رقم الإصدار في system_routes.py
# CURRENT_VERSION = { "version": "2.2.0", ... }

# 2. Commit التغييرات
git add .
git commit -m "Release v2.2.0: وصف التحديث"

# 3. إنشاء Tag
git tag -a v2.2.0 -m "الإصدار 2.2.0"

# 4. رفع التغييرات
git push origin main
git push origin v2.2.0
```

سيقوم GitHub Actions تلقائياً ببناء ورفع الصور الجديدة.

### على خادم الشركة:

```bash
./scripts/update.sh
```

---

## 🔐 إنشاء Personal Access Token

1. اذهب إلى GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. اضغط "Generate new token (classic)"
3. اختر الصلاحيات:
   - `read:packages` (لتحميل الصور)
   - `write:packages` (للرفع - للمطورين فقط)
4. انسخ الـ Token واحفظه في مكان آمن

---

## 🛠️ استكشاف الأخطاء

### الصور لا تتحدث

```bash
# تحقق من تسجيل الدخول
docker login ghcr.io -u YOUR_USERNAME

# تحقق من اسم الصورة
docker pull ghcr.io/USERNAME/REPO/backend:latest
```

### الخدمات لا تعمل

```bash
# عرض السجلات
docker-compose -f docker-compose.prod.yml logs -f

# إعادة تشغيل خدمة معينة
docker-compose -f docker-compose.prod.yml restart backend
```

### استعادة نسخة احتياطية

```bash
# استعادة قاعدة البيانات
docker exec -i material_requests_db psql -U app_user material_requests < backup.sql
```

---

## 📞 الدعم

للمساعدة، تواصل مع فريق التطوير أو افتح Issue على GitHub.
