import sys
sys.path.append('..')
import strategy
import pymongo
import builtIndicators
import pandas as pd
import matplotlib.pyplot as plt

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
bo = strategy.baseObj.baseObjSpot(conn_str)
bo.LoadDB("marketinfo","HB-btcusdt-5min")
data = []
DBcursor = bo.Collection.find().sort('id', pymongo.DESCENDING).limit(300)
for doc in DBcursor:
    data.append(doc)
data.reverse()

df = pd.DataFrame(data)
times = df["id"].values
df = pd.DataFrame(data)
close = df["close"]
fastMA = builtIndicators.ma.EMA(close,12)
slowMA = builtIndicators.ma.EMA(close,26)
MACD = fastMA - slowMA
signal = builtIndicators.ma.SMA(MACD,9)
hist = MACD - signal
print(hist)
plt.plot(times, MACD, label="MACD")
plt.plot(times, signal, label="signal")
plt.bar(times,hist,width=100,label="MACD")
plt.legend()
plt.show()
