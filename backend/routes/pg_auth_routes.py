"""
PostgreSQL Auth Routes - Users and Authentication
Migrated from MongoDB to PostgreSQL
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import uuid
import os
import json

from database import get_postgres_session, User

# JWT Settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Create router
pg_auth_router = APIRouter(prefix="/api/pg", tags=["PostgreSQL Auth"])

# ==================== PYDANTIC MODELS ====================

class UserRole:
    SYSTEM_ADMIN = "system_admin"  # مدير النظام - جديد
    SUPERVISOR = "supervisor"
    ENGINEER = "engineer"
    PROCUREMENT_MANAGER = "procurement_manager"
    PRINTER = "printer"
    DELIVERY_TRACKER = "delivery_tracker"
    GENERAL_MANAGER = "general_manager"
    QUANTITY_ENGINEER = "quantity_engineer"  # مهندس الكميات - جديد


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool = True
    supervisor_prefix: Optional[str] = None
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SetupFirstAdmin(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserCreateByAdmin(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    assigned_projects: Optional[List[str]] = []
    assigned_engineers: Optional[List[str]] = []


class UserUpdateByAdmin(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    assigned_projects: Optional[List[str]] = None
    assigned_engineers: Optional[List[str]] = None


class AdminResetPassword(BaseModel):
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


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


async def get_current_user_pg(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get current user from PostgreSQL"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="رمز الدخول غير صالح")
        
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user is None:
            raise HTTPException(status_code=401, detail="المستخدم غير موجود")
        
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="رمز الدخول غير صالح")


# ==================== AUTH ROUTES ====================

@pg_auth_router.get("/health")
async def pg_health_check(session: AsyncSession = Depends(get_postgres_session)):
    """Health check for PostgreSQL connection"""
    try:
        result = await session.execute(select(func.count()).select_from(User))
        count = result.scalar()
        return {"status": "healthy", "database": "postgresql", "users_count": count}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


@pg_auth_router.get("/setup/check")
async def check_setup_required(session: AsyncSession = Depends(get_postgres_session)):
    """Check if system needs initial setup - now checks for system_admin"""
    result = await session.execute(
        select(func.count()).select_from(User).where(User.role == UserRole.SYSTEM_ADMIN)
    )
    admin_count = result.scalar()
    return {"setup_required": admin_count == 0}


@pg_auth_router.post("/setup/first-admin", response_model=TokenResponse)
async def create_first_admin(
    admin_data: SetupFirstAdmin,
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create first system admin - only available if no admin exists"""
    # Check if any system admin exists
    result = await session.execute(
        select(func.count()).select_from(User).where(User.role == UserRole.SYSTEM_ADMIN)
    )
    admin_count = result.scalar()
    
    if admin_count > 0:
        raise HTTPException(status_code=400, detail="تم إعداد النظام مسبقاً")
    
    # Check if email exists
    result = await session.execute(select(User).where(User.email == admin_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل مسبقاً")
    
    # Validate password
    if len(admin_data.password) < 6:
        raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تكون 6 أحرف على الأقل")
    
    # Create system admin user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(admin_data.password)
    
    new_user = User(
        id=user_id,
        name=admin_data.name,
        email=admin_data.email,
        password=hashed_password,
        role=UserRole.SYSTEM_ADMIN,  # Changed to system_admin
        is_active=True,
        assigned_projects="[]",
        assigned_engineers="[]"
    )
    
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    
    access_token = create_access_token({"sub": user_id})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user_id,
            name=admin_data.name,
            email=admin_data.email,
            role=UserRole.SYSTEM_ADMIN,
            is_active=True
        )
    )


@pg_auth_router.post("/auth/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    session: AsyncSession = Depends(get_postgres_session)
):
    """Login user"""
    result = await session.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(credentials.password, user.password):
        raise HTTPException(status_code=401, detail="البريد الإلكتروني أو كلمة المرور غير صحيحة")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="تم تعطيل حسابك. تواصل مع مدير النظام")
    
    access_token = create_access_token({"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            supervisor_prefix=user.supervisor_prefix
        )
    )


@pg_auth_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user_pg)):
    """Get current user info"""
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        supervisor_prefix=current_user.supervisor_prefix
    )


