import pymongo
import datetime


class ServerManager:
    """
    Class which abstracts the connection to the MongoDB server and allows for easy access to the database

    === Attributes ===
    pymongo.MongoClient: client - the client used to connect to the server

    === Representation Invariants ===
    None :)
    """
    client: pymongo.MongoClient

    def __init__(self, database_creds: str, database_name: str):
        """
        Initializes the client and connects to the server

        === Preconditions ===
        database_creds: the credentials for the database
        database_name: the name of the database
        """
        self.client = pymongo.MongoClient(database_creds)
        self.database = self.client.get_database(database_name)

    async def register_server(self, guild_id: str, data: dict[str, any]):
        """
        Registers a server in the database

        === Preconditions ===
        guild_id: the id of the server
        data: the data to be stored
        data must have the following keys:
        role_id
        channel_id
        vc_id
        reaction_message_id
        timezone
        city
        country
        """
        self.database.servers.update_one({"_id": guild_id, **data})

    async def is_server_registered(self, guild_id: str) -> bool:
        """
        Returns whether the server is registered in the database

        === Preconditions ===
        guild_id: the id of the server
        """
        return self.database.servers.find_one({"_id": guild_id}) != None

    async def get_announcement_channel(self, guild_id: str) -> str:
        """
        Returns the channel id of the announcement channel

        === Preconditions ===
        guild_id is the id of the server and is in the database
        """
        return self.database.servers.find_one({"_id": guild_id})["channel_id"]

    async def get_athaan_chanel(self, guild_id: str) -> str:
        """
        Returns the channel id of the athaan channel

        === Preconditions ===
        guild_id is the id of the server and is in the database
        """
        return self.database.servers.find_one({"_id": guild_id})["vc_id"]

    async def get_athaan_role(self, guild_id: str) -> str:
        """
        Returns the role id of the athaan role

        === Preconditions ===
        guild_id is the id of the server and is in the database
        """
        return self.database.servers.find_one({"_id": guild_id})["role_id"]

    async def get_reaction_message_id(self, guild_id: str) -> str:
        """
        Returns the message id of the reaction message

        === Preconditions ===
        guild_id is the id of the server and is in the database
        """
        return self.database.servers.find_one({"_id": guild_id})["reaction_message_id"]

    async def get_timezone(self, guild_id: str) -> str:
        """
        Returns the timezone of the server

        === Preconditions ===
        guild_id is the id of the server and is in the database
        """
        return self.database.servers.find_one({"_id": guild_id})["timezone"]

    def is_location_in_database(self, location: tuple[str, str], current_date: datetime.time) -> bool:
        """
        Returns whether the location is in the database and is up to date

        === Preconditions ===
        location is a tuple of the city and country
        """
        # Convert location into location[0]:location[1]
        location = f"{location[0]}:{location[1]}"
        x = self.database.prayers.find_one({"_id": location})
        if x == None:
            return False
        # Check if the date is the same
        # Make a / separated string of the date
        # MM/DD/YYYY
        date = f"{current_date.year}/{current_date.month}/{current_date.day}"
        return x["date"] == date

    async def get_server_location(self, guild_id: str) -> tuple[str, str]:
        """
        Returns the location of the server

        === Preconditions ===
        guild_id is the id of the server and is in the database
        """
        return self.database.servers.find_one({"_id": guild_id})["city"], self.database.servers.find_one({"_id": guild_id})["country"]

    async def get_prayer_list(self, location: tuple[str, str]) -> dict[str, any]:
        """
        Returns the prayer list for the given timezone

        === Preconditions ===
        location is a tuple of the city and country
        location is in the database
        """
        # Convert location into location[0]:location[1]
        location = f"{location[0]}:{location[1]}"
        return self.database.prayers.find_one({"_id": location})
    
    async def insert_prayer_list(self, location: tuple[str, str], data: dict[str, any]):
        """
        Inserts the prayer list into the database

        === Preconditions ===
        location is a tuple of the city and country
        data is a dictionary of the prayer times
        data has the following keys:
        date, fajr, sunrise, dhuhr, asr, maghrib, isha
        """
        # Convert location into location[0]:location[1]
        location_str = f"{location[0]}:{location[1]}"
        
        # Add the entire data dictionary as a subdocument to the _id document
        self.database.prayers.update_one(
            {"_id": location_str},
            {"$set": data},
            upsert=True  # creates the document if it doesn't exist
        )
