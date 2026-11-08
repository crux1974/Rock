import os
from flask import Flask, Response
import yt_dlp
import git

app = Flask(__name__)

# Словник ваших каналів (назва: посилання на YouTube-трансляцію)
CHANNELS = {
    "Channel 1": "https://www.youtube.com/watch?v=-BJg05my_xE",
    "Channel 2": "https://www.youtube.com/watch?v=UiCK7SCpSIA",
    "Channel 3": "https://www.youtube.com/watch?v=O_ZO3hzSdAs",
    "Channel 4": "https://www.youtube.com/watch?v=BOBpo9bTYAE",
    "Channel 5": "https://www.youtube.com/watch?v=TDSCd8xUpcs",
    "Channel 6": "https://www.youtube.com/watch?v=3LWMFjRZQ6k",
    "Channel 7": "https://www.youtube.com/watch?v=EZP9z9CMdYg",
    "Channel 8": "https://www.youtube.com/watch?v=aiS93HDWPOM"
}

def generate_m3u():
    m3u_content = "#EXTM3U\n"
    
    # Налаштування для yt-dlp з підтримкою cookies.txt
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    # Якщо файл cookies.txt існує в проєкті, додаємо його автоматично
    if os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for name, url in CHANNELS.items():
            try:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get('url')
                if stream_url:
                    m3u_content += f"#EXTINF:-1,{name}\n{stream_url}\n"
            except Exception as e:
                print(f"Помилка для {name}: {e}")
                
    return m3u_content

def push_to_github(content):
    try:
        token = os.environ.get('GITHUB_TOKEN')
        repo_name = os.environ.get('GITHUB_REPOSITORY') # наприклад: username/repo
        
        if not token or not repo_name:
            print("Змінні середовища GITHUB_TOKEN або GITHUB_REPOSITORY не налаштовані!")
            return

        repo_path = '.'
        repo = git.Repo(repo_path)
        
        # Записуємо файл streams.m3u8 локально на сервері
        file_path = os.path.join(repo_path, 'streams.m3u8')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        # Робимо git commit та push на GitHub
        repo.index.add(['streams.m3u8'])
        repo.index.commit("Auto-update streams.m3u8 via Render")
        
        origin = repo.remote(name='origin')
        remote_url = f"https://{token}@github.com/{repo_name}.git"
        origin.set_url(remote_url)
        origin.push()
        print("Файл успішно відправлено на GitHub!")
    except Exception as e:
        print(f"Помилка при відправці на GitHub: {e}")

@app.route('/playlist.m3u8')
def playlist():
    m3u_data = generate_m3u()
    push_to_github(m3u_data)
    return Response(m3u_data, mimetype='audio/x-mpegurl')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
