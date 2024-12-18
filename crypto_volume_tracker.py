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

app = Flask(__name__)

secret_handler = SecretHandler()

# Initialize the NotificationRegistry and other services
registry = NotificationRegistry()

# Twilio credentials (pulled from environment variables)
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

# FetchData and Notification services
fetch_data = FetchData()
notification = Notification(
    twilio_sid=TWILIO_SID,
    twilio_auth_token=TWILIO_AUTH_TOKEN,
    twilio_phone=TWILIO_PHONE,
)

# Crypto Volume Tracker Routes
def crypto_volume_tracker_routes(app):
    
    @app.route("/")
    def home():
        return jsonify({"message": "Welcome to the Crypto Volume Tracker API"}), 200

    @app.route("/track_volume", methods=["POST"])
    def track_volume():
        try:
            # Parse limit from request body or default to 1000
            request_data = request.get_json()
            limit = request_data.get("limit", 1000)

            log.info(f"Starting cryptocurrency volume tracking. Limit: {limit}")

            process = ProcessData(notification=notification)

            # Fetch top cryptocurrencies
            cryptocurrencies = fetch_data.fetch_top_cryptos(limit)
            if cryptocurrencies:
                process.process_volume_change(cryptocurrencies)
                return jsonify({"message": f"Processed volume changes for top {limit} cryptocurrencies."}), 200
            else:
                return jsonify({"error": "No cryptocurrencies fetched."}), 404

        except Exception as e:
            log.error(f"Error occurred: {e}")
            return jsonify({"error": str(e)}), 500
    
# Notification Registry Routes
def notification_routes(app):

    @app.route("/notifications", methods=["GET"])
    def notificationHome():
        return jsonify({"message": "Welcome to the Notification Registry API!"})

    @app.route("/notifications", methods=["POST"])
    def add_notification():
        data = request.get_json()
        phone = data.get("phone")
        volume_percentage = data.get("volume_percentage")
        volume_time = data.get("volume_time")

        if not all([phone, volume_percentage, volume_time]):
            return jsonify({"error": "Missing required fields: phone, volume_percentage, volume_time"}), 400

        return jsonify(*registry.add_notification(phone, float(volume_percentage), volume_time))

    @app.route("/notifications", methods=["PUT"])
    def update_notification():
        data = request.get_json()
        phone = data.get("phone")
        volume_percentage = data.get("volume_percentage")
        volume_time = data.get("volume_time")

        if not all([phone, volume_percentage, volume_time]):
            return jsonify({"error": "Missing required fields: phone, volume_percentage, volume_time"}), 400

        return jsonify(*registry.update_notification(phone, float(volume_percentage), volume_time))

    @app.route("/notifications", methods=["DELETE"])
    def delete_notification():
        data = request.get_json()
        if not data.get("phone"):
            return jsonify({"error": "Missing required field: phone"}), 400

        return jsonify(*registry.delete_notification(data.get("phone")))

if __name__ == "__main__":
    # Fetch and Populate Secrets
    secret_handler.set_secret('COINMARKET_API_KEY')
    secret_handler.set_secret('TWILIO_SID')
    secret_handler.set_secret('TWILIO_AUTH_TOKEN')
    secret_handler.set_secret_from_gcp('TWILIO_PHONE')

    # Register the routes
    crypto_volume_tracker_routes(app)
    notification_routes(app)

    app.run(host="0.0.0.0", port=8080, debug=True)
