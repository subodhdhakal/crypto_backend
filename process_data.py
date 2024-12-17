import redis
from typing import List, Dict
from notification_service import Notification
from custom_logger import log

class ProcessData:
    """
    Handles processing of cryptocurrency volume data, now integrated with Redis and notifications.
    """
    def __init__(self, volume_time: str, volume_percentage: float, notification: Notification):
        self.volume_time = volume_time
        self.volume_percentage = volume_percentage / 100
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

    def calculate_volume(self, total_volume: float) -> float:
        """
        Calculate volume based on the specified time window.

        Args:
            total_volume (float): The 24-hour total volume.

        Returns:
            float: The calculated volume for the given time window.
        """
        divisor = self.time_window_divisors.get(self.volume_time)
        if divisor is None:
            log.error(f"Unsupported volume time: {self.volume_time}")
            raise ValueError(f"Unsupported volume time: {self.volume_time}")
        return total_volume / divisor

    def process_volume_change(self, new_data: List[Dict]):
        """
        Processes the volume data and checks for significant positive changes.

        Args:
            new_data (List[Dict]): Latest cryptocurrency data.
        """
        redis_key = f"{self.volume_time}"  # Use the time window as the Redis key
        notifications = []

        for coin in new_data:
            coin_id = coin['id']
            coin_name = coin['name']
            symbol = coin['symbol']
            volume = self.calculate_volume(coin['quote']['USD']['volume_24h'])

            try:
                # Retrieve previous volume for this coin and time window
                prev_volume = self.redis_client.hget(redis_key, coin_id)
                if prev_volume:
                    prev_volume = float(prev_volume)

                    # Check for positive volume change > specified percentage
                    if prev_volume > 0 and (volume - prev_volume) / prev_volume > self.volume_percentage:
                        notifications.append(
                            f"🚀 {coin_name} ({symbol}): {self.volume_percentage * 100}% increase over {self.volume_time}"
                        )
                        # log.info(f"Positive volume change detected for {coin_name} ({symbol}).")

                # Update Redis hash with the new volume
                self.redis_client.hset(redis_key, coin_id, volume)
            except redis.RedisError as e:
                log.error(f"Redis error while processing coin {coin_id}: {e}")

        # Send bulk SMS if there are notifications
        if notifications:
            bulk_message = (
                "🚀Positive Volume Changes Detected 🚀:\n\n"
                + "\n".join(notifications)
            )
            log.info(f"Sending bulk SMS Notificaiton: {bulk_message} {len(bulk_message)}")

            if len(bulk_message) > 1600:
                log.info("Truncating the bulked SMS message since it is greater than the threshold")
            max_length = 1600
            bulk_message = bulk_message[:max_length]
            self.notification.send_bulk_sms(bulk_message)

        # Set Redis key expiry to 1 day
        try:
            self.redis_client.expire(redis_key, 86400)
        except redis.RedisError as e:
            log.error(f"Failed to set expiry for Redis key {redis_key}: {e}")
