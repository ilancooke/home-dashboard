import requests
from datetime import datetime

FORECAST_URL = "https://api.weather.gov/gridpoints/PSR/164,64/forecast"
HOURLY_URL = "https://api.weather.gov/gridpoints/PSR/164,64/forecast/hourly"

HEADERS = {
    "User-Agent": "weather-display/1.0"
}


def get_weather():
    try:
        forecast_response = requests.get(
            FORECAST_URL,
            headers=HEADERS,
            timeout=10
        )
        forecast_response.raise_for_status()

        hourly_response = requests.get(
            HOURLY_URL,
            headers=HEADERS,
            timeout=10
        )
        hourly_response.raise_for_status()

        periods = forecast_response.json()["properties"]["periods"][:4]
        hourly = hourly_response.json()["properties"]["periods"][:6]

        for hour in hourly:
            dt = datetime.fromisoformat(hour["startTime"])
            hour["displayTime"] = dt.strftime("%-I %p")
            
        return periods, hourly, None

    except requests.RequestException as e:
        return [], [], str(e)
