from typing import List
from twilio.rest import Client

class Notification:
    """
    Handles sending notifications via SMS.
    """
    def __init__(self, twilio_sid: str, twilio_auth_token: str, twilio_phone: str, recipient_phones: List[str]):
        self.twilio_client = Client(twilio_sid, twilio_auth_token)
        self.twilio_phone = twilio_phone
        self.recipient_phones = recipient_phones

    def send_bulk_sms(self, message: str):
        """
        Sends a bulk SMS notification to all recipients.

        Args:
            message (str): The message to send via SMS.
        """
        for phone in self.recipient_phones:
            try:
                print(f"Sending sms for phone: {phone}")
                sms = self.twilio_client.messages.create(
                    body=message,
                    from_=self.twilio_phone,
                    to=phone
                )
                print(f"SMS sent successfully to {phone}: SID {sms.sid}")
            except Exception as e:
                print(f"Failed to send SMS to {phone}: {e}")
