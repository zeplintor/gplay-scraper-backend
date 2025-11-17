# 🚀 Backend Setup - PlayStore Analytics Pro

## Configuration des variables d'environnement

### 1. Créer le fichier `.env`

Copiez `.env.example` vers `.env` :

```bash
cp .env.example .env
```

### 2. Configurer les variables

Éditez `.env` et remplissez les valeurs :

```env
# Flask
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=générez-une-clé-secrète-unique-ici

# CORS
ALLOWED_ORIGINS=https://playstore-analytics.pro,https://votre-app.netlify.app

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# URLs
SUCCESS_URL=https://playstore-analytics.pro/success.html
CANCEL_URL=https://playstore-analytics.pro/pricing.html
```

### 3. Obtenir les clés Stripe

1. Allez sur [Stripe Dashboard](https://dashboard.stripe.com/apikeys)
2. Copiez votre **Secret Key** (sk_live_... ou sk_test_...)
3. Copiez votre **Publishable Key** (pk_live_... ou pk_test_...)

### 4. Configurer le Webhook Stripe

1. Allez sur [Stripe Webhooks](https://dashboard.stripe.com/webhooks)
2. Cliquez "Add endpoint"
3. URL : `https://votre-backend.onrender.com/api/webhook/stripe`
4. Événements à écouter :
   - `checkout.session.completed`
5. Copiez le **Signing secret** (whsec_...)

## Installation locale

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
python app.py
```

Le serveur démarre sur `http://localhost:5000`

## Déploiement sur Render

### Variables d'environnement à configurer

Dans Render Dashboard → Environment :

```
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=votre-secret-key
ALLOWED_ORIGINS=https://playstore-analytics.pro
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
SUCCESS_URL=https://playstore-analytics.pro/success.html
CANCEL_URL=https://playstore-analytics.pro/pricing.html
```

### Commandes Render

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

## Endpoints disponibles

### API Publics

- `GET /` - Informations API
- `GET /api/analyze/<app_id>` - Analyse complète
- `GET /api/field/<app_id>/<field>` - Champ spécifique
- `POST /api/compare` - Comparer plusieurs apps
- `POST /api/validate-license` - Valider une licence

### API Stripe

- `POST /api/create-checkout` - Créer session paiement
- `POST /api/webhook/stripe` - Webhook paiements

## Sécurité

✅ **Fichiers protégés** (dans .gitignore) :
- `.env`
- `licenses.json`
- `secrets/`

⚠️ **IMPORTANT** :
- Ne JAMAIS commit le fichier `.env`
- Ne JAMAIS exposer les clés secrètes Stripe
- Utiliser HTTPS en production
- Configurer CORS correctement

## Tests

```bash
# Tester l'endpoint d'analyse
curl https://votre-backend.onrender.com/api/analyze/com.whatsapp

# Tester la validation de licence
curl -X POST https://votre-backend.onrender.com/api/validate-license \
  -H "Content-Type: application/json" \
  -d '{"license_key": "TEST-KEY"}'
```

## Logs

Les logs sont accessibles dans Render Dashboard → Logs

## Support

- Email : hello@playstore-analytics.pro
- Issues : https://github.com/votre-username/gplay-scraper-backend/issues
