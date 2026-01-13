# متغيرات البيئة المطلوبة للنشر
# Deployment Environment Variables

## Backend (.env)

# PostgreSQL Database - PlanetScale
POSTGRES_HOST=eu-central-2.pg.psdb.cloud
POSTGRES_PORT=6432
POSTGRES_DB=postgres
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_SSLMODE=require

# OR use DATABASE_URL directly
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database?ssl=require

# Security
SECRET_KEY=your-super-secret-key-change-this

# CORS (comma-separated origins)
CORS_ORIGINS=https://your-domain.com,https://material-system.emergent.host

# SendGrid (optional)
SENDGRID_API_KEY=
SENDER_EMAIL=

## Frontend (.env)

REACT_APP_BACKEND_URL=https://your-backend-url
WDS_SOCKET_PORT=443
ENABLE_HEALTH_CHECK=false
