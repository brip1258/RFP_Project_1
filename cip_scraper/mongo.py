from pymongo import MongoClient
from pymongo.server_api import ServerApi

uri = f"mongodb+srv://kyletp:634312@crpupdates.7pf961t.mongodb.net/?appName=crpUpdates"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)