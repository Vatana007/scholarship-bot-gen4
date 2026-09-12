FROM python:3.11-slim

# Install Chromium and Khmer Unicode fonts for rendering beautiful PDF reports
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-khmeros \
    fonts-khmeros-core \
    fonts-noto-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and assets
COPY . .

# Environment settings
ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/usr/bin/chromium
ENV PORT=8080

EXPOSE 8080

CMD ["python", "-m", "src.main"]
