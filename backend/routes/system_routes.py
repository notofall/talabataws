"""
System Monitoring and Updates API
For System Administrator
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import os
import json
from pathlib import Path

from routes.pg_auth_routes import get_current_user_pg, UserRole
from database import User

system_router = APIRouter(prefix="/api/pg/system", tags=["System"])

# Version file
VERSION_FILE = Path("/app/backend/version.json")
LOGS_DIR = Path("/app/backend/logs")
ERROR_LOG_FILE = LOGS_DIR / "errors.log"

# Ensure logs directory exists
LOGS_DIR.mkdir(exist_ok=True)

# Current version info
CURRENT_VERSION = {
    "version": "2.1.0",
    "build_date": "2025-01-13",
    "release_notes": [
        "إضافة التقارير المتقدمة",
        "تحويل التطبيق إلى PWA",
        "شاشة إعداد قاعدة البيانات",
        "سجل التدقيق",
        "تنظيف الكود"
    ]
}


class SystemLog(BaseModel):
    timestamp: str
    level: str  # ERROR, WARNING, INFO
    source: str
    message: str
    details: Optional[str] = None


class UpdateInfo(BaseModel):
    current_version: str
    latest_version: str
    update_available: bool
    release_notes: List[str]
    download_url: Optional[str] = None


def log_error(source: str, message: str, details: str = None):
    """Log an error to the error log file"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": "ERROR",
        "source": source,
        "message": message,
        "details": details
    }
    
    try:
        with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Failed to write error log: {e}")


def log_warning(source: str, message: str, details: str = None):
    """Log a warning"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": "WARNING",
        "source": source,
        "message": message,
        "details": details
    }
    
    try:
        with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Failed to write warning log: {e}")


def log_info(source: str, message: str, details: str = None):
    """Log info"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": "INFO",
        "source": source,
        "message": message,
        "details": details
    }
    
    try:
        with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Failed to write info log: {e}")


@system_router.get("/info")
async def get_system_info(current_user: User = Depends(get_current_user_pg)):
    """Get current system information"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    # Get server info
    import platform
    import psutil
    
    # Memory info
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "version": CURRENT_VERSION["version"],
        "build_date": CURRENT_VERSION["build_date"],
        "release_notes": CURRENT_VERSION["release_notes"],
        "server": {
            "os": platform.system(),
            "os_version": platform.release(),
            "python_version": platform.python_version(),
            "hostname": platform.node()
        },
        "resources": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_percent": memory.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_percent": round(disk.percent, 1)
        },
        "uptime": datetime.utcnow().isoformat()
    }


@system_router.get("/check-updates")
async def check_for_updates(current_user: User = Depends(get_current_user_pg)):
    """Check if updates are available"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    # In a real scenario, this would check a remote server
    # For now, we simulate by comparing versions
    current = CURRENT_VERSION["version"]
    
    # Simulated latest version (in production, fetch from update server)
    latest = "2.1.0"  # Same as current = no update
    
    # You can change this to test update functionality:
    # latest = "2.2.0"  # Uncomment to simulate available update
    
    update_available = latest > current
    
    return UpdateInfo(
        current_version=current,
        latest_version=latest,
        update_available=update_available,
        release_notes=[
            "إصلاحات أمنية",
            "تحسينات في الأداء",
            "ميزات جديدة"
        ] if update_available else [],
        download_url="https://updates.example.com/v2.2.0.zip" if update_available else None
    )


