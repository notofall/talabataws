# 📦 دليل تثبيت نظام إدارة طلبات المواد

## متطلبات النظام

### الحد الأدنى:
- **المعالج**: 2 cores
- **الذاكرة**: 4 GB RAM
- **التخزين**: 20 GB SSD
- **نظام التشغيل**: Ubuntu 20.04+ / CentOS 8+ / Windows Server 2019+

### البرامج المطلوبة:
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ (اختياري - يمكن استخدام قاعدة بيانات سحابية)

---

## 🚀 طريقة التثبيت

### الخيار 1: تثبيت سريع (Docker) - موصى به

```bash
# 1. تحميل الملفات
git clone https://github.com/your-repo/material-requests.git
cd material-requests

# 2. تشغيل بـ Docker
docker-compose up -d

# 3. افتح المتصفح
# http://localhost:3000/db-setup
```

### الخيار 2: تثبيت يدوي

#### أ) تثبيت المتطلبات (Ubuntu/Debian)

```bash
# تحديث النظام
sudo apt update && sudo apt upgrade -y

# تثبيت Python
sudo apt install python3.10 python3.10-venv python3-pip -y

# تثبيت Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# تثبيت PostgreSQL (اختياري - للتثبيت المحلي)
sudo apt install postgresql postgresql-contrib -y
```

#### ب) تثبيت المتطلبات (CentOS/RHEL)

```bash
# تحديث النظام
sudo yum update -y

# تثبيت Python
sudo yum install python3 python3-pip -y

# تثبيت Node.js
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install nodejs -y

# تثبيت PostgreSQL (اختياري)
sudo yum install postgresql-server postgresql-contrib -y
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### ج) تثبيت المتطلبات (Windows)

1. تحميل وتثبيت [Python 3.10+](https://www.python.org/downloads/)
2. تحميل وتثبيت [Node.js 18+](https://nodejs.org/)
3. تحميل وتثبيت [PostgreSQL 14+](https://www.postgresql.org/download/windows/) (اختياري)

#### د) تثبيت التطبيق

```bash
# 1. فك ضغط الملفات
unzip material-requests.zip
cd material-requests

# 2. إعداد Backend
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. إعداد Frontend
cd ../frontend
npm install
npm run build

# 4. تشغيل التطبيق
cd ../backend
uvicorn server:app --host 0.0.0.0 --port 8001 &

cd ../frontend
npm start
```

---

## ⚙️ إعداد قاعدة البيانات

### عند أول تشغيل:

1. افتح المتصفح على: `http://your-server:3000/db-setup`

2. اختر نوع قاعدة البيانات:
   - **محلي**: PostgreSQL مثبت على نفس الخادم
   - **سحابي**: خدمة خارجية (PlanetScale, Supabase, AWS RDS, etc.)

3. أدخل بيانات الاتصال:
   - عنوان الخادم (Host)
   - المنفذ (Port) - عادة 5432
   - اسم قاعدة البيانات
   - اسم المستخدم
   - كلمة المرور

4. اضغط "اختبار الاتصال" ثم "تثبيت وتهيئة"

### إنشاء قاعدة بيانات محلية:

```bash
# الدخول لـ PostgreSQL
sudo -u postgres psql

# إنشاء قاعدة البيانات
CREATE DATABASE material_requests;

# إنشاء مستخدم
CREATE USER app_user WITH PASSWORD 'your_secure_password';

# منح الصلاحيات
GRANT ALL PRIVILEGES ON DATABASE material_requests TO app_user;

# الخروج
\q
```

---

## 🔧 خيارات قواعد البيانات السحابية

### PlanetScale (MySQL متوافق)
```
Host: aws.connect.psdb.cloud
Port: 3306
SSL: Required
```

### Supabase (PostgreSQL)
```
Host: db.xxxxx.supabase.co
Port: 5432
SSL: Required
```

### AWS RDS
```
Host: your-instance.region.rds.amazonaws.com
Port: 5432
SSL: Required
```

### Google Cloud SQL
```
Host: your-instance-public-ip
Port: 5432
SSL: Required
```

### Azure Database for PostgreSQL
```
Host: your-server.postgres.database.azure.com
Port: 5432
SSL: Required
```

---

## 🔒 إعدادات الأمان

### 1. تغيير المفتاح السري
```bash
# في ملف backend/.env
SECRET_KEY=your-very-long-random-secret-key-here
```

### 2. تفعيل HTTPS
```bash
# باستخدام Nginx
sudo apt install nginx certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. إعداد Firewall
```bash
# السماح فقط للمنافذ المطلوبة
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

---

## 📱 تثبيت كتطبيق (PWA)

التطبيق يدعم التثبيت على الأجهزة:

### Android / Chrome:
- افتح التطبيق في المتصفح
- ستظهر رسالة "تثبيت التطبيق"
- اضغط "تثبيت الآن"

### iOS / Safari:
1. افتح التطبيق في Safari
2. اضغط على زر المشاركة
3. اختر "إضافة إلى الشاشة الرئيسية"

---

## 🔄 التحديث

```bash
# 1. إيقاف التطبيق
sudo systemctl stop material-requests

# 2. نسخ احتياطي
pg_dump material_requests > backup_$(date +%Y%m%d).sql

# 3. تحديث الملفات
cd /path/to/app
git pull  # أو فك ضغط النسخة الجديدة

# 4. تحديث المتطلبات
cd backend && pip install -r requirements.txt
cd ../frontend && npm install && npm run build

# 5. إعادة التشغيل
sudo systemctl start material-requests
```

---

## 🆘 استكشاف الأخطاء

### مشكلة: لا يمكن الاتصال بقاعدة البيانات
```bash
# تحقق من تشغيل PostgreSQL
sudo systemctl status postgresql

# تحقق من الاتصال
psql -h localhost -U your_user -d your_database
```

### مشكلة: التطبيق لا يعمل
```bash
# تحقق من السجلات
tail -f /var/log/material-requests/backend.log
tail -f /var/log/material-requests/frontend.log
```

### مشكلة: خطأ في الصلاحيات
```bash
# تصحيح صلاحيات الملفات
sudo chown -R www-data:www-data /path/to/app
sudo chmod -R 755 /path/to/app
```

---

## 📞 الدعم الفني

- **البريد الإلكتروني**: support@your-company.com
- **الهاتف**: +966-xxx-xxx-xxxx
- **التوثيق**: https://docs.your-company.com
