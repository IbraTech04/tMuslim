import datetime
import pytz
from geopy.geocoders import Nominatim

class TimeManager:
    """
    Class for all time-related functions
    Like time until, converting timezones, etc.
    """
    
    def __init__(self):
        self.geolocator = Nominatim(user_agent="athaan-bot")
    
    async def calculateRemainingTime(self, prayerHour: int, prayerMin: int, hour: int, minute: int, fajr: str) -> tuple[int, int]:
        """
        Given two times, returns the time difference between them
        Precondition:
        Fajr is set correctly relative to whether we're calculating Fajr or not
        """
        if prayerHour == hour and prayerMin == minute:  # If the current time matches the prayer time, return 0, 0
            return 0, 0
        if fajr:  # If we're calculating Fajr do this
            prayerHour += 24 if prayerHour < hour else 0
            time_diff = (prayerHour - hour) * 60 + prayerMin - minute
        else:  # If we're not calculating Fajr, we can calculate normally 
            prayerHour += 24 if prayerHour <= hour and prayerMin <= minute else 0
            time_diff = (prayerHour - hour - (prayerMin < minute)) * 60 + (prayerMin - minute) % 60
        return divmod(time_diff, 60)

    async def get_time_in_timezone(self, timezone: str) -> datetime.datetime:
        """
        Given a timezone, returns the time in that timezone
        """
        tz = pytz.timezone(timezone)
        return datetime.datetime.now(tz)