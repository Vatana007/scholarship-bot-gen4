FROM python:3.11-slim

# Install Chromium and Khmer Unicode fonts for rendering beautiful PDF reports
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-khmeros \
    fonts-liberation \
    fontconfig \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download Kantumruy Pro and Moul Google Fonts for Khmer PDF rendering
RUN mkdir -p /usr/share/fonts/truetype/khmer && \
    curl -sSL -o /usr/share/fonts/truetype/khmer/KantumruyPro.ttf "https://github.com/google/fonts/raw/main/ofl/kantumruypro/KantumruyPro%5Bwght%5D.ttf" || true && \
    curl -sSL -o /usr/share/fonts/truetype/khmer/Moul.ttf "https://github.com/google/fonts/raw/main/ofl/moul/Moul-Regular.ttf" || true && \
    fc-cache -f /usr/share/fonts/truetype/khmer || true

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
