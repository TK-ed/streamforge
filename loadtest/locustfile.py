"""Locust stress test for the StreamForge API gateway.

Each simulated user registers + logs in once (on_start), then exercises the
read-heavy endpoints plus occasional uploads and stream-URL lookups, with
weights chosen to approximate real traffic.

Run:
    locust -f locustfile.py --host http://api.streamforge.local
    locust -f locustfile.py --host http://localhost:8000 --headless -u 100 -r 10 -t 3m

Tunables (env):
    LOADTEST_PASSWORD       password used for the throwaway accounts
    LOADTEST_UPLOAD_BYTES   size of the dummy upload body (default 64 KiB)
"""

import io
import os
import uuid

from locust import HttpUser, between, task

PASSWORD = os.getenv("LOADTEST_PASSWORD", "password123")

# Dummy upload body. The /videos/upload endpoint stores it verbatim, so this is
# enough to load-test the gateway (object store + DB + publish). The worker will
# reject it as non-video — that's expected and irrelevant to API throughput.
UPLOAD_SIZE = int(os.getenv("LOADTEST_UPLOAD_BYTES", str(64 * 1024)))
UPLOAD_PAYLOAD = b"\x00" * UPLOAD_SIZE


class StreamForgeUser(HttpUser):
    # Think time between tasks.
    wait_time = between(1, 3)

    def on_start(self):
        """Create a unique throwaway account and obtain a bearer token."""
        self.token = None
        self.video_ids = []
        self.email = f"loadtest_{uuid.uuid4().hex}@example.com"

        # Register (idempotent enough for load: each email is unique).
        self.client.post(
            "/auth/register",
            json={"email": self.email, "password": PASSWORD},
            name="POST /auth/register",
        )

        with self.client.post(
            "/auth/login",
            json={"email": self.email, "password": PASSWORD},
            name="POST /auth/login",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200 and resp.json().get("access_token"):
                self.token = resp.json()["access_token"]
                self.client.headers.update({"Authorization": f"Bearer {self.token}"})
                resp.success()
            else:
                resp.failure(f"login failed: {resp.status_code} {resp.text[:120]}")

    # ---- read-heavy traffic -------------------------------------------------

    @task(8)
    def health(self):
        self.client.get("/", name="GET /")

    @task(20)
    def me(self):
        self.client.get("/users/me", name="GET /users/me")

    @task(15)
    def list_videos(self):
        self.client.get("/videos/videos", name="GET /videos/videos")

    # ---- write / heavier paths ---------------------------------------------

    @task(3)
    def upload(self):
        filename = f"load_{uuid.uuid4().hex}.mp4"
        files = {"file": (filename, io.BytesIO(UPLOAD_PAYLOAD), "video/mp4")}
        with self.client.post(
            "/videos/upload",
            files=files,
            name="POST /videos/upload",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                vid = resp.json().get("id")
                if vid:
                    # keep a bounded history for the stream task
                    self.video_ids.append(vid)
                    self.video_ids = self.video_ids[-20:]
                resp.success()
            elif resp.status_code == 429:
                # slowapi rate-limit (5/min/IP) — expected under load, not a failure.
                resp.success()
            else:
                resp.failure(f"upload failed: {resp.status_code} {resp.text[:120]}")

    @task(10)
    def stream(self):
        if not self.video_ids:
            return
        vid = self.video_ids[-1]
        with self.client.get(
            f"/videos/{vid}/stream?quality=360",
            name="GET /videos/[id]/stream",
            catch_response=True,
        ) as resp:
            # 404 = rendition not produced yet (dummy upload); acceptable here.
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"stream failed: {resp.status_code} {resp.text[:120]}")
