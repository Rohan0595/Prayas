# syntax=docker/dockerfile:1

# ----------------------------------------
# Stage 1: Build the frontend
# ----------------------------------------
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ----------------------------------------
# Stage 2: Build the backend and serve both
# ----------------------------------------
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (build-essential needed for FAISS/some python libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies natively
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy the built frontend static files over to the backend directory
# so FastAPI can serve them via StaticFiles
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Expose Hugging Face default port
EXPOSE 7860

# Switch into backend directory to match app structure and pathing logic, 
# then launch uvicorn on port 7860
WORKDIR /app/backend

# We must bind to 0.0.0.0 and port 7860 specifically for Hugging Face
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
