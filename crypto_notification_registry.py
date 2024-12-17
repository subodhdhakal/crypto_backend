import argparse
import redis
import json
from custom_logger import log

class NotificationRegistry:
    def __init__(self):
        self.redis_client = redis.StrictRedis(host='127.0.0.1', port=6379, db=0, decode_responses=True)

    def add_notification(self, phone: str, volume_percentage: float, volume_time: str):
        """
        Adds or updates a notification preference for a given phone number.
        Args:
            phone (str): Phone number as the key.
            volume_percentage (float): The volume change percentage.
            volume_time (str): The time window for volume tracking.
        """
        # Check if the phone already has existing preferences
        existing_data = self.redis_client.get(phone)
        if existing_data:
            preferences = json.loads(existing_data)
        else:
            preferences = []

        # Avoid duplicate entries for the same volume_percentage and volume_time
        new_entry = {"volume_percentage": volume_percentage, "volume_time": volume_time}
        if new_entry not in preferences:
            preferences.append(new_entry)
            self.redis_client.set(phone, json.dumps(preferences))
            log.info(f"Added preferences to DB for phone {phone}: {new_entry}")
        else:
            log.warning(f"Entry already exists for phone {phone}: {new_entry}")

    def update_notification(self, phone: str, volume_percentage: float, volume_time: str):
        """
        Updates notification preferences for a given phone number.
        Args:
            phone (str): Phone number as the key.
            volume_percentage (float): The new volume change percentage.
            volume_time (str): The new time window for volume tracking.
        """
        if self.redis_client.exists(phone):
            new_preferences = [{"volume_percentage": volume_percentage, "volume_time": volume_time}]
            self.redis_client.set(phone, json.dumps(new_preferences))
            log.info(f"Updated preferences for phone {phone}: {new_preferences}")
        else:
            log.warning(f"No existing preferences found for phone {phone}. Use ADD to create a new entry.")

    def delete_notification(self, phone: str):
        """
        Deletes notification preferences for a given phone number.
        Args:
            phone (str): Phone number as the key.
        """
        if self.redis_client.delete(phone):
            log.info(f"Deleted preferences for phone {phone}.")
        else:
            log.warning(f"No preferences found for phone {phone} to delete.")

    def process_operation(self, operation: str, phone: str, volume_percentage: float = None, volume_time: str = None):
        """
        Processes the specified operation (ADD, UPDATE, DELETE).
        """
        if operation == "ADD" and volume_percentage and volume_time:
            self.add_notification(phone, volume_percentage, volume_time)
        elif operation == "UPDATE" and volume_percentage and volume_time:
            self.update_notification(phone, volume_percentage, volume_time)
        elif operation == "DELETE":
            self.delete_notification(phone)
        else:
            log.error("Invalid operation or missing arguments.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crypto Notification Registry")
    parser.add_argument("--phone", type=str, required=True, help="Phone number (key in Redis)")
    parser.add_argument("--volume-percentage", type=float, help="Volume change percentage")
    parser.add_argument("--volume-time", type=str, help="Volume time window (e.g., 1min, 5min)")
    parser.add_argument("--operation", type=str, required=True, choices=["ADD", "UPDATE", "DELETE"],
                        help="Operation to perform: ADD, UPDATE, DELETE")

    args = parser.parse_args()

    registry = NotificationRegistry()
    registry.process_operation(
        operation=args.operation,
        phone=args.phone,
        volume_percentage=args.volume_percentage,
        volume_time=args.volume_time
    )
