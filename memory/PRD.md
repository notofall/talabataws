# نظام إدارة طلبات المواد - PRD

## المشكلة الأصلية
نظام لمدير مشتريات يتيح لـ 10 مشرفين مواقع إنشاء طلبات مواد، ثم يعتمدها 6 مهندسين، وأخيراً يصل الطلب لمدير المشتريات لإصدار أمر الشراء للموردين.

---

## 🚀 التحول الكامل إلى PostgreSQL (13 يناير 2026)

### ✅ ما تم إنجازه بالكامل:

#### Backend - قاعدة البيانات
- [x] اتصال مع PlanetScale PostgreSQL
- [x] إنشاء 15 جدول SQL
- [x] 59 API محولة إلى PostgreSQL
- [x] جميع الـ Routes تعمل وتم اختبارها

#### Frontend - الواجهة
- [x] `AuthContext.js` - تحديث للـ PostgreSQL APIs
- [x] `LoginPage.js` - تحديث URLs
- [x] `ProcurementDashboard.js` - تحديث fetchData و Reports
- [x] `SupervisorDashboard.js` - تحديث fetchData
- [x] `EngineerDashboard.js` - تحديث fetchData
- [x] `GeneralManagerDashboard.js` - تحديث كامل للـ GM APIs

### 🧪 نتائج الاختبار:
| الصفحة | الحالة | البيانات |
|--------|--------|----------|
| تسجيل الدخول | ✅ | PostgreSQL |
| مدير المشتريات | ✅ | الطلبات والأوامر تظهر |
| المشرف | ✅ | طلب A1 يظهر |
| المدير العام | ✅ | أمر PO-00000001 معتمد |

---

## بيانات الاختبار (PostgreSQL)

| الدور | البريد الإلكتروني | كلمة المرور |
|-------|-----------------|-------------|
| مدير مشتريات | notofall@gmail.com | 123456 |
| المدير العام | md@gmail.com | 123456 |
| مهندس | engineer1@test.com | 123456 |
| مشرف | supervisor1@test.com | 123456 |

---

## المهام القادمة

### 🟡 P1 - أولوية متوسطة  
1. PWA للموبايل
2. Price Catalog APIs (PostgreSQL)
3. اختبار شامل للتدفق الكامل

### 🟢 P2 - أولوية منخفضة
1. File Attachments
2. Email Notifications (SendGrid)
3. تنظيف MongoDB القديمة

---

## إعدادات قاعدة البيانات

### PlanetScale PostgreSQL:
```
Host: eu-central-2.pg.psdb.cloud
Port: 6432
Database: postgres
SSL: Required
```

---

## الهيكل التقني النهائي

### Backend:
```
/app/backend/
├── server.py              # FastAPI app (MongoDB + PostgreSQL)
├── database/
│   ├── __init__.py
│   ├── config.py          # PostgreSQL settings
│   ├── connection.py      # SQLAlchemy engine
│   └── models.py          # 15 SQLAlchemy models
└── routes/
    ├── pg_auth_routes.py      # Auth APIs (13)
    ├── pg_projects_routes.py  # Projects APIs (5)
    ├── pg_suppliers_routes.py # Suppliers APIs (5)
    ├── pg_budget_routes.py    # Budget APIs (8)
    ├── pg_requests_routes.py  # Requests APIs (7)
    ├── pg_orders_routes.py    # Orders APIs (10)
    └── pg_settings_routes.py  # Settings APIs (11)
```

### Frontend:
```
/app/frontend/src/
├── context/AuthContext.js     # Updated for /api/pg
├── pages/
│   ├── LoginPage.js           # Updated
│   ├── ProcurementDashboard.js # Updated
│   ├── SupervisorDashboard.js  # Updated
│   ├── EngineerDashboard.js    # Updated
│   └── GeneralManagerDashboard.js # Updated
└── utils/pdfExport.js
```
