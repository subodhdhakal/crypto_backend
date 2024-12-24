import json
import re
from typing import List, Dict
from notification_service import Notification
from google.cloud import firestore
from custom_logger import log

class ProcessData:
    """
    Handles processing of cryptocurrency volume data, now integrated with Redis and notifications.
    """
    def __init__(self, notification: Notification):
        self.notification = notification
        self.firestore_client = firestore.Client(project='crypto-volume-change-tracker', database='crypto-backend-db')

        # Map time windows to their divisors
        self.time_window_divisors = {
            "1min": 24 * 60,
            "3min": 24 * 20,
            "5min": 24 * 12,
            "15min": 24 * 4,
            "30min": 48,
            "1hr": 24,
            "4hr": 6,
            "24hr": 1,
        }
        self.market_cap_min_usd = 10000000 # $10 million USD
        self.twentyfourhr_volume_min_usd = 300000 # $300k USD

    def calculate_volume(self, total_volume: float, volume_time: str) -> float:
        """
        Calculate volume based on the specified time window.

        Args:
            total_volume (float): The 24-hour total volume.

        Returns:
            float: The calculated volume for the given time window.
        """
        divisor = self.time_window_divisors.get(volume_time)
        if divisor is None:
            log.error(f"Unsupported volume time: {volume_time}")
            raise ValueError(f"Unsupported volume time: {volume_time}")
        return total_volume / divisor

    def process_volume_change(self, new_data: List[Dict]):
        """
        Processes the volume data and checks for significant positive changes.

        Args:
            new_data (List[Dict]): Latest cryptocurrency data.
        """
        notifications = []

        # Retrieve notification registry info
        preferences_ref = self.firestore_client.collection('notification_preferences')

        for doc in preferences_ref.stream():
            phone = doc.id
            try:
                # Get preferences for the current phone number
                preferences_data = doc.to_dict()
                log.info(preferences_data)
                preferences = preferences_data.get("preferences", [])

                # Ensure preferences is a list
                if not isinstance(preferences, list):
                    log.error(f"Invalid preferences format for phone {phone}: {preferences_data}")
                    continue

                for pref in preferences:
                    volume_time = pref['volume_time']
                    volume_percentage = pref['volume_percentage'] / 100

                    if not volume_time or not isinstance(volume_time, str):
                        log.error(f"Missing or invalid volume_time for phone {phone}: {pref}")
                        continue

                    if volume_percentage is None or not isinstance(volume_percentage, (int, float)):
                        log.error(f"Missing or invalid volume_percentage for phone {phone}: {pref}")
                        continue
                    
                    volume_doc = self.firestore_client.collection("volume_by_timeline").document(volume_time).get()
                    volume_data = volume_doc.to_dict() if volume_doc.exists else {}

                    for coin in new_data:
                        coin_id = str(coin['id'])
                        coin_name = coin['name']
                        symbol = coin['symbol']
                        volume = self.calculate_volume(total_volume=coin['quote']['USD']['volume_24h'], volume_time=volume_time)
                        market_cap = coin['quote']['USD']['market_cap']
                        current_price = coin['quote']['USD']['price']

                        if float(market_cap) < self.market_cap_min_usd or float(volume) < self.twentyfourhr_volume_min_usd:
                            log.info(f"Skipping {coin_name} ({symbol}) due to low market cap or volume")
                            continue

                        # Retrieve previous volume for this coin and time window
                        prev_data = volume_data.get(coin_id)
                        if prev_data:
                            prev_volume, prev_price = float(prev_data['volume']), float(prev_data['price'])

                            volume_change = (volume - prev_volume) / prev_volume if prev_volume > 0 else 0
                            
                            # Check for positive volume change > specified percentage
                            if volume_change > volume_percentage and current_price > prev_price:
                                notifications.append(
                                    f"🚀 {coin_name} ({symbol}): {volume_percentage * 100}% increase over {volume_time}. Curr Price: {current_price}"
                                )

                        # Update Firestore with the new volume
                        volume_data[coin_id] = {'volume': volume, 'price': current_price}

                # Update Firestore with the new volume
                try:
                    self.firestore_client.collection("volume_by_timeline").document(volume_time).set(volume_data)
                except Exception as e:
                    log.error(f"Error updating Firestore for volume_time {volume_time}: {str(e)}")

            except Exception as e:
                log.error(f"Error processing preferences for phone {phone}: {e}")

            # Send bulk SMS if there are notifications
            if notifications:
                bulk_message = (
                    "🚀 Positive Volume Changes Detected 🚀:\n\n"
                    + "\n".join(notifications)
                )
                log.info(f"Sending bulk SMS Notification: {bulk_message} {len(bulk_message)}")

                encoded_message = bulk_message.encode('utf-8')
                if len(encoded_message) > 1600:
                    log.info("Truncating the bulked SMS message since it is greater than the threshold")
                    truncated_message = encoded_message[:1599].decode('utf-8', errors='ignore') # Truncate to 1600
                    bulk_message = truncated_message
                    log.info(f"Truncated message length: {len(bulk_message.encode('utf-8'))}")

                self.notification.send_bulk_sms(bulk_message, phone=phone)
            else:
                log.info("No positive volume detected for given threshold")
