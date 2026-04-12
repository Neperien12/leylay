import os
import subprocess
import tempfile
import json
import re
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)

# Autorise ton domaine frontend ici (ou "*" pour tout autoriser)
CORS(app, origins="*")

# ──────────────────────────────────────────
# Utilitaires
# ──────────────────────────────────────────

def is_valid_url(url: str) -> bool:
    return bool(re.match(r'^https?://', url.strip()))


def run_ytdlp(args: list) -> tuple[str, str, int]:
    """Lance yt-dlp et retourne (stdout, stderr, returncode)."""
    result = subprocess.run(
        ["yt-dlp"] + args,
        capture_output=True, text=True, timeout=120
    )
    return result.stdout, result.stderr, result.returncode


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "leylay-backend"})


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

    # Extrait les formats utiles
    formats = []
    for f in info.get("formats", []):
        ext  = f.get("ext", "")
        vco  = f.get("vcodec", "none")
        aco  = f.get("acodec", "none")
        h    = f.get("height")
        abr  = f.get("abr")
        fid  = f.get("format_id", "")

        if vco != "none" and h:
            formats.append({
                "id": fid,
                "label": f"🎬 {h}p  ({ext.upper()})",
                "type": "video",
                "height": h,
                "ext": ext
            })
        elif aco != "none" and vco == "none" and abr:
            formats.append({
                "id": fid,
                "label": f"🎵 Audio {int(abr)}kbps ({ext.upper()})",
                "type": "audio",
                "abr": abr,
                "ext": ext
            })

    # Déduplique par label
    seen = set()
    unique_formats = []
    for f in sorted(formats, key=lambda x: x.get("height", x.get("abr", 0)), reverse=True):
        if f["label"] not in seen:
            seen.add(f["label"])
            unique_formats.append(f)

    return jsonify({
        "title":     info.get("title", ""),
        "thumbnail": info.get("thumbnail", ""),
        "duration":  info.get("duration_string", ""),
        "uploader":  info.get("uploader", ""),
        "formats":   unique_formats[:12]   # max 12 formats
    })


@app.route("/download", methods=["POST"])
def download():
    """
    Télécharge et renvoie le fichier directement.
    Body JSON : {
        "url": "https://...",
        "mode": "auto" | "audio" | "mute",
        "format_id": "137+140"   // optionnel
    }
    """
    data = request.get_json(silent=True) or {}
    url       = data.get("url", "").strip()
    mode      = data.get("mode", "auto")
    format_id = data.get("format_id", "")

    if not url or not is_valid_url(url):
        return jsonify({"error": "URL invalide"}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = os.path.join(tmpdir, "%(title)s.%(ext)s")

        # Construction des arguments yt-dlp
        args = [
            "--no-playlist",
            "--no-warnings",
            "-o", output_template,
        ]

        if format_id:
            args += ["-f", format_id]
        elif mode == "audio":
            args += ["-f", "bestaudio", "-x", "--audio-format", "mp3"]
        elif mode == "mute":
            args += ["-f", "bestvideo", "--no-audio"]
        else:
            # auto : meilleure qualité ≤ 1080p avec audio fusionné
            args += ["-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]", "--merge-output-format", "mp4"]

        args.append(url)

        stdout, stderr, code = run_ytdlp(args)

        if code != 0:
            msg = stderr.strip().splitlines()[-1] if stderr.strip() else "Echec du téléchargement"
            return jsonify({"error": msg}), 500

        # Trouve le fichier produit
        files = [f for f in os.listdir(tmpdir) if not f.startswith(".")]
        if not files:
            return jsonify({"error": "Aucun fichier généré"}), 500

        filepath = os.path.join(tmpdir, files[0])
        filename = files[0]

        # Détecte le mimetype
        ext = filename.rsplit(".", 1)[-1].lower()
        mimetypes = {
            "mp4": "video/mp4", "webm": "video/webm",
            "mkv": "video/x-matroska", "mp3": "audio/mpeg",
            "m4a": "audio/mp4", "opus": "audio/opus",
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
