FROM python:3.12-slim AS base

# Set working directory inside container
WORKDIR /apps/backend

# Copy entire apps directory (backend + frontend, but only backend will run)
COPY apps/backend .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose backend port
EXPOSE 8000

# Run FastAPI backend
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]