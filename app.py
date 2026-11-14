"""Сервер живого плейлиста (для дому, NAS, Raspberry Pi або Render).

  /playlist.m3u8       плейлист з постійними посиланнями на цей сервер
  /live/<канал>.m3u8   редирект на свіже посилання YouTube (оновлюється саме)
  /                    стан каналів

Посилання YouTube прив'язані до IP, з якого їх отримали. Тому найкраще запускати
сервер у тій самій мережі, що й телевізор/плеєр — тоді все грає без 403.
"""
import os
import threading
import time

from flask import Flask, Response, abort, redirect, request

from yt_resolver import load_channels, resolve

REFRESH_MARGIN = 15 * 60  # оновлювати за 15 хв до закінчення
FAIL_RETRY = 60           # після помилки пробувати знову через 60 с

app = Flask(__name__)
_cache, _fail, _locks = {}, {}, {}
_guard = threading.Lock()


def get_stream(ch):
    key = ch["key"]
    with _guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        now = time.time()
        url, exp = _cache.get(key, (None, 0))
        if url and exp - now > REFRESH_MARGIN:
            return url, None
        ts, err = _fail.get(key, (0, None))
        if err and now - ts < FAIL_RETRY:
            return (url if exp > now else None), err
        try:
            url, exp = resolve(ch["url"], retries=1)
            _cache[key] = (url, exp)
            _fail.pop(key, None)
            print(f"[{key}] оновлено, діє {int((exp - now) / 60)} хв", flush=True)
            return url, None
        except RuntimeError as e:
            _fail[key] = (now, str(e))
            print(f"[{key}] ПОМИЛКА: {e}", flush=True)
            return (url if exp > now else None), str(e)


@app.route("/playlist.m3u8")
@app.route("/playlist.m3u")
def playlist():
    base = request.host_url.rstrip("/")
    out = ["#EXTM3U"]
    for ch in load_channels():
        grp = f' group-title="{ch["group"]}"' if ch["group"] else ""
        out.append(f'#EXTINF:-1 tvg-id="{ch["key"]}"{grp},{ch["name"]}')
        out.append(f"{base}/live/{ch['key']}.m3u8")
    return Response("\n".join(out) + "\n", mimetype="application/vnd.apple.mpegurl",
                    headers={"Cache-Control": "no-store"})


@app.route("/live/<key>.m3u8")
def live(key):
    ch = next((c for c in load_channels() if c["key"] == key), None)
    if not ch:
        abort(404)
    url, err = get_stream(ch)
    if not url:
        return Response(f"Не вдалося отримати трансляцію: {err}\n", status=502,
                        mimetype="text/plain")
    resp = redirect(url, 302)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/")
def status():
    now = time.time()
    rows = [f"Плейлист: {request.host_url}playlist.m3u8", ""]
    for ch in load_channels():
        url, exp = _cache.get(ch["key"], (None, 0))
        _, err = _fail.get(ch["key"], (0, None))
        state = (f"OK, діє ще {int((exp - now) / 60)} хв" if url and exp > now
                 else f"ПОМИЛКА: {err}" if err else "ще не запитувався")
        rows.append(f"{ch['name']:<28} {state}")
    return Response("\n".join(rows) + "\n", mimetype="text/plain; charset=utf-8")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), threaded=True)
