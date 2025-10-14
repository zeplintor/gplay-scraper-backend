from flask import Flask, jsonify, request
from flask_cors import CORS
from gplay_scraper import GPlayScraper
import logging

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
