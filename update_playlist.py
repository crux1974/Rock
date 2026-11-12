import os
import yt_dlp
import git

# Ваші канали
CHANNELS = {
    "SharpTone Records TV": "https://m.youtube.com/watch?v=-BJg05my_xE",
    "Frontiers Music srl TV": "https://m.youtube.com/watch?v=UiCK7SCpSIA",
    "Thriller Records TV": "https://m.youtube.com/watch?v=O_ZO3hzSdAs",
    "hate5six TV": "https://m.youtube.com/watch?v=BOBpo9bTYAE",
    "KISS TV": "https://m.youtube.com/watch?v=mGarleVlICU",
    "Metallica TV": "https://m.youtube.com/watch?v=7yh2Yjlghf0",
    "Nuclear Blast Records TV": "https://m.youtube.com/watch?v=3LWMFjRZQ6k"
}

def generate_m3u():
    m3u_content = "#EXTM3U\n"
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
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

def main():
    m3u_data = generate_m3u()
    
    repo_path = '.'
    repo = git.Repo(repo_path)
    
    with repo.config_writer() as config:
        config.set_value('user', 'name', 'GitHub Actions Bot')
        config.set_value('user', 'email', 'actions@github.com')

    file_path = os.path.join(repo_path, 'streams.m3u8')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(m3u_data)
        
    repo.index.add(['streams.m3u8'])
    if repo.is_dirty(index=True, working_tree=True):
        repo.index.commit("Auto-update streams.m3u8 via GitHub Actions")
        origin = repo.remote(name='origin')
        origin.push(refspec='HEAD:main')
        print("Плейлист успішно оновлено!")
    else:
        print("Змін немає.")

if __name__ == '__main__':
    main()
