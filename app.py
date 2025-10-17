from flask import Flask, jsonify, request
from flask_cors import CORS
from gplay_scraper import GPlayScraper
import logging
import json
import os
import stripe
import secrets
import string
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Permet les requêtes depuis Netlify

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialiser le scraper
scraper = GPlayScraper()

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
        with open('licenses.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('licenses', [])
    except Exception:
        return []


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


# ============================================
# STRIPE PAYMENT INTEGRATION
# ============================================

# Configuration Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://votre-site.netlify.app')

# Prix des plans (en centimes)
PRICING = {
    'premium': {
        'amount': 999,  # 9,99€
        'currency': 'eur',
        'name': 'PlayStore Analytics Pro - Premium',
        'description': 'Analyses illimitées • 65+ métriques • Export PDF • Support prioritaire'
    }
}


def generate_license_key():
    """Génère une clé de licence au format PSAP-XXXX-XXXX-XXXX-XXXX"""
    parts = []
    for _ in range(4):
        part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        parts.append(part)
    return f"PSAP-{'-'.join(parts)}"


def save_license_to_file(license_key, email, plan='premium'):
    """Enregistre une nouvelle licence dans licenses.json"""
    try:
        with open('licenses.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        new_license = {
            'key': license_key,
            'email': email,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'expires_at': None,
            'status': 'active',
            'plan': plan,
            'notes': f'Achat Stripe le {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}'
        }

        data['licenses'].append(new_license)

        with open('licenses.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"License created: {license_key[:9]}...{license_key[-4:]} for {email}")
        return True

    except Exception as e:
        logger.error(f"Error saving license: {str(e)}")
        return False


def send_license_email(email, license_key):
    """Envoie un email avec la clé de licence (actuellement log seulement)"""
    email_body = f"""
Bonjour,

Merci d'avoir acheté PlayStore Analytics Pro Premium !

Voici votre clé de licence :

{license_key}

Pour l'activer :
1. Rendez-vous sur {FRONTEND_URL}/premium.html
2. Cliquez sur "Gérer la licence"
3. Entrez votre clé de licence
4. Profitez de toutes les fonctionnalités Premium !

Besoin d'aide ? Contactez-nous à hello@playstore-analytics.pro

L'équipe PlayStore Analytics Pro
    """

    logger.info(f"EMAIL TO SEND to {email}:")
    logger.info(f"Subject: Votre licence PlayStore Analytics Pro Premium")
    logger.info(email_body)

    # TODO: Intégrer SendGrid ou SMTP pour envoi réel d'email
    return True


@app.route('/api/create-checkout', methods=['POST'])
def create_checkout_session():
    """Crée une session Stripe Checkout pour un achat Premium"""
    try:
        data = request.get_json() or {}
        plan = data.get('plan', 'premium')
        customer_email = data.get('email', None)

        if plan not in PRICING:
            return jsonify({'error': 'Plan invalide'}), 400

        plan_info = PRICING[plan]

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': plan_info['currency'],
                    'product_data': {
                        'name': plan_info['name'],
                        'description': plan_info['description'],
                    },
                    'unit_amount': plan_info['amount'],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{FRONTEND_URL}/success.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/pricing.html?canceled=true",
            customer_email=customer_email,
            metadata={'plan': plan}
        )

        logger.info(f"Checkout session created: {checkout_session.id}")

        return jsonify({
            'success': True,
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id
        })

    except Exception as e:
        logger.error(f"Error creating checkout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Webhook Stripe : génère automatiquement une licence après paiement"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return jsonify({'error': 'Invalid payload'}), 400
    except Exception as e:
        logger.error(f"Invalid signature: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get('customer_email') or session.get('customer_details', {}).get('email')
        plan = session.get('metadata', {}).get('plan', 'premium')

        if not customer_email:
            logger.error("No customer email in Stripe session")
            return jsonify({'error': 'No email'}), 400

        license_key = generate_license_key()
        success = save_license_to_file(license_key, customer_email, plan)

        if success:
            send_license_email(customer_email, license_key)
            logger.info(f"Payment successful for {customer_email} - License: {license_key}")
            return jsonify({'success': True, 'message': 'License created and sent'})
        else:
            logger.error(f"Failed to save license for {customer_email}")
            return jsonify({'error': 'Failed to save license'}), 500

    elif event['type'] == 'payment_intent.payment_failed':
        logger.warning(f"Payment failed: {event['data']['object']}")

    return jsonify({'success': True})


@app.route('/api/checkout-status/<session_id>', methods=['GET'])
def checkout_status(session_id):
    """Vérifie le statut d'une session Stripe Checkout"""
    try:
        session = stripe.checkout.Session.retrieve(session_id)

        return jsonify({
            'success': True,
            'status': session.payment_status,
            'customer_email': session.customer_email or session.customer_details.get('email'),
            'amount_total': session.amount_total / 100,
            'currency': session.currency
        })

    except Exception as e:
        logger.error(f"Error retrieving session: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
