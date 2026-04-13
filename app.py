import os
import re
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pytubefix import YouTube

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
# Utilitaires
# ──────────────────────────────────────────

def is_valid_url(url: str) -> bool:
    return bool(re.match(r'^https?://', url.strip()))


def make_yt(url: str) -> YouTube:
    """Crée un objet YouTube avec les options qui contournent les restrictions."""
    return YouTube(
        url,
        use_po_token=True,
        use_oauth=False,
        allow_oauth_cache=True,
        client="WEB",
    )


def safe_filename(title: str, ext: str) -> str:
    """Nettoie le titre pour en faire un nom de fichier valide."""
    name = re.sub(r'[\\/*?:"<>|]', '', title).strip()
    name = name[:100]
    return f"{name}.{ext}"


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "leylay-backend"})


@app.route("/info", methods=["POST"])
def get_info():
    """
    Retourne les métadonnées d'une vidéo.
    Body JSON : { "url": "https://..." }
    """
    data = request.get_json(silent=True) or {}
    url  = data.get("url", "").strip()

    if not url or not is_valid_url(url):
        return jsonify({"error": "URL invalide"}), 400

    try:
        yt = make_yt(url)
        duration_s = yt.length or 0
        duration   = f"{duration_s // 60}:{duration_s % 60:02d}"

        return jsonify({
            "title":     yt.title or "",
            "thumbnail": yt.thumbnail_url or "",
            "duration":  duration,
            "uploader":  yt.author or "",
            "formats":   [],
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download", methods=["POST"])
def download():
    """
    Télécharge et renvoie le fichier directement.
    Body JSON : {
        "url":  "https://...",
        "mode": "auto" | "audio" | "mute"
    }

    Modes :
      auto  -> meilleure résolution progressive (vidéo + audio, jusqu'à 1080p)
      audio -> audio uniquement (.m4a)
      mute  -> meilleure vidéo sans audio
    """
    data = request.get_json(silent=True) or {}
    url  = data.get("url", "").strip()
    mode = data.get("mode", "auto")

    if not url or not is_valid_url(url):
        return jsonify({"error": "URL invalide"}), 400

    try:
        yt = make_yt(url)
        title = yt.title or "leylay"

        with tempfile.TemporaryDirectory() as tmpdir:

            if mode == "audio":
                # Audio uniquement (.m4a)
                stream = yt.streams.get_audio_only()
                if not stream:
                    return jsonify({"error": "Aucun flux audio disponible"}), 500

                filepath = stream.download(output_path=tmpdir)
                filename = safe_filename(title, "m4a")
                mime     = "audio/mp4"

            elif mode == "mute":
                # Vidéo sans audio (résolution max)
                stream = (
                    yt.streams
                      .filter(only_video=True)
                      .order_by("resolution")
                      .last()
                )
                if not stream:
                    return jsonify({"error": "Aucun flux vidéo disponible"}), 500

                filepath = stream.download(output_path=tmpdir)
                ext      = stream.subtype or "mp4"
                filename = safe_filename(title, ext)
                mime     = f"video/{ext}"

            else:
                # Auto : progressive (vidéo + audio combinés)
                stream = yt.streams.get_highest_resolution()
                if not stream:
                    stream = yt.streams.first()
                if not stream:
                    return jsonify({"error": "Aucun flux disponible"}), 500

                filepath = stream.download(output_path=tmpdir)
                ext      = stream.subtype or "mp4"
                filename = safe_filename(title, ext)
                mime     = f"video/{ext}"

            return send_file(
                filepath,
                mimetype=mime,
                as_attachment=True,
                download_name=filename
            )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
