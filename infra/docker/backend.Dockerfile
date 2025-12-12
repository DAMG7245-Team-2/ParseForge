# Base image
FROM python:3.12-slim AS base

# Disable Python bytecode + buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user and switch to it
RUN useradd -m appuser

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y tesseract-ocr libgl1 && rm -rf /var/lib/apt/lists/*

# Install dependencies (cache-friendly)
COPY apps/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only backend source
COPY apps/backend ./backend

# Set app user permissions
RUN chown -R appuser:appuser /app
USER appuser

# Expose port & run server
EXPOSE ${PORT}
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]