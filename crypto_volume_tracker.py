#!/usr/bin/env python3

import ast
import os
import argparse
from fetch_data import FetchData
from notification_service import Notification
from process_data import ProcessData

def main():
    parser = argparse.ArgumentParser(description="Track cryptocurrency volume changes.")
    parser.add_argument("--volume-time", type=str, default="1hr", help="Time window for volume calculation (e.g., 1min, 3min, 1hr, 24hr).")
    parser.add_argument("--volume-percentage", type=float, default=20, help="Percentage change in volume to trigger alerts.")
    parser.add_argument("--limit", type=int, default=1000, help="Number of top cryptocurrencies to fetch.")
    args = parser.parse_args()

    # Twilio credentials
    TWILIO_SID = os.getenv("TWILIO_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE = os.getenv("TWILIO_PHONE")
    RECIPIENT_PHONES = ast.literal_eval(os.getenv("RECIPIENT_PHONES", "[]"))

    fetch_data = FetchData()

    notification = Notification(twilio_sid=TWILIO_SID,
        twilio_auth_token=TWILIO_AUTH_TOKEN,
        twilio_phone=TWILIO_PHONE,
        recipient_phones=RECIPIENT_PHONES)
    
    process = ProcessData(
        volume_time=args.volume_time,
        volume_percentage=args.volume_percentage,
        notification=notification
    )

    cryptocurrencies = fetch_data.fetch_top_cryptos(args.limit)
    if cryptocurrencies:
        process.process_volume_change(cryptocurrencies)

if __name__ == "__main__":
    main()
