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


def _opts():
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "socket_timeout": 30}
    if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
        opts["cookiefile"] = COOKIES_FILE
    if PROXY:
        opts["proxy"] = PROXY
    return opts


def resolve(url, retries=2):
    """Повертає (посилання_на_m3u8, час_закінчення_unix). Кидає RuntimeError, якщо не вдалось.

    Береться master-плейлист HLS: у ньому всі якості та звук. Посилання на окрему
    якість YouTube тепер віддає без звуку, тому їх не використовуємо.
    """
    last_err = None
    for attempt in range(retries + 1):
        try:
            with yt_dlp.YoutubeDL(_opts()) as ydl:
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
        except Exception as e:
            last_err = e
            if "не в ефірі" in str(e):
                break
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(str(last_err).replace("\n", " "))
