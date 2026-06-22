# StreamForge

A horizontally-scalable **video streaming platform** that ingests uploaded videos, transcodes them into an adaptive **HLS** bitrate ladder with FFmpeg, and serves them back for streaming — built as a set of decoupled services around an async job pipeline, with full observability baked in.

---

## Table of Contents
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [How It Works (Request → Stream Flow)](#how-it-works-request--stream-flow)
- [Services & Ports](#services--ports)
- [API Endpoints](#api-endpoints)
- [Data Model](#data-model)
- [Rate Limiting](#rate-limiting)
- [Scaling & Autoscaling](#scaling--autoscaling)
- [GPU / Hardware Encoding](#gpu--hardware-encoding)
- [Observability](#observability)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Kubernetes](#kubernetes)
- [Load Testing](#load-testing)
- [CI](#ci)

---

## Architecture

StreamForge splits responsibilities across two runtime tiers connected by a message queue and shared object storage:

- An **API Gateway** (synchronous, user-facing) that handles auth, uploads, and stream URLs.
- A pool of **Workers** (asynchronous, CPU-bound) that do the heavy FFmpeg transcoding off the request path.

```
                         ┌─────────────┐
        register/login   │             │   JWT
   ───────────────────►  │ API Gateway │ ◄──────── clients
        upload / stream   │  (FastAPI)  │
                         └──┬───┬───┬───┘
                store input │   │   │ publish "video.uploaded"
                            ▼   │   ▼
                     ┌────────┐ │ ┌──────────┐
                     │ MinIO  │ │ │ RabbitMQ │  (durable queue + DLQ/retry)
                     │ (S3)   │ │ └────┬─────┘
                     └───▲────┘ │      │ consume
                         │      │      ▼
       upload HLS        │  ┌───┴──────────────┐
       renditions  ──────┘  │     Worker(s)     │
                            │  download → ffprobe│
                            │  → thumbnail        │
                            │  → adaptive HLS     │ (FFmpeg)
                            │  → upload renditions│
                            └─────────┬───────────┘
                                      │ status + metadata
                                      ▼
                                ┌──────────┐
                                │ Postgres │  (users, videos, renditions)
                                └──────────┘

   Observability (all services): OpenTelemetry SDK ──► OTel Collector
            ├── traces ──► Jaeger
            ├── logs   ──► Loki
            └── metrics ─► Prometheus ──► Grafana (dashboards)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **API framework** | FastAPI + Uvicorn |
| **Auth** | JWT (`python-jose`), password hashing with `passlib` + `bcrypt` |
| **Rate limiting** | Custom **Redis** sliding-window limiter (atomic Lua, `redis.asyncio`) |
| **Database** | PostgreSQL 16, SQLAlchemy ORM, Alembic migrations |
| **Object storage** | MinIO (S3-compatible) — raw uploads + HLS output |
| **Message broker** | RabbitMQ 3 (durable queues, dead-letter / retry) |
| **Transcoding** | FFmpeg + ffprobe — adaptive HLS ladder, CPU (`libx264`) by default, GPU (NVENC) selectable |
| **Workers** | Python consumers via `pika` |
| **Tracing** | OpenTelemetry → OTel Collector → **Jaeger** |
| **Logging** | OpenTelemetry / Loki |
| **Metrics** | `prometheus_client` → **Prometheus** → **Grafana** |
| **Containerization** | Docker, Docker Compose |
| **Orchestration** | Kubernetes (kind / minikube manifests under `k8s/`) |
| **Load testing** | Locust |
| **CI** | GitHub Actions (flake8, black, isort, compile + docker build checks) |

---

## How It Works (Request → Stream Flow)

1. **Auth** — A user registers (`POST /auth/register`) and logs in (`POST /auth/login`), receiving a JWT bearer token.
2. **Upload** — With the token, the user uploads a video (`POST /videos/upload`). The gateway:
   - streams the file into **MinIO** at `uploads/{video_id}/input.mp4`,
   - inserts a `videos` row with status `pending`,
   - publishes a `video.uploaded` message onto the RabbitMQ **video queue**.
3. **Async processing** — A **Worker** consumes the message and runs the pipeline:
   - downloads the source from MinIO,
   - probes it with `ffprobe` (detects audio + source height),
   - generates a **thumbnail**,
   - transcodes an **adaptive HLS** ladder — `360p / 720p / 1080p`, **downscale-only** (never upscales beyond the source), aspect-ratio preserving, using the encoder selected by the `ENCODER` env var (CPU `libx264` by default),
   - uploads the `.m3u8` playlists + segments back to MinIO under `hls/...`,
   - marks the video `completed` (or `failed` after retries are exhausted).
   - **Resilience:** failures are retried up to `MAX_RETRIES` by re-publishing the message; exhausted messages flip the video to `failed`.
4. **Stream** — The client requests `GET /videos/{video_id}/stream?quality=720`, and the gateway returns the URL of the matching HLS playlist for the player to consume.

Video lifecycle states: `pending → processing → completed` (or `failed`).

---

## Services & Ports

| Service | Port(s) | Purpose |
|---|---|---|
| API Gateway | `8000` | REST API |
| Worker | `8001` | Prometheus metrics endpoint |
| PostgreSQL | `5432` | Relational data |
| Redis | `6379` | Rate-limit counters |
| RabbitMQ | `5672`, `15672` | Broker + management UI |
| MinIO | `9000`, `9001` | S3 API + console |
| Prometheus | `9090` | Metrics scraping |
| Grafana | `3000` | Dashboards |
| OTel Collector | `4317`, `4318` | OTLP gRPC / HTTP ingest |
| Jaeger | `16686` | Trace UI |
| Loki | `3100` | Log aggregation |

---

## API Endpoints

| Method | Path | Auth | Rate limit | Description |
|---|---|---|---|---|
| `POST` | `/auth/register` | — | 5/min per IP | Create an account |
| `POST` | `/auth/login` | — | 10/min per IP | Get a JWT |
| `GET` | `/users/me` | ✅ | — | Current user |
| `POST` | `/videos/upload` | ✅ | 5/min per user | Upload a video, enqueue processing |
| `GET` | `/videos/videos` | ✅ | — | List the caller's videos |
| `GET` | `/videos/{video_id}/stream?quality=` | ✅ | — | Get an HLS streaming URL for a rendition |
| `GET` | `/` | — | — | Health check |
| `GET` | `/metrics` | — | — | Prometheus metrics |

---

## Data Model

- **`users`** — `id`, `email` (unique), `password_hash`, timestamps.
- **`videos`** — `id` (UUID), `user_id` → users, `filename`, `object_name` (unique MinIO key), `content_type`, `size`, `status`, timestamps.
- **`video_renditions`** — per-quality HLS outputs for a video.

Schema is managed with **Alembic** (`alembic/versions/`).

---

## Rate Limiting

Rate limiting is a **custom Redis-backed sliding-window-log** limiter (in `services/api_gateway/app/core/rate_limit.py`), not an off-the-shelf middleware — chosen so limits hold consistently across **many API replicas**.

- The whole check-and-increment runs as a **single atomic Lua script** (a Redis sorted set keyed by request timestamps), so concurrent requests on different replicas can't overshoot the limit.
- Keys are **per-route + per-identity**: authenticated routes limit **per user** (from the verified JWT `sub`); pre-auth routes limit **per IP** (`X-Forwarded-For`, trusting the ingress).
- The window time is read from Redis (`TIME`), so replica clock skew doesn't matter.
- **Fail-open:** if Redis is unavailable, requests are allowed (logged) so a cache blip can't take down auth. Set `REDIS_URL` to enable it; leave it unset to disable.
- On limit, returns `429` with `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining` headers.

---

## Scaling & Autoscaling

The two runtime tiers scale independently and on different signals, because they have different bottlenecks:

- **API gateway → CPU-based HPA** (`k8s/base/api/hpa.yml`). Stateless, so it's safe to scale on CPU. `minReplicas: 2` is the HA floor (one pod/node can fail and the service stays up); it scales toward `maxReplicas: 10` at 70% average CPU. The Deployment intentionally omits a fixed `replicas` so it doesn't fight the HPA.
- **Workers → KEDA on queue depth** (`k8s/base/worker/scaledobject.yml`). Transcoding is bursty and queue-driven, so workers scale on **RabbitMQ `video.processing` queue length** (~1 worker per 5 queued messages), not CPU — capacity is added the moment a backlog forms, and can scale to zero when idle.

Both require resource **requests** to be declared on the pods (done in the deployments), and:
- the API HPA needs **metrics-server** installed in the cluster;
- the worker scaler needs **KEDA** installed plus a `rabbitmq-conn` secret for the queue connection.

> Stateful components (Postgres, RabbitMQ, MinIO) are **not** autoscaled by pod count — scaling those requires clustering/replication, not more replicas.

---

## GPU / Hardware Encoding

Transcoding defaults to **CPU** (`libx264`) but the encoder is **env-selectable**, so the same code can run on an NVIDIA GPU (NVENC) where available:

| Env var | Default | Example (GPU) |
|---|---|---|
| `ENCODER` | `libx264` | `h264_nvenc` |
| `ENCODER_PRESET` | encoder-specific (`superfast` for x264, `p4` for NVENC) | `p4` |

**Setting `ENCODER=h264_nvenc` alone is not enough** — GPU encoding additionally requires:
1. A worker image whose **FFmpeg is built with NVENC support** (the default `python:3.12-slim` image is not).
2. **NVIDIA drivers + Container Toolkit** on the host (Docker), or the **NVIDIA device plugin** and a `nvidia.com/gpu: 1` resource request (Kubernetes).
3. The GPU actually **exposed** to the worker container.

Until that infrastructure is in place, leave `ENCODER` unset (CPU). On a CPU-only host, forcing `h264_nvenc` will make FFmpeg fail at runtime.

---

## Observability

Every service emits **traces, logs, and metrics** through the OpenTelemetry SDK to a central **OTel Collector**, which fans out to:

- **Jaeger** — distributed traces (`http://localhost:16686`)
- **Loki** — structured logs
- **Prometheus** — metrics (worker exposes processing time, failure counts, etc.)
- **Grafana** — dashboards over Prometheus + Loki (`http://localhost:3000`)

---

## Getting Started

### Prerequisites
- Docker + Docker Compose
- An `.env` for the API gateway at `services/api_gateway/.env` (and root `.env` for shared values)

### Run the full stack
```bash
docker compose up -d --build
```

This starts the API, worker, Postgres, Redis, RabbitMQ, MinIO, and the full observability stack. The `migrate` service applies Alembic migrations on startup.

### Useful URLs
- API docs (Swagger): http://localhost:8000/docs
- RabbitMQ management: http://localhost:15672
- MinIO console: http://localhost:9001
- Grafana: http://localhost:3000
- Jaeger: http://localhost:16686

### Tear down
```bash
docker compose down
```

---

## Project Structure

```
.
├── services/api_gateway/      # FastAPI app
│   └── app/
│       ├── api/               # auth, users, videos routers
│       ├── core/              # security (JWT), dependencies, rate_limit, observability
│       ├── services/          # minio, rabbitmq, auth services
│       ├── config.py          # pydantic-settings
│       └── main.py            # app entrypoint + lifespan
├── workers/                   # async transcoding consumers
│   ├── consumer.py            # RabbitMQ callback + retry logic
│   ├── processor.py           # download → thumbnail → HLS → upload pipeline
│   └── services/              # transcoder (FFmpeg), thumbnail, minio, metrics, publisher
├── shared/                    # SQLAlchemy models + schemas shared across services
├── alembic/                   # database migrations
├── k8s/                       # Kubernetes manifests (base + monitoring)
├── loadtest/                  # Locust load tests
├── grafana/ prometheus.yml otel-collector-config.yaml
└── docker-compose.yml
```

---

## Kubernetes

Manifests live under `k8s/`:
- `k8s/base/` — Deployments, Services, PVCs, and Ingress for the API, worker, Postgres, RabbitMQ, MinIO, and the migrate Job.
- `k8s/monitoring/` — Prometheus, Grafana, Jaeger, Loki, and the OTel Collector.

Local clusters can be brought up with **kind** (`kind-config.yaml`) or **minikube**.

---

## Load Testing

A **Locust** suite under `loadtest/` (with its own `docker-compose.yml` and `k8s/` master/worker manifests) drives synthetic upload/stream traffic to validate scaling and rate-limit behavior. Each virtual user registers a throwaway account, logs in once, then loops the read endpoints plus occasional uploads/stream lookups with realistic weights.

### Results

Run headless against the kind ingress (`http://api.streamforge.local`), Locust 2.44, 2-minute steady state.

**100 concurrent users** — ramp 10/s, ~40 req/s sustained:

| Metric | Value |
|---|---|
| Concurrent users | 100 |
| Total requests | ~4,800 |
| Throughput | ~40.5 req/s |
| Failures | **0 (0.00%)** |
| Latency — median | 8 ms |
| Latency — p95 | 910 ms |
| Latency — p99 | 2.0 s |
| Latency — max | 3.5 s |

Per-endpoint (avg / median / p95):

| Endpoint | reqs | avg | median | p95 |
|---|---|---|---|---|
| `GET /` | 788 | 14 ms | 5 ms | 64 ms |
| `GET /users/me` | 1,991 | 46 ms | 8 ms | 92 ms |
| `GET /videos/videos` | 1,508 | 42 ms | 9 ms | 89 ms |
| `GET /videos/{id}/stream` | 71 | 29 ms | 14 ms | 79 ms |
| `POST /videos/upload` | 284 | 58 ms | 13 ms | 120 ms |
| `POST /auth/login` | 100 | 1.45 s | 1.40 s | 2.1 s |
| `POST /auth/register` | 100 | 1.66 s | 1.50 s | 2.9 s |

Read paths are single-digit-millisecond; the tail latency is entirely the **bcrypt** password hashing on `/auth/register` and `/auth/login` (~1.5 s each), which is intentional work, not a server stall.

**500 concurrent users** — ramp 25/s: the auth path **saturates**. ~92% of requests fail with `500 / 502 / 504` and registration times out (60 s cap), because bcrypt hashing serializes against a single API replica + Postgres in this local kind setup. This is the bottleneck to scale next (more API replicas via the HPA, and/or offloading hashing) — not a passing result.

> Numbers above are from a local single-node **kind** cluster, so they reflect relative behavior and the auth bottleneck rather than production capacity. Re-run with the API HPA scaled out (and distributed Locust workers) to push past the auth ceiling. CSV reports land in `loadtest/results/`.

### Platform at a glance

| Aspect | Value |
|---|---|
| Cleanly sustained concurrency | 100 users, 0 failures |
| API replicas | 2–10 (CPU-based HPA) |
| Worker replicas | KEDA, scales on RabbitMQ queue depth (to zero when idle) |
| Queue system | RabbitMQ (durable + DLQ/retry) |
| Video format | Adaptive HLS (360p/720p/1080p) |
| Rate limiting | Redis sliding-window (atomic Lua) |
| Autoscaling | Kubernetes HPA (API) + KEDA (workers) |
| Monitoring | Prometheus + Grafana (+ Jaeger, Loki) |

---

## CI

GitHub Actions (`.github/workflows/`):
- **Backend CI** — `flake8`, `black --check`, `isort --check`, and `compileall` across `services/`, `shared/`, `workers/`.
- **Docker Build Check** — builds the API and worker images and validates `docker-compose config`.
```
