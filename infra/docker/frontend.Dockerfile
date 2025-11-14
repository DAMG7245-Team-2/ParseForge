# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables for the application
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8501

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
# We install dependencies before copying the rest of the code to leverage Docker layer caching
COPY apps/frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
# We copy all the Python code, the Streamlit app, and the .env file (if used directly)
COPY apps/frontend/. /app

# Expose the port Streamlit runs on
EXPOSE ${PORT}

# Healthcheck (Optional but recommended for robust deployments)
# Checks if Streamlit is responding on the exposed port
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/_stcore/health || exit 1

# Command to run the Streamlit application
# We use entrypoint form for consistency
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]