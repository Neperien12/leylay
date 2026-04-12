import os
import subprocess
import tempfile
import json
import re
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

try:
    subprocess.run(["yt-dlp", "-U"])
except:
    pass
app = Flask(__name__)

# ── Cookies YouTube depuis variable d'environnement ──
COOKIES_PATH = "/tmp/yt_cookies.txt"

def setup_cookies():
    import base64
    cookies_b64 = os.environ.get("YOUTUBE_COOKIES_B64", "")
    cookies_raw = os.environ.get("YOUTUBE_COOKIES", "")

    if cookies_b64:
        try:
            decoded = base64.b64decode(cookies_b64).decode("utf-8")
            with open(COOKIES_PATH, "w") as f:
                f.write(decoded)
            print("✅ Cookies YouTube chargés (base64)")
        except Exception as e:
            print(f"❌ Erreur décodage base64 : {e}")
    elif cookies_raw:
        with open(COOKIES_PATH, "w") as f:
            f.write(cookies_raw)
        print("✅ Cookies YouTube chargés (raw)")
    else:
        print("⚠️ Pas de cookies YouTube configurés")

setup_cookies()

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
# Utilitaires
# ──────────────────────────────────────────

def is_valid_url(url: str) -> bool:
    return bool(re.match(r'^https?://', url.strip()))


# ── Args communs injectés dans chaque appel yt-dlp ──
# android,web : contourne le blocage de formats YouTube sur certaines vidéos
YTDLP_BASE_ARGS = [
    "--extractor-args", "youtube:player_client=android,web",
    "--no-check-formats",
]

def run_ytdlp(args: list) -> tuple[str, str, int]:
    """Lance yt-dlp et retourne (stdout, stderr, returncode)."""
    base = []
    if os.path.exists(COOKIES_PATH):
        base += ["--cookies", COOKIES_PATH]
    base += YTDLP_BASE_ARGS

    result = subprocess.run(
        ["yt-dlp"] + base + args,
        capture_output=True, text=True, timeout=120
    )
    return result.stdout, result.stderr, result.returncode


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "leylay-backend"})


@app.route("/debug", methods=["POST"])
def debug_formats():
    """Route temporaire pour voir les formats bruts disponibles."""
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL manquante"}), 400

    stdout, stderr, code = run_ytdlp(["--list-formats", "--no-playlist", url])
    return jsonify({
        "stdout": stdout,
        "stderr": stderr,
        "code": code
    })


@app.route("/info", methods=["POST"])
def get_info():
    """
    Retourne les métadonnées + formats disponibles d'une vidéo.
    Body JSON : { "url": "https://..." }
    """
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()

    if not url or not is_valid_url(url):
        return jsonify({"error": "URL invalide"}), 400

    stdout, stderr, code = run_ytdlp([
        "--dump-json", "--no-playlist",
        "--no-warnings", url
    ])

    if code != 0:
        msg = stderr.strip().splitlines()[-1] if stderr.strip() else "Erreur inconnue"
        return jsonify({"error": msg}), 500

    try:
        info = json.loads(stdout)
    except json.JSONDecodeError:
        return jsonify({"error": "Réponse yt-dlp invalide"}), 500

    # ── FIX : extraire les vrais formats disponibles ──
    formats = []
    for f in info.get("formats", []):
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        # Ignorer les formats sans flux valide
        if vcodec == "none" and acodec == "none":
            continue
        formats.append({
            "format_id": f.get("format_id"),
            "ext":       f.get("ext"),
            "height":    f.get("height"),
            "vcodec":    vcodec,
            "acodec":    acodec,
            "filesize":  f.get("filesize") or f.get("filesize_approx"),
        })

    return jsonify({
        "title":     info.get("title", ""),
        "thumbnail": info.get("thumbnail", ""),
        "duration":  info.get("duration_string", ""),
        "uploader":  info.get("uploader", ""),
        "formats":   formats,
    })


@app.route("/download", methods=["POST"])
def download():
    """
    Télécharge et renvoie le fichier directement.
    Body JSON : {
        "url": "https://...",
        "mode": "auto" | "audio" | "mute"
    }
    Note : ne pas passer format_id, le backend choisit selon le mode.
    """
    data = request.get_json(silent=True) or {}
    url  = data.get("url", "").strip()
    mode = data.get("mode", "auto")

    if not url or not is_valid_url(url):
        return jsonify({"error": "URL invalide"}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = os.path.join(tmpdir, "%(title)s.%(ext)s")

        args = [
            "--no-playlist",
            "--no-warnings",
            "-o", output_template,
        ]

        if mode == "audio":
            args += [
                "-f", "bestaudio/best",
                "-x", "--audio-format", "mp3",
            ]
        elif mode == "mute":
            args += [
                "-f", "bestvideo[ext=mp4]/bestvideo/best",
                "--no-audio",
            ]
        else:
            # ── FIX : sélecteur robuste avec fallbacks successifs ──
            args += [
                "-f", "bv*+ba/b",
                "--merge-output-format", "mp4",
            ]

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

        ext = filename.rsplit(".", 1)[-1].lower()
        mimetypes = {
            "mp4":  "video/mp4",
            "webm": "video/webm",
            "mkv":  "video/x-matroska",
            "mp3":  "audio/mpeg",
            "m4a":  "audio/mp4",
            "opus": "audio/opus",
        }
        mime = mimetypes.get(ext, "application/octet-stream")

        return send_file(
            filepath,
            mimetype=mime,
            as_attachment=True,
            download_name=filename
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
