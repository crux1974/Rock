"""Генерує streams.m3u8 з channels.txt. Запускається з GitHub Actions (.github/workflows/update.yml).

Коміт і push робить сам workflow — скрипт лише пише файл.
"""
import os
import sys
import time
from datetime import datetime, timezone

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
    ok = 0
    for i, ch in enumerate(channels, 1):
        print(f"[{i}/{len(channels)}] {ch['name']} … ", end="", flush=True)
        try:
            url, expire = resolve(ch["url"])
        except RuntimeError as e:
            print(f"ПОМИЛКА: {e}")
            lines.append(f"# {ch['name']}: недоступний ({str(e)[:120]})")
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
        mins = int((expire - time.time()) / 60)
        print(f"OK, якість {quality} (діє ще {mins} хв)")
        grp = f' group-title="{ch["group"]}"' if ch["group"] else ""
        lines.append(f'#EXTINF:-1 tvg-id="{ch["key"]}"{grp},{ch["name"]}')
        lines.append(url)
        time.sleep(2)  # не засипати YouTube запитами

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"# Оновлено: {now}, в ефірі {ok}/{len(channels)}")

    if ok == 0:
        # Не затираємо попередній робочий плейлист порожнім
        print("Жодного каналу не отримано — streams.m3u8 не змінюю")
        return 1

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Готово: {ok}/{len(channels)} каналів у {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
