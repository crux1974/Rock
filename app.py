import os
import time
from flask import Flask, Response
import yt_dlp
from git import Repo

app = Flask(__name__)

CHANNELS = {
    "SharpTone Records TV": "https://www.youtube.com/@SharpToneRecords/live",
    "Frontiers Music srl TV": "https://www.youtube.com/live/UiCK7SCpSIA",
    "Thriller Records TV": "https://www.youtube.com/@thrillerrecords/live",
    "hate5six TV": "https://www.youtube.com/@hate5six/live",
    "KISS TV": "https://www.youtube.com/live/TDSCd8xUpcs",
    "Nuclear Blast Records TV": "https://www.youtube.com/@NuclearBlastRecords/live",
    "Nuclear Blast Thrash/Speed TV": "https://www.youtube.com/live/EZP9z9CMdYg",
    "Nuclear Blast Power/Heavy/Symphonic TV": "https://www.youtube.com/live/aiS93HDWPOM"
}

# Зберігаємо час останнього оновлення, щоб не спамити комітами
LAST_UPDATE = 0
UPDATE_INTERVAL = 3600  # Оновлювати не частіше ніж раз на годину

def update_github_playlist():
    global LAST_UPDATE
    if time.time() - LAST_UPDATE < UPDATE_INTERVAL:
        return

    m3u8_content = "#EXTM3U\n"
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded', 'mweb'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    }

    for name, url in CHANNELS.items():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
                
                stream_url = info.get('url')
                title = info.get('title', name)
                
                if stream_url:
                    m3u8_content += f"#EXTINF:-1, {name} | {title}\n{stream_url}\n"
        except Exception:
            continue

    # Зберігаємо локально на серверах Render
    filename = "streams.m3u8"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(m3u8_content)

    # Робимо автоматичний push на GitHub через токен
    token = os.environ.get('GITHUB_TOKEN')
    repo_name = os.environ.get('GITHUB_REPOSITORY') # Наприклад: your_username/your_repo
    
    if token and repo_name:
        try:
            repo_url = f"https://x-access-token:{token}@github.com/{repo_name}.git"
            repo = Repo.clone_from(repo_url, "temp_repo", branch="main")
            
            # Копіюємо згенерований файл у клонований репозиторій
            with open("temp_repo/streams.m3u8", "w", encoding="utf-8") as f:
                f.write(m3u8_content)
                
            repo.git.add("streams.m3u8")
            repo.index.commit("🤖 Auto-update streams.m3u8 from Render cloud")
            origin = repo.remote(name='origin')
            origin.push()
            LAST_UPDATE = time.time()
        except Exception as e:
            print(f"Git push error: {e}")

@app.route('/playlist.m3u8')
def get_playlist():
    # Запускаємо оновлення в фоні або примусово формуємо текст
    update_github_playlist()
    
    filename = "streams.m3u8"
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "#EXTM3U\n"

    return Response(content, mimetype='application/x-mpegURL')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
