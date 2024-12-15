import requests
import os
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

class FetchData:
    """
    Handles fetching cryptocurrency data from CoinMarketCap API.
    """
    def __init__(self):
        self.api_key = os.getenv("COINMARKETCAP_API_KEY")
        if not self.api_key:
            raise ValueError("API key is missing. Please set COINMARKETCAP_API_KEY in your .env file.")
        self.base_url = "https://pro-api.coinmarketcap.com/v1"

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
        params = {
            "start": 1,
            "limit": limit,
            "convert": "USD",
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            if "data" in data:
                return data["data"]
            else:
                raise ValueError("Unexpected API response structure: Missing 'data' key.")
        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 400:
                print("Bad Request: Check API parameters or account limits.")
            print(f"HTTP Error: {http_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"Request Error: {req_err}")
        return []
