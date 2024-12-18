#!/usr/bin/env python3

import os
import ast
from flask import Flask, request, jsonify
from crypto_notification_registry import NotificationRegistry
from fetch_data import FetchData
from notification_service import Notification
from process_data import ProcessData
from custom_logger import log
from secret_handler import SecretHandler

def create_app():
    """
    Application factory function to create and configure the Flask app
    """
    app = Flask(__name__)

    # Initialize the SecretHandler
    secret_handler = SecretHandler()

    # Fetch and Populate Secrets
    secrets_to_load = [
        'COINMARKET_API_KEY',
        'TWILIO_SID', 
        'TWILIO_AUTH_TOKEN', 
        'TWILIO_PHONE'
    ]

    # Load secrets with error handling
    for secret in secrets_to_load:
        try:
            secret_handler.set_secret(secret)
        except Exception as e:
            log.error(f"Failed to load secret {secret}: {e}")
            # Depending on criticality, you might want to exit or continue
            raise

    # Retrieve Twilio credentials from environment
    twilio_credentials = {
        'twilio_sid': os.getenv('TWILIO_SID'),
        'twilio_auth_token': os.getenv('TWILIO_AUTH_TOKEN'),
        'twilio_phone': os.getenv('TWILIO_PHONE')
    }

    # Validate Twilio credentials
    if not all(twilio_credentials.values()):
        log.error("Missing Twilio credentials")
        raise ValueError("Incomplete Twilio configuration")

    # Initialize services
    global services
    services = {
        'notification_registry': NotificationRegistry(),
        'fetch_data': FetchData(),
        'notification': Notification(**twilio_credentials)
    }

    # Register routes
    crypto_volume_tracker_routes(app)
    notification_routes(app)

    return app

# Crypto Volume Tracker Routes
def crypto_volume_tracker_routes(app):
    @app.route("/")
    def home():
        return jsonify({
            "message": "Welcome to the Crypto Volume Tracker API",
            "version": "1.0.0",
            "status": "healthy"
        }), 200

    @app.route("/track_volume", methods=["POST"])
    def track_volume():
        try:
            # Parse limit from request body or default to 1000
            request_data = request.get_json() or {}
            limit = request_data.get("limit", 1000)

            log.info(f"Starting cryptocurrency volume tracking. Limit: {limit}")

            # Use global services
            process = ProcessData(notification=services['notification'])

            # Fetch top cryptocurrencies
            cryptocurrencies = services['fetch_data'].fetch_top_cryptos(limit)
            if cryptocurrencies:
                process.process_volume_change(cryptocurrencies)
                return jsonify({
                    "message": f"Processed volume changes for top {limit} cryptocurrencies.",
                    "processed_count": len(cryptocurrencies)
                }), 200
            else:
                return jsonify({"error": "No cryptocurrencies fetched."}), 404

        except Exception as e:
            log.error(f"Volume tracking error: {e}")
            return jsonify({"error": str(e)}), 500

def notification_routes(app):
    @app.route("/notifications", methods=["GET"])
    def notification_home():
        return jsonify({
            "message": "Welcome to the Notification Registry API!",
            "available_methods": ["POST", "PUT", "DELETE"]
        })

    @app.route("/notifications", methods=["POST"])
    def add_notification():
        data = request.get_json()
        
        # Input validation
        required_fields = ["phone", "volume_percentage", "volume_time"]
        if not all(data.get(field) for field in required_fields):
            return jsonify({
                "error": f"Missing required fields: {', '.join(required_fields)}",
                "required_fields": required_fields
            }), 400

        try:
            result = services['notification_registry'].add_notification(
                data['phone'], 
                float(data['volume_percentage']), 
                data['volume_time']
            )
            return jsonify(result)
        except Exception as e:
            log.error(f"Notification registration error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/notifications", methods=["PUT"])
    def update_notification():
        data = request.get_json()
        
        # Input validation
        required_fields = ["phone", "volume_percentage", "volume_time"]
        if not all(data.get(field) for field in required_fields):
            return jsonify({
                "error": f"Missing required fields: {', '.join(required_fields)}",
                "required_fields": required_fields
            }), 400

        try:
            result = services['notification_registry'].update_notification(
                data['phone'], 
                float(data['volume_percentage']), 
                data['volume_time']
            )
            return jsonify(result)
        except Exception as e:
            log.error(f"Notification update error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/notifications", methods=["DELETE"])
    def delete_notification():
        data = request.get_json()
        
        if not data.get("phone"):
            return jsonify({
                "error": "Missing required field: phone"
            }), 400

        try:
            result = services['notification_registry'].delete_notification(
                data['phone']
            )
            return jsonify(result)
        except Exception as e:
            log.error(f"Notification deletion error: {e}")
            return jsonify({"error": str(e)}), 500

def main():
    # Set environment
    os.environ.setdefault('ENVIRONMENT', 'CLOUD')

    # Create Flask app
    app = create_app()

    # Run the application
    app.run(
        host="0.0.0.0", 
        port=int(os.getenv('PORT', 8080)), 
        debug=os.getenv('ENVIRONMENT') == 'LOCAL'
    )

if __name__ == "__main__":
    main()
