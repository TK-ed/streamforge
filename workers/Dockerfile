FROM python:3.12-slim

WORKDIR /app

COPY workers/requirements.txt .

RUN apt-get update && apt-get install -y ca-certificates curl ffmpeg --no-install-recommends && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

CMD ["python", "main.py"]
