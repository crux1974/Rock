"""Генерує streams.m3u8 з channels.txt. Запускається з GitHub Actions (.github/workflows/update.yml).

Коміт і push робить сам workflow — скрипт лише пише файл.
"""
import os
import sys
import time
from datetime import datetime, timezone

from external_streams import external_url, is_external
from yt_resolver import best_quality_manifest, load_channels, resolve

OUTPUT = "streams.m3u8"
CHANNELS_DIR = "channels"
# BEST_QUALITY=0 — віддавати повний набір якостей (плеєр обирає сам)
BEST_QUALITY = os.environ.get("BEST_QUALITY", "1") != "0"
REPO = os.environ.get("GITHUB_REPOSITORY", "crux1974/Rock")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{CHANNELS_DIR}"


def main():
    channels = load_channels()
    if not channels:
        print("Немає каналів у channels.txt")
        return 1

    lines = ["#EXTM3U"]
    ok = yt_ok = yt_total = yt_failed = 0
    yt_blocked = False
    for i, ch in enumerate(channels, 1):
        print(f"[{i}/{len(channels)}] {ch['name']} … ", end="", flush=True)
        grp = f' group-title="{ch["group"]}"' if ch["group"] else ""

        if is_external(ch["url"]):
            try:
                url, height = external_url(ch)
            except Exception as e:  # noqa: BLE001
                print(f"НЕ ПРАЦЮЄ: {e}")
                lines.append(f"# {ch['name']}: недоступний ({str(e)[:120]})")
                continue
            ok += 1
            via = "через воркер" if "/best?u=" in url else "напряму"
            print(f"OK, {height or '?'}p, {via}")
            lines.append(f'#EXTINF:-1 tvg-id="{ch["key"]}"{grp},{ch["name"]}')
            lines.append(url)
            continue

        yt_total += 1
        if yt_blocked:
            print("пропущено (YouTube блокує адресу)")
            lines.append(f"# {ch['name']}: пропущено (YouTube блокує адресу)")
            continue
        try:
            url, expire = resolve(ch["url"], retries=1)
        except RuntimeError as e:
            print(f"ПОМИЛКА: {e}")
            lines.append(f"# {ch['name']}: недоступний ({str(e)[:120]})")
            yt_failed += 1
            if yt_ok == 0 and yt_failed >= 2 and "not a bot" in str(e):
                print("Перші канали YouTube заблоковано («not a bot») — схоже, заблокована вся адреса.")
                yt_blocked = True
            continue
        if BEST_QUALITY:
            try:
                manifest = best_quality_manifest(url)
                os.makedirs(CHANNELS_DIR, exist_ok=True)
                with open(os.path.join(CHANNELS_DIR, f"{ch['key']}.m3u8"), "w", encoding="utf-8") as f:
                    f.write(manifest)
                quality = next((l.split("RESOLUTION=")[1].split(",")[0]
                                for l in manifest.splitlines() if "RESOLUTION=" in l), "?")
                # Додаємо мітку часу, щоб плеєр і кеш GitHub брали свіжий файл
                url = f"{RAW_BASE}/{ch['key']}.m3u8?t={int(time.time())}"
            except Exception as e:
                quality = "усі (фільтр не спрацював)"
                print(f"[фільтр якості: {e}] ", end="")
        else:
            quality = "усі"
        ok += 1
        yt_ok += 1
        mins = int((expire - time.time()) / 60)
        print(f"OK, якість {quality} (діє ще {mins} хв)")
        lines.append(f'#EXTINF:-1 tvg-id="{ch["key"]}"{grp},{ch["name"]}')
        lines.append(url)
        time.sleep(2)  # не засипати YouTube запитами

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"# Оновлено: {now}, в ефірі {ok}/{len(channels)}")

    if ok == 0 or (yt_total and yt_ok == 0):
        # Не затираємо попередній плейлист: у ньому ще можуть бути робочі посилання YouTube
        print("Канали YouTube не отримано — streams.m3u8 не змінюю")
        return 1

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Готово: {ok}/{len(channels)} каналів у {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
