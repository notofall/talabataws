"""
System Monitoring and Updates API
For System Administrator
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import os
import json
import shutil
import zipfile
import subprocess
from pathlib import Path

from routes.pg_auth_routes import get_current_user_pg, UserRole
from database import User

system_router = APIRouter(prefix="/api/pg/system", tags=["System"])

# Paths - Use relative paths for Docker compatibility
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
UPDATES_DIR = BASE_DIR / "updates"
BACKUP_DIR = BASE_DIR / "backups"
VERSION_FILE = BASE_DIR / "version.json"
APP_ROOT = BASE_DIR.parent
ERROR_LOG_FILE = LOGS_DIR / "errors.log"

# Ensure directories exist with parents
LOGS_DIR.mkdir(parents=True, exist_ok=True)
UPDATES_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Current version info
CURRENT_VERSION = {
    "version": "2.1.0",
    "build_date": "2025-01-13",
    "release_notes": [
        "إضافة التقارير المتقدمة",
        "تحويل التطبيق إلى PWA",
        "شاشة إعداد قاعدة البيانات",
        "سجل التدقيق",
        "تنظيف الكود",
        "أدوات النظام ونظام التحديثات"
    ]
}

# Update status tracking
update_status = {
    "in_progress": False,
    "current_step": "",
    "progress": 0,
    "error": None,
    "last_update": None
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
    """Check if updates are available from GitHub"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    import httpx
    
    current = CURRENT_VERSION["version"]
    latest = current
    release_notes = []
    download_url = None
    
    # Check GitHub releases for updates
    # Change this to your GitHub repo
    github_repo = os.environ.get("GITHUB_REPO", "")
    
    if github_repo:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.github.com/repos/{github_repo}/releases/latest",
                    headers={"Accept": "application/vnd.github.v3+json"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    release_data = response.json()
                    latest = release_data.get("tag_name", "").lstrip("v")
                    release_notes = release_data.get("body", "").split("\n")[:10]
                    download_url = release_data.get("html_url")
        except Exception as e:
            # If GitHub check fails, continue with current version
            print(f"Failed to check GitHub for updates: {e}")
    
    update_available = latest > current
    
    return UpdateInfo(
        current_version=current,
        latest_version=latest,
        update_available=update_available,
        release_notes=release_notes if update_available else [],
        download_url=download_url
    )


def apply_update_background(zip_path: Path, user_name: str):
    """Background task to apply update from ZIP file"""
    global update_status
    
    try:
        update_status["in_progress"] = True
        update_status["error"] = None
        
        # Step 1: Validate ZIP file
        update_status["current_step"] = "التحقق من ملف التحديث..."
        update_status["progress"] = 10
        
        if not zipfile.is_zipfile(zip_path):
            raise Exception("الملف ليس ملف ZIP صالح")
        
        # Step 2: Create backup
        update_status["current_step"] = "إنشاء نسخة احتياطية..."
        update_status["progress"] = 20
        
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = BACKUP_DIR / backup_name
        
        # Backup critical directories
        if (APP_ROOT / "backend").exists():
            shutil.copytree(APP_ROOT / "backend", backup_path / "backend", 
                          ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'updates', 'backups', 'logs'))
        if (APP_ROOT / "frontend" / "src").exists():
            shutil.copytree(APP_ROOT / "frontend" / "src", backup_path / "frontend_src")
        
        # Step 3: Extract ZIP
        update_status["current_step"] = "فك ضغط ملف التحديث..."
        update_status["progress"] = 40
        
        extract_dir = UPDATES_DIR / f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        extract_dir.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Find the root folder in extracted content (GitHub adds a folder)
        extracted_items = list(extract_dir.iterdir())
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            source_dir = extracted_items[0]
        else:
            source_dir = extract_dir
        
        # Step 4: Apply backend updates
        update_status["current_step"] = "تحديث ملفات Backend..."
        update_status["progress"] = 60
        
        if (source_dir / "backend").exists():
            # Copy new backend files (preserve .env and data)
            for item in (source_dir / "backend").iterdir():
                if item.name not in ['.env', 'data', 'logs', 'updates', 'backups', '__pycache__']:
                    try:
                        dest = APP_ROOT / "backend" / item.name
                        if item.is_dir():
                            if dest.exists():
                                shutil.rmtree(dest)
                            shutil.copytree(item, dest)
                        else:
                            shutil.copy2(item, dest)
                    except Exception as copy_error:
                        log_warning("Update", f"تخطي نسخ {item.name}: {copy_error}")
        
        # Step 5: Apply frontend updates
        update_status["current_step"] = "تحديث ملفات Frontend..."
        update_status["progress"] = 80
        
        if (source_dir / "frontend" / "src").exists():
            try:
                dest_src = APP_ROOT / "frontend" / "src"
                if dest_src.exists():
                    shutil.rmtree(dest_src)
                shutil.copytree(source_dir / "frontend" / "src", dest_src)
            except Exception as frontend_error:
                log_warning("Update", f"فشل تحديث Frontend: {frontend_error}")
        
        # Step 6: Install dependencies (if requirements changed)
        update_status["current_step"] = "تثبيت المتطلبات..."
        update_status["progress"] = 90
        
        if (source_dir / "backend" / "requirements.txt").exists():
            try:
                subprocess.run(
                    ["pip", "install", "-r", str(APP_ROOT / "backend" / "requirements.txt")],
                    check=True, capture_output=True, timeout=120
                )
            except Exception as e:
                log_warning("Update", f"فشل تثبيت المتطلبات: {e}")
        
        # Step 7: Cleanup
        update_status["current_step"] = "تنظيف الملفات المؤقتة..."
        update_status["progress"] = 95
        
        # Remove extracted files
        shutil.rmtree(extract_dir, ignore_errors=True)
        zip_path.unlink(missing_ok=True)
        
        # Keep only last 5 backups
        backups = sorted(BACKUP_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
        for old_backup in backups[5:]:
            shutil.rmtree(old_backup, ignore_errors=True)
        
        # Step 8: Complete
        update_status["current_step"] = "اكتمل التحديث بنجاح!"
        update_status["progress"] = 100
        update_status["last_update"] = datetime.now().isoformat()
        
        log_info("Update", f"تم تطبيق التحديث بنجاح بواسطة {user_name}")
        
    except Exception as e:
        update_status["error"] = str(e)
        update_status["current_step"] = f"فشل التحديث: {e}"
        log_error("Update", f"فشل التحديث: {e}")
        
        # Try to restore from backup if exists
        if 'backup_path' in locals() and backup_path.exists():
            try:
                log_info("Update", "محاولة استعادة النسخة الاحتياطية...")
                if (backup_path / "backend").exists():
                    for item in (backup_path / "backend").iterdir():
                        dest = APP_ROOT / "backend" / item.name
                        if item.is_dir():
                            if dest.exists():
                                shutil.rmtree(dest)
                            shutil.copytree(item, dest)
                        else:
                            shutil.copy2(item, dest)
            except Exception as restore_error:
                log_error("Update", f"فشل استعادة النسخة الاحتياطية: {restore_error}")
    
    finally:
        update_status["in_progress"] = False


@system_router.post("/upload-update")
async def upload_update_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_pg)
):
    """Upload and apply update from ZIP file"""
    global update_status
    
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    if update_status["in_progress"]:
        raise HTTPException(status_code=400, detail="يوجد تحديث قيد التنفيذ حالياً")
    
    # Validate file type
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="يجب رفع ملف ZIP فقط")
    
    # Save uploaded file
    upload_path = UPDATES_DIR / f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    try:
        with open(upload_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        log_info("Update", f"تم رفع ملف التحديث: {file.filename} بواسطة {current_user.name}")
        
        # Start background update process
        background_tasks.add_task(apply_update_background, upload_path, current_user.name)
        
        return {
            "success": True,
            "message": "تم رفع الملف وبدأ التحديث",
            "filename": file.filename
        }
    
    except Exception as e:
        log_error("Update", f"فشل رفع ملف التحديث: {e}")
        raise HTTPException(status_code=500, detail=f"فشل رفع الملف: {str(e)}")


@system_router.get("/update-status")
async def get_update_status(current_user: User = Depends(get_current_user_pg)):
    """Get current update status"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    return update_status


@system_router.get("/backups")
async def list_backups(current_user: User = Depends(get_current_user_pg)):
    """List available backups"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    backups = []
    if BACKUP_DIR.exists():
        for backup in sorted(BACKUP_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if backup.is_dir():
                backups.append({
                    "name": backup.name,
                    "date": datetime.fromtimestamp(backup.stat().st_mtime).isoformat(),
                    "size_mb": round(sum(f.stat().st_size for f in backup.rglob('*') if f.is_file()) / (1024*1024), 2)
                })
    
    return backups


@system_router.post("/apply-update")
async def apply_update(
    update_url: str = None,
    current_user: User = Depends(get_current_user_pg)
):
    """Apply a system update - instructions for manual update"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    log_info("System", f"طلب تعليمات التحديث بواسطة {current_user.name}")
    
    return {
        "success": True,
        "message": "يمكنك تحديث النظام بإحدى الطريقتين:",
        "methods": {
            "upload": {
                "title": "رفع ملف ZIP",
                "steps": [
                    "1. حمّل ملف ZIP من GitHub Releases",
                    "2. ارفع الملف من خلال 'رفع تحديث' أدناه",
                    "3. النظام سيطبق التحديث تلقائياً"
                ]
            },
            "docker": {
                "title": "Docker (موصى به)",
                "steps": [
                    "1. على الخادم: docker-compose pull",
                    "2. docker-compose down",
                    "3. docker-compose up -d"
                ]
            },
            "manual": {
                "title": "يدوي (SSH)",
                "steps": [
                    "1. حمّل آخر إصدار من GitHub",
                    "2. أوقف الخدمات: sudo systemctl stop material-requests",
                    "3. خذ نسخة احتياطية",
                    "4. استبدل الملفات",
                    "5. أعد تشغيل: sudo systemctl start material-requests"
                ]
            }
        }
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
