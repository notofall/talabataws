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
    """Create indexes for optimized queries with 500+ daily operations"""
    try:
        # Users collection indexes
        await db.users.create_index("id", unique=True)
        await db.users.create_index("email", unique=True)
        await db.users.create_index("role")
        await db.users.create_index("supervisor_prefix")
        
        # Material requests indexes
        await db.material_requests.create_index("id", unique=True)
        await db.material_requests.create_index("supervisor_id")
        await db.material_requests.create_index("engineer_id")
        await db.material_requests.create_index("status")
        await db.material_requests.create_index("created_at")
        await db.material_requests.create_index("request_number")
        await db.material_requests.create_index([("supervisor_id", 1), ("request_seq", -1)])
        await db.material_requests.create_index([("status", 1), ("created_at", -1)])
        
        # Purchase orders indexes
        await db.purchase_orders.create_index("id", unique=True)
        await db.purchase_orders.create_index("request_id")
        await db.purchase_orders.create_index("manager_id")
        await db.purchase_orders.create_index("status")
        await db.purchase_orders.create_index("created_at")
        await db.purchase_orders.create_index("supplier_name")
        await db.purchase_orders.create_index("project_name")
        await db.purchase_orders.create_index([("status", 1), ("created_at", -1)])
        await db.purchase_orders.create_index([("manager_id", 1), ("status", 1)])
        
        print("✅ Database indexes created successfully")
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

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ==================== MODELS ====================

class UserRole:
    SUPERVISOR = "supervisor"
    ENGINEER = "engineer"
    PROCUREMENT_MANAGER = "procurement_manager"
    PRINTER = "printer"  # موظف الطباعة

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

# Material Item Model (single item in a request)
class MaterialItem(BaseModel):
    name: str
    quantity: int
    unit: str = "قطعة"  # الوحدة: قطعة، طن، متر، كيس، الخ

# Material Request Models
class MaterialRequestCreate(BaseModel):
    items: List[MaterialItem]
    project_name: str
    reason: str
    engineer_id: str

class MaterialRequestUpdate(BaseModel):
    status: str
    rejection_reason: Optional[str] = None

class MaterialRequestResponse(BaseModel):
    id: str
    request_number: Optional[str] = None  # رقم الطلب المتسلسل للمشرف (A1, A2, B1...)
    request_seq: Optional[int] = None  # الرقم التسلسلي فقط
    items: List[MaterialItem]
    project_name: str
    reason: str
    supervisor_id: str
    supervisor_name: str
    engineer_id: str
    engineer_name: str
    status: str
    rejection_reason: Optional[str] = None
    created_at: str
    updated_at: str

# Purchase Order Models
class PurchaseOrderCreate(BaseModel):
    request_id: str
    supplier_name: str
    selected_items: List[int]  # قائمة فهارس الأصناف المختارة من الطلب الأصلي
    notes: Optional[str] = None

class PurchaseOrderResponse(BaseModel):
    id: str
    request_id: str
    request_number: Optional[str] = None  # رقم الطلب المتسلسل (A1, A2, B1...)
    items: List[MaterialItem]
    project_name: str
    supplier_name: str
    notes: Optional[str] = None
    manager_id: str
    manager_name: str
    supervisor_name: Optional[str] = None
    engineer_name: Optional[str] = None
    status: str  # pending_approval, approved, printed
    created_at: str
    approved_at: Optional[str] = None
    printed_at: Optional[str] = None

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
    valid_roles = [UserRole.SUPERVISOR, UserRole.ENGINEER, UserRole.PROCUREMENT_MANAGER, UserRole.PRINTER]
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

# ==================== MATERIAL REQUESTS ROUTES ====================

