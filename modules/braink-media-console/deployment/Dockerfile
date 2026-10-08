FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg python3 python3-venv ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/braink-media
COPY linux/requirements.txt ./linux/requirements.txt
RUN python3 -m venv /opt/media-python && /opt/media-python/bin/pip install --no-cache-dir -r linux/requirements.txt
COPY linux ./linux
RUN useradd --system --uid 10001 --create-home braink && mkdir -p /var/lib/braink-media && chown braink /var/lib/braink-media
ENV BRAINK_MEDIA_PYTHON=/opt/media-python/bin/python BRAINK_MEDIA_WORKER_STATE=/var/lib/braink-media BRAINK_MEDIA_WORKER_CONFIG=/run/secrets/media-agent.json
USER braink
CMD ["node","linux/media-host-worker.mjs"]
