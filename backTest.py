from textwrap import indent
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
cmu = cm.CmUnit(conn_str, "marketinfo", "btcusdt", "30min", 300)
squ = squeeze.SqueezeUnit(conn_str, "marketinfo", "btcusdt", "30min", 80)
BaseCount = cmu.Collection.count_documents({})
Money = 10000.0
Amount = 0.0
squData = []

dataAll = []
timeBP = [] 
timeSP = []
dataSP = []
dataBP = []

fig, (ax1, ax2, ax3, ax4) = plt.subplots(4,1,sharex=True,figsize=(8,12))

# cmmacd
indicator, Brought, Sold, closePrice, lastMacd, err = cmu.RunOnce()
while squ.preState.timeID < cmu.TimeID:
    newTurn, indicator = squ.RunOnce()

cp = 0
i = 0
while True:
    # assert timeid
    if squ.preState.timeID != cmu.TimeID:
        print("wrong time id! squ: %d, cmu: %d"%(squ.preState.timeID, cmu.TimeID))
        break 
    i += 1
    # squeeze
    newTurn, indicator = squ.RunOnce()
    if newTurn == False:
        break
    dic = {"id": squ.preState.timeID, "value": squ.preState.val, "scolor": squ.preState.scolor, "bcolor": squ.preState.bcolor, "slope": squ.preState.slope, "slopeColor": squ.preState.slopeColor}
    squData.append(dic)

    # cmmacd
    indicator, Bought, Sold, closePrice, lastMacd, err = cmu.RunOnce()
    if err == "nil":
        cp = closePrice

    if indicator == "nothing":
        # sold and bought are false
        if cmu.SPLock == False and squ.preState.scolor == "gray" and squ.preState.bcolor == "red":
            # sell it
            cmu.GMacdSP = lastMacd
            cmu.SPLock = True
            cmu.BPLock = False
            Sold = True
        if cmu.BPLock == False and squ.preState.scolor == "gray" and squ.preState.bcolor == "lime":
            # buy it
            cmu.GMacdBP = lastMacd
            cmu.BPLock = True
            cmu.SPLock = False
            Bought = True

    if indicator == "buy":
        if Bought == True:
            # state machine has updated
            print()
        elif Sold == True:
            # state machine has updated
            print()
        else:
            # GMacdBP has updated
            if cmu.BPLock == False and squ.preState.scolor == "gray" and (squ.preState.bcolor == "lime" or squ.preState.bcolor == "maroon"):
                cmu.GMacdBP = lastMacd
                cmu.SPLock = False
                cmu.BPLock = True
                Bought = True
            
    if indicator == "sell":
        if Bought == True:
            # state machine has updated
            print()
        elif Sold == True:
            # state machine has updated
            print()
        else:
            # GMacdSP has updated
            if cmu.SPLock == False and squ.preState.scolor == "gray" and (squ.preState.bcolor == "red" or squ.preState.bcolor == "green"):
                cmu.GMacdSP = lastMacd
                cmu.SPLock = True
                cmu.BPLock = False
                Sold = True

    date = datetime.datetime.fromtimestamp(cmu.TimeID).strftime('%Y-%m-%d %H:%M:%S')
    if Bought == True:
        Amount = Money / closePrice * 0.998
        Money = 0
        timeBP.append(cmu.TimeID)
        dataBP.append(closePrice)
        print("%s, HB-%s-%s, Bought, indicator: %s, ts: %d, close: %f, amount: %f, round: %d/%d" \
            %(date, cmu.symbol, cmu.period, indicator, cmu.TimeID, closePrice, Amount, i+cmu.winLen, BaseCount))
    if Sold == True:
        Money = Amount * closePrice * 0.998
        Amount = 0
        timeSP.append(cmu.TimeID)
        dataSP.append(closePrice)
        print("%s, HB-%s-%s, Sold,   indicator: %s, ts: %d, close: %f, Money:  %f, round: %d/%d"% \
            (date, cmu.symbol, cmu.period, indicator, cmu.TimeID, closePrice, Money, i+cmu.winLen, BaseCount))
RR = 0.0
if Money != 0:
    RR = (Money - 10000.0) / 10000.0
else:
    RR = (Amount * cp - 10000.0) / 10000.0
print("rate of return is: %f"%(RR))

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

fastMAAll = builtIndicators.ma.EMA(closeAll,5)
slowMAAll = builtIndicators.ma.EMA(closeAll,10)
ax1.plot(timeAll, closeAll, color='gray', label="close")
ax1.plot(timeAll, fastMAAll, color='y', label="MA5")
ax1.plot(timeAll, slowMAAll, color='g', label="MA10")
ax1.scatter(timeBP,dataBP,marker='o',c='w',edgecolors='g')
ax1.scatter(timeSP,dataSP,marker='o',c='m',edgecolors='m')

# plot cross dots between Macd and signal
crossIndexSell, crossIndexBuy= builtIndicators.cross.cross(MACD,signal)
crossTimesSell = [timeAll[ci] for ci in crossIndexSell]
crossSell = [signal[ci] for ci in crossIndexSell]
crossTimesBuy = [timeAll[ci] for ci in crossIndexBuy]
crossBuy = [signal[ci] for ci in crossIndexBuy]
ax2.plot(timeAll, MACD, label="MACD")
ax2.plot(timeAll, signal, label="signal")
ax2.scatter(crossTimesSell,crossSell,marker='o',c='r',edgecolors='r')
ax2.scatter(crossTimesBuy,crossBuy,marker='o',c='g',edgecolors='g')
ax2.bar(timeAll,hist,width=600,label="hist")

squ.Plot(squData, ax3, ax4)
plt.show()

