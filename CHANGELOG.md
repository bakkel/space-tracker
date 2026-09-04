# Changelog

## 2026-09-04
- Added a footer link to the GitHub repo on all pages.
- Added an alternative Docker deployment: `Dockerfile` + `docker-compose.yml` plus a `.dockerignore` that excludes the private infra notes. `server.py` now reads `PORT` from an environment variable (falling back to the existing default `8082`), so the same script runs unchanged on bare metal or in a container. This does not replace the existing systemd/rsync deployment — it's offered as an option for self-hosters who prefer Docker.
- Translated the entire project (UI, README, changelog) to English and removed personal branding ("Bakkel's Space Tracker" → "Space Tracker"), in preparation for making the repository public on GitHub.
- `CLAUDE.md` (personal infrastructure notes: IP, SSH port, hostname) is no longer tracked in git and excluded from `deploy.sh` and the Docker build.
- Project split off from the combined "FR24 Portal + Space Tracker" setup (previously the `Flightradar24` repo). This project now contains only the space section (ISS/Tiangong map, NASA Open Data, Artemis, space weather) — the ADS-B aircraft portal moved to the separate `adsb-portal` project.
- Server moved to its own port `8082` (was shared with the aircraft portal on `8081`).
- Deployment switched to a local `deploy.sh` script (`rsync` over SSH via the `flight2` alias) that restarts the service.
- Cross-link to the ADS-B portal removed from `ruimteweer.html`.
