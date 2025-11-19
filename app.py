from flask import Flask, jsonify, request
from flask_cors import CORS
from gplay_scraper import GPlayScraper
import logging
import json
from datetime import datetime
import os
import secrets
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration CORS sécurisée
allowed_origins_str = os.getenv('ALLOWED_ORIGINS', '*')
if allowed_origins_str == '*':
    allowed_origins = '*'
else:
    allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',')]

CORS(app,
     resources={r"/api/*": {"origins": allowed_origins}},
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"],
     supports_credentials=True)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialiser le scraper
scraper = GPlayScraper()

# Configuration globale
LICENSE_FILE_PATH = os.getenv('LICENSE_FILE_PATH', 'licenses.json')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL', 'hello@playstore-analytics.pro')
SENDGRID_FROM_NAME = os.getenv('SENDGRID_FROM_NAME', 'PlayStore Analytics Pro')

@app.route('/', methods=['GET'])
def home():
    """Page d'accueil de l'API"""
    return jsonify({
        "message": "Google Play Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "/api/analyze/<app_id>": "Analyse complète d'une app",
            "/api/field/<app_id>/<field>": "Récupère un champ spécifique",
            "/api/compare": "Compare plusieurs apps (POST)",
            "/api/search/<app_id>": "Recherche rapide avec infos essentielles"
        }
    })

