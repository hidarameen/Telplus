FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libavcodec-extra \
    libavformat-dev \
    libswscale-dev \
    libavutil-dev \
    libavdevice-dev \
    libavfilter-dev \
    libpostproc-dev \
    libx264-dev \
    libxvidcore-dev \
    libv4l-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libglib2.0-0 \
    libgl1 \
    libgtk-3-0t64 \
    wget \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /tmp/bot_temp /app/logs /app/data /app/watermark_images \
 && chmod +x install_dependencies.sh start.sh || true

RUN ffmpeg -version && ffprobe -version

EXPOSE 8000

CMD ["python", "main.py"]
