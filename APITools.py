import requests
import datetime
from random import randint

class APIHelper:
    """
    Class which abstracts the connection to the Islam API and allows for an easier way to access the API
    
    ==== Attributes ====
    None!
    
    ==== Representation Invariants ====
    Also... None!
    """
    
    def __init__(self):
        """
        Initializes the APIHelper
        """
        pass
    
    async def get_prayer_time_list(self, city: str, country: str, time: datetime.time, method: int) -> dict[str, str]:
        """
        Returns a list of prayer times for the given city and country
        """
        date_str = time.strftime("%d-%m-%Y")

        response = requests.get(f"http://api.aladhan.com/v1/timingsByCity?city={city}&country={country}&method={method}&date={date_str}")
        
        # We want to return a dict of only prayer times and sunrise, nothing else
        
        to_return = {}
        for key, value in response.json()["data"]["timings"].items():
            if key in ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]:
                to_return[key] = value
        return to_return
    
    async def get_99_names(self, name: int = -1) -> tuple[str, str, str]:
        """
        Given a name, returns the name, transliteration, and meaning of the name
        Precondition:
        name is an integer between 1 and 99 inclusive
        If name is not given, a random name is returned
        """
        if name == -1:
            name = randint(1, 99)
        
        name = requests.get(f"https://api.aladhan.com/v1/asmaAlHusna/{name}").json()

        return name["data"][0]["name"], name["data"][0]['transliteration'], name["data"][0]["en"]['meaning']
    
    async def get_hijri_date(self) -> tuple[str, str, str]:
        """
        Returns a tuple of the english and Arabic hijri date and the hijri month and year
        """
        DD_MM_YY = datetime.now().strftime("%d-%m-%Y")
        hijri_date = requests.get(f"http://api.aladhan.com/v1/gToH?date={DD_MM_YY}").json()

        return hijri_date['data']['hijri']['day'], hijri_date['data']['hijri']['month']['en'], hijri_date['data']['hijri']['year'], hijri_date['data']['hijri']['month']['ar']
            