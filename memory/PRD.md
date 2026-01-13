# نظام إدارة طلبات المواد - PRD

## المشكلة الأصلية
نظام لمدير مشتريات يتيح لـ 10 مشرفين مواقع إنشاء طلبات مواد، ثم يعتمدها 6 مهندسين، وأخيراً يصل الطلب لمدير المشتريات لإصدار أمر الشراء للموردين.

---

## 🚀 التحول إلى PostgreSQL (جديد - 13 يناير 2026)

### ما تم إنجازه في جلسة التحويل:

#### ✅ المرحلة 1: البنية التحتية
- [x] إنشاء اتصال مع PlanetScale PostgreSQL
- [x] إنشاء 15 جدول SQL في قاعدة البيانات
- [x] إنشاء ملفات الـ Database Layer:
  - `/app/backend/database/config.py` - إعدادات الاتصال
  - `/app/backend/database/connection.py` - إدارة الجلسات
  - `/app/backend/database/models.py` - نماذج SQLAlchemy

#### ✅ المرحلة 2: APIs المحولة
| API | الملف | الحالة |
|-----|-------|--------|
| Auth (تسجيل/دخول) | `pg_auth_routes.py` | ✅ |
| Users Management | `pg_auth_routes.py` | ✅ |
| Projects | `pg_projects_routes.py` | ✅ |
| Suppliers | `pg_suppliers_routes.py` | ✅ |
| Budget Categories | `pg_budget_routes.py` | ✅ |
| Material Requests | `pg_requests_routes.py` | ✅ |
| Purchase Orders | ❌ قيد التطوير | 🔄 |

### الجداول المنشأة في PostgreSQL:
```
1. users              - المستخدمين
2. projects           - المشاريع  
3. suppliers          - الموردين
4. budget_categories  - تصنيفات الميزانية
5. default_budget_categories - التصنيفات الافتراضية
6. material_requests  - طلبات المواد
7. material_request_items - أصناف الطلبات
8. purchase_orders    - أوامر الشراء
9. purchase_order_items - أصناف أوامر الشراء
10. delivery_records  - سجلات التسليم
11. audit_logs        - سجل التدقيق
12. system_settings   - إعدادات النظام
13. price_catalog     - كتالوج الأسعار
14. item_aliases      - الأسماء البديلة
15. attachments       - المرفقات
```

### نقاط النهاية الجديدة (PostgreSQL):
```
/api/pg/health                    - فحص الاتصال
/api/pg/setup/check               - فحص الإعداد
/api/pg/setup/first-admin         - إنشاء أول مدير
/api/pg/auth/login                - تسجيل الدخول
/api/pg/auth/me                   - المستخدم الحالي
/api/pg/admin/users               - إدارة المستخدمين
/api/pg/projects                  - المشاريع
/api/pg/suppliers                 - الموردين
/api/pg/budget-categories         - تصنيفات الميزانية
/api/pg/default-budget-categories - التصنيفات الافتراضية
/api/pg/requests                  - طلبات المواد
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
1. إكمال تحويل Purchase Orders APIs
2. تحديث Frontend ليستخدم `/api/pg/*`

### 🟡 P1 - أولوية متوسطة  
1. System Settings APIs
2. Reports & Analytics APIs
3. تحويل PWA للموبايل

### 🟢 P2 - أولوية منخفضة
1. Audit Trail APIs
2. Price Catalog APIs
3. File Attachments

---

## إعدادات قاعدة البيانات

### PlanetScale PostgreSQL:
```
Host: eu-central-2.pg.psdb.cloud
Port: 6432
Database: postgres
SSL: Required
```

### ملف .env:
```
POSTGRES_HOST=eu-central-2.pg.psdb.cloud
POSTGRES_PORT=6432
POSTGRES_USER=pscale_api_...
POSTGRES_PASSWORD=pscale_pw_...
POSTGRES_DB=postgres
```

---

## الهيكل التقني

### Backend:
- FastAPI + SQLAlchemy 2.0 + asyncpg
- MongoDB (قديم) + PostgreSQL (جديد)
- JWT Authentication

### Frontend:
- React + Tailwind + Shadcn UI
- RTL Arabic Support

### Database:
- PlanetScale PostgreSQL (Managed)
- Connection Pooling enabled
