import argparse
import time
from fetch_data import FetchData
from process_data import ProcessData

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Track cryptocurrency volume changes.")
    parser.add_argument("--volume-time", type=str, default="1hr", help="Time window for volume calculation (e.g., 1hr, 4hr, 30min, 24hr).")
    parser.add_argument("--volume-percentage", type=float, default=20, help="Percentage change in volume to trigger alerts.")
    parser.add_argument("--limit", type=int, default=1000, help="Number of top cryptocurrencies to fetch.")
    args = parser.parse_args()

    # Initialize classes
    fetch_data = FetchData()
    process = ProcessData(volume_time=args.volume_time, volume_percentage=args.volume_percentage)

    # Fetch and process data
    print("Fetching initial data...")
    cryptocurrencies = fetch_data.fetch_top_cryptos(args.limit)
    if cryptocurrencies:
        process.process_volume_change(cryptocurrencies)

    print("Waiting for 30 sec before fetching again...")
    time.sleep(30)  # Wait for 5 minutes

    print("Fetching updated data...")
    updated_cryptocurrencies = fetch_data.fetch_top_cryptos(args.limit)
    if updated_cryptocurrencies:
        process.process_volume_change(updated_cryptocurrencies)
