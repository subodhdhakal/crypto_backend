from datetime import datetime, timedelta, timezone
from typing import List, Dict
from CustomFilter import CustomFilter
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
        self.custom_filter = CustomFilter(self.firestore_client)

        self.market_cap_min_usd = 10000000 # $10 million USD
        self.twentyfourhr_volume_min_usd = 300000 # $300k USD

    def process_volume_change(self, new_data: List[Dict]):
        """
        Processes the volume data and checks for significant positive changes.

        Args:
            new_data (List[Dict]): Latest cryptocurrency data.
        """
        # First, check and reset tracker if needed
        self.custom_filter.check_and_reset_tracker()

        notifications = []

        sent_notifications = set()

        # Retrieve notification registry info
        preferences_ref = self.firestore_client.collection('notification_preferences')

        # Get the current UTC time
        utc_now = datetime.now(timezone.utc)
        log.info(f"Current UTC time: {utc_now}")

        # Check if we're within the reset time range (00:00 to 00:20 UTC)
        reset_time_start = datetime(utc_now.year, utc_now.month, utc_now.day, 0, 0, 0, tzinfo=timezone.utc)
        reset_time_end = reset_time_start + timedelta(minutes=20)

        # If current time is after 00:20, calculate the time remaining to the next reset (00:00 UTC the next day)
        if utc_now > reset_time_end:
            # The next reset time is the next day at 00:00 UTC
            reset_time_start = datetime(utc_now.year + (1 if utc_now.month == 12 and utc_now.day == 31 else 0),
                                 utc_now.month, utc_now.day + (1 if utc_now.hour >= 20 else 0), 0, 0, 0, tzinfo=timezone.utc)
            reset_time_end = reset_time_start + timedelta(minutes=20)
        time_until_reset = reset_time_start - utc_now

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
                        current_volume = coin['quote']['USD']['volume_24h']
                        market_cap = coin['quote']['USD']['market_cap']
                        current_price = coin['quote']['USD']['price']

                        # Reset initial 24-hour volume if within the reset time
                        if reset_time_start <= utc_now <= reset_time_end:
                            volume_data[coin_id] = {'initial_24hr_volume': current_volume, 'price': current_price}
                            log.info(f"Reset initial volume for {coin_name} ({symbol}) to {current_volume} at time: {utc_now}")
                            continue
                        else:
                            # Log the time remaining until the next reset (00:00 to 00:20 UTC)
                            hours, remainder = divmod(time_until_reset.seconds, 3600)
                            minutes, _ = divmod(remainder, 60)
                            log.info(f"No reset, initial 24hr volume resets in {hours} hrs {minutes} mins")

                        if float(market_cap) < self.market_cap_min_usd or float(current_volume) < self.twentyfourhr_volume_min_usd:
                            log.info(f"Skipping {coin_name} ({symbol}) due to low market cap or volume")
                            continue

                        # Retrieve initial 24-hour volume from DB
                        prev_data = volume_data.get(coin_id)
                        if prev_data and 'initial_24hr_volume' in prev_data and 'price' in prev_data:
                            prev_volume, prev_price = float(prev_data['initial_24hr_volume']), float(prev_data['price'])

                            volume_change = (current_volume - prev_volume) / prev_volume if prev_volume > 0 else 0
                            
                            # Check for positive volume change > specified percentage
                            if volume_change > volume_percentage and current_price > prev_price:
                                if self.custom_filter.should_send_notification(phone, coin_id, coin_name=coin_name):
                                    if coin_id not in sent_notifications:
                                        sent_notifications.add(coin_id)
                                        notifications.append(
                                            f"🚀 {coin_name} ({symbol}): {round(volume_change * 100, 2)}% increase over {volume_time}. Curr Price: {round(current_price, 7)}"
                                        )

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
