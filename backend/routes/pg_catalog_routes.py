"""
PostgreSQL Price Catalog Routes
Routes for managing price catalog and item aliases
"""
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
import uuid
import json
import io
import csv

from database import get_postgres_session, User, PriceCatalogItem, ItemAlias, BudgetCategory, Supplier
from routes.pg_auth_routes import get_current_user_pg, UserRole

# Create router
pg_catalog_router = APIRouter(prefix="/api/pg", tags=["PostgreSQL Catalog"])


# ==================== PYDANTIC MODELS ====================

class CatalogItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    unit: str = "قطعة"
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    price: float
    currency: str = "SAR"
    validity_until: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None


class CatalogItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    validity_until: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    is_active: Optional[bool] = None


class AliasCreate(BaseModel):
    alias_name: str
    catalog_item_id: str


class AliasUpdate(BaseModel):
    alias_name: Optional[str] = None
    catalog_item_id: Optional[str] = None


# ==================== PRICE CATALOG ROUTES ====================

@pg_catalog_router.get("/price-catalog")
async def get_price_catalog(
    search: str = "",
    category_id: Optional[str] = None,
    supplier_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get price catalog items with pagination and search"""
    query = select(PriceCatalogItem).where(PriceCatalogItem.is_active == True)
    
    # Apply search filter
    if search:
        query = query.where(
            or_(
                PriceCatalogItem.name.ilike(f"%{search}%"),
                PriceCatalogItem.description.ilike(f"%{search}%")
            )
        )
    
    # Apply category filter
    if category_id:
        query = query.where(PriceCatalogItem.category_id == category_id)
    
    # Apply supplier filter
    if supplier_id:
        query = query.where(PriceCatalogItem.supplier_id == supplier_id)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.order_by(PriceCatalogItem.name).offset((page - 1) * page_size).limit(page_size)
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    return {
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "unit": item.unit,
                "supplier_id": item.supplier_id,
                "supplier_name": item.supplier_name,
                "price": item.price,
                "currency": item.currency,
                "validity_until": item.validity_until,
                "category_id": item.category_id,
                "category_name": item.category_name,
                "is_active": item.is_active,
                "created_by": item.created_by,
                "created_by_name": item.created_by_name,
                "created_at": item.created_at.isoformat() if item.created_at else None
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@pg_catalog_router.post("/price-catalog")
async def create_catalog_item(
    item_data: CatalogItemCreate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create a new catalog item - procurement manager only"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بإضافة عناصر للكتالوج")
    
    # Get category name if category_id provided
    category_name = item_data.category_name
    if item_data.category_id and not category_name:
        cat_result = await session.execute(
            select(BudgetCategory).where(BudgetCategory.id == item_data.category_id)
        )
        category = cat_result.scalar_one_or_none()
        if category:
            category_name = category.name
    
    # Get supplier name if supplier_id provided
    supplier_name = item_data.supplier_name
    if item_data.supplier_id and not supplier_name:
        sup_result = await session.execute(
            select(Supplier).where(Supplier.id == item_data.supplier_id)
        )
        supplier = sup_result.scalar_one_or_none()
        if supplier:
            supplier_name = supplier.name
    
    new_item = PriceCatalogItem(
        id=str(uuid.uuid4()),
        name=item_data.name,
        description=item_data.description,
        unit=item_data.unit,
        supplier_id=item_data.supplier_id,
        supplier_name=supplier_name,
        price=item_data.price,
        currency=item_data.currency,
        validity_until=item_data.validity_until,
        category_id=item_data.category_id,
        category_name=category_name,
        is_active=True,
        created_by=current_user.id,
        created_by_name=current_user.name
    )
    
    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)
    
    return {
        "id": new_item.id,
        "name": new_item.name,
        "price": new_item.price,
        "message": "تم إضافة العنصر للكتالوج بنجاح"
    }


@pg_catalog_router.put("/price-catalog/{item_id}")
async def update_catalog_item(
    item_id: str,
    item_data: CatalogItemUpdate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Update a catalog item"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بتعديل الكتالوج")
    
    result = await session.execute(
        select(PriceCatalogItem).where(PriceCatalogItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="العنصر غير موجود")
    
    # Update fields
    update_data = item_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    
    item.updated_at = datetime.utcnow()
    
    await session.commit()
    
    return {"message": "تم تحديث العنصر بنجاح"}


@pg_catalog_router.delete("/price-catalog/{item_id}")
async def delete_catalog_item(
    item_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Delete (deactivate) a catalog item"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بحذف عناصر الكتالوج")
    
    result = await session.execute(
        select(PriceCatalogItem).where(PriceCatalogItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="العنصر غير موجود")
    
    # Soft delete
    item.is_active = False
    item.updated_at = datetime.utcnow()
    
    await session.commit()
    
    return {"message": "تم حذف العنصر بنجاح"}


@pg_catalog_router.get("/price-catalog/export")
async def export_catalog(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Export catalog to CSV"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بتصدير الكتالوج")
    
    result = await session.execute(
        select(PriceCatalogItem).where(PriceCatalogItem.is_active == True).order_by(PriceCatalogItem.name)
    )
    items = result.scalars().all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['الاسم', 'الوصف', 'الوحدة', 'السعر', 'العملة', 'المورد', 'التصنيف', 'صالح حتى'])
    
    # Data
    for item in items:
        writer.writerow([
            item.name,
            item.description or '',
            item.unit,
            item.price,
            item.currency,
            item.supplier_name or '',
            item.category_name or '',
            item.validity_until or ''
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=price_catalog_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


@pg_catalog_router.post("/price-catalog/import")
async def import_catalog(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Import catalog from CSV"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=403, detail="غير مصرح لك باستيراد الكتالوج")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="يجب أن يكون الملف بصيغة CSV")
    
    content = await file.read()
    decoded = content.decode('utf-8-sig')
    reader = csv.reader(io.StringIO(decoded))
    
    # Skip header
    next(reader, None)
    
    imported = 0
    errors = []
    
    for row_num, row in enumerate(reader, start=2):
        try:
            if len(row) < 4:
                continue
            
            name = row[0].strip()
            description = row[1].strip() if len(row) > 1 else None
            unit = row[2].strip() if len(row) > 2 else "قطعة"
            price = float(row[3]) if len(row) > 3 and row[3] else 0
            currency = row[4].strip() if len(row) > 4 else "SAR"
            supplier_name = row[5].strip() if len(row) > 5 else None
            category_name = row[6].strip() if len(row) > 6 else None
            validity_until = row[7].strip() if len(row) > 7 else None
            
            if not name or price <= 0:
                continue
            
            new_item = PriceCatalogItem(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                unit=unit,
                price=price,
                currency=currency,
                supplier_name=supplier_name,
                category_name=category_name,
                validity_until=validity_until,
                is_active=True,
                created_by=current_user.id,
                created_by_name=current_user.name
            )
            
            session.add(new_item)
            imported += 1
            
        except Exception as e:
            errors.append(f"خطأ في السطر {row_num}: {str(e)}")
    
    await session.commit()
    
    return {
        "message": f"تم استيراد {imported} عنصر بنجاح",
        "imported": imported,
        "errors": errors[:10] if errors else []
    }


# ==================== ITEM ALIASES ROUTES ====================

@pg_catalog_router.get("/item-aliases")
async def get_item_aliases(
    search: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get all item aliases"""
    query = select(ItemAlias)
    
    if search:
        query = query.where(ItemAlias.alias_name.ilike(f"%{search}%"))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    query = query.order_by(ItemAlias.alias_name).offset((page - 1) * page_size).limit(page_size)
    
    result = await session.execute(query)
    aliases = result.scalars().all()
    
    return {
        "items": [
            {
                "id": alias.id,
                "alias_name": alias.alias_name,
                "catalog_item_id": alias.catalog_item_id,
                "catalog_item_name": alias.catalog_item_name,
                "usage_count": alias.usage_count,
                "created_by": alias.created_by,
                "created_by_name": alias.created_by_name,
                "created_at": alias.created_at.isoformat() if alias.created_at else None
            }
            for alias in aliases
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@pg_catalog_router.get("/item-aliases/suggest/{item_name}")
async def suggest_alias(
    item_name: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Suggest catalog item for a given item name"""
    # First check aliases
    alias_result = await session.execute(
        select(ItemAlias).where(ItemAlias.alias_name.ilike(f"%{item_name}%"))
    )
    alias = alias_result.scalar_one_or_none()
    
    if alias:
        # Get the catalog item
        catalog_result = await session.execute(
            select(PriceCatalogItem).where(PriceCatalogItem.id == alias.catalog_item_id)
        )
        catalog_item = catalog_result.scalar_one_or_none()
        
        if catalog_item:
            # Increment usage count
            alias.usage_count += 1
            await session.commit()
            
            return {
                "found": True,
                "source": "alias",
                "catalog_item": {
                    "id": catalog_item.id,
                    "name": catalog_item.name,
                    "price": catalog_item.price,
                    "unit": catalog_item.unit,
                    "supplier_name": catalog_item.supplier_name
                }
            }
    
    # Search in catalog directly
    catalog_result = await session.execute(
        select(PriceCatalogItem).where(
            PriceCatalogItem.is_active == True,
            PriceCatalogItem.name.ilike(f"%{item_name}%")
        ).limit(5)
    )
    items = catalog_result.scalars().all()
    
    if items:
        return {
            "found": True,
            "source": "catalog",
            "suggestions": [
                {
                    "id": item.id,
                    "name": item.name,
                    "price": item.price,
                    "unit": item.unit,
                    "supplier_name": item.supplier_name
                }
                for item in items
            ]
        }
    
    return {"found": False, "suggestions": []}


@pg_catalog_router.post("/item-aliases")
async def create_alias(
    alias_data: AliasCreate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create a new item alias"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بإضافة مسميات بديلة")
    
    # Check if alias already exists
    existing = await session.execute(
        select(ItemAlias).where(ItemAlias.alias_name == alias_data.alias_name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="هذا المسمى موجود مسبقاً")
    
    # Get catalog item name
    catalog_result = await session.execute(
        select(PriceCatalogItem).where(PriceCatalogItem.id == alias_data.catalog_item_id)
    )
    catalog_item = catalog_result.scalar_one_or_none()
    
    if not catalog_item:
        raise HTTPException(status_code=404, detail="عنصر الكتالوج غير موجود")
    
    new_alias = ItemAlias(
        id=str(uuid.uuid4()),
        alias_name=alias_data.alias_name,
        catalog_item_id=alias_data.catalog_item_id,
        catalog_item_name=catalog_item.name,
        usage_count=0,
        created_by=current_user.id,
        created_by_name=current_user.name
    )
    
    session.add(new_alias)
    await session.commit()
    
    return {"message": "تم إضافة المسمى البديل بنجاح", "id": new_alias.id}


@pg_catalog_router.delete("/item-aliases/{alias_id}")
async def delete_alias(
    alias_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Delete an item alias"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بحذف المسميات البديلة")
    
    result = await session.execute(
        select(ItemAlias).where(ItemAlias.id == alias_id)
    )
    alias = result.scalar_one_or_none()
    
    if not alias:
        raise HTTPException(status_code=404, detail="المسمى غير موجود")
    
    await session.delete(alias)
    await session.commit()
    
    return {"message": "تم حذف المسمى بنجاح"}
