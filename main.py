import pymongo

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@localhost:27017"
# set a 5-second connection timeout
client = pymongo.MongoClient(conn_str,serverSelectionTimeoutMS=5000)
db = client["marketinfo"]
c = db["btcusdt-1min"]
item = c.find_one({"id":1626710400})
print(item)