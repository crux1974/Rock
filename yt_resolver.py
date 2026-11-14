"""Спільний код: читання channels.txt і отримання живого посилання з YouTube."""
import os
import re
import time

import yt_dlp

CHANNELS_FILE = os.environ.get("CHANNELS_FILE", "channels.txt")
COOKIES_FILE = os.environ.get("COOKIES_FILE", "cookies.txt")
PROXY = os.environ.get("YTDLP_PROXY", "")  # напр. http://gluetun:8888 (необов'язково)


def slug(text):
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower() or "channel"


def load_channels(path=CHANNELS_FILE):
    """Повертає список {'key','name','url','group'} з channels.txt."""
    channels, seen = [], set()
    if not os.path.exists(path):
        print(f"Файл {path} не знайдено")
        return channels
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 1:
                url = parts[0]
                m = re.search(r"@([^/]+)", url)
                name, group = (m.group(1) if m else url), ""
            else:
                name, url = parts[0], parts[1]
                group = parts[2] if len(parts) > 2 else ""
            key, n = slug(name), 2
            while key in seen:
                key, n = f"{slug(name)}_{n}", n + 1
            seen.add(key)
            channels.append({"key": key, "name": name, "url": url, "group": group})
    return channels


def _opts(proxy=None, clients=None):
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "socket_timeout": 30}
    if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
        opts["cookiefile"] = COOKIES_FILE
    proxy = PROXY if proxy is None else proxy
    if proxy:
        opts["proxy"] = proxy
    if clients:
        opts["extractor_args"] = {"youtube": {"player_client": clients}}
    return opts


# Способи по черзі: якщо YouTube просить «not a bot», пробуємо інший клієнт,
# а потім — без VPN (інколи IP WARP «засвічений», а пряме з'єднання ні).
_STRATEGIES = [
    {"proxy": None, "clients": None},
    {"proxy": None, "clients": ["tv", "web_safari"]},
    {"proxy": "", "clients": None},
    {"proxy": "", "clients": ["tv", "web_safari"]},
]


def _extract(url, strategy):
    with yt_dlp.YoutubeDL(_opts(**strategy)) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info.get("is_live"):
        raise RuntimeError(f"зараз не в ефірі (статус: {info.get('live_status')})")
    stream = info.get("manifest_url") or next(
        (f["manifest_url"] for f in reversed(info.get("formats") or [])
         if f.get("manifest_url")), None)
    if not stream:
        raise RuntimeError("yt-dlp не повернув посилання на трансляцію")
    m = re.search(r"expire[=/](\d+)", stream)
    return stream, int(m.group(1)) if m else int(time.time()) + 3600


def resolve(url, retries=2):
    """Повертає (посилання_на_m3u8, час_закінчення_unix). Кидає RuntimeError, якщо не вдалось.

    Береться master-плейлист HLS: у ньому всі якості та звук.
    """
    strategies = [st for st in _STRATEGIES if st["proxy"] != "" or PROXY]  # без VPN — дублі не потрібні
    last_err = None
    for attempt in range(retries + 1):
        for st in strategies:
            try:
                return _extract(url, st)
            except Exception as e:
                last_err = e
                if "не в ефірі" in str(e):
                    raise RuntimeError(str(e))
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(str(last_err).replace("\n", " "))


_ATTR_RE = re.compile(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)')


def _attrs(line):
    return {k: v.strip('"') for k, v in _ATTR_RE.findall(line.split(":", 1)[1])}


def best_quality_manifest(master_url):
    """Завантажує master-плейлист і лишає в ньому тільки найвищу якість (+ її звук).

    Плеєр тоді одразу грає найкращу якість і не може «з'їхати» на низьку.
    Повертає текст m3u8.
    """
    with yt_dlp.YoutubeDL(_opts()) as ydl:
        text = ydl.urlopen(master_url).read().decode("utf-8")  # noqa
    lines = text.splitlines()

    header, media, variants = [], [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXT-X-STREAM-INF:"):
            uri = lines[i + 1] if i + 1 < len(lines) else ""
            variants.append((line, uri))
            i += 2
            continue
        if line.startswith("#EXT-X-MEDIA:"):
            media.append(line)
        elif line.startswith("#EXTM3U") or line.startswith("#EXT-X-INDEPENDENT-SEGMENTS") \
                or line.startswith("#EXT-X-VERSION"):
            header.append(line)
        i += 1

    if not variants:
        return text  # невідомий формат — віддаємо як є

    def score(v):
        a = _attrs(v[0])
        w, _, h = a.get("RESOLUTION", "0x0").partition("x")
        return (int(h or 0), float(a.get("FRAME-RATE", 0) or 0), int(a.get("BANDWIDTH", 0) or 0))

    best_inf, best_uri = max(variants, key=score)
    # Лишаємо тільки звук обраної якості. Субтитри прибираємо: вбудований плеєр
    # LG webOS погано підтримує теги субтитрів у HLS, а на живому ефірі вони не потрібні.
    audio = _attrs(best_inf).get("AUDIO")
    keep_media = [m for m in media if audio and _attrs(m).get("GROUP-ID") == audio
                  and _attrs(m).get("TYPE") == "AUDIO"]
    best_inf = re.sub(r',SUBTITLES="[^"]*"', "", best_inf)
    out = (header or ["#EXTM3U"]) + keep_media + [best_inf, best_uri]
    return "\n".join(out) + "\n"
