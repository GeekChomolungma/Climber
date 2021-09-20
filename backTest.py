from strategy.Squeeze import squeeze
from strategy.CmMacd import cm
import builtIndicators
import datetime
import bson
import matplotlib.pyplot as plt
import pymongo
import pandas as pd

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
symbols = "btcusdt"
cmu = cm.CmUnit(conn_str, "marketinfo", "btcusdt", "4hour", 150)
squ = squeeze.SqueezeUnit(conn_str, "marketinfo", "btcusdt", "4hour", 80)

Money = 10000.0
Amount = 0.0
squBuyID = []
squBuyData = []
squSellID = []
squSellData = []
squData = []

dataAll = []
timeBP = [] 
timeSP = []
dataSP = []
dataBP = []
timeBPA = []
timeSPA = []
dataBPA = []
dataSPA = []

fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5,1,sharex=True,figsize=(8,12))

while True:
    # squeeze
    newTurn, indicator = squ.RunOnce()
    if newTurn == False:
        break
    dic = {"id": squ.preState.timeID, "value": squ.preState.val, "scolor": squ.preState.scolor, "bcolor": squ.preState.bcolor, "slope": squ.preState.slope, "slopeColor": squ.preState.slopeColor}
    squData.append(dic)

    date = datetime.datetime.fromtimestamp(squ.preState.timeID).strftime('%Y-%m-%d %H:%M:%S')
    if indicator == "sell":
        if Amount != 0:
            Money = 0.998 * Amount * squ.close
            Amount = 0
            squSellID.append(squ.preState.timeID)
            squSellData.append(squ.close)
    
    if indicator == "buy":
        if Money != 0:
            Amount = 0.998 * Money / squ.close
            Money = 0
            squBuyID.append(squ.preState.timeID)
            squBuyData.append(squ.close)
    
    # cmmacd
    indicator, Brought, Sold, closePrice = cmu.RunOnce()
    date = datetime.datetime.fromtimestamp(cmu.TimeID).strftime('%Y-%m-%d %H:%M:%S')
    if indicator == "buy":
        timeBPA.append(cmu.TimeID)
        dataBPA.append(closePrice)
    if indicator == "sell":
        timeSPA.append(cmu.TimeID)
        dataSPA.append(closePrice)
    if Brought == True:
        Amount = Money / closePrice * 0.998
        Money = 0
        timeBP.append(cmu.TimeID)
        dataBP.append(closePrice)
    if Sold == True:
        Money = Amount * closePrice * 0.998
        Amount = 0
        timeSP.append(cmu.TimeID)
        dataSP.append(closePrice)

DBcursorAll = cmu.Collection.find().sort('id', pymongo.ASCENDING)
for docAll in DBcursorAll:
    dataAll.append(docAll)
df = pd.DataFrame(dataAll)
timeAll = df["id"]
closeAll = df["close"]
fastMA = builtIndicators.ma.EMA(closeAll,12)
slowMA = builtIndicators.ma.EMA(closeAll,26)
MA30All = builtIndicators.ma.EMA(closeAll,30)
MACD = fastMA - slowMA
signal = builtIndicators.ma.SMA(MACD,9)
hist = MACD - signal
ax1.plot(timeAll, closeAll, color='gray', label="close")
ax1.scatter(timeBPA,dataBPA,marker='^',c='g',edgecolors='g')
ax1.scatter(timeSPA,dataSPA,marker='v',c='r',edgecolors='r')

ax2.plot(timeAll, closeAll, color='gray', label="close")
ax2.scatter(timeBP,dataBP,marker='o',c='w',edgecolors='g')
ax2.scatter(timeSP,dataSP,marker='o',c='m',edgecolors='m')

# plot cross dots between Macd and signal
crossIndexSell, crossIndexBuy= builtIndicators.cross.cross(MACD,signal)
crossTimesSell = [timeAll[ci] for ci in crossIndexSell]
crossSell = [signal[ci] for ci in crossIndexSell]
crossTimesBuy = [timeAll[ci] for ci in crossIndexBuy]
crossBuy = [signal[ci] for ci in crossIndexBuy]
ax3.plot(timeAll, MACD, label="MACD")
ax3.plot(timeAll, signal, label="signal")
ax3.scatter(crossTimesSell,crossSell,marker='o',c='r',edgecolors='r')
ax3.scatter(crossTimesBuy,crossBuy,marker='o',c='g',edgecolors='g')
ax3.bar(timeAll,hist,width=600,label="hist")

squ.Plot(squData, ax4, ax5)
plt.show()

