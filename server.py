#!/usr/bin/env python3
"""Space Tracker — live ISS/Tiangong position server + NASA Open Data proxy."""
import http.server
import socketserver
import urllib.request
import subprocess
import threading
import time
import json
import math
import os
from datetime import datetime, timedelta

PORT       = int(os.environ.get("PORT", 8082))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
CACHE_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nasa_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

NASA_KEY    = os.environ.get("NASA_API_KEY", "DEMO_KEY")
_nasa_cache = {}   # key → (bytes, timestamp)
_tle_cache  = {}   # norad_id → (dict, timestamp)

try:
    from sgp4.api import Satrec as _Satrec, jday as _sgp4_jday
    _HAS_SGP4 = True
except ImportError:
    _HAS_SGP4 = False
    print("[tiangong] sgp4 not installed — run: pip3 install sgp4")


def _gmst_rad(jd):
    T = (jd - 2451545.0) / 36525.0
    g = (280.46061837 + 360.98564736629 * (jd - 2451545.0)
         + 0.000387933 * T * T - T * T * T / 38710000.0)
    return math.radians(g % 360.0)


def _eci_to_lla(r, gmst):
    """ECI position (km) → (lat_deg, lon_deg, alt_km)"""
    RE, f = 6378.137, 1.0 / 298.257223563
    e2 = 2 * f - f * f
    cos_g, sin_g = math.cos(gmst), math.sin(gmst)
    x = r[0] * cos_g + r[1] * sin_g
    y = -r[0] * sin_g + r[1] * cos_g
    z = r[2]
    lon = math.atan2(y, x)
    p   = math.sqrt(x * x + y * y)
    lat = math.atan2(z, p * (1.0 - e2))
    for _ in range(5):
        N   = RE / math.sqrt(1.0 - e2 * math.sin(lat) ** 2)
        lat = math.atan2(z + e2 * N * math.sin(lat), p)
    N   = RE / math.sqrt(1.0 - e2 * math.sin(lat) ** 2)
    alt = (p / math.cos(lat) - N) if abs(lat) < 1.5533 else (z / math.sin(lat) - N * (1.0 - e2))
    return math.degrees(lat), math.degrees(lon), alt


def _fetch_tle(norad_id):
    """Fetch TLE for the given NORAD ID, cached for 6 hours. Tries three sources."""
    now = time.time()
    if norad_id in _tle_cache:
        data, ts = _tle_cache[norad_id]
        if now - ts < 21600:
            return data

    attempts = [
        # JSON API specific to NORAD ID (most reliable)
        ("json", f"https://tle.ivanstanojevic.me/api/tle/{norad_id}"),
        # CelesTrak stations file (contains ISS + Tiangong)
        ("txt",  "https://celestrak.org/SATCAT/stations.txt"),
        ("txt",  "https://www.celestrak.com/SATCAT/stations.txt"),
    ]

    for fmt, url in attempts:
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "8", "-L", url],
                capture_output=True, timeout=10
            )
            if result.returncode != 0 or not result.stdout:
                print(f"[tle] {url}: curl exit {result.returncode}")
                continue

            if fmt == "json":
                j = json.loads(result.stdout)
                if j.get("line1") and j.get("line2"):
                    data = {"line1": j["line1"], "line2": j["line2"]}
                    _tle_cache[norad_id] = (data, now)
                    print(f"[tle] NORAD {norad_id} fetched (JSON) from {url}")
                    return data
            else:
                lines = [l.strip() for l in
                         result.stdout.decode("utf-8", errors="ignore").splitlines()
                         if l.strip()]
                for i, line in enumerate(lines):
                    if line.startswith(f"1 {norad_id}") and i + 1 < len(lines):
                        data = {"line1": line, "line2": lines[i + 1]}
                        _tle_cache[norad_id] = (data, now)
                        print(f"[tle] NORAD {norad_id} fetched (TXT) from {url}")
                        return data
                print(f"[tle] NORAD {norad_id} not found in {url} ({len(lines)} lines)")
        except Exception as e:
            print(f"[tle] {url}: {e}")

    if norad_id in _tle_cache:
        return _tle_cache[norad_id][0]
    return None


