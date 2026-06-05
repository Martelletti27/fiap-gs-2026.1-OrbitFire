"""Cliente e ingestao de clima Open-Meteo."""

from src.infrastructure.weather.client import OpenMeteoClient
from src.infrastructure.weather.parser import ParsedWeatherDaily, parse_open_meteo_daily
from src.infrastructure.weather.targets import WeatherTarget, resolve_weather_targets

__all__ = [
    "OpenMeteoClient",
    "ParsedWeatherDaily",
    "WeatherTarget",
    "parse_open_meteo_daily",
    "resolve_weather_targets",
]
