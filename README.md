# Space Tracker

Een zelfgehoste webportal die de ISS en het Chinese ruimtestation Tiangong live op een wereldkaart volgt, met ruimteweer, bemanning en NASA open data. Draait als lichtgewicht Python service, geen frameworks, geen build stap.

## Functionaliteiten

- **Live kaart** (`iss.html`) — live ISS- en Tiangong-positie op een wereldkaart, via server-side SGP4-baanberekening
- **NASA Open Data** (`nasa.html`) — APOD, ruimteweer-notificaties, near-earth objects, EPIC aardfoto's, Mars-roverfoto's
- **Artemis** (`artemis.html`) — missietijdlijn + live NASA Artemis blog RSS-feed
- **Ruimteweer** (`ruimteweer.html`) — uitleg ruimteweer-events/codes
- **Astronauten in de ruimte** — wie er momenteel in een baan om de aarde zit
- **PWA** — installeerbaar als home screen app op iPhone; full screen, dark statusbalk
- **Mobielvriendelijk** — responsieve layout

## Architectuur

```
server.py   :8082  ← serveert de portal
├── GET /api/iss           → live ISS-positie (server-side SGP4)
├── GET /api/tiangong      → live Tiangong-positie (server-side SGP4)
├── GET /api/astros        → astronauten momenteel in de ruimte
└── GET /api/nasa/*        → NASA Open Data (APOD, DONKI, NEO, EPIC, Mars, EONET), gecached
└── GET /api/artemis/feed  → NASA Artemis blog RSS-feed, gecached
```

TLE-data (baangegevens) wordt opgehaald en 6 uur gecached uit meerdere bronnen (ivanstanojevic.me, CelesTrak).

## Vereisten

- Python 3.7+
- `sgp4` package: `pip3 install sgp4`
- Optioneel: een [NASA API key](https://api.nasa.gov/) (`NASA_API_KEY` env var) — zonder key wordt de gedeelde `DEMO_KEY` gebruikt, met een lager rate limit

## Installatie

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

### Deployment

`deploy.sh` synct dit project via `rsync` over SSH naar de Pi en herstart de service:

```bash
./deploy.sh
```

Pas `REMOTE`, `REMOTE_DIR` en `SERVICE` bovenaan het script aan naar je eigen situatie.

## Configuratie

Bovenaan `server.py`:

| Variabele | Standaard | Beschrijving |
|---|---|---|
| `PORT` | `8082` | Poort waarop de portal luistert |
| `NASA_API_KEY` (env var) | `DEMO_KEY` | NASA API key |

## Bestandsstructuur

```
space-tracker/
├── server.py               Python HTTP server + SGP4-baanberekening + NASA/ISS proxy
├── space-tracker.service   systemd unit bestand
├── deploy.sh                rsync-over-SSH deploy naar de Pi
├── static/
│   ├── index.html           Landingspagina
│   ├── iss.html              Live ISS/Tiangong-kaart
│   ├── nasa.html             NASA Open Data
│   ├── artemis.html          Artemis missietijdlijn + RSS-feed
│   ├── ruimteweer.html       Uitleg ruimteweer-codes
│   ├── manifest.json         PWA manifest (home screen app)
│   ├── icon-180.png          Apple touch icon
│   ├── icon-192.png          PWA icon
│   └── icon-512.png          PWA icon (groot)
└── nasa_cache/                NASA API response cache (automatisch aangemaakt, niet in repo)
```

## Gebruik

Open `http://<host>:8082` in een browser voor de landingspagina, of direct `/iss.html` voor de kaart.

### Installeren als iPhone app (PWA)

1. Open de portal in **Safari** op je iPhone
2. Tik op het **deelicoon** (↑) → **"Zet op beginscherm"**
3. Bevestig — de portal verschijnt als volledig scherm app op je beginscherm
