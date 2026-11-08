import os
from flask import Flask, Response
import yt_dlp
import git

app = Flask(__name__)

# Словник ваших каналів
CHANNELS = {
    "SharpTone Records TV": "https://www.youtube.com/watch?v=-BJg05my_xE",
    "Frontiers Music srl TV": "https://www.youtube.com/watch?v=UiCK7SCpSIA",
    "Thriller Records TV": "https://www.youtube.com/watch?v=O_ZO3hzSdAs",
    "hate5six TV": "https://www.youtube.com/watch?v=BOBpo9bTYAE",
    "KISS TV": "https://www.youtube.com/@KissTheBand/live",
    "Metallica TV": "https://www.youtube.com/@metallica/live",
    "Nuclear Blast Records TV": "https://www.youtube.com/watch?v=3LWMFjRZQ6k",
    "Nuclear Blast Thrash/Speed TV": "https://www.youtube.com/watch?v=EZP9z9CMdYg",
    "Nuclear Blast Power/Heavy/Symphonic TV": "https://www.youtube.com/watch?v=aiS93HDWPOM"
}

def generate_m3u():
    m3u_content = "#EXTM3U\n"
    
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
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
        repo_name = os.environ.get('GITHUB_REPOSITORY') # наприклад: crux1974/Rock-c4rx
        
        if not token or not repo_name:
            print("Змінні середовища GITHUB_TOKEN або GITHUB_REPOSITORY не налаштовані!")
            return

        repo_path = '.'
        repo = git.Repo(repo_path)
        
        # Налаштовуємо ім'я та пошту для комітів, щоб git не сварився
        with repo.config_writer() as config:
            config.set_value('user', 'name', 'Render Bot')
            config.set_value('user', 'email', 'bot@render.com')

        # Записуємо файл streams.m3u8 локально
        file_path = os.path.join(repo_path, 'streams.m3u8')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        # Робимо git commit
        repo.index.add(['streams.m3u8'])
        repo.index.commit("Auto-update streams.m3u8 via Render")
        
        # Автоматично створюємо або оновлюємо remote origin з токеном
        remote_url = f"https://{token}@github.com/{repo_name}.git"
        if 'origin' in [r.name for r in repo.remotes]:
            origin = repo.remote(name='origin')
            origin.set_url(remote_url)
        else:
            origin = repo.create_remote('origin', remote_url)
            
        origin.push(refspec='HEAD:main')
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
