# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY .env* ./

# Create necessary directories
RUN mkdir -p ./exports ./chat_history

# Set environment variables
ENV PYTHONPATH=/app/app
ENV PORT=8080
ENV HOST=0.0.0.0

# Create non-root user for security
RUN useradd -m -u 1000 gradio && chown -R gradio:gradio /app
USER gradio

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Run the application
CMD ["python", "-m", "app.main"] 