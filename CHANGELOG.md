# Changelog

## 2026-09-04
- Project losgekoppeld van de gecombineerde "FR24 Portal + Space Tracker" opzet (voorheen `Flightradar24`-repo). Dit project bevat voortaan alleen het ruimtevaart-gedeelte (ISS/Tiangong-kaart, NASA Open Data, Artemis, ruimteweer) — de ADS-B vliegtuigportal is verhuisd naar het aparte `adsb-portal`-project.
- Server verplaatst naar eigen poort `8082` (was gedeeld met de vliegtuigportal op `8081`).
- Deployment omgezet naar een lokaal `deploy.sh`-script (`rsync` over SSH via de `flight2`-alias) dat de service herstart.
- Kruislink naar de ADS-B portal verwijderd uit `ruimteweer.html`.
