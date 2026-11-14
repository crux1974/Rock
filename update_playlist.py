"""Генерує streams.m3u8 з channels.txt. Запускається з GitHub Actions (.github/workflows/update.yml).

Коміт і push робить сам workflow — скрипт лише пише файл.
"""
import sys
import time
from datetime import datetime, timezone

from yt_resolver import load_channels, resolve

OUTPUT = "streams.m3u8"


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
        ok += 1
        mins = int((expire - time.time()) / 60)
        print(f"OK (діє ще {mins} хв)")
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
