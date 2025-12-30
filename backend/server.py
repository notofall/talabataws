from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create database indexes for better performance with high load
async def create_indexes():
    """Create indexes for optimized queries with 500+ daily operations and 20+ concurrent users"""
    try:
        # Users collection indexes
        await db.users.create_index("id", unique=True)
        await db.users.create_index("email", unique=True)
        await db.users.create_index("role")
        await db.users.create_index("supervisor_prefix")
        await db.users.create_index([("role", 1), ("created_at", -1)])  # For role-based listings
        
        # Material requests indexes - optimized for high volume
        await db.material_requests.create_index("id", unique=True)
        await db.material_requests.create_index("supervisor_id")
        await db.material_requests.create_index("engineer_id")
        await db.material_requests.create_index("status")
        await db.material_requests.create_index("created_at")
        await db.material_requests.create_index("request_number")
        await db.material_requests.create_index("project_id")
        await db.material_requests.create_index([("supervisor_id", 1), ("request_seq", -1)])
        await db.material_requests.create_index([("status", 1), ("created_at", -1)])
        await db.material_requests.create_index([("project_id", 1), ("status", 1), ("created_at", -1)])  # Project filtering
        await db.material_requests.create_index([("engineer_id", 1), ("status", 1)])  # Engineer dashboard
        await db.material_requests.create_index("$**", name="text_search_idx")  # Text search
        
        # Purchase orders indexes - optimized for manager dashboard and reports
        await db.purchase_orders.create_index("id", unique=True)
        await db.purchase_orders.create_index("request_id")
        await db.purchase_orders.create_index("manager_id")
        await db.purchase_orders.create_index("status")
        await db.purchase_orders.create_index("created_at")
        await db.purchase_orders.create_index("supplier_id")
        await db.purchase_orders.create_index("supplier_name")
        await db.purchase_orders.create_index("project_name")
        await db.purchase_orders.create_index("category_id")
        await db.purchase_orders.create_index("supplier_receipt_number")
        await db.purchase_orders.create_index([("status", 1), ("created_at", -1)])
        await db.purchase_orders.create_index([("manager_id", 1), ("status", 1)])
        await db.purchase_orders.create_index([("project_name", 1), ("created_at", -1)])  # Project reports
        await db.purchase_orders.create_index([("supplier_id", 1), ("created_at", -1)])  # Supplier reports
        await db.purchase_orders.create_index([("category_id", 1), ("total_amount", 1)])  # Budget tracking
        
        # Suppliers indexes
        await db.suppliers.create_index("id", unique=True)
        await db.suppliers.create_index("name")
        await db.suppliers.create_index([("name", 1), ("created_at", -1)])
        
        # Delivery records indexes - optimized for tracking
        await db.delivery_records.create_index("id", unique=True)
        await db.delivery_records.create_index("order_id")
        await db.delivery_records.create_index("delivery_date")
        await db.delivery_records.create_index([("order_id", 1), ("delivery_date", -1)])
        await db.delivery_records.create_index("delivered_by")
        
        # Budget categories indexes
        await db.budget_categories.create_index("id", unique=True)
        await db.budget_categories.create_index("project_id")
        await db.budget_categories.create_index("created_by")
        await db.budget_categories.create_index([("project_id", 1), ("name", 1)])  # Budget reports
        
        # Default budget categories indexes (global templates)
        await db.default_budget_categories.create_index("id", unique=True)
        await db.default_budget_categories.create_index("created_by")
        
        # Projects indexes
        await db.projects.create_index("id", unique=True)
        await db.projects.create_index("status")
        await db.projects.create_index("created_by")
        await db.projects.create_index("name")
        await db.projects.create_index([("status", 1), ("created_at", -1)])
        
        # Audit logs indexes - optimized for compliance queries
        await db.audit_logs.create_index("id", unique=True)
        await db.audit_logs.create_index([("entity_type", 1), ("entity_id", 1)])
        await db.audit_logs.create_index("timestamp")
        await db.audit_logs.create_index("user_id")
        await db.audit_logs.create_index([("entity_type", 1), ("timestamp", -1)])  # Audit reports
        
        # Attachments indexes
        await db.attachments.create_index("id", unique=True)
        await db.attachments.create_index([("entity_type", 1), ("entity_id", 1)])
        
        print("✅ Database indexes created successfully for high-performance operations")
    except Exception as e:
        print(f"⚠️ Index creation warning: {e}")

# JWT Settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Create the main app
app = FastAPI(title="نظام إدارة طلبات المواد")

# Health check endpoint at root level (for Kubernetes)
@app.get("/health")
async def root_health_check():
    """Health check endpoint for Kubernetes liveness/readiness probes"""
    return {"status": "healthy"}

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ==================== MODELS ====================

class UserRole:
    SUPERVISOR = "supervisor"
    ENGINEER = "engineer"
    PROCUREMENT_MANAGER = "procurement_manager"
    PRINTER = "printer"  # موظف الطباعة
    DELIVERY_TRACKER = "delivery_tracker"  # متابع التوريد

class RequestStatus:
    PENDING_ENGINEER = "pending_engineer"
    APPROVED_BY_ENGINEER = "approved_by_engineer"
    REJECTED_BY_ENGINEER = "rejected_by_engineer"
    PURCHASE_ORDER_ISSUED = "purchase_order_issued"
    PARTIALLY_ORDERED = "partially_ordered"  # تم إصدار بعض أوامر الشراء

class PurchaseOrderStatus:
    PENDING_APPROVAL = "pending_approval"  # بانتظار اعتماد مدير المشتريات
    APPROVED = "approved"  # معتمد - جاهز للطباعة
    PRINTED = "printed"  # تمت الطباعة
    SHIPPED = "shipped"  # تم الشحن
    DELIVERED = "delivered"  # تم التسليم
    PARTIALLY_DELIVERED = "partially_delivered"  # تسليم جزئي

# User Models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str  # supervisor, engineer, procurement_manager

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    supervisor_prefix: Optional[str] = None  # حرف المشرف (A, B, C...)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Password Models
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# Supplier Models
class SupplierCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None

class SupplierResponse(BaseModel):
    id: str
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    created_at: str

# Material Item Model (single item in a request)
class MaterialItem(BaseModel):
    name: str
    quantity: int
    unit: str = "قطعة"  # الوحدة: قطعة، طن، متر، كيس، الخ
    estimated_price: Optional[float] = None  # السعر التقديري (اختياري)

# Purchase Order Item with Price
class PurchaseOrderItem(BaseModel):
    name: str
    quantity: int
    unit: str = "قطعة"
    unit_price: float = 0  # سعر الوحدة
    total_price: float = 0  # السعر الإجمالي
    delivered_quantity: int = 0  # الكمية المستلمة

# Material Request Models
class MaterialRequestCreate(BaseModel):
    items: List[MaterialItem]
    project_id: str  # معرف المشروع
    reason: str
    engineer_id: str
    expected_delivery_date: Optional[str] = None  # تاريخ الحاجة المتوقع

class MaterialRequestUpdate(BaseModel):
    status: str
    rejection_reason: Optional[str] = None

class MaterialRequestResponse(BaseModel):
    id: str
    request_number: Optional[str] = None  # رقم الطلب المتسلسل للمشرف (A1, A2, B1...)
    request_seq: Optional[int] = None  # الرقم التسلسلي فقط
    items: List[MaterialItem]
    project_id: Optional[str] = None
    project_name: str
    reason: str
    supervisor_id: str
    supervisor_name: str
    engineer_id: str
    engineer_name: str
    status: str
    rejection_reason: Optional[str] = None
    expected_delivery_date: Optional[str] = None  # تاريخ الحاجة المتوقع
    created_at: str
    updated_at: str

# Purchase Order Models
class PurchaseOrderCreate(BaseModel):
    request_id: str
    supplier_id: Optional[str] = None  # معرف المورد من القائمة
    supplier_name: str  # اسم المورد (يدوي أو من القائمة)
    selected_items: List[int]  # قائمة فهارس الأصناف المختارة من الطلب الأصلي
    item_prices: Optional[List[dict]] = None  # أسعار الأصناف [{"index": 0, "unit_price": 100}] - اختياري
    category_id: Optional[str] = None  # تصنيف الميزانية
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None  # الشروط والأحكام
    expected_delivery_date: Optional[str] = None  # تاريخ التسليم المتوقع

class PurchaseOrderUpdate(BaseModel):
    """تحديث أمر الشراء - جميع الحقول اختيارية"""
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    item_prices: Optional[List[dict]] = None  # أسعار الأصناف [{"name": "...", "unit_price": 100}]
    category_id: Optional[str] = None
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None
    expected_delivery_date: Optional[str] = None
    supplier_invoice_number: Optional[str] = None  # رقم فاتورة المورد

class PurchaseOrderResponse(BaseModel):
    id: str
    request_id: str
    request_number: Optional[str] = None  # رقم الطلب المتسلسل (A1, A2, B1...)
    items: List[dict]  # Changed to dict to include prices
    project_name: str
    project_id: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: str
    category_id: Optional[str] = None  # تصنيف الميزانية
    category_name: Optional[str] = None  # اسم التصنيف
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None
    manager_id: str
    manager_name: str
    supervisor_name: Optional[str] = None
    engineer_name: Optional[str] = None
    status: str  # pending_approval, approved, printed, shipped, delivered
    total_amount: float = 0  # المبلغ الإجمالي
    expected_delivery_date: Optional[str] = None
    created_at: str
    approved_at: Optional[str] = None
    printed_at: Optional[str] = None
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    delivery_notes: Optional[str] = None
    supplier_receipt_number: Optional[str] = None  # رقم استلام المورد
    supplier_invoice_number: Optional[str] = None  # رقم فاتورة المورد
    received_by_id: Optional[str] = None  # معرف المستلم
    received_by_name: Optional[str] = None  # اسم المستلم
    updated_at: Optional[str] = None  # تاريخ آخر تحديث

# Delivery Record Model
class DeliveryRecord(BaseModel):
    order_id: str
    items_delivered: List[dict]  # [{"name": "...", "quantity_delivered": 5}]
    delivery_date: str
    received_by: str  # اسم المستلم
    notes: Optional[str] = None

# Default Budget Category Models - التصنيفات الافتراضية (العامة)
class DefaultBudgetCategoryCreate(BaseModel):
    name: str  # اسم التصنيف (سباكة، كهرباء، رخام...)
    default_budget: float = 0  # الميزانية الافتراضية (اختياري)

class DefaultBudgetCategoryUpdate(BaseModel):
    name: Optional[str] = None
    default_budget: Optional[float] = None

# Budget Category Models - تصنيفات الميزانية
class BudgetCategoryCreate(BaseModel):
    name: str  # اسم التصنيف (سباكة، كهرباء، رخام...)
    project_id: str  # معرف المشروع
    estimated_budget: float  # الميزانية التقديرية

class BudgetCategoryUpdate(BaseModel):
    name: Optional[str] = None
    estimated_budget: Optional[float] = None

class BudgetCategoryResponse(BaseModel):
    id: str
    name: str
    project_name: str
    project_id: Optional[str] = None
    estimated_budget: float
    actual_spent: float = 0  # المصروف الفعلي (يُحسب من أوامر الشراء)
    remaining: float = 0  # المتبقي
    variance_percentage: float = 0  # نسبة الفرق
    created_by: str
    created_by_name: str
    created_at: str

# Project Models - إدارة المشاريع
class ProjectCreate(BaseModel):
    name: str  # اسم المشروع
    owner_name: str  # اسم مالك المشروع
    description: Optional[str] = None
    location: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    owner_name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None  # active, completed, on_hold

class ProjectResponse(BaseModel):
    id: str
    name: str
    owner_name: str
    description: Optional[str] = None
    location: Optional[str] = None
    status: str = "active"
    created_by: str
    created_by_name: str
    created_at: str
    total_requests: int = 0
    total_orders: int = 0
    total_budget: float = 0
    total_spent: float = 0

# Audit Trail Model - سجل المراجعة
class AuditLogResponse(BaseModel):
    id: str
    entity_type: str  # project, request, order, category
    entity_id: str
    action: str  # create, update, delete, approve, reject, ship, deliver
    changes: Optional[dict] = None  # التغييرات {field: {old: x, new: y}}
    user_id: str
    user_name: str
    user_role: str
    timestamp: str
    description: str  # وصف مختصر للإجراء

# Attachment Models - المرفقات
class AttachmentResponse(BaseModel):
    id: str
    entity_type: str  # request, order
    entity_id: str
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    uploaded_by: str
    uploaded_by_name: str
    uploaded_at: str

# ==================== HELPER FUNCTIONS ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="رمز الدخول غير صالح")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="المستخدم غير موجود")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="رمز الدخول غير صالح")