@pg_auth_router.post("/auth/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Change current user's password"""
    if not verify_password(password_data.current_password, current_user.password):
        raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة")
    
    if len(password_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل")
    
    current_user.password = get_password_hash(password_data.new_password)
    await session.commit()
    
    return {"message": "تم تغيير كلمة المرور بنجاح"}


# ==================== USER MANAGEMENT ROUTES ====================

@pg_auth_router.get("/users/list")
async def get_users_list_for_filters(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get list of users for filters - accessible by all authenticated users"""
    result = await session.execute(select(User).where(User.is_active == True).order_by(User.name))
    users = result.scalars().all()
    
    return [
        {
            "id": u.id,
            "name": u.name,
            "role": u.role
        }
        for u in users
    ]


@pg_auth_router.get("/admin/users")
async def get_all_users_admin(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get all users - system admin only"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="فقط مدير النظام يمكنه إدارة المستخدمين")
    
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "supervisor_prefix": u.supervisor_prefix,
            "assigned_projects": json.loads(u.assigned_projects or "[]"),
            "assigned_engineers": json.loads(u.assigned_engineers or "[]"),
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]


@pg_auth_router.post("/admin/users")
async def create_user_by_admin(
    user_data: UserCreateByAdmin,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create a new user - system admin only"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="فقط مدير النظام يمكنه إنشاء المستخدمين")
    
    # Check if email exists
    result = await session.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل مسبقاً")
    
    # Validate role
    valid_roles = [UserRole.SYSTEM_ADMIN, UserRole.SUPERVISOR, UserRole.ENGINEER, UserRole.PROCUREMENT_MANAGER,
                   UserRole.PRINTER, UserRole.DELIVERY_TRACKER, UserRole.GENERAL_MANAGER, UserRole.QUANTITY_ENGINEER]
    if user_data.role not in valid_roles:
        raise HTTPException(status_code=400, detail="الدور غير صالح")
    
    # Validate password
    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تكون 6 أحرف على الأقل")
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)
    
    # Assign supervisor prefix if supervisor
    supervisor_prefix = None
    if user_data.role == UserRole.SUPERVISOR:
        result = await session.execute(
            select(User.supervisor_prefix).where(
                User.role == UserRole.SUPERVISOR,
                User.supervisor_prefix.isnot(None)
            )
        )
        existing_prefixes = [r[0] for r in result.fetchall()]
        
        available_prefixes = [chr(i) for i in range(65, 91)]  # A-Z
        for prefix in existing_prefixes:
            if prefix in available_prefixes:
                available_prefixes.remove(prefix)
        
        if available_prefixes:
            supervisor_prefix = available_prefixes[0]
    
    new_user = User(
        id=user_id,
        name=user_data.name,
        email=user_data.email,
        password=hashed_password,
        role=user_data.role,
        is_active=True,
        supervisor_prefix=supervisor_prefix,
        assigned_projects=json.dumps(user_data.assigned_projects or []),
        assigned_engineers=json.dumps(user_data.assigned_engineers or [])
    )
    
    session.add(new_user)
    await session.commit()
    
    return {
        "message": "تم إنشاء المستخدم بنجاح",
        "user": {
            "id": user_id,
            "name": user_data.name,
            "email": user_data.email,
            "role": user_data.role
        }
    }


@pg_auth_router.put("/admin/users/{user_id}")
async def update_user_by_admin(
    user_id: str,
    user_data: UserUpdateByAdmin,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Update a user - system admin only"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="فقط مدير النظام يمكنه تعديل المستخدمين")
    
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    if user_data.name is not None:
        user.name = user_data.name
    
    if user_data.email is not None and user_data.email != user.email:
        result = await session.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل مسبقاً")
        user.email = user_data.email
    
    if user_data.role is not None:
        valid_roles = [UserRole.SYSTEM_ADMIN, UserRole.SUPERVISOR, UserRole.ENGINEER, UserRole.PROCUREMENT_MANAGER,
                       UserRole.PRINTER, UserRole.DELIVERY_TRACKER, UserRole.GENERAL_MANAGER, UserRole.QUANTITY_ENGINEER]
        if user_data.role not in valid_roles:
            raise HTTPException(status_code=400, detail="الدور غير صالح")
        user.role = user_data.role
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    if user_data.assigned_projects is not None:
        user.assigned_projects = json.dumps(user_data.assigned_projects)
    
    if user_data.assigned_engineers is not None:
        user.assigned_engineers = json.dumps(user_data.assigned_engineers)
    
    await session.commit()
    
    return {"message": "تم تحديث المستخدم بنجاح"}


@pg_auth_router.post("/admin/users/{user_id}/reset-password")
async def admin_reset_user_password(
    user_id: str,
    password_data: AdminResetPassword,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Reset user password - system admin only"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="فقط مدير النظام يمكنه إعادة تعيين كلمات المرور")
    
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    if len(password_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تكون 6 أحرف على الأقل")
    
    user.password = get_password_hash(password_data.new_password)
    await session.commit()
    
    return {"message": "تم إعادة تعيين كلمة المرور بنجاح"}


@pg_auth_router.put("/admin/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Toggle user active status - system admin only"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="فقط مدير النظام يمكنه تغيير حالة المستخدمين")
    
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="لا يمكنك تعطيل حسابك")
    
    user.is_active = not user.is_active
    await session.commit()
    
    return {
        "message": f"تم {'تفعيل' if user.is_active else 'تعطيل'} الحساب بنجاح",
        "is_active": user.is_active
    }


@pg_auth_router.delete("/admin/users/{user_id}")
async def delete_user_by_admin(
    user_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Delete a user - system admin only"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="فقط مدير النظام يمكنه حذف المستخدمين")
    
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="لا يمكنك حذف حسابك")
    
    await session.delete(user)
    await session.commit()
    
    return {"message": "تم حذف المستخدم بنجاح"}


@pg_auth_router.get("/users/engineers")
async def get_engineers(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get all engineers"""
    result = await session.execute(
        select(User).where(User.role == UserRole.ENGINEER)
    )
    engineers = result.scalars().all()
    
    return [
        UserResponse(
            id=e.id,
            name=e.name,
            email=e.email,
            role=e.role,
            is_active=e.is_active
        )
        for e in engineers
    ]
