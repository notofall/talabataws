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

class RequestStatus:
    PENDING_ENGINEER = "pending_engineer"
    APPROVED_BY_ENGINEER = "approved_by_engineer"
    REJECTED_BY_ENGINEER = "rejected_by_engineer"
    PURCHASE_ORDER_ISSUED = "purchase_order_issued"

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
    notes: Optional[str] = None

class PurchaseOrderResponse(BaseModel):
    id: str
    request_id: str
    items: List[MaterialItem]
    project_name: str
    supplier_name: str
    notes: Optional[str] = None
    manager_id: str
    manager_name: str
    created_at: str

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
    valid_roles = [UserRole.SUPERVISOR, UserRole.ENGINEER, UserRole.PROCUREMENT_MANAGER]
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
    
    # Convert items to dict format
    items_list = [item.model_dump() for item in request_data.items]
    
    request_doc = {
        "id": request_id,
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
        <h2>طلب مواد جديد</h2>
        <p>مرحباً {engineer['name']},</p>
        <p>تم استلام طلب مواد جديد يحتاج لاعتمادك:</p>
        <p><strong>المواد المطلوبة:</strong></p>
        <ul>{items_html}</ul>
        <p><strong>المشروع:</strong> {request_data.project_name}</p>
        <p><strong>السبب:</strong> {request_data.reason}</p>
        <p><strong>المشرف:</strong> {current_user['name']}</p>
    </div>
    """
    await send_email_notification(
        engineer["email"],
        "طلب مواد جديد يحتاج اعتمادك",
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
        query["status"] = RequestStatus.APPROVED_BY_ENGINEER
    
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
        raise HTTPException(status_code=400, detail="لا يمكن تعديل هذا الطلب")
    
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
        raise HTTPException(status_code=400, detail="لا يمكن تعديل هذا الطلب")
    
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
    
    if request["status"] != RequestStatus.APPROVED_BY_ENGINEER:
        raise HTTPException(status_code=400, detail="الطلب غير معتمد من المهندس")
    
    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    order_doc = {
        "id": order_id,
        "request_id": order_data.request_id,
        "items": request.get("items", []),
        "project_name": request["project_name"],
        "supplier_name": order_data.supplier_name,
        "notes": order_data.notes,
        "manager_id": current_user["id"],
        "manager_name": current_user["name"],
        "created_at": now
    }
    
    await db.purchase_orders.insert_one(order_doc)
    
    # Update request status
    await db.material_requests.update_one(
        {"id": order_data.request_id},
        {"$set": {
            "status": RequestStatus.PURCHASE_ORDER_ISSUED,
            "updated_at": now
        }}
    )
    
    # Notify supervisor and engineer
    supervisor = await db.users.find_one({"id": request["supervisor_id"]}, {"_id": 0})
    engineer = await db.users.find_one({"id": request["engineer_id"]}, {"_id": 0})
    
    # Build items list for email
    items_html = "".join([f"<li>{item['name']} - {item['quantity']} {item.get('unit', 'قطعة')}</li>" for item in request.get('items', [])])
    
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

@api_router.get("/purchase-orders", response_model=List[PurchaseOrderResponse])
async def get_purchase_orders(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == UserRole.PROCUREMENT_MANAGER:
        query["manager_id"] = current_user["id"]
    
    orders = await db.purchase_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
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
            "status": {"$in": [RequestStatus.APPROVED_BY_ENGINEER, RequestStatus.PURCHASE_ORDER_ISSUED]}
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
            "status": {"$in": [RequestStatus.APPROVED_BY_ENGINEER, RequestStatus.PURCHASE_ORDER_ISSUED]}
        })
        stats = {"total": total, "pending": pending, "approved": approved}
    
    elif current_user["role"] == UserRole.PROCUREMENT_MANAGER:
        pending_orders = await db.material_requests.count_documents({
            "status": RequestStatus.APPROVED_BY_ENGINEER
        })
        total_orders = await db.purchase_orders.count_documents({})
        stats = {"pending_orders": pending_orders, "total_orders": total_orders}
    
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
