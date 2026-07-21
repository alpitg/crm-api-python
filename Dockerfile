# Use a lightweight Python runtime
FROM python:3.12-slim

# Prevent Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Ensure logs appear immediately
ENV PYTHONUNBUFFERED=1

# Create a non-root user
RUN groupadd -r app && useradd -r -g app app

# Set working directory
WORKDIR /app

# Install system dependencies (if required by your packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (Docker layer caching)
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

COPY .env .env

# Set ownership
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Expose application port
EXPOSE 8000

# Start the application
# CMD ["python", "main.py"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
