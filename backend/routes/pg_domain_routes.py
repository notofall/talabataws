"""
PostgreSQL Domain & SSL Routes - Domain Configuration and SSL Management
For System Admin role only
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
import json
import os
from pathlib import Path

from database import get_postgres_session, User, SystemSetting

# Create router
pg_domain_router = APIRouter(prefix="/api/pg/domain", tags=["PostgreSQL Domain & SSL"])

# Import auth dependency
from routes.pg_auth_routes import get_current_user_pg, UserRole

# Data directory for persistent config
DATA_DIR = Path("/app/data")
NGINX_DIR = DATA_DIR / "nginx"
SSL_DIR = DATA_DIR / "ssl"
CONFIG_FILE = DATA_DIR / "domain_config.json"


# ==================== PYDANTIC MODELS ====================

class DomainConfig(BaseModel):
    domain: str
    enable_ssl: bool = True
    ssl_mode: str = "letsencrypt"  # "letsencrypt" or "manual"
    admin_email: Optional[str] = None  # For Let's Encrypt


class SSLCertUpload(BaseModel):
    cert_content: str  # Base64 encoded certificate
    key_content: str   # Base64 encoded private key


class DomainStatus(BaseModel):
    is_configured: bool = False
    domain: Optional[str] = None
    ssl_enabled: bool = False
    ssl_mode: Optional[str] = None
    ssl_valid_until: Optional[str] = None
    nginx_status: str = "not_configured"


# ==================== HELPER FUNCTIONS ====================

def require_system_admin(current_user: User):
    """Check if user is system admin"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="فقط مدير النظام يمكنه الوصول لهذه الصفحة")


def ensure_directories():
    """Ensure required directories exist"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    NGINX_DIR.mkdir(parents=True, exist_ok=True)
    SSL_DIR.mkdir(parents=True, exist_ok=True)


def load_domain_config() -> dict:
    """Load domain configuration from file"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_domain_config(config: dict):
    """Save domain configuration to file"""
    ensure_directories()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def generate_nginx_config(domain: str, ssl_enabled: bool = False) -> str:
    """Generate Nginx configuration"""
    if ssl_enabled:
        return f"""# Nginx Configuration for {domain}
# Generated automatically - Do not edit manually

upstream backend {{
    server backend:8001;
}}

upstream frontend {{
    server frontend:3000;
}}

# Redirect HTTP to HTTPS
server {{
    listen 80;
    server_name {domain};
    
    location /.well-known/acme-challenge/ {{
        root /var/www/certbot;
    }}
    
    location / {{
        return 301 https://$host$request_uri;
    }}
}}

# HTTPS Server
server {{
    listen 443 ssl http2;
    server_name {domain};
    
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy settings
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Backend API
    location /api/ {{
        proxy_pass http://backend/api/;
    }}
    
    # Frontend
    location / {{
        proxy_pass http://frontend/;
    }}
}}
"""
    else:
        return f"""# Nginx Configuration for {domain}
# Generated automatically - Do not edit manually

upstream backend {{
    server backend:8001;
}}

upstream frontend {{
    server frontend:3000;
}}

server {{
    listen 80;
    server_name {domain};
    
    # Proxy settings
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Backend API
    location /api/ {{
        proxy_pass http://backend/api/;
    }}
    
    # Frontend
    location / {{
        proxy_pass http://frontend/;
    }}
}}
"""


def generate_docker_compose_nginx() -> str:
    """Generate docker-compose override for Nginx"""
    return """# Docker Compose Override for Nginx
# Add this to your docker-compose.yml or use as docker-compose.override.yml

version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: talabat_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./data/nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./data/ssl:/etc/nginx/ssl:ro
      - ./data/certbot/www:/var/www/certbot:ro
    depends_on:
      - backend
      - frontend
    restart: unless-stopped
    networks:
      - talabat_network

  # Certbot for Let's Encrypt (optional)
  certbot:
    image: certbot/certbot
    container_name: talabat_certbot
    volumes:
      - ./data/ssl:/etc/letsencrypt
      - ./data/certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
    networks:
      - talabat_network
"""


# ==================== API ENDPOINTS ====================

@pg_domain_router.get("/status")
async def get_domain_status(
    current_user: User = Depends(get_current_user_pg)
):
    """Get current domain configuration status"""
    require_system_admin(current_user)
    
    config = load_domain_config()
    
    status = DomainStatus(
        is_configured=bool(config.get("domain")),
        domain=config.get("domain"),
        ssl_enabled=config.get("ssl_enabled", False),
        ssl_mode=config.get("ssl_mode"),
        ssl_valid_until=config.get("ssl_valid_until"),
        nginx_status="configured" if config.get("domain") else "not_configured"
    )
    
    # Check if SSL certificate exists
    if status.ssl_enabled:
        cert_path = SSL_DIR / "fullchain.pem"
        if cert_path.exists():
            status.nginx_status = "ssl_ready"
        else:
            status.nginx_status = "ssl_pending"
    
    return status