# Audit Trail Helper Function
async def log_audit(
    entity_type: str,
    entity_id: str,
    action: str,
    user: dict,
    description: str,
    changes: dict = None
):
    """تسجيل حدث في سجل المراجعة"""
    audit_doc = {
        "id": str(uuid.uuid4()),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "changes": changes,
        "user_id": user["id"],
        "user_name": user["name"],
        "user_role": user["role"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": description
    }
    await db.audit_logs.insert_one(audit_doc)

# ==================== EMAIL SERVICE ====================

async def get_supervisor_prefix(supervisor_id: str) -> str:
    """Get or assign the supervisor's prefix letter (A, B, C...)"""
    supervisor = await db.users.find_one({"id": supervisor_id}, {"_id": 0})
    if not supervisor:
        return "X"
    
    # If supervisor already has a prefix, return it
    if supervisor.get("supervisor_prefix"):
        return supervisor["supervisor_prefix"]
    
    # Assign a new prefix based on the number of supervisors with prefixes
    existing_prefixes = await db.users.distinct("supervisor_prefix", {"role": UserRole.SUPERVISOR, "supervisor_prefix": {"$exists": True, "$ne": None}})
    
    # Generate next letter (A, B, C, ..., Z, AA, AB, ...)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    used_count = len(existing_prefixes)
    
    if used_count < 26:
        new_prefix = alphabet[used_count]
    else:
        # For more than 26 supervisors: AA, AB, AC...
        first_letter = alphabet[(used_count - 26) // 26]
        second_letter = alphabet[(used_count - 26) % 26]
        new_prefix = first_letter + second_letter
    
    # Save the prefix to the supervisor
    await db.users.update_one(
        {"id": supervisor_id},
        {"$set": {"supervisor_prefix": new_prefix}}
    )
    
    return new_prefix

async def get_next_request_number(supervisor_id: str) -> tuple:
    """Get the next sequential request number for a supervisor (e.g., A1, A2, B1...)"""
    # Get supervisor prefix
    prefix = await get_supervisor_prefix(supervisor_id)
    
    # Find the highest request sequence for this supervisor
    last_request = await db.material_requests.find_one(
        {"supervisor_id": supervisor_id},
        {"request_seq": 1},
        sort=[("request_seq", -1)]
    )
    
    # Get next sequence number
    if last_request and last_request.get("request_seq"):
        next_seq = last_request["request_seq"] + 1
    else:
        next_seq = 1
    
    return prefix + str(next_seq), next_seq

async def send_email_notification(to_email: str, subject: str, content: str):
    """Send email notification using SendGrid"""
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
    sender_email = os.environ.get('SENDER_EMAIL')
    
    if not sendgrid_api_key or not sender_email:
        logging.warning("SendGrid not configured, skipping email")
        return False
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        message = Mail(
            from_email=sender_email,
            to_emails=to_email,
            subject=subject,
            html_content=content
        )
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل مسبقاً")
    
    # Validate role
    valid_roles = [UserRole.SUPERVISOR, UserRole.ENGINEER, UserRole.PROCUREMENT_MANAGER, UserRole.PRINTER, UserRole.DELIVERY_TRACKER]
    if user_data.role not in valid_roles:
        raise HTTPException(status_code=400, detail="الدور غير صالح")
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)
    
    user_doc = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "password": hashed_password,
        "role": user_data.role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    access_token = create_access_token({"sub": user_id})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user_id,
            name=user_data.name,
            email=user_data.email,
            role=user_data.role
        )
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="البريد الإلكتروني أو كلمة المرور غير صحيحة")
    
    access_token = create_access_token({"sub": user["id"]})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user["id"],
            name=user["name"],
            email=user["email"],
            role=user["role"]
        )
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)

@api_router.post("/auth/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """تغيير كلمة المرور للمستخدم الحالي"""
    # Get user with password
    user = await db.users.find_one({"id": current_user["id"]})
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    # Verify current password
    if not verify_password(password_data.current_password, user["password"]):
        raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة")
    
    # Validate new password
    if len(password_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل")
    
    # Hash and update new password
    new_hashed_password = get_password_hash(password_data.new_password)
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"password": new_hashed_password}}
    )
    
    # Log audit
    await log_audit(
        entity_type="user",
        entity_id=current_user["id"],
        action="change_password",
        user=current_user,
        description="تم تغيير كلمة المرور"
    )
    
    return {"message": "تم تغيير كلمة المرور بنجاح"}

@api_router.post("/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """طلب استعادة كلمة المرور - يرسل كلمة مرور جديدة عبر البريد"""
    # Find user by email
    user = await db.users.find_one({"email": request.email})
    if not user:
        # Return success even if user not found for security
        return {"message": "إذا كان البريد مسجلاً، ستصلك كلمة المرور الجديدة"}
    
    # Generate random password
    import random
    import string
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    # Hash and update password
    hashed_password = get_password_hash(new_password)
    await db.users.update_one(
        {"email": request.email},
        {"$set": {"password": hashed_password}}
    )
    
    # Send email with new password
    email_content = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif; padding: 20px; background: #f9fafb; border-radius: 8px;">
        <h2 style="color: #ea580c; margin-bottom: 20px;">استعادة كلمة المرور</h2>
        <p style="font-size: 16px; color: #374151;">مرحباً {user['name']},</p>
        <p style="font-size: 14px; color: #6b7280;">تم إنشاء كلمة مرور جديدة لحسابك:</p>
        <div style="background: #fff; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center; border: 2px solid #ea580c;">
            <p style="font-size: 24px; font-weight: bold; color: #1f2937; letter-spacing: 3px; margin: 0;">{new_password}</p>
        </div>
        <p style="font-size: 14px; color: #6b7280;">يرجى تسجيل الدخول وتغيير كلمة المرور فوراً.</p>
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #e5e7eb;">
        <p style="font-size: 12px; color: #9ca3af;">نظام إدارة طلبات المواد</p>
    </div>
    """
    
    email_sent = await send_email_notification(
        request.email,
        "استعادة كلمة المرور - نظام إدارة طلبات المواد",
        email_content
    )
    
    if email_sent:
        return {"message": "تم إرسال كلمة المرور الجديدة إلى بريدك الإلكتروني"}
    else:
        # If email failed, still return success but log it
        logging.warning(f"Email not configured - New password for {request.email}: {new_password}")
        return {"message": "تم إنشاء كلمة مرور جديدة. إذا لم تصلك الرسالة، تواصل مع الإدارة.", "temp_password": new_password}

# ==================== USERS ROUTES ====================

@api_router.get("/users/engineers", response_model=List[UserResponse])
async def get_engineers(current_user: dict = Depends(get_current_user)):
    engineers = await db.users.find(
        {"role": UserRole.ENGINEER},
        {"_id": 0, "password": 0}
    ).to_list(100)
    return [UserResponse(**eng) for eng in engineers]

@api_router.get("/users", response_model=List[UserResponse])
async def get_all_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(100)
    return [UserResponse(**u) for u in users]

# ==================== PROJECTS ROUTES ====================

@api_router.post("/projects")
async def create_project(
    project_data: ProjectCreate,
    current_user: dict = Depends(get_current_user)
):
    """إنشاء مشروع جديد - المشرف فقط"""
    if current_user["role"] != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="فقط المشرف يمكنه إنشاء المشاريع")
    
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    project_doc = {
        "id": project_id,
        "name": project_data.name,
        "owner_name": project_data.owner_name,
        "description": project_data.description,
        "location": project_data.location,
        "status": "active",
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "created_at": now
    }
    
    await db.projects.insert_one(project_doc)
    
    # نسخ التصنيفات الافتراضية تلقائياً للمشروع الجديد
    default_categories = await db.default_budget_categories.find({}, {"_id": 0}).to_list(100)
    categories_added = 0
    for default_cat in default_categories:
        category_id = str(uuid.uuid4())
        category_doc = {
            "id": category_id,
            "name": default_cat["name"],
            "project_id": project_id,
            "project_name": project_data.name,
            "estimated_budget": default_cat["default_budget"],
            "created_by": default_cat["created_by"],
            "created_by_name": default_cat["created_by_name"],
            "created_at": now
        }
        await db.budget_categories.insert_one(category_doc)
        categories_added += 1
    
    # Log audit
    await log_audit(
        entity_type="project",
        entity_id=project_id,
        action="create",
        user=current_user,
        description=f"إنشاء مشروع جديد: {project_data.name} (مع {categories_added} تصنيف)"
    )
    
    return {
        **{k: v for k, v in project_doc.items() if k != "_id"},
        "total_requests": 0,
        "total_orders": 0,
        "total_budget": 0,
        "total_spent": 0,
        "categories_added": categories_added
    }

@api_router.get("/projects")
async def get_projects(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """الحصول على قائمة المشاريع"""
    query = {}
    if status:
        query["status"] = status
    
    projects = await db.projects.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    # Calculate stats for each project
    result = []
    for p in projects:
        # Get request count
        request_count = await db.material_requests.count_documents({"project_id": p["id"]})
        
        # Get order count and total spent
        pipeline = [
            {"$match": {"project_id": p["id"]}},
            {"$group": {"_id": None, "count": {"$sum": 1}, "total": {"$sum": "$total_amount"}}}
        ]
        order_stats = await db.purchase_orders.aggregate(pipeline).to_list(1)
        order_count = order_stats[0]["count"] if order_stats else 0
        total_spent = order_stats[0]["total"] if order_stats else 0
        
        # Get total budget from categories
        budget_pipeline = [
            {"$match": {"project_id": p["id"]}},
            {"$group": {"_id": None, "total": {"$sum": "$estimated_budget"}}}
        ]
        budget_stats = await db.budget_categories.aggregate(budget_pipeline).to_list(1)
        total_budget = budget_stats[0]["total"] if budget_stats else 0
        
        result.append({
            **p,
            "total_requests": request_count,
            "total_orders": order_count,
            "total_budget": total_budget,
            "total_spent": total_spent
        })
    
    return result

@api_router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """الحصول على تفاصيل مشروع"""
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    # Get stats
    request_count = await db.material_requests.count_documents({"project_id": project_id})
    
    pipeline = [
        {"$match": {"project_id": project_id}},
        {"$group": {"_id": None, "count": {"$sum": 1}, "total": {"$sum": "$total_amount"}}}
    ]
    order_stats = await db.purchase_orders.aggregate(pipeline).to_list(1)
    
    budget_pipeline = [
        {"$match": {"project_id": project_id}},
        {"$group": {"_id": None, "total": {"$sum": "$estimated_budget"}}}
    ]
    budget_stats = await db.budget_categories.aggregate(budget_pipeline).to_list(1)
    
    return {
        **project,
        "total_requests": request_count,
        "total_orders": order_stats[0]["count"] if order_stats else 0,
        "total_budget": budget_stats[0]["total"] if budget_stats else 0,
        "total_spent": order_stats[0]["total"] if order_stats else 0
    }

@api_router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    update_data: ProjectUpdate,
    current_user: dict = Depends(get_current_user)
):
    """تحديث مشروع - المشرف فقط"""
    if current_user["role"] != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="فقط المشرف يمكنه تعديل المشاريع")
    
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    update_fields = {}
    changes = {}
    
    for field in ["name", "owner_name", "description", "location", "status"]:
        new_value = getattr(update_data, field)
        if new_value is not None and project.get(field) != new_value:
            changes[field] = {"old": project.get(field), "new": new_value}
            update_fields[field] = new_value
    
    if update_fields:
        await db.projects.update_one({"id": project_id}, {"$set": update_fields})
        
        await log_audit(
            entity_type="project",
            entity_id=project_id,
            action="update",
            user=current_user,
            description=f"تحديث المشروع: {project['name']}",
            changes=changes
        )
    
    return {"message": "تم تحديث المشروع بنجاح"}

@api_router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """حذف مشروع - المشرف فقط"""
    if current_user["role"] != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="فقط المشرف يمكنه حذف المشاريع")
    
    # Check if project has requests
    request_count = await db.material_requests.count_documents({"project_id": project_id})
    if request_count > 0:
        raise HTTPException(status_code=400, detail=f"لا يمكن حذف المشروع لوجود {request_count} طلبات مرتبطة به")
    
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    await db.projects.delete_one({"id": project_id})
    
    await log_audit(
        entity_type="project",
        entity_id=project_id,
        action="delete",
        user=current_user,
        description=f"حذف المشروع: {project['name']}"
    )
    
    return {"message": "تم حذف المشروع بنجاح"}

# ==================== DEFAULT BUDGET CATEGORIES ROUTES ====================
# التصنيفات الافتراضية (العامة) التي تُنسخ تلقائياً لكل مشروع جديد

@api_router.get("/default-budget-categories")
async def get_default_budget_categories(current_user: dict = Depends(get_current_user)):
    """الحصول على التصنيفات الافتراضية"""
    categories = await db.default_budget_categories.find({}, {"_id": 0}).sort("created_at", 1).to_list(100)
    return categories

@api_router.post("/default-budget-categories")
async def create_default_budget_category(
    category_data: DefaultBudgetCategoryCreate,
    current_user: dict = Depends(get_current_user)
):
    """إنشاء تصنيف افتراضي جديد - مدير المشتريات فقط"""
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه إدارة التصنيفات الافتراضية")
    
    # Check if category with same name exists
    existing = await db.default_budget_categories.find_one({"name": category_data.name})
    if existing:
        raise HTTPException(status_code=400, detail="يوجد تصنيف بنفس الاسم")
    
    category_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    category_doc = {
        "id": category_id,
        "name": category_data.name,
        "default_budget": category_data.default_budget,
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "created_at": now
    }
    
    await db.default_budget_categories.insert_one(category_doc)
    
    await log_audit(
        entity_type="default_category",
        entity_id=category_id,
        action="create",
        user=current_user,
        description=f"إنشاء تصنيف افتراضي: {category_data.name}"
    )
    
    return {k: v for k, v in category_doc.items() if k != "_id"}

