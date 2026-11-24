# Deploying Maternacare AI

The app is a Flask + SQLite server. It **cannot** run on GitHub Pages (static only).
Use one of the options below. All read `PORT` from the environment; set
`DATABASE_PATH` to a persistent volume path if you want data to survive redeploys.

> ⚠️ Before exposing this publicly, read the clinical/legal notes in README.md.
> This is a prototype for education and navigation, not a regulated medical device.

---

## Option 1 — Render.com (easiest, free tier)

1. Sign up at https://render.com (GitHub login works).
2. Dashboard → **New** → **Blueprint** → connect `drvictorbiswas-cmd/maternacare-ai`.
3. Render detects `render.yaml` → **Apply**.
4. Wait for the build. You'll get a URL like `https://maternacare-ai.onrender.com`.

Free-tier instances sleep after inactivity; the first request after sleep takes a few seconds.

**Persistence:** add a Render Disk in the dashboard and set env var
`DATABASE_PATH=/data/maternacare.db` with the disk mounted at `/data`.

---

## Option 2 — Fly.io

```bash
# Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
fly auth signup            # or: fly auth login
cd maternacare-ai
fly launch --no-deploy     # uses fly.toml; pick a unique app name if prompted

# Persistent SQLite volume (optional but recommended):
fly volumes create maternacare_data --region sin --size 1

# Uncomment the [[mounts]] block in fly.toml, then set the DB path:
fly secrets set DATABASE_PATH=/app/data/maternacare.db

fly deploy
fly open
```

---

## Option 3 — Railway

1. Sign up at https://railway.app with GitHub.
2. **New Project** → **Deploy from GitHub repo** → select `maternacare-ai`.
3. Railway detects the `Dockerfile` automatically.
4. Settings → **Networking** → generate a public domain.
5. For persistence add a Volume and set `DATABASE_PATH` to a path inside it.

---

## Option 4 — Any VPS / local server (Docker)

```bash
git clone https://github.com/drvictorbiswas-cmd/maternacare-ai.git
cd maternacare-ai
docker build -t maternacare-ai .
docker run -d -p 10000:10000 \
  -v "$(pwd)/data:/app/data" \
  -e DATABASE_PATH=/app/data/maternacare.db \
  maternacare-ai
```

Then put a reverse proxy (nginx/Caddy) with HTTPS in front of port 10000.

---

## Option 5 — Without Docker

```bash
pip install -r requirements.txt
export PORT=10000
export DATABASE_PATH=./data/maternacare.db
gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 app:app
```

---

## Verify a deployment

```bash
curl https://<your-url>/api/state
```
Expected JSON with `"profile": null` and `"traditions_count": 12`.

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `5055` | HTTP port (set by hosts) |
| `DATABASE_PATH` | `./data/maternacare.db` | SQLite file location |
| `FLASK_DEBUG` | `1` | Set to `0` in production (Dockerfile uses gunicorn, so debug is off there) |
