# leylay — backend yt-dlp

Backend Flask + yt-dlp pour le frontend leylay.  
Déployable gratuitement sur **Railway** ou **Render**.

---

## 📁 Structure

```
leylay-backend/
├── app.py            ← Le serveur Flask
├── requirements.txt  ← Dépendances Python
├── Procfile          ← Commande de démarrage
├── railway.toml      ← Config Railway
├── render.yaml       ← Config Render
└── leylay.html       ← Ton frontend (à héberger séparément)
```

---

## 🚀 Déploiement sur Railway (recommandé)

### Étape 1 — Crée un compte
→ https://railway.app (connexion avec GitHub)

### Étape 2 — Nouveau projet
1. Clique **"New Project"**
2. Choisis **"Deploy from GitHub repo"**
3. Push ce dossier sur GitHub d'abord (voir plus bas), puis sélectionne le repo

### Étape 3 — Variables d'environnement
Dans Railway → ton service → **Variables** :
```
PORT = 5000
```
(Railway injecte automatiquement `PORT`, mais c'est bien de le définir)

### Étape 4 — Récupère ton URL
Une fois déployé, Railway te donne une URL publique du type :
```
https://leylay-backend-production.up.railway.app
```

### Étape 5 — Met à jour le frontend
Dans `leylay.html`, ligne :
```javascript
const BACKEND = "https://TON-BACKEND.up.railway.app";
```
Remplace par ton URL Railway.

---

## 🚀 Déploiement sur Render (alternative)

### Étape 1
→ https://render.com (connexion avec GitHub)

### Étape 2
1. **"New Web Service"**
2. Connecte ton repo GitHub
3. Render détecte automatiquement `render.yaml`

### Étape 3
Ton URL sera du type :
```
https://leylay-backend.onrender.com
```
⚠️ Sur Render gratuit, le serveur "dort" après 15min d'inactivité.  
Le premier appel peut prendre ~30 secondes. Railway est plus réactif.

---

## 📤 Pousser sur GitHub

```bash
cd leylay-backend
git init
git add .
git commit -m "leylay backend"
git branch -M main
git remote add origin https://github.com/TON-USERNAME/leylay-backend.git
git push -u origin main
```

---

## 🔌 API Endpoints

### `GET /`
Health check — vérifie que le serveur tourne.

### `POST /info`
Retourne les métadonnées et formats disponibles.
```json
{ "url": "https://youtube.com/watch?v=..." }
```

### `POST /download`
Télécharge et renvoie le fichier directement.
```json
{
  "url": "https://youtube.com/watch?v=...",
  "mode": "auto",        // "auto" | "audio" | "mute"
  "format_id": "137+140" // optionnel, vient du /info
}
```

---

## 🛠️ Test en local

```bash
pip install -r requirements.txt
python app.py
```
Serveur disponible sur http://localhost:5000
