FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg is the only system package pip cannot provide: yt-dlp needs it to
# extract audio, whisper needs it to decode the file.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install torch first from the CPU-only index; the default wheel bundles CUDA
# and is several GB larger. pip then sees the pinned version as satisfied and
# skips it when installing the rest of the requirements.
COPY requirements.txt .
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.13.0 \
    && pip install -r requirements.txt

# The whisper model is not baked into the image; compose mounts a volume on
# /root/.cache/whisper so it is downloaded once on the first request and
# then survives container rebuilds.
COPY . .

# Directories that compose mounts as volumes.
RUN mkdir -p /app/data /app/transcribed_data

# Apply migrations, then hand PID 1 over to gunicorn via exec so it receives
# stop signals directly. One worker: every worker loads its own whisper model.
CMD python manage.py migrate --noinput \
    && exec gunicorn core.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 1 \
        --threads 2 \
        --timeout 600
