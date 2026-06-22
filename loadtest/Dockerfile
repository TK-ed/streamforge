FROM python:3.12-slim

WORKDIR /app

COPY loadtest/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY loadtest/locustfile.py .

EXPOSE 8089

# Defaults to the web UI; compose/k8s override with --master/--worker/--headless.
ENTRYPOINT ["locust", "-f", "locustfile.py"]
