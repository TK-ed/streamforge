FROM python:3.12-slim

WORKDIR /app

COPY workers/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y ffmpeg

COPY . .

ENV PYTHONPATH=/app

CMD ["python", "main.py"]
