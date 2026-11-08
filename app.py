import os
from flask import Flask, Response
import yt_dlp

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

@app.route('/playlist.m3u8')
def get_playlist():
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

    return Response(m3u8_content, mimetype='application/x-mpegURL')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
