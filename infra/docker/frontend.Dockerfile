FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8501

WORKDIR /app

# 2. Install Python packages and clear pip cache
COPY apps/frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

# 3. Create non-root user (using Debian commands)
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid 1001 -m -s /bin/bash appuser

# 4. Copy app code and set ownership
COPY apps/frontend/ /app
RUN chown -R appuser:appuser /app

EXPOSE ${PORT}
USER appuser

CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]