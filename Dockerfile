FROM python:3.12-slim

# Deno — JS-рушій, без якого yt-dlp втрачає частину форматів YouTube
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py yt_resolver.py ./

ENV PORT=10000 CHANNELS_FILE=/data/channels.txt COOKIES_FILE=/data/cookies.txt
EXPOSE 10000

# При кожному старті оновлюємо yt-dlp: YouTube часто змінюється
CMD pip install --no-cache-dir -q -U "yt-dlp[default]" ; \
    exec gunicorn -b 0.0.0.0:$PORT --threads 8 --timeout 120 app:app
