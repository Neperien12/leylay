from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

# YTDLP_BASE_ARGS Configuration
YTDLP_BASE_ARGS = [
    '--user-agent', 'Mozilla/5.0',
    '-S', 'vcodec:h264,res,acodec:aac',
    '-f', 'bv*+ba/best',
    '--merge-output-format', 'mp4',
    '--max-filesize', '50M',
    '--format-sort', 'res:720'
]

@app.route('/download', methods=['POST'])
def download():
    url = request.json['url']
    command = ['yt-dlp'] + YTDLP_BASE_ARGS + [url]
    try:
        subprocess.run(command, check=True)
        return jsonify({'status': 'success'}), 200
    except subprocess.CalledProcessError:
        return jsonify({'status': 'error'}), 500

if __name__ == '__main__':
    app.run(debug=True)