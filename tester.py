from pytz import country_timezones, timezone
import datetime
city = "Mississauga"
country = "North America"

combined = country + "/" + city

def find_city(query):
    for country, cities in country_timezones.items():
        for city in cities:
            if query in city:
                return timezone(city)

print(find_city("Mississauga"))