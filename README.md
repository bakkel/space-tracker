# Space Tracker

A self-hosted web portal that tracks the ISS and the Chinese Tiangong space station live on a world map, with space weather, crew and NASA open data. Runs as a lightweight Python service, no frameworks, no build step.

## Features

- **Live map** (`index.html`) — home page: live ISS and Tiangong position on a world map, via server-side SGP4 orbit calculation
- **NASA Open Data** (`nasa.html`) — APOD, space weather notifications, near-earth objects, EPIC Earth photos, Mars rover photos
- **Artemis** (`artemis.html`) — mission timeline + live NASA Artemis blog RSS feed
- **Space Weather** (`ruimteweer.html`) — explanation of space weather events/codes
- **People in space** — who's currently in orbit around Earth
- **PWA** — installable as a home screen app on iPhone; full screen, dark status bar
- **Mobile-friendly** — responsive layout

## Architecture

```
server.py   :8082  ← serves the portal
├── GET /api/iss           → live ISS position (server-side SGP4)
├── GET /api/tiangong      → live Tiangong position (server-side SGP4)
├── GET /api/astros        → people currently in space
└── GET /api/nasa/*        → NASA Open Data (APOD, DONKI, NEO, EPIC, Mars, EONET), cached
└── GET /api/artemis/feed  → NASA Artemis blog RSS feed, cached
```

TLE data (orbital elements) is fetched and cached for 6 hours from multiple sources (ivanstanojevic.me, CelesTrak).

## Requirements

- Python 3.7+
- `sgp4` package: `pip3 install sgp4`
- Optional: a [NASA API key](https://api.nasa.gov/) (`NASA_API_KEY` env var) — without a key the shared `DEMO_KEY` is used, with a lower rate limit

## Installation

```bash
git clone <repo-url> space-tracker
cd space-tracker
```

### Systemd service

```bash
sudo cp space-tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable space-tracker
sudo systemctl start space-tracker
```

Edit the `User` and `WorkingDirectory` in `space-tracker.service` to match your own system user and install path first.

### Deployment

`deploy.sh` syncs this project to the Pi via `rsync` over SSH and restarts the service:

```bash
./deploy.sh
```

Adjust `REMOTE`, `REMOTE_DIR` and `SERVICE` at the top of the script to match your own setup.

### Docker (alternative)

Instead of the systemd service, you can run the portal in a container:

```bash
docker compose up -d --build
```

The NASA API response cache is persisted to `./nasa_cache` via a bind mount, so cached data survives container restarts.

## Configuration

At the top of `server.py` (or as environment variables, e.g. in `docker-compose.yml`):

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8082` | Port the portal listens on |
| `NASA_API_KEY` (env var) | `DEMO_KEY` | NASA API key |

## Project structure

```
space-tracker/
├── server.py               Python HTTP server + SGP4 orbit calculation + NASA/ISS proxy
├── space-tracker.service   systemd unit file
├── deploy.sh                rsync-over-SSH deploy to the Pi
├── Dockerfile               Container image for the portal (alternative to systemd)
├── docker-compose.yml       Runs the portal via Docker
├── static/
│   ├── index.html           Live ISS/Tiangong map — also the home page
│   ├── nasa.html             NASA Open Data
│   ├── artemis.html          Artemis mission timeline + RSS feed
│   ├── ruimteweer.html       Space weather code explanations
│   ├── manifest.json         PWA manifest (home screen app)
│   ├── icon-180.png          Apple touch icon
│   ├── icon-192.png          PWA icon
│   └── icon-512.png          PWA icon (large)
└── nasa_cache/                NASA API response cache (created automatically, not in repo)
```

## Usage

Open `http://<host>:8082` in a browser for the live map.

### Installing as an iPhone app (PWA)

1. Open the portal in **Safari** on your iPhone
2. Tap the **share icon** (↑) → **"Add to Home Screen"**
3. Confirm — the portal now appears as a full-screen app on your home screen

## License

MIT — see [LICENSE](LICENSE).
