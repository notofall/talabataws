-- ======================================================
-- سكريبت التحديث لقاعدة البيانات PostgreSQL
-- التاريخ: 17 يناير 2026
-- الغرض: إضافة الأعمدة الجديدة لدعم ربط الأصناف بكتالوج الأسعار
-- ======================================================

-- ===== 1. إضافة أعمدة ربط الكتالوج لجدول purchase_order_items =====
-- هذه الأعمدة تسمح بربط أصناف أمر الشراء بكتالوج الأسعار

DO $$
BEGIN
    -- إضافة عمود catalog_item_id إذا لم يكن موجوداً
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'purchase_order_items' 
        AND column_name = 'catalog_item_id'
    ) THEN
        ALTER TABLE purchase_order_items 
        ADD COLUMN catalog_item_id VARCHAR(36) NULL;
        
        RAISE NOTICE 'تم إضافة عمود catalog_item_id إلى جدول purchase_order_items';
    ELSE
        RAISE NOTICE 'عمود catalog_item_id موجود بالفعل';
    END IF;
    
    -- إضافة عمود item_code إذا لم يكن موجوداً
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'purchase_order_items' 
        AND column_name = 'item_code'
    ) THEN
        ALTER TABLE purchase_order_items 
        ADD COLUMN item_code VARCHAR(100) NULL;
        
        RAISE NOTICE 'تم إضافة عمود item_code إلى جدول purchase_order_items';
    ELSE
        RAISE NOTICE 'عمود item_code موجود بالفعل';
    END IF;
END $$;

-- إنشاء فهرس لتحسين الأداء (إذا لم يكن موجوداً)
CREATE INDEX IF NOT EXISTS idx_po_items_catalog 
ON purchase_order_items(catalog_item_id);

-- ===== 2. إضافة عمود code لجدول projects إذا لم يكن موجوداً =====
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'projects' 
        AND column_name = 'code'
    ) THEN
        ALTER TABLE projects 
        ADD COLUMN code VARCHAR(50) UNIQUE NULL;
        
        RAISE NOTICE 'تم إضافة عمود code إلى جدول projects';
    ELSE
        RAISE NOTICE 'عمود code موجود بالفعل في جدول projects';
    END IF;
END $$;

-- ===== 3. إضافة عمود code لجدول budget_categories إذا لم يكن موجوداً =====
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'budget_categories' 
        AND column_name = 'code'
    ) THEN
        ALTER TABLE budget_categories 
        ADD COLUMN code VARCHAR(50) NULL;
        
        RAISE NOTICE 'تم إضافة عمود code إلى جدول budget_categories';
    ELSE
        RAISE NOTICE 'عمود code موجود بالفعل في جدول budget_categories';
    END IF;
END $$;

-- ===== 4. إضافة عمود item_code لجدول price_catalog إذا لم يكن موجوداً =====
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'price_catalog' 
        AND column_name = 'item_code'
    ) THEN
        ALTER TABLE price_catalog 
        ADD COLUMN item_code VARCHAR(50) UNIQUE NULL;
        
        RAISE NOTICE 'تم إضافة عمود item_code إلى جدول price_catalog';
    ELSE
        RAISE NOTICE 'عمود item_code موجود بالفعل في جدول price_catalog';
    END IF;
END $$;

-- ===== 5. إنشاء جدول planned_quantities إذا لم يكن موجوداً =====
CREATE TABLE IF NOT EXISTS planned_quantities (
    id VARCHAR(36) PRIMARY KEY,
    item_name VARCHAR(255) NOT NULL,
    item_code VARCHAR(100) NULL,
    unit VARCHAR(50) DEFAULT 'قطعة',
    description TEXT NULL,
    planned_quantity FLOAT NOT NULL,
    ordered_quantity FLOAT DEFAULT 0,
    remaining_quantity FLOAT NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
    project_name VARCHAR(255) NOT NULL,
    category_id VARCHAR(36) NULL REFERENCES budget_categories(id),
    category_name VARCHAR(255) NULL,
    catalog_item_id VARCHAR(36) NULL REFERENCES price_catalog(id),
    expected_order_date TIMESTAMP NULL,
    status VARCHAR(50) DEFAULT 'planned',
    priority INTEGER DEFAULT 2,
    notes TEXT NULL,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id),
    created_by_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL,
    updated_by VARCHAR(36) NULL,
    updated_by_name VARCHAR(255) NULL
);

-- إنشاء الفهارس لجدول planned_quantities
CREATE INDEX IF NOT EXISTS idx_planned_project_status ON planned_quantities(project_id, status);
CREATE INDEX IF NOT EXISTS idx_planned_expected_date ON planned_quantities(expected_order_date);
CREATE INDEX IF NOT EXISTS idx_planned_item_name ON planned_quantities(item_name);

-- ===== التحقق من التحديثات =====
SELECT 'التحقق من الأعمدة المضافة:' AS message;

SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name IN ('purchase_order_items', 'projects', 'budget_categories', 'price_catalog')
AND column_name IN ('catalog_item_id', 'item_code', 'code')
ORDER BY table_name, column_name;

-- التحقق من وجود جدول planned_quantities
SELECT 'التحقق من جدول planned_quantities:' AS message;
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_name = 'planned_quantities'
) AS table_exists;

SELECT '✅ تم تنفيذ التحديثات بنجاح!' AS final_message;
