FROM node:18-alpine

WORKDIR /app

COPY package*.json ./

RUN rm -rf node_modules package-lock.json
RUN npm cache clean --force
RUN npm install --legacy-peer-deps
RUN npm install ajv@latest --legacy-peer-deps

COPY . .

ENV REACT_APP_BACKEND_URL=http://localhost:8001

RUN npm run build

RUN npm install -g serve

EXPOSE 3000

CMD ["serve", "-s", "build", "-l", "3000"]