@api_router.post("/requests", response_model=MaterialRequestResponse)
async def create_material_request(
    request_data: MaterialRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="فقط المشرفين يمكنهم إنشاء طلبات")
    
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
        "project_name": request_data.project_name,
        "reason": request_data.reason,
        "supervisor_id": current_user["id"],
        "supervisor_name": current_user["name"],
        "engineer_id": request_data.engineer_id,
        "engineer_name": engineer["name"],
        "status": RequestStatus.PENDING_ENGINEER,
        "rejection_reason": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.material_requests.insert_one(request_doc)
    
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
        <p><strong>المشروع:</strong> {request_data.project_name}</p>
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
        # مدير المشتريات يرى الطلبات المعتمدة والتي بها أوامر شراء جزئية
        query["status"] = {"$in": [RequestStatus.APPROVED_BY_ENGINEER, RequestStatus.PARTIALLY_ORDERED]}
    
    requests = await db.material_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [MaterialRequestResponse(**r) for r in requests]

@api_router.get("/requests/all", response_model=List[MaterialRequestResponse])
async def get_all_requests(current_user: dict = Depends(get_current_user)):
    """Get all requests for viewing (all users can see all requests)"""
    requests = await db.material_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [MaterialRequestResponse(**r) for r in requests]

# Model for updating request
class MaterialRequestEdit(BaseModel):
    items: List[MaterialItem]
    project_name: str
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
        "project_name": edit_data.project_name,
        "reason": edit_data.reason,
        "engineer_id": edit_data.engineer_id,
        "engineer_name": engineer["name"],
        "updated_at": now
    }
    
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
    
    selected_items = []
    for idx in order_data.selected_items:
        if 0 <= idx < len(all_items):
            selected_items.append(all_items[idx])
        else:
            raise HTTPException(status_code=400, detail=f"فهرس الصنف {idx} غير صالح")
    
    if not selected_items:
        raise HTTPException(status_code=400, detail="الرجاء اختيار صنف واحد على الأقل")
    
    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    order_doc = {
        "id": order_id,
        "request_id": order_data.request_id,
        "request_number": request.get("request_number"),  # رقم الطلب المتسلسل
        "items": selected_items,
        "project_name": request["project_name"],
        "supplier_name": order_data.supplier_name,
        "notes": order_data.notes,
        "manager_id": current_user["id"],
        "manager_name": current_user["name"],
        "supervisor_name": request.get("supervisor_name", ""),
        "engineer_name": request.get("engineer_name", ""),
        "status": PurchaseOrderStatus.PENDING_APPROVAL,
        "created_at": now,
        "approved_at": None,
        "printed_at": None
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

@api_router.get("/purchase-orders", response_model=List[PurchaseOrderResponse])
async def get_purchase_orders(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == UserRole.PROCUREMENT_MANAGER:
        query["manager_id"] = current_user["id"]
    elif current_user["role"] == UserRole.PRINTER:
        # موظف الطباعة يرى فقط الأوامر المعتمدة
        query["status"] = {"$in": [PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PRINTED]}
    
    orders = await db.purchase_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Handle legacy orders without status field and fetch supervisor/engineer names
    result = []
    for o in orders:
        if "status" not in o:
            o["status"] = PurchaseOrderStatus.APPROVED  # Default to approved for old orders
        if "approved_at" not in o:
            o["approved_at"] = None
        if "printed_at" not in o:
            o["printed_at"] = None
        
        # Fetch supervisor and engineer names and request_number from original request if not present
        if "supervisor_name" not in o or "engineer_name" not in o or "request_number" not in o:
            request = await db.material_requests.find_one({"id": o.get("request_id")}, {"_id": 0})
            if request:
                o["supervisor_name"] = request.get("supervisor_name", "")
                o["engineer_name"] = request.get("engineer_name", "")
                o["request_number"] = request.get("request_number")
            else:
                o["supervisor_name"] = o.get("supervisor_name", "")
                o["engineer_name"] = o.get("engineer_name", "")
                o["request_number"] = o.get("request_number")
        
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
    
    # Get all purchase orders for this request
    existing_orders = await db.purchase_orders.find({"request_id": request_id}, {"_id": 0}).to_list(100)
    
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
    return [PurchaseOrderResponse(**o) for o in orders]

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

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include the router in the main app
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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