@api_router.put("/default-budget-categories/{category_id}")
async def update_default_budget_category(
    category_id: str,
    update_data: DefaultBudgetCategoryUpdate,
    current_user: dict = Depends(get_current_user)
):
    """تحديث تصنيف افتراضي - مدير المشتريات فقط"""
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه تعديل التصنيفات الافتراضية")
    
    category = await db.default_budget_categories.find_one({"id": category_id}, {"_id": 0})
    if not category:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")
    
    update_fields = {}
    if update_data.name is not None:
        update_fields["name"] = update_data.name
    if update_data.default_budget is not None:
        update_fields["default_budget"] = update_data.default_budget
    
    if update_fields:
        await db.default_budget_categories.update_one(
            {"id": category_id},
            {"$set": update_fields}
        )
    
    return {"message": "تم تحديث التصنيف الافتراضي بنجاح"}

@api_router.delete("/default-budget-categories/{category_id}")
async def delete_default_budget_category(
    category_id: str,
    current_user: dict = Depends(get_current_user)
):
    """حذف تصنيف افتراضي - مدير المشتريات فقط"""
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه حذف التصنيفات الافتراضية")
    
    category = await db.default_budget_categories.find_one({"id": category_id}, {"_id": 0})
    if not category:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")
    
    await db.default_budget_categories.delete_one({"id": category_id})
    
    await log_audit(
        entity_type="default_category",
        entity_id=category_id,
        action="delete",
        user=current_user,
        description=f"حذف تصنيف افتراضي: {category['name']}"
    )
    
    return {"message": "تم حذف التصنيف الافتراضي بنجاح"}

@api_router.post("/default-budget-categories/apply-to-project/{project_id}")
async def apply_default_categories_to_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """تطبيق التصنيفات الافتراضية على مشروع موجود - مدير المشتريات فقط"""
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه تطبيق التصنيفات")
    
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    # Get default categories
    default_categories = await db.default_budget_categories.find({}, {"_id": 0}).to_list(100)
    if not default_categories:
        raise HTTPException(status_code=400, detail="لا توجد تصنيفات افتراضية")
    
    # Get existing categories for this project
    existing_names = set()
    existing = await db.budget_categories.find({"project_id": project_id}, {"name": 1}).to_list(100)
    for cat in existing:
        existing_names.add(cat["name"])
    
    now = datetime.now(timezone.utc).isoformat()
    added_count = 0
    
    for default_cat in default_categories:
        # Skip if category with same name already exists
        if default_cat["name"] in existing_names:
            continue
        
        category_id = str(uuid.uuid4())
        category_doc = {
            "id": category_id,
            "name": default_cat["name"],
            "project_id": project_id,
            "project_name": project["name"],
            "estimated_budget": default_cat["default_budget"],
            "created_by": current_user["id"],
            "created_by_name": current_user["name"],
            "created_at": now
        }
        await db.budget_categories.insert_one(category_doc)
        added_count += 1
    
    return {"message": f"تم إضافة {added_count} تصنيف للمشروع", "added_count": added_count}

# ==================== BUDGET CATEGORIES ROUTES ====================

