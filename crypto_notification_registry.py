from custom_logger import log
from google.cloud import firestore

class NotificationRegistry:
    def __init__(self):
        # Initialize Firestore client
        self.firestore_client = firestore.Client(project='crypto-volume-change-tracker', database='crypto-backend-db')
        self.collection_name = "notification_preferences"

    def add_notification(self, phone: str, volume_percentage: float, volume_time: str):
        doc_ref = self.firestore_client.collection(self.collection_name).document(phone)
        doc = doc_ref.get()

        preferences = doc.to_dict().get("preferences", []) if doc.exists else []

        new_entry = {"volume_percentage": volume_percentage, "volume_time": volume_time}
        if new_entry not in preferences:
            preferences.append(new_entry)
            doc_ref.set({"preferences": preferences})
            log.info(f"Added notification preference for phone: {phone}: {new_entry}")
            return {"message": "Notification preference added.", "data": new_entry}, 201
        else:
            log.warning(f"Entry already exists for phone {phone}: {new_entry}")
            return {"message": "Entry already exists.", "data": new_entry}, 409

    def update_notification(self, phone: str, volume_percentage: float, volume_time: str):
        doc_ref = self.firestore_client.collection(self.collection_name).document(phone)
        doc = doc_ref.get()

        if doc.exists:
            new_preferences = [{"volume_percentage": volume_percentage, "volume_time": volume_time}]
            doc_ref.set({"preferences": new_preferences})
            log.info(f"Updated notification preferences for phone {phone}: {new_preferences}")
            return {"message": "Notification preferences updated.", "data": new_preferences}, 200
        else:
            log.warning(f"No existing notification preferences found for phone {phone}.")
            return {"message": "No existing preferences found.", "phone": phone}, 404

    def delete_notification(self, phone: str):
        doc_ref = self.firestore_client.collection(self.collection_name).document(phone)
        doc = doc_ref.get()

        if doc.exists:
            doc_ref.delete()
            log.info(f"Deleted notification preferences for phone {phone}.")
            return {"message": "Notification preferences deleted.", "phone": phone}, 200
        else:
            log.warning(f"No notification preferences found for phone {phone} to delete.")
            return {"message": "No preferences found to delete.", "phone": phone}, 404
