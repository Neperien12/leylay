FROM python:3.11-slim

# Installer ffmpeg + dépendances
RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

# Installer yt-dlp (version récente)
RUN pip install --no-cache-dir yt-dlp flask flask-cors

WORKDIR /app
COPY . .

CMD ["python", "app.py"]
CMD ["gunicorn", "-b", "0.0.0.0:$PORT", "app:app"]
