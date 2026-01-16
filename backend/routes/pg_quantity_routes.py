"""
PostgreSQL Quantity Engineer Routes - إدارة الكميات المخططة
دور مهندس الكميات: إضافة وتعديل كميات الأصناف فقط
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, and_, or_
import uuid
import json
import io
import csv

from database import (
    get_postgres_session, User, Project, PlannedQuantity,
    PriceCatalogItem, BudgetCategory, PurchaseOrder, PurchaseOrderItem
)
from routes.pg_auth_routes import get_current_user_pg, UserRole

# Create router
pg_quantity_router = APIRouter(prefix="/api/pg/quantity", tags=["Quantity Engineer"])


# ==================== PYDANTIC MODELS ====================

class PlannedQuantityCreate(BaseModel):
    item_name: str
    item_code: Optional[str] = None
    unit: str = "قطعة"
    description: Optional[str] = None
    planned_quantity: float
    project_id: str
    category_id: Optional[str] = None
    catalog_item_id: Optional[str] = None
    expected_order_date: Optional[str] = None
    priority: int = 2
    notes: Optional[str] = None


class PlannedQuantityUpdate(BaseModel):
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    planned_quantity: Optional[float] = None
    project_id: Optional[str] = None
    category_id: Optional[str] = None
    catalog_item_id: Optional[str] = None
    expected_order_date: Optional[str] = None
    priority: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class BulkPlannedQuantityCreate(BaseModel):
    items: List[PlannedQuantityCreate]


# ==================== HELPER FUNCTIONS ====================

def require_quantity_access(current_user: User):
    """Check if user has access to quantity features"""
    allowed_roles = [
        UserRole.QUANTITY_ENGINEER,
        UserRole.PROCUREMENT_MANAGER,
        UserRole.SYSTEM_ADMIN
    ]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")


# ==================== PLANNED QUANTITIES CRUD ====================

@pg_quantity_router.get("/planned")
async def get_planned_quantities(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get all planned quantities with filters"""
    require_quantity_access(current_user)
    
    query = select(PlannedQuantity)
    
    # Apply filters
    if project_id:
        query = query.where(PlannedQuantity.project_id == project_id)
    
    if status:
        query = query.where(PlannedQuantity.status == status)
    
    if search:
        query = query.where(
            or_(
                PlannedQuantity.item_name.ilike(f"%{search}%"),
                PlannedQuantity.item_code.ilike(f"%{search}%")
            )
        )
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(PlannedQuantity.created_at)).offset(offset).limit(page_size)
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    return {
        "items": [
            {
                "id": item.id,
                "item_name": item.item_name,
                "item_code": item.item_code,
                "unit": item.unit,
                "description": item.description,
                "planned_quantity": item.planned_quantity,
                "ordered_quantity": item.ordered_quantity,
                "remaining_quantity": item.remaining_quantity,
                "project_id": item.project_id,
                "project_name": item.project_name,
                "category_id": item.category_id,
                "category_name": item.category_name,
                "catalog_item_id": item.catalog_item_id,
                "expected_order_date": item.expected_order_date.isoformat() if item.expected_order_date else None,
                "status": item.status,
                "priority": item.priority,
                "notes": item.notes,
                "created_by": item.created_by,
                "created_by_name": item.created_by_name,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@pg_quantity_router.post("/planned")
async def create_planned_quantity(
    data: PlannedQuantityCreate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create a new planned quantity"""
    require_quantity_access(current_user)
    
    # Get project name
    project_result = await session.execute(
        select(Project).where(Project.id == data.project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    # Get category name if provided
    category_name = None
    if data.category_id:
        cat_result = await session.execute(
            select(BudgetCategory).where(BudgetCategory.id == data.category_id)
        )
        category = cat_result.scalar_one_or_none()
        if category:
            category_name = category.name
    
    # Parse expected order date
    expected_date = None
    if data.expected_order_date:
        try:
            expected_date = datetime.fromisoformat(data.expected_order_date.replace('Z', '+00:00'))
        except:
            pass
    
    new_item = PlannedQuantity(
        id=str(uuid.uuid4()),
        item_name=data.item_name,
        item_code=data.item_code,
        unit=data.unit,
        description=data.description,
        planned_quantity=data.planned_quantity,
        ordered_quantity=0,
        remaining_quantity=data.planned_quantity,
        project_id=data.project_id,
        project_name=project.name,
        category_id=data.category_id,
        category_name=category_name,
        catalog_item_id=data.catalog_item_id,
        expected_order_date=expected_date,
        status="planned",
        priority=data.priority,
        notes=data.notes,
        created_by=current_user.id,
        created_by_name=current_user.name
    )
    
    session.add(new_item)
    await session.commit()
    
    return {"message": "تم إضافة الكمية المخططة بنجاح", "id": new_item.id}


@pg_quantity_router.post("/planned/bulk")
async def create_bulk_planned_quantities(
    data: BulkPlannedQuantityCreate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create multiple planned quantities at once"""
    require_quantity_access(current_user)
    
    created = 0
    errors = []
    
    for idx, item_data in enumerate(data.items):
        try:
            # Get project name
            project_result = await session.execute(
                select(Project).where(Project.id == item_data.project_id)
            )
            project = project_result.scalar_one_or_none()
            if not project:
                errors.append(f"العنصر {idx+1}: المشروع غير موجود")
                continue
            
            # Get category name
            category_name = None
            if item_data.category_id:
                cat_result = await session.execute(
                    select(BudgetCategory).where(BudgetCategory.id == item_data.category_id)
                )
                category = cat_result.scalar_one_or_none()
                if category:
                    category_name = category.name
            
            # Parse expected order date
            expected_date = None
            if item_data.expected_order_date:
                try:
                    expected_date = datetime.fromisoformat(item_data.expected_order_date.replace('Z', '+00:00'))
                except:
                    pass
            
            new_item = PlannedQuantity(
                id=str(uuid.uuid4()),
                item_name=item_data.item_name,
                item_code=item_data.item_code,
                unit=item_data.unit,
                description=item_data.description,
                planned_quantity=item_data.planned_quantity,
                ordered_quantity=0,
                remaining_quantity=item_data.planned_quantity,
                project_id=item_data.project_id,
                project_name=project.name,
                category_id=item_data.category_id,
                category_name=category_name,
                catalog_item_id=item_data.catalog_item_id,
                expected_order_date=expected_date,
                status="planned",
                priority=item_data.priority,
                notes=item_data.notes,
                created_by=current_user.id,
                created_by_name=current_user.name
            )
            
            session.add(new_item)
            created += 1
            
        except Exception as e:
            errors.append(f"العنصر {idx+1}: {str(e)}")
    
    await session.commit()
    
    return {
        "message": f"تم إضافة {created} عنصر بنجاح",
        "created": created,
        "errors": errors[:10] if errors else []
    }


@pg_quantity_router.put("/planned/{item_id}")
async def update_planned_quantity(
    item_id: str,
    data: PlannedQuantityUpdate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Update a planned quantity"""
    require_quantity_access(current_user)
    
    result = await session.execute(
        select(PlannedQuantity).where(PlannedQuantity.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="العنصر غير موجود")
    
    # Update fields
    if data.item_name is not None:
        item.item_name = data.item_name
    if data.item_code is not None:
        item.item_code = data.item_code
    if data.unit is not None:
        item.unit = data.unit
    if data.description is not None:
        item.description = data.description
    if data.planned_quantity is not None:
        old_planned = item.planned_quantity
        item.planned_quantity = data.planned_quantity
        # Recalculate remaining
        item.remaining_quantity = data.planned_quantity - item.ordered_quantity
        if item.remaining_quantity < 0:
            item.remaining_quantity = 0
    if data.priority is not None:
        item.priority = data.priority
    if data.notes is not None:
        item.notes = data.notes
    if data.status is not None:
        item.status = data.status
    
    if data.project_id is not None:
        project_result = await session.execute(
            select(Project).where(Project.id == data.project_id)
        )
        project = project_result.scalar_one_or_none()
        if project:
            item.project_id = data.project_id
            item.project_name = project.name
    
    if data.expected_order_date is not None:
        try:
            item.expected_order_date = datetime.fromisoformat(data.expected_order_date.replace('Z', '+00:00'))
        except:
            pass
    
    item.updated_at = datetime.utcnow()
    item.updated_by = current_user.id
    item.updated_by_name = current_user.name
    
    await session.commit()
    
    return {"message": "تم تحديث الكمية بنجاح"}


@pg_quantity_router.delete("/planned/{item_id}")
async def delete_planned_quantity(
    item_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Delete a planned quantity"""
    require_quantity_access(current_user)
    
    result = await session.execute(
        select(PlannedQuantity).where(PlannedQuantity.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="العنصر غير موجود")
    
    # Only allow deletion if not ordered yet
    if item.ordered_quantity > 0:
        raise HTTPException(status_code=400, detail="لا يمكن حذف عنصر تم طلبه بالفعل")
    
    await session.delete(item)
    await session.commit()
    
    return {"message": "تم حذف العنصر بنجاح"}


# ==================== IMPORT/EXPORT ====================

@pg_quantity_router.get("/planned/template")
async def get_import_template(
    current_user: User = Depends(get_current_user_pg)
):
    """Download Excel template for importing planned quantities"""
    require_quantity_access(current_user)
    
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    except ImportError:
        raise HTTPException(status_code=500, detail="مكتبة Excel غير متوفرة")
    
    wb = Workbook()
    ws = wb.active
    ws.title = "نموذج الكميات"
    ws.sheet_view.rightToLeft = True
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Headers
    headers = ['كود الصنف', 'اسم الصنف', 'الوصف', 'الوحدة', 'الكمية المخططة', 'تاريخ الطلب المتوقع', 'الأولوية', 'ملاحظات']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
    
    # Example row
    example_data = ['ITM-001', 'حديد تسليح 12مم', 'حديد تسليح قطر 12مم', 'طن', '100', '2026-02-01', '1', 'ملاحظات']
    for col, value in enumerate(example_data, 1):
        cell = ws.cell(row=2, column=col, value=value)
        cell.border = thin_border
    
    # Instructions row
    ws.cell(row=4, column=1, value="تعليمات:")
    ws.cell(row=5, column=1, value="- الأولوية: 1=عالية، 2=متوسطة، 3=منخفضة")
    ws.cell(row=6, column=1, value="- تاريخ الطلب المتوقع بصيغة: YYYY-MM-DD")
    
    # Column widths
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 40
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 20
    ws.column_dimensions['G'].width = 12
    ws.column_dimensions['H'].width = 30
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=quantity_template.xlsx"}
    )


@pg_quantity_router.post("/planned/import")
async def import_planned_quantities(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Import planned quantities from Excel/CSV"""
    require_quantity_access(current_user)
    
    # Get project
    project_result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    filename = file.filename.lower()
    content = await file.read()
    
    imported = 0
    errors = []
    
    # Handle Excel files
    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        try:
            from openpyxl import load_workbook
            
            wb = load_workbook(io.BytesIO(content))
            ws = wb.active
            
            for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    if not row or not row[1]:  # Skip empty rows
                        continue
                    
                    item_code = str(row[0]).strip() if row[0] else None
                    item_name = str(row[1]).strip() if row[1] else None
                    description = str(row[2]).strip() if len(row) > 2 and row[2] else None
                    unit = str(row[3]).strip() if len(row) > 3 and row[3] else "قطعة"
                    planned_qty = float(row[4]) if len(row) > 4 and row[4] else 0
                    expected_date_str = str(row[5]).strip() if len(row) > 5 and row[5] else None
                    priority = int(row[6]) if len(row) > 6 and row[6] else 2
                    notes = str(row[7]).strip() if len(row) > 7 and row[7] else None
                    
                    if not item_name or planned_qty <= 0:
                        continue
                    
                    # Parse expected date
                    expected_date = None
                    if expected_date_str:
                        try:
                            expected_date = datetime.strptime(expected_date_str[:10], "%Y-%m-%d")
                        except:
                            pass
                    
                    new_item = PlannedQuantity(
                        id=str(uuid.uuid4()),
                        item_name=item_name,
                        item_code=item_code,
                        unit=unit,
                        description=description,
                        planned_quantity=planned_qty,
                        ordered_quantity=0,
                        remaining_quantity=planned_qty,
                        project_id=project_id,
                        project_name=project.name,
                        expected_order_date=expected_date,
                        status="planned",
                        priority=priority if 1 <= priority <= 3 else 2,
                        notes=notes,
                        created_by=current_user.id,
                        created_by_name=current_user.name
                    )
                    
                    session.add(new_item)
                    imported += 1
                    
                except Exception as e:
                    errors.append(f"خطأ في السطر {row_num}: {str(e)}")
                    
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"فشل في قراءة ملف Excel: {str(e)}")
    
    # Handle CSV files
    elif filename.endswith('.csv'):
        decoded = content.decode('utf-8-sig')
        reader = csv.reader(io.StringIO(decoded))
        next(reader, None)  # Skip header
        
        for row_num, row in enumerate(reader, start=2):
            try:
                if len(row) < 2:
                    continue
                
                item_code = row[0].strip() if len(row) > 0 else None
                item_name = row[1].strip() if len(row) > 1 else None
                description = row[2].strip() if len(row) > 2 else None
                unit = row[3].strip() if len(row) > 3 else "قطعة"
                planned_qty = float(row[4]) if len(row) > 4 and row[4] else 0
                expected_date_str = row[5].strip() if len(row) > 5 else None
                priority = int(row[6]) if len(row) > 6 and row[6] else 2
                notes = row[7].strip() if len(row) > 7 else None
                
                if not item_name or planned_qty <= 0:
                    continue
                
                expected_date = None
                if expected_date_str:
                    try:
                        expected_date = datetime.strptime(expected_date_str[:10], "%Y-%m-%d")
                    except:
                        pass
                
                new_item = PlannedQuantity(
                    id=str(uuid.uuid4()),
                    item_name=item_name,
                    item_code=item_code,
                    unit=unit,
                    description=description,
                    planned_quantity=planned_qty,
                    ordered_quantity=0,
                    remaining_quantity=planned_qty,
                    project_id=project_id,
                    project_name=project.name,
                    expected_order_date=expected_date,
                    status="planned",
                    priority=priority if 1 <= priority <= 3 else 2,
                    notes=notes,
                    created_by=current_user.id,
                    created_by_name=current_user.name
                )
                
                session.add(new_item)
                imported += 1
                
            except Exception as e:
                errors.append(f"خطأ في السطر {row_num}: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="يجب أن يكون الملف بصيغة Excel أو CSV")
    
    await session.commit()
    
    return {
        "message": f"تم استيراد {imported} عنصر بنجاح",
        "imported": imported,
        "errors": errors[:10] if errors else []
    }


@pg_quantity_router.get("/planned/export")
async def export_planned_quantities(
    project_id: Optional[str] = None,
    format: str = "excel",
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Export planned quantities to Excel"""
    require_quantity_access(current_user)
    
    query = select(PlannedQuantity)
    if project_id:
        query = query.where(PlannedQuantity.project_id == project_id)
    query = query.order_by(desc(PlannedQuantity.created_at))
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    except ImportError:
        raise HTTPException(status_code=500, detail="مكتبة Excel غير متوفرة")
    
    wb = Workbook()
    ws = wb.active
    ws.title = "الكميات المخططة"
    ws.sheet_view.rightToLeft = True
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Headers
    headers = ['كود الصنف', 'اسم الصنف', 'الوحدة', 'المشروع', 'الكمية المخططة', 'الكمية المطلوبة', 'الكمية المتبقية', 'تاريخ الطلب المتوقع', 'الحالة', 'الأولوية']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
    
    # Data
    status_ar = {
        "planned": "مخطط",
        "partially_ordered": "طلب جزئي",
        "fully_ordered": "مكتمل",
        "overdue": "متأخر"
    }
    priority_ar = {1: "عالية", 2: "متوسطة", 3: "منخفضة"}
    
    for row_num, item in enumerate(items, 2):
        ws.cell(row=row_num, column=1, value=item.item_code or "-").border = thin_border
        ws.cell(row=row_num, column=2, value=item.item_name).border = thin_border
        ws.cell(row=row_num, column=3, value=item.unit).border = thin_border
        ws.cell(row=row_num, column=4, value=item.project_name).border = thin_border
        ws.cell(row=row_num, column=5, value=item.planned_quantity).border = thin_border
        ws.cell(row=row_num, column=6, value=item.ordered_quantity).border = thin_border
        ws.cell(row=row_num, column=7, value=item.remaining_quantity).border = thin_border
        ws.cell(row=row_num, column=8, value=item.expected_order_date.strftime("%Y-%m-%d") if item.expected_order_date else "-").border = thin_border
        ws.cell(row=row_num, column=9, value=status_ar.get(item.status, item.status)).border = thin_border
        ws.cell(row=row_num, column=10, value=priority_ar.get(item.priority, "متوسطة")).border = thin_border
    
    # Column widths
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 25
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 15
    ws.column_dimensions['H'].width = 18
    ws.column_dimensions['I'].width = 12
    ws.column_dimensions['J'].width = 12
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=planned_quantities_{datetime.now().strftime('%Y%m%d')}.xlsx"}
    )


# ==================== REPORTS ====================

@pg_quantity_router.get("/reports/summary")
async def get_quantity_summary_report(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get summary report for planned quantities"""
    # Allow procurement manager and general manager to view reports
    allowed_roles = [
        UserRole.QUANTITY_ENGINEER,
        UserRole.PROCUREMENT_MANAGER,
        UserRole.GENERAL_MANAGER,
        UserRole.SYSTEM_ADMIN
    ]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    query = select(PlannedQuantity)
    if project_id:
        query = query.where(PlannedQuantity.project_id == project_id)
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    total_planned = sum(item.planned_quantity for item in items)
    total_ordered = sum(item.ordered_quantity for item in items)
    total_remaining = sum(item.remaining_quantity for item in items)
    
    # Count by status
    status_counts = {}
    for item in items:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1
    
    # Overdue items (expected date passed and not fully ordered)
    now = datetime.utcnow()
    overdue_items = [
        item for item in items 
        if item.expected_order_date and item.expected_order_date < now and item.remaining_quantity > 0
    ]
    
    # Items due soon (within 10 days)
    due_soon = [
        item for item in items
        if item.expected_order_date and now <= item.expected_order_date <= now + timedelta(days=10) and item.remaining_quantity > 0
    ]
    
    # By project
    projects_data = {}
    for item in items:
        if item.project_name not in projects_data:
            projects_data[item.project_name] = {
                "project_name": item.project_name,
                "project_id": item.project_id,
                "total_items": 0,
                "planned_qty": 0,
                "ordered_qty": 0,
                "remaining_qty": 0
            }
        projects_data[item.project_name]["total_items"] += 1
        projects_data[item.project_name]["planned_qty"] += item.planned_quantity
        projects_data[item.project_name]["ordered_qty"] += item.ordered_quantity
        projects_data[item.project_name]["remaining_qty"] += item.remaining_quantity
    
    return {
        "summary": {
            "total_items": len(items),
            "total_planned_qty": total_planned,
            "total_ordered_qty": total_ordered,
            "total_remaining_qty": total_remaining,
            "completion_rate": round((total_ordered / total_planned * 100), 1) if total_planned > 0 else 0,
            "overdue_count": len(overdue_items),
            "due_soon_count": len(due_soon)
        },
        "status_breakdown": status_counts,
        "by_project": list(projects_data.values()),
        "overdue_items": [
            {
                "id": item.id,
                "item_name": item.item_name,
                "project_name": item.project_name,
                "remaining_qty": item.remaining_quantity,
                "expected_date": item.expected_order_date.isoformat() if item.expected_order_date else None,
                "days_overdue": (now - item.expected_order_date).days if item.expected_order_date else 0
            }
            for item in sorted(overdue_items, key=lambda x: x.expected_order_date or now)[:10]
        ],
        "due_soon_items": [
            {
                "id": item.id,
                "item_name": item.item_name,
                "project_name": item.project_name,
                "remaining_qty": item.remaining_quantity,
                "expected_date": item.expected_order_date.isoformat() if item.expected_order_date else None,
                "days_until": (item.expected_order_date - now).days if item.expected_order_date else 0
            }
            for item in sorted(due_soon, key=lambda x: x.expected_order_date or now)[:10]
        ]
    }


@pg_quantity_router.get("/dashboard/stats")
async def get_quantity_dashboard_stats(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get dashboard stats for quantity engineer"""
    require_quantity_access(current_user)
    
    # Get all planned items
    result = await session.execute(select(PlannedQuantity))
    items = result.scalars().all()
    
    # Get projects count
    projects_result = await session.execute(select(func.count()).select_from(Project))
    projects_count = projects_result.scalar()
    
    # Get catalog items count
    catalog_result = await session.execute(
        select(func.count()).select_from(PriceCatalogItem).where(PriceCatalogItem.is_active == True)
    )
    catalog_count = catalog_result.scalar()
    
    now = datetime.utcnow()
    overdue = len([i for i in items if i.expected_order_date and i.expected_order_date < now and i.remaining_quantity > 0])
    due_soon = len([i for i in items if i.expected_order_date and now <= i.expected_order_date <= now + timedelta(days=10) and i.remaining_quantity > 0])
    
    return {
        "total_planned_items": len(items),
        "total_planned_qty": sum(i.planned_quantity for i in items),
        "total_ordered_qty": sum(i.ordered_quantity for i in items),
        "total_remaining_qty": sum(i.remaining_quantity for i in items),
        "overdue_items": overdue,
        "due_soon_items": due_soon,
        "projects_count": projects_count,
        "catalog_items_count": catalog_count
    }
