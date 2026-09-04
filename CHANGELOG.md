# Changelog

## 2026-09-04
- Fixed a bug where a NASA API rate-limit error (still valid JSON) was cached as if it were real data, so `/api/nasa/*` kept serving the error for the full cache TTL (up to 6 hours) instead of recovering once the rate limit reset. `_nasa_fetch()` now recognizes `{"error": ...}` responses, refuses to cache them, and falls back to the last known-good response instead.
- Added an MIT `LICENSE`, now that the repository is public.
- Merged the landing page into the map page — `iss.html` is now `index.html` and serves as the home page; the separate landing page was removed. Matches the same change made in `adsb-portal`. Other pages now link back with `<a href="/">` instead of `/iss.html`.
- Removed remaining Dutch text and "Bakkel" branding from `static/manifest.json` (PWA name/description), missed in the earlier translation pass.
- Made the repository public on GitHub.
- Rewrote git history to permanently remove `CLAUDE.md` from all past commits (it had only been untracked going forward, not purged from history) — required before making the repo public, since it contained a real Pi IP address, SSH port and hostname. History was force-pushed; commit hashes changed as a result.
- Added a footer link to the GitHub repo on all pages.
- Added an alternative Docker deployment: `Dockerfile` + `docker-compose.yml` plus a `.dockerignore` that excludes the private infra notes. `server.py` now reads `PORT` from an environment variable (falling back to the existing default `8082`), so the same script runs unchanged on bare metal or in a container. This does not replace the existing systemd/rsync deployment — it's offered as an option for self-hosters who prefer Docker.
- Translated the entire project (UI, README, changelog) to English and removed personal branding ("Bakkel's Space Tracker" → "Space Tracker"), in preparation for making the repository public on GitHub.
- `CLAUDE.md` (personal infrastructure notes: IP, SSH port, hostname) is no longer tracked in git and excluded from `deploy.sh` and the Docker build.
- Project split off from the combined "FR24 Portal + Space Tracker" setup (previously the `Flightradar24` repo). This project now contains only the space section (ISS/Tiangong map, NASA Open Data, Artemis, space weather) — the ADS-B aircraft portal moved to the separate `adsb-portal` project.
- Server moved to its own port `8082` (was shared with the aircraft portal on `8081`).
- Deployment switched to a local `deploy.sh` script (`rsync` over SSH via the `flight2` alias) that restarts the service.
- Cross-link to the ADS-B portal removed from `ruimteweer.html`.
