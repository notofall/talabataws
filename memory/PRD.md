# نظام إدارة طلبات المواد - PRD

## المشكلة الأصلية
نظام لمدير مشتريات يتيح لـ 10 مشرفين مواقع إنشاء طلبات مواد، ثم يعتمدها 6 مهندسين، وأخيراً يصل الطلب لمدير المشتريات لإصدار أمر الشراء للموردين.

---

## 🚀 التحول إلى PostgreSQL (13 يناير 2026)

### ✅ ما تم إنجازه بالكامل:

#### البنية التحتية
- [x] اتصال مع PlanetScale PostgreSQL
- [x] إنشاء 15 جدول SQL
- [x] إنشاء ملفات Database Layer (config, connection, models)

#### الـ APIs المحولة (59 API)
| الملف | عدد APIs | الحالة |
|-------|----------|--------|
| `pg_auth_routes.py` | 13 | ✅ |
| `pg_projects_routes.py` | 5 | ✅ |
| `pg_suppliers_routes.py` | 5 | ✅ |
| `pg_budget_routes.py` | 8 | ✅ |
| `pg_requests_routes.py` | 7 | ✅ |
| `pg_orders_routes.py` | 10 | ✅ |
| `pg_settings_routes.py` | 11 | ✅ |

### نقاط النهاية الجديدة:
```
/api/pg/auth/*           - المصادقة
/api/pg/admin/users/*    - إدارة المستخدمين
/api/pg/projects/*       - المشاريع
/api/pg/suppliers/*      - الموردين
/api/pg/budget-categories/* - تصنيفات الميزانية
/api/pg/requests/*       - طلبات المواد
/api/pg/purchase-orders/* - أوامر الشراء
/api/pg/gm/*             - لوحة المدير العام
/api/pg/settings/*       - الإعدادات
/api/pg/reports/*        - التقارير
/api/pg/admin/*          - إدارة البيانات
/api/pg/audit-logs       - سجل التدقيق
```

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

### 🔴 P0 - أولوية قصوى
1. تعديل Frontend ليستخدم `/api/pg/*` بدلاً من `/api/*`
2. اختبار شامل للتدفق الكامل

### 🟡 P1 - أولوية متوسطة  
1. تحويل PWA للموبايل
2. إضافة Price Catalog APIs

### 🟢 P2 - أولوية منخفضة
1. File Attachments
2. Email Notifications

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

## الهيكل التقني

### Backend:
```
/app/backend/
├── server.py              # FastAPI app
├── database/
│   ├── __init__.py
│   ├── config.py          # PostgreSQL settings
│   ├── connection.py      # SQLAlchemy engine
│   └── models.py          # 15 SQLAlchemy models
└── routes/
    ├── pg_auth_routes.py
    ├── pg_projects_routes.py
    ├── pg_suppliers_routes.py
    ├── pg_budget_routes.py
    ├── pg_requests_routes.py
    ├── pg_orders_routes.py
    └── pg_settings_routes.py
```