@app.route('/api/analyze/<app_id>', methods=['GET'])
def analyze_app(app_id):
    """
    Analyse complète d'une application
    Exemple: /api/analyze/com.whatsapp
    """
    try:
        logger.info(f"Analyzing app: {app_id}")
        data = scraper.analyze(app_id)
        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        logger.error(f"Error analyzing {app_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route('/api/field/<app_id>/<field>', methods=['GET'])
def get_field(app_id, field):
    """
    Récupère un champ spécifique d'une app
    Exemple: /api/field/com.whatsapp/title
    """
    try:
        logger.info(f"Getting field '{field}' for app: {app_id}")
        value = scraper.get_field(app_id, field)
        return jsonify({
            "success": True,
            "app_id": app_id,
            "field": field,
            "value": value
        })
    except Exception as e:
        logger.error(f"Error getting field {field} for {app_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route('/api/search/<app_id>', methods=['GET'])
def search_app(app_id):
    """
    Recherche rapide avec informations essentielles
    Exemple: /api/search/com.whatsapp
    """
    try:
        logger.info(f"Quick search for app: {app_id}")
        
        # Champs essentiels pour l'affichage rapide
        essential_fields = [
            "title", "developer", "genre", "score", 
            "ratings", "installs", "free", "icon",
            "summary", "contentRating"
        ]
        
        data = scraper.get_fields(app_id, essential_fields)
        
        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        logger.error(f"Error in quick search for {app_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


@app.route('/api/health', methods=['GET'])
def api_health():
    """
    Endpoint de santé utilisé pour ping / préchauffer l'API
    """
    return jsonify({
        "success": True,
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    })

@app.route('/api/compare', methods=['POST'])
def compare_apps():
    """
    Compare plusieurs applications
    Body JSON: {"app_ids": ["com.whatsapp", "com.telegram"]}
    """
    try:
        data = request.get_json()
        app_ids = data.get('app_ids', [])
        
        if not app_ids:
            return jsonify({
                "success": False,
                "error": "No app_ids provided"
            }), 400
        
        logger.info(f"Comparing apps: {app_ids}")
        
        results = []
        for app_id in app_ids:
            try:
                app_data = scraper.get_fields(app_id, [
                    "title", "developer", "score", "ratings", 
                    "installs", "realInstalls", "genre"
                ])
                app_data['app_id'] = app_id
                results.append(app_data)
            except Exception as e:
                logger.warning(f"Error getting data for {app_id}: {str(e)}")
                results.append({
                    "app_id": app_id,
                    "error": str(e)
                })
        
        return jsonify({
            "success": True,
            "data": results
        })
    except Exception as e:
        logger.error(f"Error comparing apps: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.route('/api/metrics/<app_id>', methods=['GET'])
def get_metrics(app_id):
    """
    Récupère uniquement les métriques importantes
    Exemple: /api/metrics/com.whatsapp
    """
    try:
        logger.info(f"Getting metrics for app: {app_id}")
        
        metrics_fields = [
            "score", "ratings", "reviews", "installs",
            "realInstalls", "dailyInstalls", "monthlyInstalls",
            "histogram"
        ]
        
        data = scraper.get_fields(app_id, metrics_fields)
        
        return jsonify({
            "success": True,
            "app_id": app_id,
            "metrics": data
        })
    except Exception as e:
        logger.error(f"Error getting metrics for {app_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


def load_licenses():
    """
    Charge les licences depuis le fichier licenses.json.
    Retourne une liste de licences ou une liste vide en cas d'erreur.
    """
    try:
        with open(LICENSE_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('licenses', [])
    except Exception as e:
        logger.error(f"Error loading licenses: {str(e)}")
        return []


def write_licenses(licenses):
    """
    Sauvegarde la liste des licences dans le fichier JSON
    """
    try:
        with open(LICENSE_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump({'licenses': licenses}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error writing licenses: {str(e)}")
        return False


def generate_license_key():
    """
    Génère une clé du type PSAP-XXXX-XXXX-XXXX-XXXX en évitant les caractères ambigus
    """
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    parts = [''.join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
    return 'PSAP-' + '-'.join(parts)


def get_or_create_license(email, plan='premium'):
    """
    Retourne une licence active pour l'email ou en crée une nouvelle
    """
    if not email:
        return None, False

    normalized_email = email.strip().lower()
    licenses = load_licenses()

    existing_license = next(
        (lic for lic in licenses
         if lic.get('email', '').lower() == normalized_email and lic.get('status') == 'active'),
        None
    )

    if existing_license:
        return existing_license, False

    # Générer une nouvelle clé unique
    existing_keys = {lic.get('key') for lic in licenses}
    new_key = generate_license_key()
    attempts = 0
    while new_key in existing_keys and attempts < 10:
        new_key = generate_license_key()
        attempts += 1

    license_entry = {
        'key': new_key,
        'email': normalized_email,
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'expires_at': None,
        'status': 'active',
        'plan': plan,
        'notes': 'Généré automatiquement via Stripe'
    }

    licenses.append(license_entry)
    write_licenses(licenses)
    return license_entry, True


def send_license_email(email, license_key, plan='premium', amount=None, currency='EUR'):
    """
    Envoie la clé de licence par email via SendGrid
    """
    if not SENDGRID_API_KEY:
        logger.warning('SENDGRID_API_KEY manquant : impossible d\'envoyer l’email de licence')
        return False

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        price_line = ''
        if amount:
            price_line = f"<p><strong>Montant :</strong> {amount:.2f} {currency.upper()}</p>"

        html_content = f"""
            <p>Bonjour 👋</p>
            <p>Merci d'avoir rejoint PlayStore Analytics Pro. Voici votre clé de licence {plan.title()} :</p>
            <p style="font-size:18px;font-weight:bold;background:#f3f4f6;padding:12px 16px;border-radius:8px;font-family:monospace;">
                {license_key}
            </p>
            {price_line}
            <p>👉 Activez-la depuis la page premium : https://playstore-analytics.pro/premium.html</p>
            <p>Une question ? hello@playstore-analytics.pro</p>
            <p>Merci,<br>{SENDGRID_FROM_NAME}</p>
        """

        message = Mail(
            from_email=(SENDGRID_FROM_EMAIL, SENDGRID_FROM_NAME),
            to_emails=email,
            subject='Votre clé PlayStore Analytics Pro',
            html_content=html_content
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f'SendGrid response: {response.status_code}')
        return response.status_code in (200, 201, 202)

    except Exception as e:
        logger.error(f'Error sending license email: {str(e)}')
        return False


def deliver_license(email, plan='premium', amount=None, currency='EUR', force_email=False):
    """
    Crée (ou récupère) une licence et tente d'envoyer l'email associé
    """
    license_entry, created = get_or_create_license(email, plan=plan)
    if not license_entry:
        return None, False

    if created or force_email:
        send_license_email(
            email=email,
            license_key=license_entry['key'],
            plan=plan,
            amount=amount,
            currency=currency
        )

    logger.info(f"License {'created' if created else 'reused'} for {email}")
    return license_entry, created


def is_license_expired(expires_at):
    """
    Vérifie si une licence est expirée à partir de sa date ISO.
    """
    if not expires_at:
        return False
    try:
        exp_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return exp_date < datetime.now(exp_date.tzinfo)
    except Exception:
        return False


@app.route('/api/validate-license', methods=['POST', 'OPTIONS'])
def validate_license():
    """
    Endpoint de validation des licences.
    """
    if request.method == 'OPTIONS':
        return '', 204

    data = request.get_json() or {}
    key = data.get('key', '').strip().upper()

    if not key:
        return jsonify({
            'success': False,
            'valid': False,
            'message': 'Clé requise'
        }), 400

    licenses = load_licenses()
    license_found = next(
        (lic for lic in licenses if lic.get('key', '').upper() == key),
        None
    )

    if not license_found:
        return jsonify({
            'success': True,
            'valid': False,
            'message': 'Clé invalide'
        })

    if license_found.get('status') != 'active':
        return jsonify({
            'success': True,
            'valid': False,
            'message': f"Licence {license_found.get('status')}"
        })

    if is_license_expired(license_found.get('expires_at')):
        return jsonify({
            'success': True,
            'valid': False,
            'message': 'Licence expirée'
        })

    return jsonify({
        'success': True,
        'valid': True,
        'message': 'Licence valide',
        'data': {
            'email': license_found.get('email'),
            'created_at': license_found.get('created_at'),
            'expires_at': license_found.get('expires_at'),
            'plan': license_found.get('plan', 'premium')
        }
    })


@app.route('/api/create-checkout', methods=['POST', 'OPTIONS'])
def create_checkout():
    """
    Crée une session Stripe Checkout pour acheter une licence Premium
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        import stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

        data = request.get_json() or {}
        email = data.get('email', '')
        plan = (data.get('plan') or 'premium').lower()

        # Créer une session Checkout
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'PlayStore Analytics Pro - Licence Premium',
                        'description': 'Analyses illimitées à vie + Exports PDF + 65+ métriques avancées',
                        'images': ['https://playstore-analytics.pro/assets/og-image.jpg'],
                    },
                    'unit_amount': 999,  # 9.99 EUR en centimes
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=os.getenv('SUCCESS_URL', 'https://playstore-analytics.pro/success.html') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=os.getenv('CANCEL_URL', 'https://playstore-analytics.pro/pricing.html'),
            customer_email=email,
            metadata={
                'product': 'premium_license',
                'plan': plan,
                'email': email
            }
        )

        return jsonify({
            'success': True,
            'sessionId': checkout_session.id,
            'url': checkout_session.url
        })

    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/checkout-status/<session_id>', methods=['GET'])
def get_checkout_status(session_id):
    """
    Récupère les informations d'une session Stripe Checkout après paiement
    """
    try:
        import stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

        session = stripe.checkout.Session.retrieve(session_id)
        amount_total = (session.amount_total or 0) / 100  # Stripe renvoie en centimes
        currency = (session.currency or 'eur').upper()

        customer_email = session.customer_email
        customer_details = getattr(session, 'customer_details', None)
        if not customer_email and customer_details:
            customer_email = customer_details.get('email')

        license_entry = None
        license_created = False

        if session.payment_status == 'paid' and customer_email:
            metadata = session.get('metadata', {}) or {}
            plan = metadata.get('plan', 'premium')
            license_entry, license_created = deliver_license(
                email=customer_email,
                plan=plan,
                amount=amount_total,
                currency=currency
            )

        return jsonify({
            'success': True,
            'session_id': session.id,
            'status': session.payment_status,
            'amount_total': amount_total,
            'currency': currency,
            'customer_email': customer_email,
            'license_key': license_entry.get('key') if license_entry else None,
            'license_created': license_created
        })

    except Exception as e:
        logger.error(f"Error retrieving checkout session {session_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Session introuvable'
        }), 400


@app.route('/api/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """
    Webhook pour recevoir les événements Stripe (paiements réussis, etc.)
    """
    try:
        import stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

        payload = request.data
        sig_header = request.headers.get('Stripe-Signature')
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )

        # Gérer l'événement de paiement réussi
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']

            # Créer automatiquement une licence
            email = session.get('customer_email')
            if email:
                metadata = session.get('metadata', {}) or {}
                plan = metadata.get('plan', 'premium')
                amount_total = (session.get('amount_total') or 0) / 100
                currency = (session.get('currency') or 'eur').upper()
                deliver_license(
                    email,
                    plan=plan,
                    amount=amount_total,
                    currency=currency,
                    force_email=True
                )
            else:
                logger.warning('Stripe session completed without customer_email')

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False') == 'True'
    app.run(debug=debug, host='0.0.0.0', port=port)