def _nasa_cache_file(key):
    safe = key.replace('/', '_').replace(' ', '_')
    return os.path.join(CACHE_DIR, safe + ".json")

def _nasa_fetch(key, url, ttl=3600, max_time=10):
    import json as _json
    now = time.time()
    # 1. Memory
    if key in _nasa_cache:
        data, ts = _nasa_cache[key]
        if now - ts < ttl:
            return data
    # 2. Disk (survives server restarts)
    cf = _nasa_cache_file(key)
    disk_data = None
    if os.path.exists(cf):
        try:
            with open(cf, 'rb') as f:
                saved = _json.loads(f.read())
            disk_data = saved['d'].encode()
            _nasa_cache[key] = (disk_data, saved['ts'])
            if now - saved['ts'] < ttl:
                return disk_data
        except Exception:
            pass
    # 3. Fetch API
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", str(max_time), url],
            capture_output=True, timeout=max_time + 4
        )
        if result.returncode == 0 and result.stdout:
            try:
                parsed = _json.loads(result.stdout)
            except ValueError:
                print(f"[nasa] {key}: invalid JSON response")
            else:
                # A NASA API error (e.g. rate limit) is still valid JSON — don't
                # cache it, or it keeps getting served for the full TTL.
                if isinstance(parsed, dict) and "error" in parsed:
                    print(f"[nasa] {key}: NASA API error — {parsed['error']}")
                else:
                    _nasa_cache[key] = (result.stdout, now)
                    try:
                        with open(cf, 'w') as f:
                            _json.dump({'ts': now, 'd': result.stdout.decode('utf-8', errors='replace')}, f)
                    except Exception:
                        pass
                    return result.stdout
    except Exception as e:
        print(f"[nasa] fetch {key}: {e}")
    # Fall back to the last known-good response (memory or disk) rather than nothing
    if key in _nasa_cache:
        return _nasa_cache[key][0]
    return disk_data


def _mars_fetch():
    # NASA's api.nasa.gov/mars-photos endpoint proxies to a third-party Heroku
    # app that has gone offline, so we use JPL's own raw-images feed instead —
    # no API key needed, and it returns the latest images directly (no need
    # to guess the current Martian sol).
    return _nasa_fetch("mars_latest",
        "https://mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020&feedtype=json&num=5&page=0&order=sol+desc",
        3600, max_time=15)


def _artemis_fetch():
    import json as _j
    import xml.etree.ElementTree as _ET
    import re as _re
    now = time.time()
    cached = _nasa_cache.get("artemis_feed")
    if cached and now - cached[1] < 3600:
        return cached[0]
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "15",
             "-A", "Mozilla/5.0 (compatible; SpaceTracker/1.0)",
             "https://www.nasa.gov/blogs/artemis/feed"],
            capture_output=True, timeout=19
        )
        if result.returncode != 0 or not result.stdout:
            return cached[0] if cached else None
        ns = {
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'dc':      'http://purl.org/dc/elements/1.1/',
        }
        root  = _ET.fromstring(result.stdout)
        items = []
        for item in root.findall('.//item'):
            title    = item.findtext('title', '').strip()
            link     = item.findtext('link',  '').strip()
            pub_date = item.findtext('pubDate', '').strip()
            desc     = _re.sub(r'<[^>]+>', '', item.findtext('description', '')).strip()
            if len(desc) > 280:
                desc = desc[:280].rsplit(' ', 1)[0] + '…'
            author   = item.findtext('dc:creator', '', namespaces=ns).strip()
            content  = item.findtext('content:encoded', '', namespaces=ns)
            img_m    = _re.search(r'src=["\']([^"\']+images-assets\.nasa\.gov[^"\']+~(?:large|medium)\.jpg)[^"\']*["\']', content)
            img      = img_m.group(1) if img_m else ''
            cats     = [c.text for c in item.findall('category') if c.text]
            items.append({'title': title, 'link': link, 'date': pub_date,
                          'excerpt': desc, 'image': img, 'author': author,
                          'categories': cats[:3]})
        data = _j.dumps({'items': items}).encode('utf-8')
        _nasa_cache["artemis_feed"] = (data, now)
        return data
    except Exception as e:
        print(f"[artemis] fetch error: {e}")
        return cached[0] if cached else None


