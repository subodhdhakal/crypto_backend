import redis
import json
from custom_logger import log

class NotificationRegistry:
    def __init__(self):
        self.redis_client = redis.StrictRedis(host='10.207.168.59', port=6379, db=0, decode_responses=True)

    def add_notification(self, phone: str, volume_percentage: float, volume_time: str):
        existing_data = self.redis_client.get(phone)
        preferences = json.loads(existing_data) if existing_data else []

        new_entry = {"volume_percentage": volume_percentage, "volume_time": volume_time}
        if new_entry not in preferences:
            preferences.append(new_entry)
            self.redis_client.set(phone, json.dumps(preferences))
            log.info(f"Added notification preference for phone: {phone}: {new_entry}")
            return {"message": "Notification preference added.", "data": new_entry}, 201
        else:
            log.warning(f"Entry already exists for phone {phone}: {new_entry}")
            return {"message": "Entry already exists.", "data": new_entry}, 409

    def update_notification(self, phone: str, volume_percentage: float, volume_time: str):
        if self.redis_client.exists(phone):
            new_preferences = [{"volume_percentage": volume_percentage, "volume_time": volume_time}]
            self.redis_client.set(phone, json.dumps(new_preferences))
            log.info(f"Updated notification preferences for phone {phone}: {new_preferences}")
            return {"message": "Notification preferences updated.", "data": new_preferences}, 200
        else:
            log.warning(f"No existing notification preferences found for phone {phone}.")
            return {"message": "No existing preferences found.", "phone": phone}, 404

    def delete_notification(self, phone: str):
        if self.redis_client.delete(phone):
            log.info(f"Deleted notification preferences for phone {phone}.")
            return {"message": "Notification preferences deleted.", "phone": phone}, 200
        else:
            log.warning(f"No notification preferences found for phone {phone} to delete.")
            return {"message": "No preferences found to delete.", "phone": phone}, 404
