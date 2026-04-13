import os
import re
import json
import base64
import subprocess
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)

CORS(app,
     origins="*",
     allow_headers=["Content-Type", "Accept"],
     methods=["GET", "POST", "OPTIONS"]
)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

# ──────────────────────────────────────────
# Cookies YouTube
# ──────────────────────────────────────────

COOKIES_PATH = "/tmp/yt_cookies.txt"

def setup_cookies():
    cookies_b64 = os.environ.get("YOUTUBE_COOKIES_B64", "")
    cookies_raw = os.environ.get("YOUTUBE_COOKIES", "")

    if cookies_b64:
        try:
            decoded = base64.b64decode(cookies_b64).decode("utf-8")
            with open(COOKIES_PATH, "w") as f:
                f.write(decoded)
            print("✅ Cookies YouTube chargés (base64)")
        except Exception as e:
            print(f"❌ Erreur décodage cookies : {e}")
    elif cookies_raw:
        with open(COOKIES_PATH, "w") as f:
            f.write(cookies_raw)
        print("✅ Cookies YouTube chargés (raw)")
    else:
        print("⚠️ Pas de cookies YouTube configurés")

setup_cookies()

# ──────────────────────────────────────────
# Utilitaires
# ──────────────────────────────────────────

def is_valid_url(url: str) -> bool:
    return bool(re.match(r'^https?://', url.strip()))


def build_base_args() -> list:
    """Args communs à tous les appels yt-dlp."""
    args = [
        "--extractor-args", "youtube:player_client=android,web",
        "--no-check-formats",
        "--no-warnings",
    ]
    if os.path.exists(COOKIES_PATH):
        args += ["--cookies", COOKIES_PATH]
    return args


def run_ytdlp(args: list) -> tuple[str, str, int]:
    result = subprocess.run(
        ["yt-dlp"] + build_base_args() + args,
        capture_output=True, text=True, timeout=180
    )
    return result.stdout, result.stderr, result.returncode


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@app.route("/", methods=["GET"])
def health():
    cookies_ok = os.path.exists(COOKIES_PATH)
    return jsonify({
        "status":  "ok",
        "service": "leylay-backend",
        "cookies": cookies_ok,
    })


@app.route("/info", methods=["POST"])
def get_info():
    data = request.get_json(silent=True) or {}
    url  = data.get("url", "").strip()

    if not url or not is_valid_url(url):
        return jsonify({"error": "URL invalide"}), 400

    stdout, stderr, code = run_ytdlp(["--dump-json", "--no-playlist", url])

    if code != 0:
        msg = stderr.strip().splitlines()[-1] if stderr.strip() else "Erreur inconnue"
        return jsonify({"error": msg}), 500

    try:
        info = json.loads(stdout)
    except json.JSONDecodeError:
        return jsonify({"error": "Réponse yt-dlp invalide"}), 500

    duration_s = info.get("duration", 0) or 0
    duration   = f"{int(duration_s) // 60}:{int(duration_s) % 60:02d}"

    return jsonify({
        "title":     info.get("title", ""),
        "thumbnail": info.get("thumbnail", ""),
        "duration":  duration,
        "uploader":  info.get("uploader", ""),
        "formats":   [],
    })


@app.route("/download", methods=["POST"])
def download():
    """
    Body JSON : { "url": "...", "mode": "auto" | "audio" | "mute" }
    """
    data = request.get_json(silent=True) or {}
    url  = data.get("url", "").strip()
    mode = data.get("mode", "auto")

    if not url or not is_valid_url(url):
        return jsonify({"error": "URL invalide"}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        output_tpl = os.path.join(tmpdir, "%(title)s.%(ext)s")

        args = ["--no-playlist", "-o", output_tpl]

        if mode == "audio":
            args += ["-f", "bestaudio/best", "-x", "--audio-format", "mp3"]
        elif mode == "mute":
            args += ["-f", "bestvideo[ext=mp4]/bestvideo/best", "--no-audio"]
        else:
            args += ["-f", "bv*+ba/b", "--merge-output-format", "mp4"]

        args.append(url)

        stdout, stderr, code = run_ytdlp(args)

        if code != 0:
            msg = stderr.strip().splitlines()[-1] if stderr.strip() else "Echec du téléchargement"
            return jsonify({"error": msg}), 500

        files = [f for f in os.listdir(tmpdir) if not f.startswith(".")]
        if not files:
            return jsonify({"error": "Aucun fichier généré"}), 500

        filepath = os.path.join(tmpdir, files[0])
        filename = files[0]
        ext      = filename.rsplit(".", 1)[-1].lower()

        mimetypes = {
            "mp4":  "video/mp4",
            "webm": "video/webm",
            "mkv":  "video/x-matroska",
            "mp3":  "audio/mpeg",
            "m4a":  "audio/mp4",
            "opus": "audio/opus",
        }

        return send_file(
            filepath,
            mimetype=mimetypes.get(ext, "application/octet-stream"),
            as_attachment=True,
            download_name=filename
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
