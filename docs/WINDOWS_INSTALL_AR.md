# 🚀 دليل التثبيت على Windows

## الطريقة الأولى: Docker Desktop (موصى بها) ⭐

### الخطوة 1: تثبيت Docker Desktop

1. حمّل Docker Desktop من الرابط:
   **https://www.docker.com/products/docker-desktop**

2. شغّل ملف التثبيت واتبع الخطوات
3. بعد التثبيت، أعد تشغيل الكمبيوتر
4. افتح Docker Desktop وانتظر حتى يعمل (أيقونة الحوت في شريط المهام)

### الخطوة 2: تشغيل التطبيق

**الطريقة السهلة:**
- انقر مرتين على ملف `start.bat`

**أو من سطر الأوامر:**
```cmd
docker-compose -f docker-compose.windows.yml up -d
```

### الخطوة 3: فتح التطبيق

افتح المتصفح على الرابط:
```
http://localhost
```

### إيقاف التطبيق
```cmd
docker-compose -f docker-compose.windows.yml down
```

---

## الطريقة الثانية: التثبيت اليدوي

### المتطلبات:
- Python 3.10 أو أحدث
- Node.js 18 أو أحدث
- PostgreSQL 14 أو أحدث

### الخطوة 1: تثبيت PostgreSQL

1. حمّل PostgreSQL من: https://www.postgresql.org/download/windows/
2. ثبّته واحفظ كلمة المرور التي تختارها
3. أنشئ قاعدة بيانات جديدة باسم `talabat_db`

### الخطوة 2: إعداد Backend

```cmd
cd backend

# إنشاء بيئة افتراضية
python -m venv venv

# تفعيل البيئة
venv\Scripts\activate

# تثبيت المكتبات
pip install fastapi uvicorn sqlalchemy asyncpg psycopg2-binary pydantic pydantic-settings python-jose passlib bcrypt python-multipart python-dotenv alembic openpyxl sendgrid httpx psutil email-validator

# إنشاء ملف .env
echo POSTGRES_HOST=localhost > .env
echo POSTGRES_PORT=5432 >> .env
echo POSTGRES_DB=talabat_db >> .env
echo POSTGRES_USER=postgres >> .env
echo POSTGRES_PASSWORD=YOUR_PASSWORD >> .env
echo SECRET_KEY=my-secret-key >> .env

# تشغيل السيرفر
python -m uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

### الخطوة 3: إعداد Frontend (في نافذة CMD جديدة)

```cmd
cd frontend

# تثبيت المكتبات
npm install --legacy-peer-deps

# إنشاء ملف .env
echo REACT_APP_BACKEND_URL=http://localhost:8001 > .env

# تشغيل الواجهة
npm start
```

### الخطوة 4: فتح التطبيق

افتح المتصفح على:
```
http://localhost:3000
```

---

## ❓ الأسئلة الشائعة

### Docker لا يعمل؟
- تأكد من تفعيل Hyper-V و WSL2 في Windows
- أعد تشغيل الكمبيوتر بعد تثبيت Docker

### خطأ في تثبيت مكتبات Python؟
- استخدم الأمر المختصر في الخطوة 2 بدلاً من `pip install -r requirements.txt`

### خطأ في npm install؟
- استخدم `npm install --legacy-peer-deps`

### لا أستطيع الاتصال بقاعدة البيانات؟
- تأكد من أن PostgreSQL يعمل
- تأكد من صحة كلمة المرور في ملف `.env`

---

## 📞 الدعم

إذا واجهت أي مشكلة، شارك:
1. لقطة شاشة للخطأ
2. الخطوة التي توقفت عندها
3. نظام التشغيل (Windows 10/11)
