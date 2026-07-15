from command_handler import *
import requests
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

def weather(text,context):
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)
    language = identify_lang(text)

    diff_last_sym = 0
    # if input contains "in" or "в" try to get rid of that and identify the city
    if(language == "en" and "in " in text):
        _,_,text = text.partition("in ")
    elif(language == "ru" and "в " in text):
        diff_last_sym = 1
        _,_,text = text.partition("в ")

    print("Sending requests...")
    city = text
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={
            "name": city,
            "count": 1,
            "language": language
        }
    )
    if(not diff_last_sym):
        original_city_input = city
        data = response.json()
        try:
            name = data["results"][0]["name"]
            lat = data["results"][0]["latitude"]
            lon = data["results"][0]["longitude"]
        except Exception as e:
            if(language == "ru"):
                msg = f"Город {city} не был найден. Попробуйте ещё раз !"
                print(msg)
                reply_to_channel(msg,context)
                return
            if(language == "lv"):
                msg = f"Pilsēta {city} netika atrasta. Pamēģiniet vēlreiz !"
                print(msg)
                reply_to_channel(msg,context)
                return
            msg = f"Couldn't find city {city}. Try again !"
            print(msg)
            reply_to_channel(msg,context)
            return
    else :
        last_syms = [" ","а","е","ь","","","ы"]
        found = 0
        for ch in last_syms:
            "Change last sym"
            city = city[:-1]+ch
            response = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={
                    "name": city.strip(),
                    "count": 1,
                    "language": language
                }
            )
            data = response.json()
            try:
                name = data["results"][0]["name"]
                lat = data["results"][0]["latitude"]
                lon = data["results"][0]["longitude"]
                found = 1
                break
            except Exception as e:
                continue
        if(not found):
            if(language == "ru"):
                msg = f"Город {original_city_input} не был найден. Попробуйте ещё раз !"
                print(msg)
                reply_to_channel(msg,context)
                return
            if(language == "lv"):
                msg = f"Pilsēta {original_city_input} netika atrasta. Pamēģiniet vēlreiz !"
                print(msg)
                reply_to_channel(msg,context)
                return
            msg = f"Couldn't find city {original_city_input}. Try again !"
            print(msg)
            reply_to_channel(msg,context)
            return

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url_weather = "https://api.open-meteo.com/v1/forecast"
    weather_params = {
    	"latitude": lat,
    	"longitude": lon,
    	"current": ["temperature_2m", "apparent_temperature", "wind_speed_10m", "relative_humidity_2m", "rain", "snowfall"],
    }
    responses = openmeteo.weather_api(url_weather, params = weather_params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    # print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
    # print(f"Elevation: {response.Elevation()} m asl")
    # print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

    # Process current data. The order of variables needs to be the same as requested.
    current = response.Current()
    current_temperature_2m = round(current.Variables(0).Value(),1)
    current_apparent_temperature = round(current.Variables(1).Value(),1)
    current_wind_speed_10m = round(current.Variables(2).Value(),1)
    current_relative_humidity_2m = round(current.Variables(3).Value(),1)
    current_rain = round(current.Variables(4).Value(),1)
    current_snowfall = round(current.Variables(5).Value(),1) 
    labels = {
        "en": {
            "temp": "Temperature",
            "feels": "Feels like",
            "wind": "Wind speed",
            "humidity": "Humidity",
            "rain": "Rain",
            "snow": "Snowfall",
        },
        "lv": {
            "temp": "Temperatūra",
            "feels": "Šķietamā temperatūra",
            "wind": "Vēja ātrums",
            "humidity": "Mitrums",
            "rain": "Lietus",
            "snow": "Sniegs",
        },
        "ru": {
            "temp": "Температура",
            "feels": "Ощущаемая температура",
            "wind": "Скорость ветра",
            "humidity": "Влажность",
            "rain": "Дождь",
            "snow": "Снег",
        },
    }

    l = labels.get(language, labels["en"])

    message = (
        f"{l['temp']}: {current_temperature_2m}\n"
        f"{l['feels']}: {current_apparent_temperature}\n"
        f"{l['wind']}: {current_wind_speed_10m}\n"
        f"{l['humidity']}: {current_relative_humidity_2m}\n"
        f"{l['rain']}: {current_rain}\n"
        f"{l['snow']}: {current_snowfall}"
    )

    print(message)
    reply_to_channel(message, context)

def register(register_command):
    root = Path(__file__).parent / "config"
    with open(root,"r") as fp:
        for line in fp:
            register_command(f"{line.strip()}",weather)

#register command
register(register_command)