# ── ISS BACKGROUND FETCH ─────────────────────────────────────────────────────

_iss_cache      = None
_iss_cache_lock = threading.Lock()

_tiangong_cache = None
_tiangong_lock  = threading.Lock()

_astros_cache = None
_astros_lock  = threading.Lock()


def iss_fetch_loop():
    global _iss_cache
    sat    = None
    tle_ts = 0
    fail   = 0
    while True:
        if sat is None or time.time() - tle_ts > 21600:
            tle = _fetch_tle("25544")
            if tle:
                try:
                    sat    = _Satrec.twoline2rv(tle["line1"], tle["line2"])
                    tle_ts = time.time()
                    fail   = 0
                    print("[iss] TLE loaded, SGP4 active")
                except Exception as e:
                    print(f"[iss] TLE parse error: {e}")
                    sat = None
            else:
                fail += 1
                time.sleep(min(60 * fail, 1800))
                continue

        if sat is None:
            time.sleep(30)
            continue

        try:
            now     = datetime.utcnow()
            jd, fr  = _sgp4_jday(now.year, now.month, now.day,
                                   now.hour, now.minute,
                                   now.second + now.microsecond / 1e6)
            e, r, v = sat.sgp4(jd, fr)
            if e == 0:
                gmst          = _gmst_rad(jd + fr)
                lat, lon, alt = _eci_to_lla(r, gmst)
                vel           = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2) * 3600.0
                foot          = 2.0 * 6371.0 * math.acos(min(1.0, 6371.0 / (6371.0 + alt)))
                pos           = json.dumps({
                    "latitude":   round(lat,  4),
                    "longitude":  round(lon,  4),
                    "altitude":   round(alt,  1),
                    "velocity":   round(vel,  0),
                    "footprint":  round(foot, 0),
                    "visibility": "unknown",
                    "timestamp":  int(time.time()),
                }).encode()
                with _iss_cache_lock:
                    _iss_cache = pos
        except Exception as ex:
            print(f"[iss] loop error: {ex}")
        time.sleep(5)


def tiangong_loop():
    global _tiangong_cache
    if not _HAS_SGP4:
        return
    sat    = None
    tle_ts = 0
    fail   = 0
    while True:
        if sat is None or time.time() - tle_ts > 21600:
            tle = _fetch_tle("48274")
            if tle:
                try:
                    sat    = _Satrec.twoline2rv(tle["line1"], tle["line2"])
                    tle_ts = time.time()
                    fail   = 0
                    print("[tiangong] TLE loaded, position calculation active")
                except Exception as e:
                    print(f"[tiangong] TLE parse error: {e}")
                    sat = None
            else:
                fail += 1
                time.sleep(min(60 * fail, 1800))
                continue

        if sat is None:
            time.sleep(30)
            continue

        try:
            now     = datetime.utcnow()
            jd, fr  = _sgp4_jday(now.year, now.month, now.day,
                                   now.hour, now.minute,
                                   now.second + now.microsecond / 1e6)
            e, r, v = sat.sgp4(jd, fr)
            if e == 0:
                gmst          = _gmst_rad(jd + fr)
                lat, lon, alt = _eci_to_lla(r, gmst)
                vel           = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2) * 3600.0
                foot          = 2.0 * 6371.0 * math.acos(min(1.0, 6371.0 / (6371.0 + alt)))
                pos           = json.dumps({
                    "latitude":   round(lat,  4),
                    "longitude":  round(lon,  4),
                    "altitude":   round(alt,  1),
                    "velocity":   round(vel,  0),
                    "footprint":  round(foot, 0),
                    "visibility": "unknown",
                    "timestamp":  int(time.time()),
                }).encode()
                with _tiangong_lock:
                    _tiangong_cache = pos
        except Exception as ex:
            print(f"[tiangong] loop error: {ex}")
        time.sleep(5)