@api_router.post("/budget-categories")
async def create_budget_category(
    category_data: BudgetCategoryCreate,
    current_user: dict = Depends(get_current_user)
):
    """إنشاء تصنيف ميزانية جديد - مدير المشتريات فقط"""
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه إدارة التصنيفات")
    
    # Get project name
    project = await db.projects.find_one({"id": category_data.project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    category_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    category_doc = {
        "id": category_id,
        "name": category_data.name,
        "project_id": category_data.project_id,
        "project_name": project["name"],
        "estimated_budget": category_data.estimated_budget,
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "created_at": now
    }
    
    await db.budget_categories.insert_one(category_doc)
    
    await log_audit(
        entity_type="category",
        entity_id=category_id,
        action="create",
        user=current_user,
        description=f"إنشاء تصنيف ميزانية: {category_data.name} للمشروع {project['name']}"
    )
    
    # Return without _id
    return {
        "id": category_id,
        "name": category_data.name,
        "project_id": category_data.project_id,
        "project_name": project["name"],
        "estimated_budget": category_data.estimated_budget,
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "created_at": now,
        "actual_spent": 0,
        "remaining": category_data.estimated_budget,
        "variance_percentage": 0
    }

@api_router.get("/budget-categories")
async def get_budget_categories(
    project_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """الحصول على تصنيفات الميزانية مع المصروف الفعلي"""
    query = {}
    if project_id:
        query["project_id"] = project_id
    
    categories = await db.budget_categories.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    # Calculate actual spent for each category
    result = []
    for cat in categories:
        # Get total spent from purchase orders in this category
        pipeline = [
            {"$match": {"category_id": cat["id"]}},
            {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
        ]
        spent_result = await db.purchase_orders.aggregate(pipeline).to_list(1)
        actual_spent = spent_result[0]["total"] if spent_result else 0
        
        remaining = cat["estimated_budget"] - actual_spent
        variance_percentage = ((actual_spent - cat["estimated_budget"]) / cat["estimated_budget"] * 100) if cat["estimated_budget"] > 0 else 0
        
        result.append({
            **cat,
            "actual_spent": actual_spent,
            "remaining": remaining,
            "variance_percentage": round(variance_percentage, 2)
        })
    
    return result

@api_router.get("/budget-categories/by-project")
async def get_budget_categories_grouped(current_user: dict = Depends(get_current_user)):
    """الحصول على التصنيفات مجمعة حسب المشروع"""
    categories = await db.budget_categories.find({}, {"_id": 0}).sort("project_name", 1).to_list(500)
    
    # Group by project
    projects = {}
    for cat in categories:
        project = cat["project_name"]
        if project not in projects:
            projects[project] = {
                "project_name": project,
                "total_estimated": 0,
                "total_spent": 0,
                "categories": []
            }
        
        # Get actual spent
        pipeline = [
            {"$match": {"category_id": cat["id"]}},
            {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
        ]
        spent_result = await db.purchase_orders.aggregate(pipeline).to_list(1)
        actual_spent = spent_result[0]["total"] if spent_result else 0
        
        cat["actual_spent"] = actual_spent
        cat["remaining"] = cat["estimated_budget"] - actual_spent
        
        projects[project]["categories"].append(cat)
        projects[project]["total_estimated"] += cat["estimated_budget"]
        projects[project]["total_spent"] += actual_spent
    
    return list(projects.values())

@api_router.put("/budget-categories/{category_id}")
async def update_budget_category(
    category_id: str,
    update_data: BudgetCategoryUpdate,
    current_user: dict = Depends(get_current_user)
):
    """تحديث تصنيف ميزانية - مدير المشتريات فقط"""
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه إدارة التصنيفات")
    
    category = await db.budget_categories.find_one({"id": category_id}, {"_id": 0})
    if not category:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")
    
    update_fields = {}
    if update_data.name is not None:
        update_fields["name"] = update_data.name
    if update_data.estimated_budget is not None:
        update_fields["estimated_budget"] = update_data.estimated_budget
    
    if update_fields:
        await db.budget_categories.update_one(
            {"id": category_id},
            {"$set": update_fields}
        )
    
    return {"message": "تم تحديث التصنيف بنجاح"}

@api_router.delete("/budget-categories/{category_id}")
async def delete_budget_category(
    category_id: str,
    current_user: dict = Depends(get_current_user)
):
    """حذف تصنيف ميزانية - مدير المشتريات فقط"""
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه إدارة التصنيفات")
    
    # Check if any purchase orders use this category
    po_count = await db.purchase_orders.count_documents({"category_id": category_id})
    if po_count > 0:
        raise HTTPException(status_code=400, detail=f"لا يمكن حذف التصنيف لوجود {po_count} أوامر شراء مرتبطة به")
    
    result = await db.budget_categories.delete_one({"id": category_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")
    
    return {"message": "تم حذف التصنيف بنجاح"}

@api_router.get("/budget-reports")
async def get_budget_reports(
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """تقرير المقارنة بين الميزانية التقديرية والفعلية"""
    query = {}
    if project_id:
        query["project_id"] = project_id
    elif project_name:
        query["project_name"] = project_name
    
    categories = await db.budget_categories.find(query, {"_id": 0}).to_list(500)
    
    # Get project info if filtering by project
    project_info = None
    if project_id:
        project_info = await db.projects.find_one({"id": project_id}, {"_id": 0})
    
    report = {
        "project": project_info,
        "total_estimated": 0,
        "total_spent": 0,
        "total_remaining": 0,
        "categories": [],
        "over_budget": [],  # التصنيفات التي تجاوزت الميزانية
        "under_budget": []  # التصنيفات ضمن الميزانية
    }
    
    for cat in categories:
        # Get actual spent
        pipeline = [
            {"$match": {"category_id": cat["id"]}},
            {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
        ]
        spent_result = await db.purchase_orders.aggregate(pipeline).to_list(1)
        actual_spent = spent_result[0]["total"] if spent_result else 0
        
        remaining = cat["estimated_budget"] - actual_spent
        variance = actual_spent - cat["estimated_budget"]
        variance_percentage = (variance / cat["estimated_budget"] * 100) if cat["estimated_budget"] > 0 else 0
        
        cat_report = {
            "id": cat["id"],
            "name": cat["name"],
            "project_id": cat.get("project_id"),
            "project_name": cat.get("project_name"),
            "estimated_budget": cat["estimated_budget"],
            "actual_spent": actual_spent,
            "remaining": remaining,
            "variance": variance,
            "variance_percentage": round(variance_percentage, 2),
            "status": "over_budget" if remaining < 0 else "under_budget"
        }
        
        report["categories"].append(cat_report)
        report["total_estimated"] += cat["estimated_budget"]
        report["total_spent"] += actual_spent
        
        if remaining < 0:
            report["over_budget"].append(cat_report)
        else:
            report["under_budget"].append(cat_report)
    
    report["total_remaining"] = report["total_estimated"] - report["total_spent"]
    report["overall_variance_percentage"] = round(
        ((report["total_spent"] - report["total_estimated"]) / report["total_estimated"] * 100) 
        if report["total_estimated"] > 0 else 0, 2
    )
    
    return report

# ==================== SUPPLIERS ROUTES ====================

@api_router.post("/suppliers", response_model=SupplierResponse)
async def create_supplier(
    supplier_data: SupplierCreate,
    current_user: dict = Depends(get_current_user)
):
    """إنشاء مورد جديد - مدير المشتريات فقط"""
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه إضافة موردين")
    
    supplier_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    supplier_doc = {
        "id": supplier_id,
        "name": supplier_data.name,
        "contact_person": supplier_data.contact_person,
        "phone": supplier_data.phone,
        "email": supplier_data.email,
        "address": supplier_data.address,
        "notes": supplier_data.notes,
        "created_at": now
    }
    
    await db.suppliers.insert_one(supplier_doc)
    return SupplierResponse(**{k: v for k, v in supplier_doc.items() if k != "_id"})

@api_router.get("/suppliers", response_model=List[SupplierResponse])
async def get_suppliers(current_user: dict = Depends(get_current_user)):
    """الحصول على قائمة الموردين"""
    suppliers = await db.suppliers.find({}, {"_id": 0}).sort("name", 1).to_list(200)
    return [SupplierResponse(**s) for s in suppliers]

@api_router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(supplier_id: str, current_user: dict = Depends(get_current_user)):
    """الحصول على بيانات مورد محدد"""
    supplier = await db.suppliers.find_one({"id": supplier_id}, {"_id": 0})
    if not supplier:
        raise HTTPException(status_code=404, detail="المورد غير موجود")
    return SupplierResponse(**supplier)

@api_router.put("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: str,
    supplier_data: SupplierCreate,
    current_user: dict = Depends(get_current_user)
):
    """تحديث بيانات مورد"""
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه تعديل الموردين")
    
    supplier = await db.suppliers.find_one({"id": supplier_id}, {"_id": 0})
    if not supplier:
        raise HTTPException(status_code=404, detail="المورد غير موجود")
    
    update_data = {
        "name": supplier_data.name,
        "contact_person": supplier_data.contact_person,
        "phone": supplier_data.phone,
        "email": supplier_data.email,
        "address": supplier_data.address,
        "notes": supplier_data.notes
    }
    
    await db.suppliers.update_one({"id": supplier_id}, {"$set": update_data})
    updated = await db.suppliers.find_one({"id": supplier_id}, {"_id": 0})
    return SupplierResponse(**updated)

@api_router.delete("/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: str, current_user: dict = Depends(get_current_user)):
    """حذف مورد"""
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه حذف الموردين")
    
    result = await db.suppliers.delete_one({"id": supplier_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="المورد غير موجود")
    return {"message": "تم حذف المورد بنجاح"}

# ==================== MATERIAL REQUESTS ROUTES ====================

@api_router.post("/requests", response_model=MaterialRequestResponse)
async def create_material_request(
    request_data: MaterialRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="فقط المشرفين يمكنهم إنشاء طلبات")
    
    # Get project info
    project = await db.projects.find_one({"id": request_data.project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=400, detail="المشروع غير موجود")
    
    # Get engineer info
    engineer = await db.users.find_one({"id": request_data.engineer_id}, {"_id": 0})
    if not engineer or engineer["role"] != UserRole.ENGINEER:
        raise HTTPException(status_code=400, detail="المهندس غير موجود")
    
    request_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Get next sequential request number for this supervisor (e.g., A1, A2, B1...)
    request_number, request_seq = await get_next_request_number(current_user["id"])
    
    # Convert items to dict format
    items_list = [item.model_dump() for item in request_data.items]
    
    request_doc = {
        "id": request_id,
        "request_number": request_number,
        "request_seq": request_seq,
        "items": items_list,
        "project_id": request_data.project_id,
        "project_name": project["name"],
        "reason": request_data.reason,
        "supervisor_id": current_user["id"],
        "supervisor_name": current_user["name"],
        "engineer_id": request_data.engineer_id,
        "engineer_name": engineer["name"],
        "status": RequestStatus.PENDING_ENGINEER,
        "rejection_reason": None,
        "expected_delivery_date": request_data.expected_delivery_date,
        "created_at": now,
        "updated_at": now
    }
    
    await db.material_requests.insert_one(request_doc)
    
    # Log audit
    await log_audit(
        entity_type="request",
        entity_id=request_id,
        action="create",
        user=current_user,
        description=f"إنشاء طلب مواد جديد #{request_number} للمشروع {project['name']}"
    )
    
    # Build items list for email
    items_html = "".join([f"<li>{item.name} - {item.quantity} {item.unit}</li>" for item in request_data.items])
    
    # Send email notification to engineer
    email_content = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif;">
        <h2>طلب مواد جديد - رقم {request_number}</h2>
        <p>مرحباً {engineer['name']},</p>
        <p>تم استلام طلب مواد جديد يحتاج لاعتمادك:</p>
        <p><strong>رقم الطلب:</strong> {request_number}</p>
        <p><strong>المواد المطلوبة:</strong></p>
        <ul>{items_html}</ul>
        <p><strong>المشروع:</strong> {project['name']}</p>
        <p><strong>السبب:</strong> {request_data.reason}</p>
        <p><strong>المشرف:</strong> {current_user['name']}</p>
    </div>
    """
    await send_email_notification(
        engineer["email"],
        f"طلب مواد جديد #{request_number} يحتاج اعتمادك",
        email_content
    )
    
    return MaterialRequestResponse(**{k: v for k, v in request_doc.items() if k != "_id"})

@api_router.get("/requests", response_model=List[MaterialRequestResponse])
async def get_requests(current_user: dict = Depends(get_current_user)):
    query = {}
    
    if current_user["role"] == UserRole.SUPERVISOR:
        query["supervisor_id"] = current_user["id"]
    elif current_user["role"] == UserRole.ENGINEER:
        query["engineer_id"] = current_user["id"]
    elif current_user["role"] == UserRole.PROCUREMENT_MANAGER:
        # مدير المشتريات يرى جميع الطلبات لمتابعة سير العمل
        pass  # No filter - see all requests
    
    # Limit to 500 results for performance (with indexes, this is fast)
    requests = await db.material_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [MaterialRequestResponse(**r) for r in requests]

@api_router.get("/requests/all", response_model=List[MaterialRequestResponse])
async def get_all_requests(current_user: dict = Depends(get_current_user)):
    """Get all requests for viewing (all users can see all requests) - limited to 500"""
    requests = await db.material_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [MaterialRequestResponse(**r) for r in requests]

# Model for updating request
class MaterialRequestEdit(BaseModel):
    items: List[MaterialItem]
    project_id: Optional[str] = None  # معرف المشروع (اختياري للطلبات القديمة)
    reason: str
    engineer_id: str

@api_router.put("/requests/{request_id}/edit", response_model=MaterialRequestResponse)
async def edit_request(
    request_id: str,
    edit_data: MaterialRequestEdit,
    current_user: dict = Depends(get_current_user)
):
    """Edit a request - only supervisor can edit and only before engineer approval"""
    if current_user["role"] != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="فقط المشرفين يمكنهم تعديل الطلبات")
    
    request = await db.material_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    
    if request["supervisor_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="لا يمكنك تعديل طلب مشرف آخر")
    
    if request["status"] != RequestStatus.PENDING_ENGINEER:
        raise HTTPException(status_code=400, detail="لا يمكن تعديل الطلب بعد اعتماده أو رفضه")
    
    # Get new engineer info if changed
    engineer = await db.users.find_one({"id": edit_data.engineer_id}, {"_id": 0})
    if not engineer or engineer["role"] != UserRole.ENGINEER:
        raise HTTPException(status_code=400, detail="المهندس غير موجود")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Convert items to dict format
    items_list = [item.model_dump() for item in edit_data.items]
    
    update_data = {
        "items": items_list,
        "reason": edit_data.reason,
        "engineer_id": edit_data.engineer_id,
        "engineer_name": engineer["name"],
        "updated_at": now
    }
    
    # Get project info if project_id provided
    if edit_data.project_id:
        project = await db.projects.find_one({"id": edit_data.project_id}, {"_id": 0})
        if project:
            update_data["project_id"] = edit_data.project_id
            update_data["project_name"] = project["name"]
    
    await db.material_requests.update_one(
        {"id": request_id},
        {"$set": update_data}
    )
    
    updated_request = await db.material_requests.find_one({"id": request_id}, {"_id": 0})
    return MaterialRequestResponse(**updated_request)

@api_router.get("/requests/{request_id}", response_model=MaterialRequestResponse)
async def get_request(request_id: str, current_user: dict = Depends(get_current_user)):
    request = await db.material_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    return MaterialRequestResponse(**request)

@api_router.put("/requests/{request_id}/approve")
async def approve_request(request_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != UserRole.ENGINEER:
        raise HTTPException(status_code=403, detail="فقط المهندسين يمكنهم اعتماد الطلبات")
    
    request = await db.material_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    
    if request["engineer_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="هذا الطلب غير موجه لك")
    
    if request["status"] != RequestStatus.PENDING_ENGINEER:
        raise HTTPException(status_code=400, detail="هذا الطلب تم اعتماده أو رفضه مسبقاً")
    
    await db.material_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": RequestStatus.APPROVED_BY_ENGINEER,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify procurement manager
    managers = await db.users.find({"role": UserRole.PROCUREMENT_MANAGER}, {"_id": 0}).to_list(10)
    for manager in managers:
        # Build items list for email
        items_html = "".join([f"<li>{item['name']} - {item['quantity']} {item.get('unit', 'قطعة')}</li>" for item in request.get('items', [])])
        email_content = f"""
        <div dir="rtl" style="font-family: Arial, sans-serif;">
            <h2>طلب مواد معتمد</h2>
            <p>مرحباً {manager['name']},</p>
            <p>تم اعتماد طلب مواد ويحتاج لإصدار أمر شراء:</p>
            <p><strong>المواد:</strong></p>
            <ul>{items_html}</ul>
            <p><strong>المشروع:</strong> {request['project_name']}</p>
            <p><strong>المهندس المعتمد:</strong> {current_user['name']}</p>
        </div>
        """
        await send_email_notification(
            manager["email"],
            "طلب مواد معتمد يحتاج أمر شراء",
            email_content
        )
    
    return {"message": "تم اعتماد الطلب بنجاح"}

@api_router.put("/requests/{request_id}/reject")
async def reject_request(
    request_id: str,
    rejection_data: dict,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != UserRole.ENGINEER:
        raise HTTPException(status_code=403, detail="فقط المهندسين يمكنهم رفض الطلبات")
    
    request = await db.material_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    
    if request["engineer_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="هذا الطلب غير موجه لك")
    
    if request["status"] != RequestStatus.PENDING_ENGINEER:
        raise HTTPException(status_code=400, detail="هذا الطلب تم اعتماده أو رفضه مسبقاً")
    
    await db.material_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": RequestStatus.REJECTED_BY_ENGINEER,
            "rejection_reason": rejection_data.get("reason", ""),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify supervisor
    supervisor = await db.users.find_one({"id": request["supervisor_id"]}, {"_id": 0})
    if supervisor:
        # Build items list for email
        items_html = "".join([f"<li>{item['name']} - {item['quantity']} {item.get('unit', 'قطعة')}</li>" for item in request.get('items', [])])
        email_content = f"""
        <div dir="rtl" style="font-family: Arial, sans-serif;">
            <h2>تم رفض طلب المواد</h2>
            <p>مرحباً {supervisor['name']},</p>
            <p>تم رفض طلب المواد الخاص بك:</p>
            <p><strong>المواد:</strong></p>
            <ul>{items_html}</ul>
            <p><strong>سبب الرفض:</strong> {rejection_data.get('reason', 'لم يتم تحديد السبب')}</p>
        </div>
        """
        await send_email_notification(
            supervisor["email"],
            "تم رفض طلب المواد",
            email_content
        )
    
    return {"message": "تم رفض الطلب"}

# ==================== PURCHASE ORDERS ROUTES ====================

@api_router.post("/purchase-orders", response_model=PurchaseOrderResponse)
async def create_purchase_order(
    order_data: PurchaseOrderCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه إصدار أوامر الشراء")
    
    # Get request
    request = await db.material_requests.find_one({"id": order_data.request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    
    # Allow creating PO for approved or partially ordered requests
    if request["status"] not in [RequestStatus.APPROVED_BY_ENGINEER, RequestStatus.PARTIALLY_ORDERED]:
        raise HTTPException(status_code=400, detail="الطلب غير معتمد من المهندس")
    
    # Get selected items from the request
    all_items = request.get("items", [])
    if not order_data.selected_items:
        raise HTTPException(status_code=400, detail="الرجاء اختيار صنف واحد على الأقل")
    
    # Build items with prices
    selected_items = []
    total_amount = 0
    item_prices_map = {}
    
    # Create price lookup from item_prices
    if order_data.item_prices:
        for price_item in order_data.item_prices:
            item_prices_map[price_item.get("index", -1)] = price_item.get("unit_price", 0)
    
    for idx in order_data.selected_items:
        if 0 <= idx < len(all_items):
            item = all_items[idx].copy() if isinstance(all_items[idx], dict) else all_items[idx]
            if isinstance(item, dict):
                item_data = item
            else:
                item_data = item.model_dump() if hasattr(item, 'model_dump') else dict(item)
            
            # Add price information
            unit_price = item_prices_map.get(idx, 0)
            quantity = item_data.get("quantity", 0)
            item_total = unit_price * quantity
            
            item_data["unit_price"] = unit_price
            item_data["total_price"] = item_total
            item_data["delivered_quantity"] = 0
            
            selected_items.append(item_data)
            total_amount += item_total
        else:
            raise HTTPException(status_code=400, detail=f"فهرس الصنف {idx} غير صالح")
    
    if not selected_items:
        raise HTTPException(status_code=400, detail="الرجاء اختيار صنف واحد على الأقل")
    
    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Get category name if category_id is provided
    category_name = None
    if order_data.category_id:
        category = await db.budget_categories.find_one({"id": order_data.category_id}, {"_id": 0})
        if category:
            category_name = category.get("name")
    
    order_doc = {
        "id": order_id,
        "request_id": order_data.request_id,
        "request_number": request.get("request_number"),  # رقم الطلب المتسلسل
        "items": selected_items,
        "project_name": request["project_name"],
        "supplier_id": order_data.supplier_id,
        "supplier_name": order_data.supplier_name,
        "category_id": order_data.category_id,  # تصنيف الميزانية
        "category_name": category_name,  # اسم التصنيف
        "notes": order_data.notes,
        "terms_conditions": order_data.terms_conditions,
        "manager_id": current_user["id"],
        "manager_name": current_user["name"],
        "supervisor_name": request.get("supervisor_name", ""),
        "engineer_name": request.get("engineer_name", ""),
        "status": PurchaseOrderStatus.PENDING_APPROVAL,
        "total_amount": total_amount,
        "expected_delivery_date": order_data.expected_delivery_date,
        "created_at": now,
        "approved_at": None,
        "printed_at": None,
        "shipped_at": None,
        "delivered_at": None,
        "delivery_notes": None
    }
    
    await db.purchase_orders.insert_one(order_doc)
    
    # Check if all items have been ordered
    existing_orders = await db.purchase_orders.find({"request_id": order_data.request_id}, {"_id": 0}).to_list(100)
    ordered_item_indices = set()
    for order in existing_orders:
        for item in order.get("items", []):
            # Find the index of this item in the original request
            for i, req_item in enumerate(all_items):
                if req_item["name"] == item["name"] and req_item["quantity"] == item["quantity"]:
                    ordered_item_indices.add(i)
                    break
    
    # Update request status based on how many items have been ordered
    if len(ordered_item_indices) >= len(all_items):
        new_status = RequestStatus.PURCHASE_ORDER_ISSUED
    else:
        new_status = RequestStatus.PARTIALLY_ORDERED
    
    await db.material_requests.update_one(
        {"id": order_data.request_id},
        {"$set": {
            "status": new_status,
            "updated_at": now
        }}
    )
    
    # Notify supervisor and engineer
    supervisor = await db.users.find_one({"id": request["supervisor_id"]}, {"_id": 0})
    engineer = await db.users.find_one({"id": request["engineer_id"]}, {"_id": 0})
    
    # Build items list for email
    items_html = "".join([f"<li>{item['name']} - {item['quantity']} {item.get('unit', 'قطعة')}</li>" for item in selected_items])
    
    for user in [supervisor, engineer]:
        if user:
            email_content = f"""
            <div dir="rtl" style="font-family: Arial, sans-serif;">
                <h2>تم إصدار أمر شراء</h2>
                <p>مرحباً {user['name']},</p>
                <p>تم إصدار أمر شراء للطلب:</p>
                <p><strong>المواد:</strong></p>
                <ul>{items_html}</ul>
                <p><strong>المورد:</strong> {order_data.supplier_name}</p>
            </div>
            """
            await send_email_notification(
                user["email"],
                "تم إصدار أمر شراء",
                email_content
            )
    
    return PurchaseOrderResponse(**{k: v for k, v in order_doc.items() if k != "_id"})

@api_router.put("/purchase-orders/{order_id}")
async def update_purchase_order(
    order_id: str,
    update_data: PurchaseOrderUpdate,
    current_user: dict = Depends(get_current_user)
):
    """تعديل أمر الشراء - مدير المشتريات فقط"""
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه تعديل أوامر الشراء")
    
    order = await db.purchase_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    # Prepare update fields
    update_fields = {}
    
    if update_data.supplier_name:
        update_fields["supplier_name"] = update_data.supplier_name
    
    if update_data.supplier_id:
        update_fields["supplier_id"] = update_data.supplier_id
    
    if update_data.category_id:
        category = await db.budget_categories.find_one({"id": update_data.category_id}, {"_id": 0})
        if category:
            update_fields["category_id"] = update_data.category_id
            update_fields["category_name"] = category["name"]
    
    if update_data.notes is not None:
        update_fields["notes"] = update_data.notes
    
    if update_data.terms_conditions is not None:
        update_fields["terms_conditions"] = update_data.terms_conditions
    
    if update_data.expected_delivery_date:
        update_fields["expected_delivery_date"] = update_data.expected_delivery_date
    
    if update_data.supplier_invoice_number is not None:
        update_fields["supplier_invoice_number"] = update_data.supplier_invoice_number
    
    # Update item prices if provided
    if update_data.item_prices:
        items = order.get("items", [])
        total_amount = 0
        
        # Create a map of item name to price for easier lookup
        price_map = {}
        for price_item in update_data.item_prices:
            item_name = price_item.get("name", "")
            item_index = price_item.get("index")
            unit_price = price_item.get("unit_price", 0)
            
            if item_name:
                price_map[item_name] = unit_price
            elif item_index is not None and item_index < len(items):
                items[item_index]["unit_price"] = unit_price
                items[item_index]["total_price"] = unit_price * items[item_index].get("quantity", 0)
        
        # Apply prices by name
        for item in items:
            if item.get("name") in price_map:
                unit_price = price_map[item["name"]]
                item["unit_price"] = unit_price
                item["total_price"] = unit_price * item.get("quantity", 0)
            total_amount += item.get("total_price", 0)
        
        update_fields["items"] = items
        update_fields["total_amount"] = total_amount
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="لا توجد بيانات للتحديث")
    
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.purchase_orders.update_one(
        {"id": order_id},
        {"$set": update_fields}
    )
    
    # Log audit
    await log_audit(
        entity_type="purchase_order",
        entity_id=order_id,
        action="update",
        user=current_user,
        description=f"تم تعديل أمر الشراء"
    )
    
    updated_order = await db.purchase_orders.find_one({"id": order_id}, {"_id": 0})
    return PurchaseOrderResponse(**updated_order)

@api_router.put("/purchase-orders/{order_id}/approve")
async def approve_purchase_order(order_id: str, current_user: dict = Depends(get_current_user)):
    """اعتماد أمر الشراء من مدير المشتريات"""
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه اعتماد أوامر الشراء")
    
    order = await db.purchase_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    if order["status"] != PurchaseOrderStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="أمر الشراء تم اعتماده مسبقاً")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.purchase_orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": PurchaseOrderStatus.APPROVED,
            "approved_at": now
        }}
    )
    
    # Notify printers
    printers = await db.users.find({"role": UserRole.PRINTER}, {"_id": 0}).to_list(10)
    items_html = "".join([f"<li>{item['name']} - {item['quantity']} {item.get('unit', 'قطعة')}</li>" for item in order.get('items', [])])
    
    for printer in printers:
        email_content = f"""
        <div dir="rtl" style="font-family: Arial, sans-serif;">
            <h2>أمر شراء جاهز للطباعة</h2>
            <p>مرحباً {printer['name']},</p>
            <p>تم اعتماد أمر شراء جديد ويحتاج للطباعة:</p>
            <p><strong>المواد:</strong></p>
            <ul>{items_html}</ul>
            <p><strong>المورد:</strong> {order['supplier_name']}</p>
            <p><strong>المشروع:</strong> {order['project_name']}</p>
        </div>
        """
        await send_email_notification(
            printer["email"],
            "أمر شراء جاهز للطباعة",
            email_content
        )
    
    return {"message": "تم اعتماد أمر الشراء بنجاح"}

@api_router.put("/purchase-orders/{order_id}/print")
async def mark_purchase_order_printed(order_id: str, current_user: dict = Depends(get_current_user)):
    """تسجيل طباعة أمر الشراء من موظف الطباعة"""
    if current_user["role"] != UserRole.PRINTER:
        raise HTTPException(status_code=403, detail="فقط موظف الطباعة يمكنه تسجيل الطباعة")
    
    order = await db.purchase_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    if order["status"] != PurchaseOrderStatus.APPROVED:
        raise HTTPException(status_code=400, detail="أمر الشراء غير معتمد أو تمت طباعته مسبقاً")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.purchase_orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": PurchaseOrderStatus.PRINTED,
            "printed_at": now
        }}
    )
    
    return {"message": "تم تسجيل طباعة أمر الشراء بنجاح"}

# ==================== DELIVERY TRACKING ROUTES ====================

@api_router.put("/purchase-orders/{order_id}/ship")
async def mark_order_shipped(order_id: str, current_user: dict = Depends(get_current_user)):
    """تسجيل شحن أمر الشراء"""
    if current_user["role"] not in [UserRole.PROCUREMENT_MANAGER, UserRole.PRINTER]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    order = await db.purchase_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    if order["status"] not in [PurchaseOrderStatus.PRINTED, PurchaseOrderStatus.APPROVED]:
        raise HTTPException(status_code=400, detail="أمر الشراء يجب أن يكون مطبوعاً أو معتمداً")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.purchase_orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": PurchaseOrderStatus.SHIPPED,
            "shipped_at": now
        }}
    )
    
    return {"message": "تم تسجيل شحن أمر الشراء بنجاح"}

@api_router.put("/purchase-orders/{order_id}/deliver")
async def record_delivery(
    order_id: str,
    delivery_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """تسجيل استلام المواد - المشرف أو المهندس"""
    if current_user["role"] not in [UserRole.SUPERVISOR, UserRole.ENGINEER, UserRole.PROCUREMENT_MANAGER]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بتسجيل الاستلام")
    
    order = await db.purchase_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update delivered quantities for items
    items = order.get("items", [])
    items_delivered = delivery_data.get("items_delivered", [])
    all_delivered = True
    
    for delivered_item in items_delivered:
        for item in items:
            if item["name"] == delivered_item.get("name"):
                item["delivered_quantity"] = item.get("delivered_quantity", 0) + delivered_item.get("quantity_delivered", 0)
                if item["delivered_quantity"] < item["quantity"]:
                    all_delivered = False
                break
    
    # Check if all items are fully delivered
    for item in items:
        if item.get("delivered_quantity", 0) < item.get("quantity", 0):
            all_delivered = False
            break
    
    new_status = PurchaseOrderStatus.DELIVERED if all_delivered else PurchaseOrderStatus.PARTIALLY_DELIVERED
    
    # Create delivery record
    delivery_record = {
        "id": str(uuid.uuid4()),
        "order_id": order_id,
        "items_delivered": items_delivered,
        "delivery_date": delivery_data.get("delivery_date", now),
        "received_by": delivery_data.get("received_by", current_user["name"]),
        "notes": delivery_data.get("notes", ""),
        "recorded_by": current_user["id"],
        "recorded_at": now
    }
    
    await db.delivery_records.insert_one(delivery_record)
    
    await db.purchase_orders.update_one(
        {"id": order_id},
        {"$set": {
            "items": items,
            "status": new_status,
            "delivered_at": now if all_delivered else order.get("delivered_at"),
            "delivery_notes": delivery_data.get("notes", "")
        }}
    )
    
    return {
        "message": "تم تسجيل الاستلام بنجاح",
        "status": new_status,
        "all_delivered": all_delivered
    }

@api_router.get("/purchase-orders/{order_id}/deliveries")
async def get_order_deliveries(order_id: str, current_user: dict = Depends(get_current_user)):
    """الحصول على سجلات التسليم لأمر شراء"""
    deliveries = await db.delivery_records.find(
        {"order_id": order_id}, 
        {"_id": 0}
    ).sort("recorded_at", -1).to_list(50)
    
    return deliveries

@api_router.get("/purchase-orders/pending-delivery")
async def get_pending_delivery_orders(current_user: dict = Depends(get_current_user)):
    """الأوامر التي تحتاج استلام - للمشرف والمهندس"""
    if current_user["role"] not in [UserRole.SUPERVISOR, UserRole.ENGINEER]:
        return []
    
    query = {"status": {"$in": [PurchaseOrderStatus.SHIPPED, PurchaseOrderStatus.PARTIALLY_DELIVERED]}}
    orders = await db.purchase_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    result = []
    for o in orders:
        o.setdefault("total_amount", 0)
        o.setdefault("supplier_id", None)
        o.setdefault("terms_conditions", None)
        o.setdefault("expected_delivery_date", None)
        o.setdefault("approved_at", None)
        o.setdefault("printed_at", None)
        o.setdefault("shipped_at", None)
        o.setdefault("delivered_at", None)
        o.setdefault("delivery_notes", None)
        o.setdefault("supplier_receipt_number", None)
        o.setdefault("received_by_id", None)
        o.setdefault("received_by_name", None)
        result.append(PurchaseOrderResponse(**o))
    
    return result

@api_router.get("/purchase-orders", response_model=List[PurchaseOrderResponse])
async def get_purchase_orders(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == UserRole.PROCUREMENT_MANAGER:
        query["manager_id"] = current_user["id"]
    elif current_user["role"] == UserRole.PRINTER:
        # موظف الطباعة يرى فقط الأوامر المعتمدة والمطبوعة والمشحونة
        query["status"] = {"$in": [PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PRINTED, PurchaseOrderStatus.SHIPPED]}
    # المشرف والمهندس يستخدمون endpoint منفصل للاستلام
    
    orders = await db.purchase_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Batch fetch all related requests to avoid N+1 query problem
    orders_needing_request_data = [o for o in orders if "supervisor_name" not in o or "engineer_name" not in o or "request_number" not in o]
    request_ids = list(set([o.get("request_id") for o in orders_needing_request_data if o.get("request_id")]))
    
    requests_map = {}
    if request_ids:
        requests_list = await db.material_requests.find(
            {"id": {"$in": request_ids}}, 
            {"_id": 0, "id": 1, "supervisor_name": 1, "engineer_name": 1, "request_number": 1}
        ).to_list(None)
        requests_map = {r["id"]: r for r in requests_list}
    
    # Batch fetch category names
    category_ids = list(set([o.get("category_id") for o in orders if o.get("category_id")]))
    categories_map = {}
    if category_ids:
        categories_list = await db.budget_categories.find(
            {"id": {"$in": category_ids}},
            {"_id": 0, "id": 1, "name": 1}
        ).to_list(None)
        categories_map = {c["id"]: c["name"] for c in categories_list}
    
    # Process orders with batch-fetched data
    result = []
    for o in orders:
        # Set defaults for missing fields
        o.setdefault("status", PurchaseOrderStatus.APPROVED)
        o.setdefault("approved_at", None)
        o.setdefault("printed_at", None)
        o.setdefault("shipped_at", None)
        o.setdefault("delivered_at", None)
        o.setdefault("delivery_notes", None)
        o.setdefault("total_amount", 0)
        o.setdefault("supplier_id", None)
        o.setdefault("terms_conditions", None)
        o.setdefault("expected_delivery_date", None)
        o.setdefault("category_id", None)
        o.setdefault("supplier_receipt_number", None)
        o.setdefault("received_by_id", None)
        o.setdefault("received_by_name", None)
        
        # Add category name
        o["category_name"] = categories_map.get(o.get("category_id"), None)
        
        # Use batch-fetched request data
        if "supervisor_name" not in o or "engineer_name" not in o or "request_number" not in o:
            request = requests_map.get(o.get("request_id"), {})
            o["supervisor_name"] = request.get("supervisor_name", o.get("supervisor_name", ""))
            o["engineer_name"] = request.get("engineer_name", o.get("engineer_name", ""))
            o["request_number"] = request.get("request_number", o.get("request_number"))
        
        result.append(PurchaseOrderResponse(**o))
    
    return result

# Get remaining items for a request (not yet ordered)
@api_router.get("/requests/{request_id}/remaining-items")
async def get_remaining_items(request_id: str, current_user: dict = Depends(get_current_user)):
    """الحصول على الأصناف المتبقية التي لم يتم إصدار أوامر شراء لها"""
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    request = await db.material_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    
    all_items = request.get("items", [])
    
    # Get all purchase orders for this request (limited to 50 - reasonable max for single request)
    existing_orders = await db.purchase_orders.find(
        {"request_id": request_id}, 
        {"_id": 0, "items": 1}
    ).to_list(50)
    
    # Track which items have been ordered
    ordered_items = []
    for order in existing_orders:
        ordered_items.extend(order.get("items", []))
    
    # Find remaining items
    remaining_items = []
    for idx, item in enumerate(all_items):
        item_ordered = False
        for ordered in ordered_items:
            if ordered["name"] == item["name"] and ordered["quantity"] == item["quantity"]:
                item_ordered = True
                break
        if not item_ordered:
            remaining_items.append({"index": idx, **item})
    
    return {"remaining_items": remaining_items, "all_items": [{"index": i, **item} for i, item in enumerate(all_items)]}

# ==================== DELIVERY TRACKER ROUTES ====================

@api_router.get("/delivery-tracker/orders")
async def get_orders_for_tracking(current_user: dict = Depends(get_current_user)):
    """الحصول على أوامر الشراء التي تحتاج متابعة - لمتابع التوريد"""
    if current_user["role"] not in [UserRole.DELIVERY_TRACKER, UserRole.PROCUREMENT_MANAGER]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    # Get orders that are shipped but not fully delivered
    query = {"status": {"$in": [PurchaseOrderStatus.SHIPPED, PurchaseOrderStatus.PARTIALLY_DELIVERED, PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PRINTED]}}
    orders = await db.purchase_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Batch fetch category names
    category_ids = list(set([o.get("category_id") for o in orders if o.get("category_id")]))
    categories_map = {}
    if category_ids:
        categories_list = await db.budget_categories.find({"id": {"$in": category_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(None)
        categories_map = {c["id"]: c["name"] for c in categories_list}
    
    result = []
    for o in orders:
        o.setdefault("status", PurchaseOrderStatus.APPROVED)
        o.setdefault("total_amount", 0)
        o.setdefault("supplier_receipt_number", None)
        o.setdefault("received_by_id", None)
        o.setdefault("received_by_name", None)
        o["category_name"] = categories_map.get(o.get("category_id"))
        result.append(o)
    
    return result

@api_router.put("/delivery-tracker/orders/{order_id}/confirm-receipt")
async def confirm_receipt(
    order_id: str,
    receipt_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """تأكيد استلام أمر الشراء مع رقم استلام المورد"""
    if current_user["role"] not in [UserRole.DELIVERY_TRACKER, UserRole.PROCUREMENT_MANAGER, UserRole.SUPERVISOR]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    order = await db.purchase_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    supplier_receipt_number = receipt_data.get("supplier_receipt_number")
    delivery_notes = receipt_data.get("delivery_notes", "")
    items_delivered = receipt_data.get("items_delivered", [])
    
    if not supplier_receipt_number:
        raise HTTPException(status_code=400, detail="الرجاء إدخال رقم استلام المورد")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update delivered quantities in items
    updated_items = order.get("items", [])
    all_delivered = True
    
    for delivered_item in items_delivered:
        item_name = delivered_item.get("name")
        qty_delivered = delivered_item.get("quantity_delivered", 0)
        
        for item in updated_items:
            if item.get("name") == item_name:
                current_delivered = item.get("delivered_quantity", 0)
                item["delivered_quantity"] = current_delivered + qty_delivered
                if item["delivered_quantity"] < item.get("quantity", 0):
                    all_delivered = False
                break
    
    # Determine new status
    has_any_delivery = any(item.get("delivered_quantity", 0) > 0 for item in updated_items)
    if all_delivered:
        new_status = PurchaseOrderStatus.DELIVERED
    elif has_any_delivery:
        new_status = PurchaseOrderStatus.PARTIALLY_DELIVERED
    else:
        new_status = order["status"]
    
    # Update order
    update_data = {
        "items": updated_items,
        "status": new_status,
        "supplier_receipt_number": supplier_receipt_number,
        "delivery_notes": delivery_notes,
        "received_by_id": current_user["id"],
        "received_by_name": current_user["name"],
        "delivered_at": now if new_status == PurchaseOrderStatus.DELIVERED else order.get("delivered_at")
    }
    
    await db.purchase_orders.update_one({"id": order_id}, {"$set": update_data})
    
    # Log audit
    await log_audit(
        entity_type="order",
        entity_id=order_id,
        action="confirm_receipt",
        user=current_user,
        description=f"تأكيد استلام أمر الشراء - رقم استلام المورد: {supplier_receipt_number}"
    )
    
    # Create delivery record
    delivery_record = {
        "id": str(uuid.uuid4()),
        "order_id": order_id,
        "items_delivered": items_delivered,
        "supplier_receipt_number": supplier_receipt_number,
        "delivery_date": now,
        "received_by": current_user["name"],
        "received_by_id": current_user["id"],
        "notes": delivery_notes
    }
    await db.delivery_records.insert_one(delivery_record)
    
    return {
        "message": "تم تأكيد الاستلام بنجاح",
        "status": new_status,
        "supplier_receipt_number": supplier_receipt_number
    }

@api_router.get("/delivery-tracker/stats")
async def get_delivery_stats(current_user: dict = Depends(get_current_user)):
    """إحصائيات متابعة التوريد"""
    if current_user["role"] not in [UserRole.DELIVERY_TRACKER, UserRole.PROCUREMENT_MANAGER]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    # Count orders by status
    shipped_count = await db.purchase_orders.count_documents({"status": PurchaseOrderStatus.SHIPPED})
    partial_count = await db.purchase_orders.count_documents({"status": PurchaseOrderStatus.PARTIALLY_DELIVERED})
    delivered_count = await db.purchase_orders.count_documents({"status": PurchaseOrderStatus.DELIVERED})
    approved_count = await db.purchase_orders.count_documents({"status": PurchaseOrderStatus.APPROVED})
    printed_count = await db.purchase_orders.count_documents({"status": PurchaseOrderStatus.PRINTED})
    
    return {
        "pending_delivery": shipped_count + partial_count,
        "shipped": shipped_count,
        "partially_delivered": partial_count,
        "delivered": delivered_count,
        "awaiting_shipment": approved_count + printed_count
    }

# ==================== AUDIT TRAIL ROUTES ====================

@api_router.get("/audit-logs")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """الحصول على سجل المراجعة"""
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    if user_id:
        query["user_id"] = user_id
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return logs

@api_router.get("/audit-logs/entity/{entity_type}/{entity_id}")
async def get_entity_audit_logs(
    entity_type: str,
    entity_id: str,
    current_user: dict = Depends(get_current_user)
):
    """الحصول على سجل المراجعة لكيان محدد"""
    logs = await db.audit_logs.find(
        {"entity_type": entity_type, "entity_id": entity_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    return logs

# ==================== ATTACHMENTS ROUTES ====================

import os
import shutil
from fastapi import UploadFile, File

UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@api_router.post("/attachments/{entity_type}/{entity_id}")
async def upload_attachment(
    entity_type: str,
    entity_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """رفع مرفق لطلب أو أمر شراء"""
    if entity_type not in ["request", "order"]:
        raise HTTPException(status_code=400, detail="نوع الكيان غير صالح")
    
    # Validate entity exists
    if entity_type == "request":
        entity = await db.material_requests.find_one({"id": entity_id})
    else:
        entity = await db.purchase_orders.find_one({"id": entity_id})
    
    if not entity:
        raise HTTPException(status_code=404, detail="الكيان غير موجود")
    
    # Generate unique filename
    attachment_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{attachment_id}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        file_size = len(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل في حفظ الملف: {str(e)}")
    
    # Save attachment record
    attachment_doc = {
        "id": attachment_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "filename": filename,
        "original_filename": file.filename,
        "file_size": file_size,
        "file_type": file.content_type or "application/octet-stream",
        "uploaded_by": current_user["id"],
        "uploaded_by_name": current_user["name"],
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.attachments.insert_one(attachment_doc)
    
    await log_audit(
        entity_type=entity_type,
        entity_id=entity_id,
        action="attachment_upload",
        user=current_user,
        description=f"رفع مرفق: {file.filename}"
    )
    
    return {k: v for k, v in attachment_doc.items() if k != "_id"}

@api_router.get("/attachments/{entity_type}/{entity_id}")
async def get_attachments(
    entity_type: str,
    entity_id: str,
    current_user: dict = Depends(get_current_user)
):
    """الحصول على مرفقات كيان"""
    attachments = await db.attachments.find(
        {"entity_type": entity_type, "entity_id": entity_id},
        {"_id": 0}
    ).sort("uploaded_at", -1).to_list(50)
    return attachments

@api_router.delete("/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """حذف مرفق"""
    attachment = await db.attachments.find_one({"id": attachment_id}, {"_id": 0})
    if not attachment:
        raise HTTPException(status_code=404, detail="المرفق غير موجود")
    
    # Only uploader or manager can delete
    if attachment["uploaded_by"] != current_user["id"] and current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بحذف هذا المرفق")
    
    # Delete file
    file_path = os.path.join(UPLOAD_DIR, attachment["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)
    
    await db.attachments.delete_one({"id": attachment_id})
    
    await log_audit(
        entity_type=attachment["entity_type"],
        entity_id=attachment["entity_id"],
        action="attachment_delete",
        user=current_user,
        description=f"حذف مرفق: {attachment['original_filename']}"
    )
    
    return {"message": "تم حذف المرفق بنجاح"}

from fastapi.responses import FileResponse

@api_router.get("/attachments/download/{attachment_id}")
async def download_attachment(
    attachment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """تحميل مرفق"""
    attachment = await db.attachments.find_one({"id": attachment_id}, {"_id": 0})
    if not attachment:
        raise HTTPException(status_code=404, detail="المرفق غير موجود")
    
    file_path = os.path.join(UPLOAD_DIR, attachment["filename"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="الملف غير موجود")
    
    return FileResponse(
        file_path,
        filename=attachment["original_filename"],
        media_type=attachment["file_type"]
    )

# ==================== ADVANCED REPORTS ====================

@api_router.get("/reports/project/{project_id}")
async def get_project_report(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """تقرير مفصل للمشروع"""
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    # Get all requests for project
    requests = await db.material_requests.find({"project_id": project_id}, {"_id": 0}).to_list(1000)
    
    # Get all orders for project
    orders = await db.purchase_orders.find({"project_id": project_id}, {"_id": 0}).to_list(1000)
    
    # Get budget categories
    categories = await db.budget_categories.find({"project_id": project_id}, {"_id": 0}).to_list(100)
    
    # Calculate budget stats per category
    budget_breakdown = []
    for cat in categories:
        pipeline = [
            {"$match": {"category_id": cat["id"]}},
            {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
        ]
        spent_result = await db.purchase_orders.aggregate(pipeline).to_list(1)
        actual_spent = spent_result[0]["total"] if spent_result else 0
        
        budget_breakdown.append({
            "category_name": cat["name"],
            "estimated_budget": cat["estimated_budget"],
            "actual_spent": actual_spent,
            "remaining": cat["estimated_budget"] - actual_spent,
            "percentage_used": round((actual_spent / cat["estimated_budget"] * 100) if cat["estimated_budget"] > 0 else 0, 2)
        })
    
    # Spending by supplier
    supplier_pipeline = [
        {"$match": {"project_id": project_id}},
        {"$group": {"_id": "$supplier_name", "total": {"$sum": "$total_amount"}, "count": {"$sum": 1}}}
    ]
    supplier_spending = await db.purchase_orders.aggregate(supplier_pipeline).to_list(100)
    
    # Orders by status
    status_pipeline = [
        {"$match": {"project_id": project_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}, "total": {"$sum": "$total_amount"}}}
    ]
    status_breakdown = await db.purchase_orders.aggregate(status_pipeline).to_list(20)
    
    # Monthly spending
    monthly_pipeline = [
        {"$match": {"project_id": project_id}},
        {"$addFields": {"month": {"$substr": ["$created_at", 0, 7]}}},
        {"$group": {"_id": "$month", "total": {"$sum": "$total_amount"}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    monthly_spending = await db.purchase_orders.aggregate(monthly_pipeline).to_list(24)
    
    return {
        "project": project,
        "summary": {
            "total_requests": len(requests),
            "total_orders": len(orders),
            "total_budget": sum(c["estimated_budget"] for c in categories),
            "total_spent": sum(o.get("total_amount", 0) for o in orders),
            "pending_requests": len([r for r in requests if r["status"] == "pending"]),
            "approved_orders": len([o for o in orders if o["status"] == "approved"]),
            "delivered_orders": len([o for o in orders if o["status"] == "delivered"])
        },
        "budget_breakdown": budget_breakdown,
        "supplier_spending": [{"supplier": s["_id"], "total": s["total"], "orders": s["count"]} for s in supplier_spending],
        "status_breakdown": [{"status": s["_id"], "count": s["count"], "total": s["total"]} for s in status_breakdown],
        "monthly_spending": [{"month": m["_id"], "total": m["total"], "orders": m["count"]} for m in monthly_spending]
    }

@api_router.get("/reports/spending-analysis")
async def get_spending_analysis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """تحليل الإنفاق الشامل"""
    match_query = {}
    if start_date or end_date:
        match_query["created_at"] = {}
        if start_date:
            match_query["created_at"]["$gte"] = start_date
        if end_date:
            match_query["created_at"]["$lte"] = end_date
    
    # Spending by project
    project_pipeline = [
        {"$match": match_query} if match_query else {"$match": {}},
        {"$group": {"_id": "$project_name", "total": {"$sum": "$total_amount"}, "count": {"$sum": 1}}}
    ]
    project_spending = await db.purchase_orders.aggregate(project_pipeline).to_list(100)
    
    # Spending by supplier
    supplier_pipeline = [
        {"$match": match_query} if match_query else {"$match": {}},
        {"$group": {"_id": "$supplier_name", "total": {"$sum": "$total_amount"}, "count": {"$sum": 1}}}
    ]
    supplier_spending = await db.purchase_orders.aggregate(supplier_pipeline).to_list(100)
    
    # Spending by category
    category_pipeline = [
        {"$match": {**match_query, "category_id": {"$ne": None}}} if match_query else {"$match": {"category_id": {"$ne": None}}},
        {"$lookup": {"from": "budget_categories", "localField": "category_id", "foreignField": "id", "as": "category"}},
        {"$unwind": {"path": "$category", "preserveNullAndEmptyArrays": True}},
        {"$group": {"_id": "$category.name", "total": {"$sum": "$total_amount"}, "count": {"$sum": 1}}}
    ]
    category_spending = await db.purchase_orders.aggregate(category_pipeline).to_list(100)
    
    # Monthly trend
    monthly_pipeline = [
        {"$match": match_query} if match_query else {"$match": {}},
        {"$addFields": {"month": {"$substr": ["$created_at", 0, 7]}}},
        {"$group": {"_id": "$month", "total": {"$sum": "$total_amount"}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    monthly_trend = await db.purchase_orders.aggregate(monthly_pipeline).to_list(24)
    
    # Total stats
    total_orders = await db.purchase_orders.count_documents(match_query or {})
    total_pipeline = [
        {"$match": match_query} if match_query else {"$match": {}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
    ]
    total_result = await db.purchase_orders.aggregate(total_pipeline).to_list(1)
    total_spent = total_result[0]["total"] if total_result else 0
    
    return {
        "total_orders": total_orders,
        "total_spent": total_spent,
        "average_order_value": round(total_spent / total_orders, 2) if total_orders > 0 else 0,
        "by_project": [{"project": p["_id"], "total": p["total"], "orders": p["count"]} for p in project_spending],
        "by_supplier": [{"supplier": s["_id"], "total": s["total"], "orders": s["count"]} for s in supplier_spending],
        "by_category": [{"category": c["_id"] or "بدون تصنيف", "total": c["total"], "orders": c["count"]} for c in category_spending],
        "monthly_trend": [{"month": m["_id"], "total": m["total"], "orders": m["count"]} for m in monthly_trend]
    }

# ==================== DASHBOARD STATS ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    stats = {}
    
    if current_user["role"] == UserRole.SUPERVISOR:
        total = await db.material_requests.count_documents({"supervisor_id": current_user["id"]})
        pending = await db.material_requests.count_documents({
            "supervisor_id": current_user["id"],
            "status": RequestStatus.PENDING_ENGINEER
        })
        approved = await db.material_requests.count_documents({
            "supervisor_id": current_user["id"],
            "status": {"$in": [RequestStatus.APPROVED_BY_ENGINEER, RequestStatus.PURCHASE_ORDER_ISSUED, RequestStatus.PARTIALLY_ORDERED]}
        })
        rejected = await db.material_requests.count_documents({
            "supervisor_id": current_user["id"],
            "status": RequestStatus.REJECTED_BY_ENGINEER
        })
        stats = {"total": total, "pending": pending, "approved": approved, "rejected": rejected}
    
    elif current_user["role"] == UserRole.ENGINEER:
        total = await db.material_requests.count_documents({"engineer_id": current_user["id"]})
        pending = await db.material_requests.count_documents({
            "engineer_id": current_user["id"],
            "status": RequestStatus.PENDING_ENGINEER
        })
        approved = await db.material_requests.count_documents({
            "engineer_id": current_user["id"],
            "status": {"$in": [RequestStatus.APPROVED_BY_ENGINEER, RequestStatus.PURCHASE_ORDER_ISSUED, RequestStatus.PARTIALLY_ORDERED]}
        })
        stats = {"total": total, "pending": pending, "approved": approved}
    
    elif current_user["role"] == UserRole.PROCUREMENT_MANAGER:
        pending_orders = await db.material_requests.count_documents({
            "status": {"$in": [RequestStatus.APPROVED_BY_ENGINEER, RequestStatus.PARTIALLY_ORDERED]}
        })
        total_orders = await db.purchase_orders.count_documents({"manager_id": current_user["id"]})
        pending_approval = await db.purchase_orders.count_documents({
            "manager_id": current_user["id"],
            "status": PurchaseOrderStatus.PENDING_APPROVAL
        })
        approved_orders = await db.purchase_orders.count_documents({
            "manager_id": current_user["id"],
            "status": {"$in": [PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PRINTED]}
        })
        stats = {
            "pending_orders": pending_orders,
            "total_orders": total_orders,
            "pending_approval": pending_approval,
            "approved_orders": approved_orders
        }
    
    elif current_user["role"] == UserRole.PRINTER:
        pending_print = await db.purchase_orders.count_documents({
            "status": PurchaseOrderStatus.APPROVED
        })
        printed = await db.purchase_orders.count_documents({
            "status": PurchaseOrderStatus.PRINTED
        })
        stats = {"pending_print": pending_print, "printed": printed}
    
    return stats

# ==================== HIGH PERFORMANCE PAGINATED APIs ====================
# These APIs support pagination, filtering, and are optimized for 20+ concurrent users

class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

@api_router.get("/v2/requests")
async def get_requests_paginated(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user: dict = Depends(get_current_user)
):
    """
    Paginated requests API - optimized for high load
    - Supports filtering by status, project
    - Supports text search
    - Server-side pagination
    """
    query = {}
    
    # Role-based filtering
    if current_user["role"] == UserRole.SUPERVISOR:
        query["supervisor_id"] = current_user["id"]
    elif current_user["role"] == UserRole.ENGINEER:
        query["engineer_id"] = current_user["id"]
    
    # Optional filters
    if status:
        if status == "approved":
            query["status"] = {"$in": [RequestStatus.APPROVED_BY_ENGINEER, RequestStatus.PARTIALLY_ORDERED]}
        elif status == "pending":
            query["status"] = RequestStatus.PENDING_ENGINEER
        elif status == "ordered":
            query["status"] = RequestStatus.PURCHASE_ORDER_ISSUED
        else:
            query["status"] = status
    
    if project_id:
        query["project_id"] = project_id
    
    if search:
        query["$or"] = [
            {"request_number": {"$regex": search, "$options": "i"}},
            {"items.name": {"$regex": search, "$options": "i"}},
            {"project_name": {"$regex": search, "$options": "i"}},
            {"supervisor_name": {"$regex": search, "$options": "i"}}
        ]
    
    # Get total count
    total = await db.material_requests.count_documents(query)
    
    # Calculate pagination
    page_size = min(page_size, 100)  # Max 100 per page
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    skip = (page - 1) * page_size
    
    # Sort direction
    sort_dir = -1 if sort_order == "desc" else 1
    
    # Fetch paginated data
    requests = await db.material_requests.find(
        query, 
        {"_id": 0}
    ).sort(sort_by, sort_dir).skip(skip).limit(page_size).to_list(page_size)
    
    return {
        "items": requests,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }

@api_router.get("/v2/purchase-orders")
async def get_purchase_orders_paginated(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    project_name: Optional[str] = None,
    supplier_name: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user: dict = Depends(get_current_user)
):
    """
    Paginated purchase orders API - optimized for high load
    - Supports filtering by status, project, supplier
    - Supports comprehensive search
    - Server-side pagination with batch fetching
    """
    query = {}
    
    # Role-based filtering
    if current_user["role"] == UserRole.PROCUREMENT_MANAGER:
        query["manager_id"] = current_user["id"]
    elif current_user["role"] == UserRole.PRINTER:
        query["status"] = {"$in": [PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PRINTED, PurchaseOrderStatus.SHIPPED]}
    
    # Optional filters
    if status:
        if status == "approved":
            query["status"] = {"$in": [PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PRINTED, PurchaseOrderStatus.PENDING_APPROVAL]}
        elif status == "shipped":
            query["status"] = {"$in": [PurchaseOrderStatus.SHIPPED, PurchaseOrderStatus.PARTIALLY_DELIVERED]}
        elif status == "delivered":
            query["status"] = PurchaseOrderStatus.DELIVERED
        else:
            query["status"] = status
    
    if project_name:
        query["project_name"] = {"$regex": project_name, "$options": "i"}
    
    if supplier_name:
        query["supplier_name"] = {"$regex": supplier_name, "$options": "i"}
    
    if search:
        query["$or"] = [
            {"id": {"$regex": search, "$options": "i"}},
            {"request_id": {"$regex": search, "$options": "i"}},
            {"project_name": {"$regex": search, "$options": "i"}},
            {"supplier_name": {"$regex": search, "$options": "i"}},
            {"supplier_receipt_number": {"$regex": search, "$options": "i"}}
        ]
    
    # Get total count
    total = await db.purchase_orders.count_documents(query)
    
    # Calculate pagination
    page_size = min(page_size, 100)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    skip = (page - 1) * page_size
    
    # Sort direction
    sort_dir = -1 if sort_order == "desc" else 1
    
    # Fetch paginated data
    orders = await db.purchase_orders.find(
        query, 
        {"_id": 0}
    ).sort(sort_by, sort_dir).skip(skip).limit(page_size).to_list(page_size)
    
    # Batch fetch related data
    request_ids = list(set([o.get("request_id") for o in orders if o.get("request_id")]))
    category_ids = list(set([o.get("category_id") for o in orders if o.get("category_id")]))
    
    requests_map = {}
    if request_ids:
        requests_list = await db.material_requests.find(
            {"id": {"$in": request_ids}}, 
            {"_id": 0, "id": 1, "supervisor_name": 1, "engineer_name": 1, "request_number": 1}
        ).to_list(None)
        requests_map = {r["id"]: r for r in requests_list}
    
    categories_map = {}
    if category_ids:
        categories_list = await db.budget_categories.find(
            {"id": {"$in": category_ids}},
            {"_id": 0, "id": 1, "name": 1}
        ).to_list(None)
        categories_map = {c["id"]: c["name"] for c in categories_list}
    
    # Process orders
    result = []
    for o in orders:
        o.setdefault("status", PurchaseOrderStatus.APPROVED)
        o.setdefault("total_amount", 0)
        o["category_name"] = categories_map.get(o.get("category_id"), None)
        
        if "supervisor_name" not in o or "engineer_name" not in o:
            request = requests_map.get(o.get("request_id"), {})
            o["supervisor_name"] = request.get("supervisor_name", o.get("supervisor_name", ""))
            o["engineer_name"] = request.get("engineer_name", o.get("engineer_name", ""))
            o["request_number"] = request.get("request_number", o.get("request_number"))
        
        result.append(o)
    
    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }

@api_router.get("/v2/dashboard/stats")
async def get_dashboard_stats_optimized(current_user: dict = Depends(get_current_user)):
    """
    Optimized dashboard stats using aggregation pipelines
    Much faster than multiple count queries for high load
    """
    stats = {}
    
    if current_user["role"] == UserRole.SUPERVISOR:
        # Use aggregation for all counts in one query
        pipeline = [
            {"$match": {"supervisor_id": current_user["id"]}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        status_counts = await db.material_requests.aggregate(pipeline).to_list(None)
        status_map = {s["_id"]: s["count"] for s in status_counts}
        
        stats = {
            "total_requests": sum(status_map.values()),
            "pending": status_map.get(RequestStatus.PENDING_ENGINEER, 0),
            "approved": status_map.get(RequestStatus.APPROVED_BY_ENGINEER, 0) + status_map.get(RequestStatus.PARTIALLY_ORDERED, 0),
            "ordered": status_map.get(RequestStatus.PURCHASE_ORDER_ISSUED, 0)
        }
        
        # Pending deliveries
        pending_delivery = await db.purchase_orders.count_documents({
            "supervisor_id": current_user["id"],
            "status": {"$in": [PurchaseOrderStatus.SHIPPED, PurchaseOrderStatus.PARTIALLY_DELIVERED]}
        })
        stats["pending_delivery"] = pending_delivery
        
    elif current_user["role"] == UserRole.ENGINEER:
        pipeline = [
            {"$match": {"engineer_id": current_user["id"]}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        status_counts = await db.material_requests.aggregate(pipeline).to_list(None)
        status_map = {s["_id"]: s["count"] for s in status_counts}
        
        stats = {
            "pending_approval": status_map.get(RequestStatus.PENDING_ENGINEER, 0),
            "approved": status_map.get(RequestStatus.APPROVED_BY_ENGINEER, 0),
            "total_requests": sum(status_map.values())
        }
        
    elif current_user["role"] == UserRole.PROCUREMENT_MANAGER:
        # Requests stats
        req_pipeline = [
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        req_counts = await db.material_requests.aggregate(req_pipeline).to_list(None)
        req_map = {s["_id"]: s["count"] for s in req_counts}
        
        # Orders stats
        order_pipeline = [
            {"$match": {"manager_id": current_user["id"]}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        order_counts = await db.purchase_orders.aggregate(order_pipeline).to_list(None)
        order_map = {s["_id"]: s["count"] for s in order_counts}
        
        stats = {
            "pending_orders": req_map.get(RequestStatus.APPROVED_BY_ENGINEER, 0) + req_map.get(RequestStatus.PARTIALLY_ORDERED, 0),
            "total_orders": sum(order_map.values()),
            "pending_approval": order_map.get(PurchaseOrderStatus.PENDING_APPROVAL, 0),
            "approved_orders": order_map.get(PurchaseOrderStatus.APPROVED, 0) + order_map.get(PurchaseOrderStatus.PRINTED, 0),
            "shipped_orders": order_map.get(PurchaseOrderStatus.SHIPPED, 0) + order_map.get(PurchaseOrderStatus.PARTIALLY_DELIVERED, 0),
            "delivered_orders": order_map.get(PurchaseOrderStatus.DELIVERED, 0)
        }
        
    elif current_user["role"] == UserRole.PRINTER:
        order_pipeline = [
            {"$match": {"status": {"$in": [PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PRINTED]}}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        order_counts = await db.purchase_orders.aggregate(order_pipeline).to_list(None)
        order_map = {s["_id"]: s["count"] for s in order_counts}
        
        stats = {
            "pending_print": order_map.get(PurchaseOrderStatus.APPROVED, 0),
            "printed": order_map.get(PurchaseOrderStatus.PRINTED, 0)
        }
        
    elif current_user["role"] == UserRole.DELIVERY_TRACKER:
        order_pipeline = [
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        order_counts = await db.purchase_orders.aggregate(order_pipeline).to_list(None)
        order_map = {s["_id"]: s["count"] for s in order_counts}
        
        stats = {
            "pending_delivery": order_map.get(PurchaseOrderStatus.PRINTED, 0),
            "shipped": order_map.get(PurchaseOrderStatus.SHIPPED, 0),
            "partially_delivered": order_map.get(PurchaseOrderStatus.PARTIALLY_DELIVERED, 0),
            "delivered": order_map.get(PurchaseOrderStatus.DELIVERED, 0),
            "awaiting_shipment": order_map.get(PurchaseOrderStatus.APPROVED, 0) + order_map.get(PurchaseOrderStatus.PRINTED, 0)
        }
    
    return stats

@api_router.get("/v2/search")
async def global_search(
    q: str,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    Global search across requests and purchase orders
    Returns combined results for quick navigation
    """
    results = {
        "requests": [],
        "orders": []
    }
    
    if len(q) < 2:
        return results
    
    search_limit = min(limit, 50)
    
    # Search requests
    request_query = {"$or": [
        {"request_number": {"$regex": q, "$options": "i"}},
        {"items.name": {"$regex": q, "$options": "i"}},
        {"project_name": {"$regex": q, "$options": "i"}}
    ]}
    
    requests = await db.material_requests.find(
        request_query,
        {"_id": 0, "id": 1, "request_number": 1, "project_name": 1, "status": 1, "created_at": 1}
    ).limit(search_limit).to_list(search_limit)
    results["requests"] = requests
    
    # Search orders
    order_query = {"$or": [
        {"id": {"$regex": q, "$options": "i"}},
        {"project_name": {"$regex": q, "$options": "i"}},
        {"supplier_name": {"$regex": q, "$options": "i"}},
        {"supplier_receipt_number": {"$regex": q, "$options": "i"}}
    ]}
    
    orders = await db.purchase_orders.find(
        order_query,
        {"_id": 0, "id": 1, "project_name": 1, "supplier_name": 1, "status": 1, "total_amount": 1, "created_at": 1}
    ).limit(search_limit).to_list(search_limit)
    results["orders"] = orders
    
    return results

# ==================== BACKUP & RESTORE SYSTEM ====================
# نظام النسخ الاحتياطي والاستعادة - لمدير المشتريات فقط

@api_router.get("/backup/export")
async def export_backup(current_user: dict = Depends(get_current_user)):
    """
    تصدير نسخة احتياطية كاملة من النظام
    مدير المشتريات فقط
    """
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه تصدير النسخة الاحتياطية")
    
    now = datetime.now(timezone.utc).isoformat()
    
    backup_data = {
        "backup_info": {
            "created_at": now,
            "created_by": current_user["name"],
            "created_by_id": current_user["id"],
            "version": "2.0"
        },
        "users": await db.users.find({}, {"_id": 0}).to_list(None),
        "projects": await db.projects.find({}, {"_id": 0}).to_list(None),
        "material_requests": await db.material_requests.find({}, {"_id": 0}).to_list(None),
        "purchase_orders": await db.purchase_orders.find({}, {"_id": 0}).to_list(None),
        "suppliers": await db.suppliers.find({}, {"_id": 0}).to_list(None),
        "budget_categories": await db.budget_categories.find({}, {"_id": 0}).to_list(None),
        "default_budget_categories": await db.default_budget_categories.find({}, {"_id": 0}).to_list(None),
        "delivery_records": await db.delivery_records.find({}, {"_id": 0}).to_list(None),
        "audit_logs": await db.audit_logs.find({}, {"_id": 0}).to_list(None),
    }
    
    # Log audit
    await log_audit(
        entity_type="backup",
        entity_id="export",
        action="export",
        user=current_user,
        description=f"تصدير نسخة احتياطية كاملة"
    )
    
    return backup_data

@api_router.post("/backup/import")
async def import_backup(
    backup_data: dict,
    clear_existing: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    استيراد نسخة احتياطية
    مدير المشتريات فقط
    clear_existing: إذا كان True سيحذف البيانات الموجودة قبل الاستيراد
    """
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه استيراد النسخة الاحتياطية")
    
    if "backup_info" not in backup_data:
        raise HTTPException(status_code=400, detail="ملف النسخة الاحتياطية غير صالح")
    
    import_stats = {
        "users": 0,
        "projects": 0,
        "material_requests": 0,
        "purchase_orders": 0,
        "suppliers": 0,
        "budget_categories": 0,
        "default_budget_categories": 0,
        "delivery_records": 0,
        "skipped": 0,
        "errors": []
    }
    
    # Clear existing data if requested
    if clear_existing:
        await db.projects.delete_many({})
        await db.material_requests.delete_many({})
        await db.purchase_orders.delete_many({})
        await db.suppliers.delete_many({})
        await db.budget_categories.delete_many({})
        await db.default_budget_categories.delete_many({})
        await db.delivery_records.delete_many({})
    
    # Import collections
    collections_to_import = [
        ("users", db.users, ["id", "email"]),
        ("projects", db.projects, ["id"]),
        ("material_requests", db.material_requests, ["id"]),
        ("purchase_orders", db.purchase_orders, ["id"]),
        ("suppliers", db.suppliers, ["id"]),
        ("budget_categories", db.budget_categories, ["id"]),
        ("default_budget_categories", db.default_budget_categories, ["id"]),
        ("delivery_records", db.delivery_records, ["id"]),
    ]
    
    for collection_name, collection, unique_fields in collections_to_import:
        if collection_name in backup_data:
            for doc in backup_data[collection_name]:
                try:
                    # Check if document already exists
                    query = {field: doc.get(field) for field in unique_fields if doc.get(field)}
                    if query:
                        existing = await collection.find_one(query)
                        if existing:
                            import_stats["skipped"] += 1
                            continue
                    
                    await collection.insert_one(doc)
                    import_stats[collection_name] += 1
                except Exception as e:
                    import_stats["errors"].append(f"{collection_name}: {str(e)[:50]}")
    
    # Log audit
    await log_audit(
        entity_type="backup",
        entity_id="import",
        action="import",
        user=current_user,
        description=f"استيراد نسخة احتياطية - {sum([import_stats[k] for k in import_stats if isinstance(import_stats[k], int)])} سجل"
    )
    
    return {
        "message": "تم استيراد النسخة الاحتياطية بنجاح",
        "stats": import_stats,
        "backup_info": backup_data.get("backup_info", {})
    }

@api_router.get("/backup/stats")
async def get_backup_stats(current_user: dict = Depends(get_current_user)):
    """
    إحصائيات البيانات الحالية
    مدير المشتريات فقط
    """
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه عرض إحصائيات النسخ الاحتياطي")
    
    stats = {
        "users": await db.users.count_documents({}),
        "projects": await db.projects.count_documents({}),
        "material_requests": await db.material_requests.count_documents({}),
        "purchase_orders": await db.purchase_orders.count_documents({}),
        "suppliers": await db.suppliers.count_documents({}),
        "budget_categories": await db.budget_categories.count_documents({}),
        "default_budget_categories": await db.default_budget_categories.count_documents({}),
        "delivery_records": await db.delivery_records.count_documents({}),
        "audit_logs": await db.audit_logs.count_documents({}),
    }
    
    stats["total_records"] = sum(stats.values())
    
    return stats

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "healthy"}
@api_router.post("/admin/reset-database")
async def reset_database(current_user: dict = Depends(get_current_user)):
    """
    تنظيف قاعدة البيانات بالكامل - للمدير فقط
    ⚠️ تحذير: سيحذف جميع البيانات!
    """
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه تنظيف قاعدة البيانات")
    
    # Delete all collections data
    collections_to_clear = [
        "users",
        "material_requests", 
        "purchase_orders",
        "suppliers",
        "delivery_records",
        "budget_categories",
        "projects",
        "audit_logs",
        "attachments"
    ]
    
    deleted_counts = {}
    for collection_name in collections_to_clear:
        collection = db[collection_name]
        result = await collection.delete_many({})
        deleted_counts[collection_name] = result.deleted_count
    
    return {
        "message": "تم تنظيف قاعدة البيانات بنجاح",
        "deleted": deleted_counts
    }

@api_router.post("/admin/clean-data-keep-users")
async def clean_data_keep_users(current_user: dict = Depends(get_current_user)):
    """
    تنظيف جميع البيانات مع الحفاظ على المستخدمين والتصنيفات الافتراضية
    """
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه تنظيف البيانات")
    
    # Collections to clear (keep users and default_budget_categories)
    collections_to_clear = [
        "material_requests", 
        "purchase_orders",
        "suppliers",
        "delivery_records",
        "budget_categories",
        "projects",
        "audit_logs",
        "attachments"
    ]
    
    deleted_counts = {}
    for collection_name in collections_to_clear:
        collection = db[collection_name]
        result = await collection.delete_many({})
        deleted_counts[collection_name] = result.deleted_count
    
    # Get counts of preserved data
    users_count = await db.users.count_documents({})
    default_cats_count = await db.default_budget_categories.count_documents({})
    
    return {
        "message": "تم تنظيف البيانات بنجاح مع الحفاظ على المستخدمين والتصنيفات الافتراضية",
        "deleted": deleted_counts,
        "preserved": {
            "users": users_count,
            "default_budget_categories": default_cats_count
        }
    }

@api_router.delete("/admin/clear-test-data")
async def clear_test_data(current_user: dict = Depends(get_current_user)):
    """
    حذف البيانات التجريبية فقط (المستخدمين بإيميل @test.com)
    """
    if current_user["role"] != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه حذف البيانات التجريبية")
    
    # Delete test users
    test_users = await db.users.find({"email": {"$regex": "@test.com$"}}).to_list(100)
    test_user_ids = [u["id"] for u in test_users]
    
    deleted = {
        "users": 0,
        "requests": 0,
        "orders": 0,
        "projects": 0,
        "categories": 0,
        "suppliers": 0
    }
    
    if test_user_ids:
        # Delete users
        result = await db.users.delete_many({"email": {"$regex": "@test.com$"}})
        deleted["users"] = result.deleted_count
        
        # Delete their requests
        result = await db.material_requests.delete_many({"supervisor_id": {"$in": test_user_ids}})
        deleted["requests"] = result.deleted_count
        
        # Delete their orders
        result = await db.purchase_orders.delete_many({"manager_id": {"$in": test_user_ids}})
        deleted["orders"] = result.deleted_count
        
        # Delete their projects
        result = await db.projects.delete_many({"created_by": {"$in": test_user_ids}})
        deleted["projects"] = result.deleted_count
        
        # Delete their categories
        result = await db.budget_categories.delete_many({"created_by": {"$in": test_user_ids}})
        deleted["categories"] = result.deleted_count
    
    # Delete test suppliers
    result = await db.suppliers.delete_many({"name": {"$regex": "اختبار|تجريب|test", "$options": "i"}})
    deleted["suppliers"] = result.deleted_count
    
    return {
        "message": "تم حذف البيانات التجريبية بنجاح",
        "deleted": deleted
    }

# ==================== APP CONFIGURATION ====================
# Include the router in the main app (after all routes are defined)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_db_client():
    """Initialize database indexes on startup"""
    await create_indexes()

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
