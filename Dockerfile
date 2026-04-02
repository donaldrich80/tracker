# Stage 1: Build React frontend + provide git binary
FROM node:20 AS frontend-builder
WORKDIR /frontend
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim
WORKDIR /app

# Copy git from node image (node:20 is Debian-based and includes git)
COPY --from=frontend-builder /usr/bin/git /usr/bin/git
COPY --from=frontend-builder /usr/lib/git-core /usr/lib/git-core
COPY --from=frontend-builder /usr/share/git-core /usr/share/git-core

# Copy pre-downloaded wheels for offline install
COPY wheelhouse/ /wheelhouse/

# Install backend dependencies from local wheels (no network needed)
COPY backend/pyproject.toml .
RUN pip install --no-cache-dir --no-index --find-links=/wheelhouse setuptools && \
    pip install --no-cache-dir --no-index --find-links=/wheelhouse --no-build-isolation -e .

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Create data directory for SQLite
RUN mkdir -p /data

ENV DB_PATH=/data/tracker.db
ENV FRONTEND_DIST=/app/frontend/dist
ENV GIT_PYTHON_REFRESH=quiet

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
