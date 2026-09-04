import requests
from datetime import datetime

FORECAST_URL = "https://api.weather.gov/gridpoints/PSR/164,64/forecast"
HOURLY_URL = "https://api.weather.gov/gridpoints/PSR/164,64/forecast/hourly"

HEADERS = {
    "User-Agent": "weather-display/1.0"
}

LOW_PRECIPITATION_THRESHOLD = 30


def _weather_symbol(
    forecast,
    is_daytime=True,
    icon_url="",
    precipitation_probability=None,
):
    """Return a lightweight Unicode symbol based on the NWS icon category."""
    icon_code = (
        icon_url.rsplit("/", 1)[-1]
        .split("?", 1)[0]
        .split(",", 1)[0]
        .lower()
    )

    low_probability = (
        precipitation_probability is not None
        and precipitation_probability < LOW_PRECIPITATION_THRESHOLD
    )

    icon_symbols = {
        "skc": "☀" if is_daytime else "☾",
        "few": "☼",
        "sct": "☼",
        "bkn": "☁",
        "ovc": "☁",
        "wind": "≋",
        "rain": "☂",
        "rain_showers": "☂",
        "tsra": "☁" if low_probability else "⚡",
        "snow": "❄",
        "blizzard": "❄",
        "rain_snow": "❄",
        "rain_sleet": "❄",
        "snow_sleet": "❄",
        "fzra": "❄",
        "fog": "≋",
        "mist": "≋",
        "haze": "≋",
    }

    if icon_code in icon_symbols:
        return icon_symbols[icon_code]

    # Keep a text fallback for incomplete or older NWS responses.
    forecast = forecast.lower()

    if any(word in forecast for word in ("thunder", "storm")):
        return "☁" if low_probability else "⚡"
    if any(word in forecast for word in ("snow", "sleet", "blizzard", "flurr")):
        return "❄"
    if any(word in forecast for word in ("rain", "shower", "drizzle")):
        return "☂"
    if any(word in forecast for word in ("cloud", "overcast", "fog", "haze")):
        return "☁"
    if "partly" in forecast or "mostly" in forecast:
        return "☼"
    if any(word in forecast for word in ("sunny", "clear")):
        return "☀" if is_daytime else "☾"

    return "☀" if is_daytime else "☾"


def _forecast_symbol(
    forecast,
    precipitation_probability,
    icon_url="",
    is_daytime=True,
):
    """Choose a weather icon from the readable forecast condition first."""
    forecast = forecast.lower()
    significant_precipitation = (
        precipitation_probability is None
        or precipitation_probability >= LOW_PRECIPITATION_THRESHOLD
    )
    has_thunderstorms = any(word in forecast for word in ("thunder", "storm"))
    has_rain = any(word in forecast for word in ("rain", "shower", "drizzle"))

    if significant_precipitation and has_thunderstorms:
        return "⛈️"
    if significant_precipitation and has_rain:
        return "🌦️" if is_daytime else "🌧️"
    if "partly" in forecast:
        return "⛅" if is_daytime else "☁️"
    if "mostly sunny" in forecast or "mostly clear" in forecast:
        return "🌤️" if is_daytime else "🌙"
    if "mostly cloudy" in forecast:
        return "🌥️" if is_daytime else "☁️"
    if "sunny" in forecast or "clear" in forecast:
        return "☀" if is_daytime else "🌙"
    if "cloud" in forecast or "overcast" in forecast:
        return "☁️"
    if has_thunderstorms or has_rain:
        return "⛅" if is_daytime else "☁️"

    return _weather_symbol(
        forecast,
        is_daytime,
        icon_url,
        precipitation_probability,
    )


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

        forecast_periods = forecast_response.json()["properties"]["periods"]
        hourly = hourly_response.json()["properties"]["periods"][:5]

        for hour in hourly:
            precipitation_probability = hour.get(
                "probabilityOfPrecipitation", {}
            ).get("value")
            hour["symbol"] = _forecast_symbol(
                hour["shortForecast"],
                precipitation_probability,
                hour.get("icon", ""),
                hour.get("isDaytime", True),
            )

        daily = []
        for index, daytime in enumerate(forecast_periods):
            if not daytime.get("isDaytime"):
                continue

            nighttime = next(
                (
                    period
                    for period in forecast_periods[index + 1:]
                    if not period.get("isDaytime")
                ),
                None,
            )

            day_precipitation = daytime.get(
                "probabilityOfPrecipitation", {}
            ).get("value")
            night_precipitation = (
                nighttime.get("probabilityOfPrecipitation", {}).get("value")
                if nighttime
                else None
            )
            precipitation_values = [
                value
                for value in (day_precipitation, night_precipitation)
                if value is not None
            ]
            daily_precipitation = (
                max(precipitation_values)
                if precipitation_values
                else None
            )

            daily.append({
                "name": daytime["name"],
                "high": daytime["temperature"],
                "highUnit": daytime["temperatureUnit"],
                "low": nighttime["temperature"] if nighttime else None,
                "lowUnit": nighttime["temperatureUnit"] if nighttime else "",
                "dayForecast": daytime["shortForecast"],
                "nightForecast": nighttime["shortForecast"] if nighttime else "",
                "precipitationChance": daily_precipitation,
                "symbol": _forecast_symbol(
                    daytime["shortForecast"],
                    daily_precipitation,
                    daytime.get("icon", ""),
                ),
            })

            if len(daily) == 5:
                break

        for hour in hourly:
            dt = datetime.fromisoformat(hour["startTime"])
            hour["displayTime"] = dt.strftime("%-I %p")
            
        return daily, hourly, None

    except requests.RequestException as e:
        return [], [], str(e)
