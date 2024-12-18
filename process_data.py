import json
import re
import redis
from typing import List, Dict
from notification_service import Notification
from custom_logger import log

class ProcessData:
    """
    Handles processing of cryptocurrency volume data, now integrated with Redis and notifications.
    """
    def __init__(self, notification: Notification):
        self.notification = notification
        self.redis_client = redis.StrictRedis(host='127.0.0.1', port=6379, db=0, decode_responses=True)

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
        keys = self.redis_client.keys("*")

        phone_pattern = r"^\+\d{10,15}$"
        notifications = []

        for phone in keys:
            if re.match(phone_pattern, phone):
                try:
                    preferences = json.loads(self.redis_client.get(phone))

                    for pref in preferences:
                        volume_time = pref['volume_time']
                        volume_percentage = pref['volume_percentage'] / 100
                        
                        redis_key = f"{volume_time}"  # Use the time window as the Redis key
                        for coin in new_data:
                            coin_id = coin['id']
                            coin_name = coin['name']
                            symbol = coin['symbol']
                            volume = self.calculate_volume(total_volume=coin['quote']['USD']['volume_24h'], volume_time=volume_time)

                            # Retrieve previous volume for this coin and time window
                            prev_volume = self.redis_client.hget(redis_key, coin_id)
                            if prev_volume:
                                prev_volume = float(prev_volume)

                                # Check for positive volume change > specified percentage
                                if prev_volume > 0 and (volume - prev_volume) / prev_volume > volume_percentage:
                                    notifications.append(
                                        f"🚀 {coin_name} ({symbol}): {volume_percentage * 100}% increase over {volume_time}"
                                    )

                            # Update Redis hash with the new volume
                            self.redis_client.hset(redis_key, coin_id, volume)


                except redis.RedisError as e:
                    log.error(f"Redis error while processing phone {phone}: {e}")
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
                        bulk_message = bulk_message[:1600]  # Truncate to max length

                    self.notification.send_bulk_sms(bulk_message, phone=phone)
