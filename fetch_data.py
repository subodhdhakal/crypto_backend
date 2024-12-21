import requests
import os
from typing import List, Dict
from dotenv import load_dotenv
from custom_logger import log

# Load environment variables from a .env file
load_dotenv()

class FetchData:
    """
    Handles fetching cryptocurrency data from CoinMarketCap API.
    """
    def __init__(self):
        self.api_key = os.getenv("COINMARKET_API_KEY")
        if not self.api_key:
            log.error("API Key is missing")
            raise ValueError("API key is missing. Please set COINMARKETCAP_API_KEY in your .env file.")
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
        self.market_cap_min_usd = 25000000 # $25 million USD
        self.twentyfourhr_volume_min_usd = 450000 # $450k USD

    def fetch_top_cryptos(self, limit: int = 10000) -> List[Dict]:
        """
        Fetches the top cryptocurrencies by market capitalization from CoinMarketCap.
        Args:
            limit (int): Number of cryptocurrencies to fetch (max 10,000).

        Returns:
            List[Dict]: A list of cryptocurrency data.
        """
        url = f"{self.base_url}/cryptocurrency/listings/latest"
        headers = {
            "Accepts": "application/json",
            "X-CMC_PRO_API_KEY": self.api_key,
        }
        start = 1
        chunk_size = 1000  # API allows a max of 1000 coins per request
        all_data = []

        try:
            while start <= limit:
                params = {
                    "start": start,
                    "limit": min(chunk_size, limit - len(all_data)),
                    "convert": "USD",
                    "market_cap_min": self.market_cap_min_usd,
                    "volume_24h_min": self.twentyfourhr_volume_min_usd,
                }
                log.info(f"Fetching data with start={start} and limit={params['limit']}...")
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                if "data" in data:
                    all_data.extend(data["data"])
                    log.info(f"Fetched {len(data['data'])} coins. Total so far: {len(all_data)}")
                else:
                    log.error("Unexpected API response structure")
                    raise ValueError("Unexpected API response structure: Missing 'data' key.")

                # Increment the start for the next batch
                start += chunk_size

                # Break the loop if we've retrieved all available data
                if len(data["data"]) < chunk_size:
                    log.info("Reached the end of available data from API.")
                    break

        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 400:
                log.error("Bad Request: Check API parameters or account limits.")
            log.error(f"HTTP Error: {http_err}")
        except requests.exceptions.RequestException as req_err:
            log.error(f"Request Error: {req_err}")

        return all_data