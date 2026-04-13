# leylay — backend

Backend Flask + pytubefix pour le frontend leylay.  
Déployable gratuitement sur **Railway**.

---

## 📁 Structure

```
leylay-backend/
├── app.py            ← Le serveur Flask
├── requirements.txt  ← Dépendances Python
├── Procfile          ← Commande de démarrage
└── index.html        ← Le frontend (à héberger séparément)
```

---

## 🚀 Déploiement sur Railway

### Étape 1 — Crée un compte
→ https://railway.app (connexion avec GitHub)

### Étape 2 — Push sur GitHub
```bash
cd leylay-backend
git init
git add .
git commit -m "leylay backend"
git branch -M main
git remote add origin https://github.com/TON-USERNAME/leylay-backend.git
git push -u origin main
```

### Étape 3 — Nouveau projet Railway
1. Clique **"New Project"**
2. Choisis **"Deploy from GitHub repo"**
3. Sélectionne ton repo

Railway détecte le `Procfile` automatiquement — ne touche à rien dans les settings.

### Étape 4 — Récupère ton URL
Une fois déployé, Railway te donne une URL publique du type :
```
https://leylay-backend-production.up.railway.app
```

### Étape 5 — Met à jour le frontend
Dans `index.html`, ligne :
```javascript
const BACKEND = "https://TON-BACKEND.up.railway.app";
```
Remplace par ton URL Railway.

---

## 🔌 API Endpoints

### `GET /`
Health check — vérifie que le serveur tourne.
```json
{ "status": "ok", "service": "leylay-backend" }
```

### `POST /info`
Retourne les métadonnées de la vidéo.
```json
{ "url": "https://youtube.com/watch?v=..." }
```
Réponse :
```json
{
  "title": "Titre de la vidéo",
  "thumbnail": "https://...",
  "duration": "3:45",
  "uploader": "Nom de la chaîne",
  "formats": []
}
```

### `POST /download`
Télécharge et renvoie le fichier directement.
```json
{
  "url": "https://youtube.com/watch?v=...",
  "mode": "auto"
}
```
Modes disponibles :
- `auto` — meilleure qualité vidéo + audio (progressive, jusqu'à 720p)
- `audio` — audio uniquement `.m4a`
- `mute` — vidéo sans audio

---

## 🛠️ Test en local

```bash
pip install -r requirements.txt
python app.py
```

Serveur disponible sur http://localhost:8080
