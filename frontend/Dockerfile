# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package.json yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile || yarn install

# Copy source code
COPY . .

# Build argument for backend URL
ARG REACT_APP_BACKEND_URL=http://localhost/api
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

# Build the app
RUN yarn build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Install serve for serving static files
RUN npm install -g serve

# Copy built files
COPY --from=build /app/build ./build

# Expose port
EXPOSE 3000

# Serve the app
CMD ["serve", "-s", "build", "-l", "3000"]