@system_router.post("/apply-update")
async def apply_update(
    update_url: str = None,
    current_user: User = Depends(get_current_user_pg)
):
    """Apply a system update (placeholder)"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    # Log the update attempt
    log_info("System", f"محاولة تحديث النظام بواسطة {current_user.name}")
    
    # In production, this would:
    # 1. Download the update package
    # 2. Verify the package signature
    # 3. Backup current files
    # 4. Apply the update
    # 5. Restart services
    
    return {
        "success": True,
        "message": "هذه الميزة قيد التطوير. يرجى تحديث النظام يدوياً.",
        "manual_steps": [
            "1. قم بتحميل آخر إصدار من الموقع الرسمي",
            "2. أوقف الخدمات: sudo systemctl stop material-requests",
            "3. خذ نسخة احتياطية من قاعدة البيانات",
            "4. استبدل الملفات بالإصدار الجديد",
            "5. أعد تشغيل الخدمات: sudo systemctl start material-requests"
        ]
    }


@system_router.get("/logs")
async def get_system_logs(
    level: Optional[str] = None,  # ERROR, WARNING, INFO, ALL
    source: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user_pg)
):
    """Get system logs"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    logs = []
    
    # Read logs from file
    if ERROR_LOG_FILE.exists():
        try:
            with open(ERROR_LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # Apply filters
                        if level and level != "ALL" and log_entry.get("level") != level:
                            continue
                        if source and source not in log_entry.get("source", ""):
                            continue
                        
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading logs: {e}")
    
    # Sort by timestamp (newest first) and limit
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    logs = logs[:limit]
    
    # Get log statistics
    all_logs = []
    if ERROR_LOG_FILE.exists():
        try:
            with open(ERROR_LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        all_logs.append(json.loads(line.strip()))
                    except:
                        continue
        except:
            pass
    
    stats = {
        "total": len(all_logs),
        "errors": len([l for l in all_logs if l.get("level") == "ERROR"]),
        "warnings": len([l for l in all_logs if l.get("level") == "WARNING"]),
        "info": len([l for l in all_logs if l.get("level") == "INFO"]),
        "today": len([l for l in all_logs if l.get("timestamp", "")[:10] == datetime.utcnow().strftime("%Y-%m-%d")])
    }
    
    return {
        "logs": logs,
        "stats": stats
    }


@system_router.post("/logs/add")
async def add_log_entry(
    level: str,
    source: str,
    message: str,
    details: Optional[str] = None
):
    """Add a log entry (for internal use or testing)"""
    if level == "ERROR":
        log_error(source, message, details)
    elif level == "WARNING":
        log_warning(source, message, details)
    else:
        log_info(source, message, details)
    
    return {"success": True}


@system_router.delete("/logs/clear")
async def clear_old_logs(
    days_to_keep: int = 30,
    current_user: User = Depends(get_current_user_pg)
):
    """Clear logs older than specified days"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    if not ERROR_LOG_FILE.exists():
        return {"success": True, "deleted": 0, "remaining": 0}
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    
    # Read all logs
    remaining_logs = []
    deleted_count = 0
    
    try:
        with open(ERROR_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    log_time = datetime.fromisoformat(log_entry.get("timestamp", ""))
                    
                    if log_time >= cutoff_date:
                        remaining_logs.append(line)
                    else:
                        deleted_count += 1
                except:
                    remaining_logs.append(line)  # Keep malformed entries
        
        # Rewrite file with remaining logs
        with open(ERROR_LOG_FILE, 'w', encoding='utf-8') as f:
            f.writelines(remaining_logs)
        
        log_info("System", f"تم حذف {deleted_count} سجل قديم بواسطة {current_user.name}")
        
        return {
            "success": True,
            "deleted": deleted_count,
            "remaining": len(remaining_logs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل في حذف السجلات: {str(e)}")


@system_router.get("/database-stats")
async def get_database_stats(current_user: User = Depends(get_current_user_pg)):
    """Get database statistics"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    from sqlalchemy import text
    from database import get_postgres_session, User as UserModel, PurchaseOrder, MaterialRequest, Project, Supplier
    from sqlalchemy import select, func
    
    async for session in get_postgres_session():
        try:
            # Count records in each table
            users_count = await session.execute(select(func.count()).select_from(UserModel))
            orders_count = await session.execute(select(func.count()).select_from(PurchaseOrder))
            requests_count = await session.execute(select(func.count()).select_from(MaterialRequest))
            projects_count = await session.execute(select(func.count()).select_from(Project))
            suppliers_count = await session.execute(select(func.count()).select_from(Supplier))
            
            return {
                "tables": {
                    "users": users_count.scalar(),
                    "purchase_orders": orders_count.scalar(),
                    "material_requests": requests_count.scalar(),
                    "projects": projects_count.scalar(),
                    "suppliers": suppliers_count.scalar()
                },
                "database_type": "PostgreSQL",
                "connection_pool": {
                    "size": 10,
                    "max_overflow": 5
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"فشل في جلب إحصائيات قاعدة البيانات: {str(e)}")
