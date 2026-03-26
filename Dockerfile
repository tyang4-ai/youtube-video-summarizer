FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy frontend build
COPY --from=frontend-build /app/frontend/dist ./app/static/

# Create data directory
RUN mkdir -p /data/pdfs

# Copy and set up start script
COPY start.sh ./
RUN chmod +x start.sh

ENV PORT=8000
EXPOSE 8000
CMD ["/app/start.sh"]
