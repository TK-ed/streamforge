# StreamForge load test (Locust)

Stress-tests the API gateway: auth (register/login), `GET /users/me`,
`GET /videos/videos`, `POST /videos/upload`, and `GET /videos/{id}/stream`.

Each virtual user registers a unique throwaway account, logs in once, then
loops the endpoints with realistic weights. Upload `429`s (the 5/min rate limit)
and stream `404`s (rendition not ready for the dummy upload) are counted as
expected, not failures, so the failure column reflects real errors.

See `locustfile.py` for the scenario and weights.

---

## 1) Local (simplest)

```bash
pip install -r loadtest/requirements.txt

# Interactive web UI at http://localhost:8089
locust -f loadtest/locustfile.py --host http://api.streamforge.local

# Headless: 100 users, ramp 10/s, 3 minutes, write a CSV report
locust -f loadtest/locustfile.py --host http://api.streamforge.local \
  --headless -u 100 -r 10 -t 3m --csv report
```

`--host` is your API base URL — `http://api.streamforge.local` (k8s ingress) or
`http://localhost:8000` (docker-compose).

## 2) Distributed via Docker Compose (1 master + N workers)

```bash
TARGET_HOST=http://api.streamforge.local \
  docker compose -f loadtest/docker-compose.yml up --build --scale locust-worker=4
```

Open http://localhost:8089. `extra_hosts` lets the containers resolve
`api.streamforge.local` to your host's ingress.

## 3) In-cluster on Kubernetes (targets the internal `streamforge-api` service)

```bash
# build + load the image into kind
docker build -f loadtest/Dockerfile -t streamforge-loadtest:latest .
kind load docker-image streamforge-loadtest:latest --name kind

kubectl apply -f loadtest/k8s/master.yml
kubectl apply -f loadtest/k8s/worker.yml

# scale the generators
kubectl scale deploy/locust-worker --replicas=8 -n streamforge

# open the UI
kubectl port-forward -n streamforge svc/locust-master 8089:8089
# -> http://localhost:8089
```

Running in-cluster removes ingress/host-network overhead, so it measures the
service itself rather than your laptop's network path.

### Tunables (env)

| Var | Default | Meaning |
|-----|---------|---------|
| `LOADTEST_PASSWORD` | `password123` | password for throwaway accounts |
| `LOADTEST_UPLOAD_BYTES` | `65536` | dummy upload body size in bytes |

---

## Notes / caveats

- **Rate limit:** `POST /videos/upload` is limited to 5/min **per IP** (slowapi).
  Distributed workers behind one egress IP will see many `429`s — expected, and
  treated as success. Raise the limit in `core/middleware.py` if you want to
  stress the upload path harder.
- **Dummy uploads** are not real videos, so the worker fails transcoding and the
  stream lookup returns `404`. That's fine for API throughput testing; to drive
  real transcode load, point the upload task at a real MP4 fixture instead.
- **Throwaway accounts** accumulate in Postgres. Truncate `users`/`videos`
  between big runs if you care about a clean DB.
