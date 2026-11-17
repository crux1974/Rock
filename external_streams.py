"""Канали не з YouTube: прямі m3u8-потоки і канали з FAST-плейлистів (app-m3u-generator).

Формати посилань у channels.txt:
  Назва | https://.../playlist.m3u8 | Група          — прямий HLS-потік
  Назва | fast:plex_all:Metal.Rocks | Група          — канал з плейлиста app-m3u-generator
                                                       (береться свіже посилання за назвою)

Кожен запуск потік перевіряється (плейлист + відрізок відео). Якщо задано BEST_PROXY
(воркер Cloudflare), прямі потоки йдуть через нього — тоді плеєр отримує лише найвищу якість.
"""
import ipaddress
import os
import re
from urllib.parse import quote, urljoin, urlparse

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
BEST_PROXY = os.environ.get("BEST_PROXY", "").strip().rstrip("/")
FAST_REPO = os.environ.get("FAST_REPO", "crux1974/app-m3u-generator")
_fast_cache = {}


def is_external(url):
    return not re.search(r"(^|\.)(youtube\.com|youtu\.be)/", url) or url.startswith("fast:")


def _is_ip_host(url):
    try:
        ipaddress.ip_address(urlparse(url).hostname or "")
        return True
    except ValueError:
        return False


def _lookup_fast(spec):
    """fast:<файл плейлиста>:<точна назва каналу> → посилання з app-m3u-generator."""
    _, playlist, name = spec.split(":", 2)
    if playlist not in _fast_cache:
        url = f"https://raw.githubusercontent.com/{FAST_REPO}/main/playlists/{playlist}.m3u"
        r = requests.get(url, headers=UA, timeout=30)
        r.raise_for_status()
        _fast_cache[playlist] = r.text.splitlines()
    lines = _fast_cache[playlist]
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF") and line.rsplit(",", 1)[-1].strip() == name:
            for nxt in lines[i + 1:]:
                if nxt and not nxt.startswith("#"):
                    return nxt.strip()
    raise RuntimeError(f"канал «{name}» не знайдено в {playlist}.m3u")


def check_hls(url):
    """Перевіряє, що потік живий. Повертає висоту найкращої якості (0 — невідомо)."""
    r = requests.get(url, headers=UA, timeout=20)
    if r.status_code != 200 or "#EXTM3U" not in r.text[:300]:
        raise RuntimeError(f"плейлист відповідає {r.status_code}")
    text, base = r.text, r.url
    lines = text.splitlines()
    best, best_key = None, (-1, -1)
    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF") and i + 1 < len(lines):
            h = re.search(r"RESOLUTION=\d+x(\d+)", line)
            bw = re.search(r"BANDWIDTH=(\d+)", line)
            key = (int(h.group(1)) if h else 0, int(bw.group(1)) if bw else 0)
            if key > best_key:
                best_key, best = key, urljoin(base, lines[i + 1].strip())
    media_url, media = (best, requests.get(best, headers=UA, timeout=20).text) if best else (base, text)
    segs = [l.strip() for l in media.splitlines() if l.strip() and not l.startswith("#")]
    if not segs:
        raise RuntimeError("у плейлисті немає відрізків відео")
    s = requests.get(urljoin(media_url, segs[-1]), headers={**UA, "Range": "bytes=0-65535"},
                     timeout=20, stream=True)
    s.close()
    if s.status_code not in (200, 206):
        raise RuntimeError(f"відео відповідає {s.status_code}")
    return max(best_key[0], 0)


def external_url(ch):
    """Повертає (посилання для плейлиста, висота якості). Кидає RuntimeError, якщо потік мертвий."""
    src = ch["url"]
    if src.startswith("fast:"):
        src = _lookup_fast(src)

    candidates = []
    if BEST_PROXY and "workers.dev" not in src and not _is_ip_host(src) and src.startswith("https://"):
        candidates.append(f"{BEST_PROXY}/best?u={quote(src, safe='')}")
    candidates.append(src)

    last = None
    for url in candidates:
        try:
            return url, check_hls(url)
        except Exception as e:  # noqa: BLE001
            last = e
    raise RuntimeError(str(last)[:150])