@pg_domain_router.post("/configure")
async def configure_domain(
    domain_config: DomainConfig,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Configure domain and generate Nginx configuration"""
    require_system_admin(current_user)
    
    ensure_directories()
    
    # Validate domain
    domain = domain_config.domain.strip().lower()
    if not domain or " " in domain:
        raise HTTPException(status_code=400, detail="اسم الدومين غير صالح")
    
    # Generate Nginx config
    nginx_config = generate_nginx_config(domain, domain_config.enable_ssl)
    
    # Save Nginx config
    nginx_conf_path = NGINX_DIR / "nginx.conf"
    with open(nginx_conf_path, 'w') as f:
        f.write(nginx_config)
    
    # Save domain config
    config = {
        "domain": domain,
        "ssl_enabled": domain_config.enable_ssl,
        "ssl_mode": domain_config.ssl_mode,
        "admin_email": domain_config.admin_email,
        "configured_at": datetime.utcnow().isoformat(),
        "configured_by": current_user.name
    }
    save_domain_config(config)
    
    # Generate docker-compose override
    docker_compose_content = generate_docker_compose_nginx()
    docker_compose_path = DATA_DIR / "docker-compose.nginx.yml"
    with open(docker_compose_path, 'w') as f:
        f.write(docker_compose_content)
    
    # Save setting to database
    now = datetime.utcnow()
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == "domain_config")
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = json.dumps(config)
        setting.updated_by = current_user.id
        setting.updated_by_name = current_user.name
        setting.updated_at = now
    else:
        new_setting = SystemSetting(
            id=str(uuid.uuid4()),
            key="domain_config",
            value=json.dumps(config),
            description="إعدادات الدومين",
            updated_by=current_user.id,
            updated_by_name=current_user.name,
            created_at=now
        )
        session.add(new_setting)
    
    await session.commit()
    
    return {
        "message": "تم حفظ إعدادات الدومين بنجاح",
        "domain": domain,
        "nginx_config_path": str(nginx_conf_path),
        "docker_compose_path": str(docker_compose_path),
        "next_steps": [
            "1. انسخ ملف docker-compose.nginx.yml إلى مجلد المشروع",
            "2. شغّل: docker-compose -f docker-compose.yml -f data/docker-compose.nginx.yml up -d",
            "3. وجّه الدومين إلى عنوان IP الخادم",
            f"4. {'قم بإعداد شهادة SSL' if domain_config.enable_ssl else 'الدومين جاهز للاستخدام'}"
        ]
    }


@pg_domain_router.post("/ssl/upload")
async def upload_ssl_certificate(
    cert_file: UploadFile = File(..., description="شهادة SSL (fullchain.pem)"),
    key_file: UploadFile = File(..., description="المفتاح الخاص (privkey.pem)"),
    current_user: User = Depends(get_current_user_pg)
):
    """Upload SSL certificate and private key manually"""
    require_system_admin(current_user)
    
    ensure_directories()
    
    # Validate file types
    if not cert_file.filename.endswith(('.pem', '.crt', '.cer')):
        raise HTTPException(status_code=400, detail="صيغة ملف الشهادة غير صالحة")
    
    if not key_file.filename.endswith(('.pem', '.key')):
        raise HTTPException(status_code=400, detail="صيغة ملف المفتاح غير صالحة")
    
    # Read and save certificate
    cert_content = await cert_file.read()
    cert_path = SSL_DIR / "fullchain.pem"
    with open(cert_path, 'wb') as f:
        f.write(cert_content)
    
    # Read and save private key
    key_content = await key_file.read()
    key_path = SSL_DIR / "privkey.pem"
    with open(key_path, 'wb') as f:
        f.write(key_content)
    
    # Set secure permissions
    os.chmod(key_path, 0o600)
    
    # Update config
    config = load_domain_config()
    config["ssl_uploaded_at"] = datetime.utcnow().isoformat()
    config["ssl_uploaded_by"] = current_user.name
    save_domain_config(config)
    
    return {
        "message": "تم رفع شهادة SSL بنجاح",
        "cert_path": str(cert_path),
        "key_path": str(key_path),
        "next_steps": [
            "1. أعد تشغيل Nginx: docker-compose restart nginx",
            "2. تحقق من عمل HTTPS على الدومين"
        ]
    }


@pg_domain_router.post("/ssl/letsencrypt")
async def setup_letsencrypt(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_pg)
):
    """Setup Let's Encrypt SSL certificate automatically"""
    require_system_admin(current_user)
    
    config = load_domain_config()
    
    if not config.get("domain"):
        raise HTTPException(status_code=400, detail="يجب إعداد الدومين أولاً")
    
    if not config.get("admin_email"):
        raise HTTPException(status_code=400, detail="يجب إدخال البريد الإلكتروني للمدير")
    
    domain = config["domain"]
    email = config["admin_email"]
    
    # Generate Let's Encrypt command
    certbot_command = f"""
# أوامر الحصول على شهادة Let's Encrypt
# شغّل هذه الأوامر على الخادم

# 1. تأكد من أن الدومين يشير إلى الخادم
# 2. شغّل Certbot:
docker run -it --rm \\
  -v {SSL_DIR}:/etc/letsencrypt \\
  -v {DATA_DIR}/certbot/www:/var/www/certbot \\
  -p 80:80 \\
  certbot/certbot certonly \\
  --standalone \\
  -d {domain} \\
  --email {email} \\
  --agree-tos \\
  --no-eff-email

# 3. بعد الحصول على الشهادة، انسخها:
cp /etc/letsencrypt/live/{domain}/fullchain.pem {SSL_DIR}/
cp /etc/letsencrypt/live/{domain}/privkey.pem {SSL_DIR}/

# 4. أعد تشغيل Nginx:
docker-compose restart nginx
"""
    
    # Save the command to a file
    script_path = DATA_DIR / "setup_ssl.sh"
    with open(script_path, 'w') as f:
        f.write(certbot_command)
    os.chmod(script_path, 0o755)
    
    return {
        "message": "تم إنشاء سكربت إعداد Let's Encrypt",
        "domain": domain,
        "email": email,
        "script_path": str(script_path),
        "instructions": certbot_command,
        "note": "شغّل السكربت على الخادم بعد التأكد من توجيه الدومين"
    }


@pg_domain_router.get("/nginx-config")
async def get_nginx_config(
    current_user: User = Depends(get_current_user_pg)
):
    """Get current Nginx configuration"""
    require_system_admin(current_user)
    
    nginx_conf_path = NGINX_DIR / "nginx.conf"
    
    if not nginx_conf_path.exists():
        return {"config": None, "message": "لم يتم إعداد Nginx بعد"}
    
    with open(nginx_conf_path, 'r') as f:
        config = f.read()
    
    return {
        "config": config,
        "path": str(nginx_conf_path)
    }


@pg_domain_router.get("/docker-compose")
async def get_docker_compose_config(
    current_user: User = Depends(get_current_user_pg)
):
    """Get Docker Compose configuration for Nginx"""
    require_system_admin(current_user)
    
    docker_compose_path = DATA_DIR / "docker-compose.nginx.yml"
    
    if not docker_compose_path.exists():
        # Generate default
        content = generate_docker_compose_nginx()
        return {"config": content, "path": None, "generated": True}
    
    with open(docker_compose_path, 'r') as f:
        config = f.read()
    
    return {
        "config": config,
        "path": str(docker_compose_path),
        "generated": False
    }


@pg_domain_router.delete("/reset")
async def reset_domain_config(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Reset all domain configuration"""
    require_system_admin(current_user)
    
    # Remove config file
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
    
    # Remove Nginx config
    nginx_conf_path = NGINX_DIR / "nginx.conf"
    if nginx_conf_path.exists():
        nginx_conf_path.unlink()
    
    # Remove SSL certificates
    for cert_file in ["fullchain.pem", "privkey.pem"]:
        cert_path = SSL_DIR / cert_file
        if cert_path.exists():
            cert_path.unlink()
    
    # Remove from database
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == "domain_config")
    )
    setting = result.scalar_one_or_none()
    if setting:
        await session.delete(setting)
        await session.commit()
    
    return {"message": "تم إعادة تعيين إعدادات الدومين بنجاح"}


@pg_domain_router.get("/dns-instructions")
async def get_dns_instructions(
    current_user: User = Depends(get_current_user_pg)
):
    """Get DNS configuration instructions"""
    require_system_admin(current_user)
    
    config = load_domain_config()
    domain = config.get("domain", "your-domain.com")
    
    instructions = f"""
# تعليمات إعداد DNS للدومين: {domain}

## الخطوة 1: الحصول على عنوان IP الخادم
- إذا كنت تستخدم VPS، استخدم عنوان IP العام للخادم
- إذا كنت تستخدم استضافة سحابية، استخدم عنوان IP المقدم من الخدمة

## الخطوة 2: إضافة سجلات DNS
في لوحة تحكم مزود الدومين الخاص بك:

### سجل A (مطلوب):
| النوع | الاسم | القيمة | TTL |
|-------|-------|--------|-----|
| A | @ | [عنوان IP الخادم] | 3600 |
| A | www | [عنوان IP الخادم] | 3600 |

### سجل CNAME (اختياري):
| النوع | الاسم | القيمة | TTL |
|-------|-------|--------|-----|
| CNAME | www | {domain} | 3600 |

## الخطوة 3: انتظر انتشار DNS
- قد يستغرق الأمر من 5 دقائق إلى 48 ساعة
- يمكنك التحقق باستخدام: nslookup {domain}

## الخطوة 4: إعداد SSL (اختياري لكن موصى به)
بعد توجيه الدومين بنجاح:
1. استخدم Let's Encrypt للحصول على شهادة مجانية
2. أو ارفع شهادة SSL الخاصة بك

## مزودي DNS الشائعين:
- Cloudflare: https://dash.cloudflare.com
- GoDaddy: https://dcc.godaddy.com/domains
- Namecheap: https://www.namecheap.com/domains/
- Google Domains: https://domains.google.com

## ملاحظات:
- تأكد من فتح المنافذ 80 و 443 في جدار الحماية
- إذا كنت خلف NAT، قم بإعداد Port Forwarding
"""
    
    return {
        "domain": domain,
        "instructions": instructions
    }
