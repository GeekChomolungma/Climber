import sys
sys.path.append('..')
import strategy
import pymongo
import builtIndicators
import pandas as pd
import matplotlib.pyplot as plt

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@65.52.174.232:27017"
bo = strategy.baseObj.baseObjSpot(conn_str)
bo.LoadDB("marketinfo","HB-btcusdt-30min")
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

crossIndexSell, crossIndexBuy= builtIndicators.cross.cross(MACD,signal)
crossTimesSell = [times[ci] for ci in crossIndexSell]
crossSell = [signal[ci] for ci in crossIndexSell]
crossTimesBuy = [times[ci] for ci in crossIndexBuy]
crossBuy = [signal[ci] for ci in crossIndexBuy]

plt.plot(times, MACD, label="MACD")
plt.plot(times, signal, label="signal")
plt.scatter(crossTimesSell,crossSell,marker='o',c='r',edgecolors='r')
plt.scatter(crossTimesBuy,crossBuy,marker='o',c='g',edgecolors='g')
plt.bar(times,hist,width=100,label="hist")
plt.legend()
plt.show()
