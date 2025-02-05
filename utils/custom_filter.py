from datetime import datetime, timedelta, timezone
from google.cloud import firestore
from utils.custom_logger import log

class CustomFilter:
    """
    This class handles tracking notifications and filtering out duplicate notifications
    based on a counter for each coin per phone.
    """
    def __init__(self, firestore_client: firestore.Client):
        self.firestore_client = firestore_client
        self.reset_tracker_ref = self.firestore_client.collection("reset_tracker").document("tracker")
        self.notification_tracker_ref = self.firestore_client.collection("notification_tracker")

    def check_and_reset_tracker(self):
        """
        Checks if 24 hours have passed since the last reset, and if so, resets the notification_tracker table.
        """
        reset_data = self.reset_tracker_ref.get()
        if reset_data.exists:
            last_reset = reset_data.to_dict().get("last_reset")
            if last_reset:
                time_diff = datetime.now(timezone.utc) - last_reset

                # Reset if more than 24 hours have passed
                if time_diff >= timedelta(hours=24):
                    log.info("24 hours have passed since last reset. Resetting notification_tracker table.")
                    self.reset_notification_tracker()
                    self.update_last_reset_time()
            else:
                log.warning("No last reset time found, setting it now.")
                self.update_last_reset_time()
        else:
            log.info("Reset tracker document not found. Setting last reset time now.")
            self.update_last_reset_time()

    def update_last_reset_time(self):
        """
        Updates the last reset time in the reset_tracker document.
        """
        self.reset_tracker_ref.set({
            "last_reset": datetime.now(timezone.utc)
        })

    def reset_notification_tracker(self):
        """
        Resets the notification tracker table (notification_tracker) by clearing the counters.
        """
        docs = self.notification_tracker_ref.stream()
        for doc in docs:
            self.notification_tracker_ref.document(doc.id).update({"counter": 0})
        log.info("Notification tracker reset successfully.")

    def should_send_notification(self, phone: str, coin_id: str, coin_name: str) -> bool:
        """
        Checks if a notification should be sent for the given phone number and coin.
        If the counter for notifications is less than 3, the notification is allowed.

        Args:
            phone (str): The phone number to check.
            coin_id (str): The ID of the coin to check.

        Returns:
            bool: True if the notification should be sent, False otherwise.
        """
        tracker_ref = self.firestore_client.collection("notification_tracker")
        tracker_doc = tracker_ref.document(f"{phone}_{coin_id}").get()

        if tracker_doc.exists:
            tracker_data = tracker_doc.to_dict()
            counter = tracker_data.get('counter', 0)
            if counter >= 3:
                log.info(f"Skipping notification for coinid: {coin_id} coin: {coin_name} as it has been sent 3 times already.")
                return False  # Don't send the notification
            else:
                # Increment counter
                tracker_ref.document(f"{phone}_{coin_id}").update({"counter": firestore.Increment(1)})
                return True  # Send the notification
        else:
            # If no previous entry, initialize counter
            tracker_ref.document(f"{phone}_{coin_id}").set({
                "counter": 1, "phone_number": phone, "coin_id": coin_id, "coin_name": coin_name
            })
            return True  # Send the notification
