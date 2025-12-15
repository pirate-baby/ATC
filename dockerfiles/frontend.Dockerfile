# ATC Frontend Dockerfile
# React application with Vite and hot-reload support for development

FROM node:20-alpine

WORKDIR /app

# Install dependencies first for better caching
COPY package*.json ./

RUN npm ci

# Copy application code
# Note: In development, this is overridden by volume mount
COPY . .

# Expose Vite dev server port
EXPOSE 3000

# Default command (overridden in docker-compose for development)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