def astros_loop():
    global _astros_cache
    while True:
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "10", "http://api.open-notify.org/astros.json"],
                capture_output=True, timeout=14
            )
            if result.returncode == 0 and result.stdout:
                try:
                    json.loads(result.stdout)  # valideer JSON
                    with _astros_lock:
                        _astros_cache = result.stdout
                    print("[astros] updated")
                except ValueError:
                    print("[astros] invalid JSON response")
        except Exception as ex:
            print(f"[astros] loop error: {ex}")
        time.sleep(900)  # 15 minuten


# ── HTTP HANDLER ──────────────────────────────────────────────────────────────

class SpaceTrackerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/iss"):
            with _iss_cache_lock:
                self._raw_json(_iss_cache)
        elif self.path.startswith("/api/tiangong"):
            with _tiangong_lock:
                self._raw_json(_tiangong_cache)
        elif self.path.startswith("/api/astros"):
            with _astros_lock:
                self._raw_json(_astros_cache)
        elif self.path.startswith("/api/nasa/apod"):
            self._raw_json(_nasa_fetch("apod",
                f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}", 86400))
        elif self.path.startswith("/api/nasa/donki"):
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            self._raw_json(_nasa_fetch("donki",
                f"https://api.nasa.gov/DONKI/notifications?startDate={week_ago}&type=all&api_key={NASA_KEY}", 3600))
        elif self.path.startswith("/api/nasa/neo/week"):
            today = datetime.now().strftime("%Y-%m-%d")
            end   = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            self._raw_json(_nasa_fetch(f"neo_week_{today}",
                f"https://api.nasa.gov/neo/rest/v1/feed?start_date={today}&end_date={end}&api_key={NASA_KEY}", 3600))
        elif self.path.startswith("/api/nasa/neo"):
            self._raw_json(_nasa_fetch("neo",
                f"https://api.nasa.gov/neo/rest/v1/feed/today?api_key={NASA_KEY}", 3600))
        elif self.path.startswith("/api/nasa/epic"):
            self._raw_json(_nasa_fetch("epic",
                f"https://api.nasa.gov/EPIC/api/natural?api_key={NASA_KEY}", 86400))
        elif self.path.startswith("/api/nasa/mars"):
            self._raw_json(_mars_fetch())
        elif self.path.startswith("/api/nasa/eonet"):
            self._raw_json(_nasa_fetch("eonet",
                "https://eonet.gsfc.nasa.gov/api/v3/events?limit=20&status=open", 3600))
        elif self.path.startswith("/api/artemis/feed"):
            self._raw_json(_artemis_fetch())
        else:
            super().do_GET()

    def _raw_json(self, data):
        if not data:
            self.send_response(503)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"No data available")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass


# ── MAIN ─────────────────────────────────────────────────────────────────────

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    os.makedirs(STATIC_DIR, exist_ok=True)
    threading.Thread(target=iss_fetch_loop, daemon=True).start()
    threading.Thread(target=tiangong_loop,  daemon=True).start()
    threading.Thread(target=astros_loop,    daemon=True).start()
    print(f"Space Tracker → http://0.0.0.0:{PORT}")
    with ThreadingHTTPServer(("0.0.0.0", PORT), SpaceTrackerHandler) as httpd:
        httpd.serve_forever()
