import pymongo
import KC
import BB
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import linregress
import numpy as np

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@65.52.174.232:27017"
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

fig, (ax1,ax2,ax3) = plt.subplots(3,1,sharex=False,figsize=(8,12), facecolor="gray")
highS = high.rolling(window=20).max()
lowS = low.rolling(window=20).min()
hlAvg = (highS + lowS)/2.0
smaS = close.rolling(window=20).mean()
diffAvgs = (hlAvg + smaS)/2.0
slope, intercept, r_value, p_value, std_err = linregress(np.arange(20), close[-20:] - diffAvgs[-20:])
ax1.plot(time, close, color='gray', label="close")
ax1.plot(time, upperKC, color='y', label="upperKC")
ax1.plot(time, lowerKC, color='g', label="lowerKC")
ax1.plot(time, upperBB, color='r', label="upperBB")
ax1.plot(time, lowerBB, color='b', label="lowerBB")

ax2.plot(np.arange(20), intercept + slope*np.arange(20), 'r', label='fitted line')
ax2.scatter(np.arange(20), close[-20:] - diffAvgs[-20:], marker='o',c='w',edgecolors='g')
print(intercept + slope*19)
print(close[-1:].values - diffAvgs[-1:].values)

ax3.plot(np.arange(len(highS)), highS, 'r')
ax3.plot(np.arange(len(lowS)), lowS, 'g')
ax3.plot(np.arange(len(hlAvg)), hlAvg, 'b')

plt.show()