# ============================================
# Frontend Dockerfile - نظام طلبات المواد
# ============================================
FROM node:18-alpine

WORKDIR /app

# نسخ ملفات الحزم أولاً للاستفادة من التخزين المؤقت
COPY package*.json ./

# تنظيف وتثبيت التبعيات
RUN rm -rf node_modules package-lock.json && \
    npm cache clean --force && \
    npm install --legacy-peer-deps && \
    npm install ajv@latest --legacy-peer-deps

# نسخ ملفات المشروع
COPY . .

# بناء التطبيق مع URL افتراضي (سيتم استبداله عند التشغيل)
ENV REACT_APP_BACKEND_URL=http://localhost:8001
RUN npm run build

# تثبيت serve لتقديم الملفات الثابتة
RUN npm install -g serve

# جعل سكربت التشغيل قابل للتنفيذ
RUN chmod +x /app/entrypoint.sh

EXPOSE 3000

# استخدام سكربت التشغيل
ENTRYPOINT ["/app/entrypoint.sh"]
