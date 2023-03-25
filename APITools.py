import requests
import datetime
from random import randint
import json
import pytz

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
        self.names = json.load(open("Assets/Names.json"))
    
    async def get_prayer_time_list(self, city: str, country: str, time: datetime.time) -> dict[str, str]:
        """
        Returns a list of prayer times for the given city and country
        """
        date_str = time.strftime("%d-%m-%Y")

        response = requests.get(f"http://api.aladhan.com/v1/timingsByCity/{date_str}?city={city}&country={country}")
                
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
        if name == -1 or name not in range(1, 100):
            name = randint(1, 99)
        
        name = self.names["names"][name - 1]
        
        return name["name"], name['transliteration'], name["en"]['meaning']
    
    async def get_hijri_date(self, date: datetime.date) -> tuple[str, str, str, str]:
        """
        Returns a tuple of the english and Arabic hijri date and the hijri month and year
        """
        DD_MM_YY = date.strftime("%d-%m-%Y")
        hijri_date = requests.get(f"http://api.aladhan.com/v1/gToH?date={DD_MM_YY}").json()

        return hijri_date['data']['hijri']['day'], hijri_date['data']['hijri']['month']['en'], hijri_date['data']['hijri']['year'], hijri_date['data']['hijri']['month']['ar']
    
    async def get_eid_al_adha(self, date: datetime.datetime, timezone: str) -> int:
        """
        Returns the date of Eid al Adha
        """
        
        # Step one: we need to figure out what hijri year it is
        hijri_year = await self.get_hijri_date(date)
        hijri_year = hijri_year[2]    
        eid_date = requests.get(f"http://api.aladhan.com/v1/hToG/1-10-{hijri_year}").json()["data"]["gregorian"]["date"]
        # We now have a string in the form of DD-MM-YYYY
        # convert this to a datetime object
        eid_date = datetime.datetime.strptime(eid_date, "%d-%m-%Y")
        timezone = pytz.timezone(timezone)
        eid_date = timezone.localize(eid_date)
        # Now we calculate the amount of days from <date> to <eid_date>
        elapsed_days = (eid_date - date).days
        return elapsed_days