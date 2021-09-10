import pymongo
import KC
import BB
import pandas as pd
import matplotlib.pyplot as plt

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
MgoClient = pymongo.MongoClient(conn_str,serverSelectionTimeoutMS=5000)
DB = MgoClient["marketinfo"]
Collection = DB["HB-btcusdt-30min"]
data = []
DBcursor = Collection.find().sort('id', pymongo.ASCENDING)
for doc in DBcursor:
    data.append(doc)
df = pd.DataFrame(data)
close = df["close"]
high = df["high"]
low = df["low"]
time = df["id"]
upperKC, lowerKC = KC.KC(close, high, low)
upperBB, lowerBB = BB.BB(close)

fig, ax1 = plt.subplots(1,1,sharex=True,figsize=(8,12), facecolor="gray")
ax1.plot(time, close, color='gray', label="close")
ax1.plot(time, upperKC, color='y', label="upperKC")
ax1.plot(time, lowerKC, color='g', label="lowerKC")
ax1.plot(time, upperBB, color='r', label="upperBB")
ax1.plot(time, lowerBB, color='b', label="lowerBB")
plt.show()