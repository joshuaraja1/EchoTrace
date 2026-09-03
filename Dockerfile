FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ECHOTRACE_DATA_DIR=/data

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN addgroup --system echotrace && adduser --system --ingroup echotrace echotrace \
    && mkdir -p /data && chown echotrace:echotrace /data
USER echotrace

EXPOSE 8000
CMD ["echotrace-api", "--host", "0.0.0.0", "--port", "8000"]
