"""
PostgreSQL Database Models - SQLAlchemy ORM
All tables for the Procurement Management System
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, 
    ForeignKey, Index, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid as uuid_lib
import enum

from .connection import Base


# ==================== ENUMS ====================

class UserRole(str, enum.Enum):
    SUPERVISOR = "supervisor"
    ENGINEER = "engineer"
    PROCUREMENT_MANAGER = "procurement_manager"
    PRINTER = "printer"
    DELIVERY_TRACKER = "delivery_tracker"
    GENERAL_MANAGER = "general_manager"
    SYSTEM_ADMIN = "system_admin"
    QUANTITY_ENGINEER = "quantity_engineer"  # مهندس الكميات - دور جديد


class RequestStatus(str, enum.Enum):
    PENDING_ENGINEER = "pending_engineer"
    APPROVED_BY_ENGINEER = "approved_by_engineer"
    REJECTED_BY_ENGINEER = "rejected_by_engineer"
    REJECTED_BY_MANAGER = "rejected_by_manager"
    PURCHASE_ORDER_ISSUED = "purchase_order_issued"
    PARTIALLY_ORDERED = "partially_ordered"


class OrderStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"
    PENDING_GM_APPROVAL = "pending_gm_approval"
    APPROVED = "approved"
    PRINTED = "printed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    PARTIALLY_DELIVERED = "partially_delivered"


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


# ==================== USER MODEL ====================

class User(Base):
    """User table - stores all system users"""
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    supervisor_prefix: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    assigned_projects: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array as text
    assigned_engineers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array as text
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_users_role_created_at', 'role', 'created_at'),
    )


# ==================== PROJECT MODEL ====================

class Project(Base):
    """Project table - stores all projects"""
    __tablename__ = "projects"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_by_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_projects_status_created_at', 'status', 'created_at'),
    )


# ==================== SUPPLIER MODEL ====================

class Supplier(Base):
    """Supplier table - stores all suppliers"""
    __tablename__ = "suppliers"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_suppliers_name_created_at', 'name', 'created_at'),
    )


# ==================== BUDGET CATEGORY MODELS ====================

class DefaultBudgetCategory(Base):
    """Default budget categories - template categories for new projects"""
    __tablename__ = "default_budget_categories"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_budget: Mapped[float] = mapped_column(Float, default=0)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_by_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BudgetCategory(Base):
    """Budget categories - per project budget tracking"""
    __tablename__ = "budget_categories"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # كود التصنيف
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    estimated_budget: Mapped[float] = mapped_column(Float, default=0)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_by_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_budget_categories_project_name', 'project_id', 'name'),
        Index('idx_budget_categories_code', 'code'),
    )


# ==================== MATERIAL REQUEST MODELS ====================

class MaterialRequest(Base):
    """Material request - main request table"""
    __tablename__ = "material_requests"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    request_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    request_seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    supervisor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    supervisor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    engineer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    engineer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending_engineer", index=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_delivery_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_requests_status_created_at', 'status', 'created_at'),
        Index('idx_requests_supervisor_seq', 'supervisor_id', 'request_seq'),
        Index('idx_requests_project_status', 'project_id', 'status', 'created_at'),
        Index('idx_requests_engineer_status', 'engineer_id', 'status'),
    )


class MaterialRequestItem(Base):
    """Material request items - individual items in a request"""
    __tablename__ = "material_request_items"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("material_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="قطعة")
    estimated_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    item_index: Mapped[int] = mapped_column(Integer, default=0)  # Order in the request


# ==================== PURCHASE ORDER MODELS ====================

class PurchaseOrder(Base):
    """Purchase order - main order table"""
    __tablename__ = "purchase_orders"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    order_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    order_seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("material_requests.id"), nullable=False, index=True)
    request_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("suppliers.id"), nullable=True, index=True)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("budget_categories.id"), nullable=True, index=True)
    category_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    manager_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    manager_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supervisor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    engineer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending_approval", index=True)
    needs_gm_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approved_by_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gm_approved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    gm_approved_by_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    terms_conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_delivery_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    supplier_receipt_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    supplier_invoice_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    received_by_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    received_by_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    gm_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    printed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_orders_status_created_at', 'status', 'created_at'),
        Index('idx_orders_manager_status', 'manager_id', 'status'),
        Index('idx_orders_project_created_at', 'project_name', 'created_at'),
        Index('idx_orders_supplier_created_at', 'supplier_id', 'created_at'),
        Index('idx_orders_category_amount', 'category_id', 'total_amount'),
    )


class PurchaseOrderItem(Base):
    """Purchase order items - individual items in an order"""
    __tablename__ = "purchase_order_items"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="قطعة")
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    total_price: Mapped[float] = mapped_column(Float, default=0)
    delivered_quantity: Mapped[int] = mapped_column(Integer, default=0)
    item_index: Mapped[int] = mapped_column(Integer, default=0)


# ==================== DELIVERY RECORD MODEL ====================

class DeliveryRecord(Base):
    """Delivery records - tracks partial deliveries"""
    __tablename__ = "delivery_records"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("purchase_orders.id"), nullable=False, index=True)
    items_delivered: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    delivery_date: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    delivered_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    received_by: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_delivery_order_date', 'order_id', 'delivery_date'),
    )


# ==================== AUDIT LOG MODEL ====================

class AuditLog(Base):
    """Audit logs - tracks all system actions"""
    __tablename__ = "audit_logs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    changes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON object
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_role: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_entity_timestamp', 'entity_type', 'timestamp'),
    )


# ==================== SYSTEM SETTINGS MODEL ====================

class SystemSetting(Base):
    """System settings - configurable system parameters"""
    __tablename__ = "system_settings"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    updated_by_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==================== PRICE CATALOG MODEL ====================

class PriceCatalogItem(Base):
    """Price catalog - standard item pricing"""
    __tablename__ = "price_catalog"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(50), default="قطعة")
    supplier_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("suppliers.id"), nullable=True, index=True)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="SAR")
    validity_until: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    category_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("budget_categories.id"), nullable=True, index=True)
    category_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_by_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_catalog_name_active', 'name', 'is_active'),
    )


# ==================== ITEM ALIAS MODEL ====================

class ItemAlias(Base):
    """Item aliases - maps alternative names to catalog items"""
    __tablename__ = "item_aliases"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    alias_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    catalog_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("price_catalog.id"), nullable=False, index=True)
    catalog_item_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_by_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==================== ATTACHMENT MODEL ====================

class Attachment(Base):
    """Attachments - file attachments for requests/orders"""
    __tablename__ = "attachments"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    uploaded_by_name: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_attachments_entity', 'entity_type', 'entity_id'),
    )


# ==================== PLANNED QUANTITY MODEL ====================

class PlannedQuantityStatus(str, enum.Enum):
    PLANNED = "planned"  # مخطط
    PARTIALLY_ORDERED = "partially_ordered"  # تم طلب جزء
    FULLY_ORDERED = "fully_ordered"  # تم الطلب بالكامل
    OVERDUE = "overdue"  # متأخر


class PlannedQuantity(Base):
    """Planned quantities - الكميات المخططة من مهندس الكميات"""
    __tablename__ = "planned_quantities"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid_lib.uuid4()))
    
    # Item details
    item_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    item_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(50), default="قطعة")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Quantity details
    planned_quantity: Mapped[float] = mapped_column(Float, nullable=False)  # الكمية المخططة
    ordered_quantity: Mapped[float] = mapped_column(Float, default=0)  # الكمية المطلوبة
    remaining_quantity: Mapped[float] = mapped_column(Float, nullable=False)  # الكمية المتبقية
    
    # Project reference
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Category (optional)
    category_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("budget_categories.id"), nullable=True)
    category_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Catalog reference (optional)
    catalog_item_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("price_catalog.id"), nullable=True)
    
    # Expected order date
    expected_order_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="planned", index=True)
    
    # Priority (1=high, 2=medium, 3=low)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Tracking
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_by_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    updated_by_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    __table_args__ = (
        Index('idx_planned_project_status', 'project_id', 'status'),
        Index('idx_planned_expected_date', 'expected_order_date'),
    )
