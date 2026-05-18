FROM python:3.11-slim

# Set working directory to the backend module root inside /app/backend
WORKDIR /app/backend

# Copy and install python dependencies first for efficient caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . .

# Expose backend port
EXPOSE 8000

# Set Python search path to /app so that absolute backend.xxx imports resolve perfectly
ENV PYTHONPATH=/app

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
