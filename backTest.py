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
cmu4 = cm.CmUnit(conn_str, "marketinfo", "btcusdt", "4hour", 100)
squ = squeeze.SqueezeUnit(conn_str, "marketinfo", "btcusdt", "30min", 80)
squ4 = squeeze.SqueezeUnit(conn_str, "marketinfo", "btcusdt", "4hour", 80)
BaseCount = cmu.Collection.count_documents({})
Money = 10000.0
Amount = 0.0

goalTime = []
goals = []

squData = []
squData4 = []

dataAll = []
timeBP = []
timeSP = []
dataSP = []
dataBP = []
macdDiffTime = []
macdDiffData = []

timeBPHigh = []
timeSPHigh = []
dataSPHigh = []
dataBPHigh = []

fig, (ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8) = plt.subplots(8,1,sharex=True,figsize=(8,12))

# cmmacd
indicator, closePrice, lastMacd, lastSlowMA, stdMA, err = cmu4.RunOnce()
newTurn, indicator, timeID, val, slope, scolor, bcolor, slopeColor = squ4.RunOnce()
squ4.updatePreState(timeID, val, slope, scolor, bcolor, slopeColor)

print("squ4 timeid is %d"%(squ4.preState.timeID))
while cmu.TimeID + cmu.Offset < squ4.preState.timeID + squ4.Offset:
    cmu.RunOnce()
print("init ExpectedID of cmmacd")
while squ.preState.timeID + squ.Offset < squ4.preState.timeID + + squ4.Offset:
    newTurn, indicator, timeID, val, slope, scolor, bcolor, slopeColor = squ.RunOnce()
    squ.updatePreState(timeID, val, slope, scolor, bcolor, slopeColor)
print("init ExpectedID of squeeze")

cp = 0
i = 0
gGoal = 0
squGoal = 0
squGoal4 = 0
cmGoal = 0
cmGoal4 = 0
while True:
    # 1.灰十字, 对应亮色可以视为该方向的强势信号
    # 2.观察相邻几段灰十字区是否同亮色, 同色连续表示非常强烈的单边信号
    # 3.连续两段同亮色的灰色十字区后, 出现异亮色灰十字时, 表明单边趋势破坏, 可以立刻反向操作
    #   连续两段同亮色的灰色十字区后, 出现同亮色灰十字时, 表明单边趋势强势, 立即平仓
    #   连续两段同亮色的灰色十字区后, 出现同暗色灰十字时, 是否也可表明单边趋势破坏?
    # 5.黑十字, 表示混沌

    # 6.Macd的正负号, 可以视为该方向的相对信号
    # 7.cm策略红绿点之间的最高最低点记录
    # 8.连续红绿点之间的距离和相邻买卖点之间的距离比值, 是否构成操作信号?
    # assert timeid
    if squ.preState.timeID != cmu.TimeID:
        print("wrong time id! squ: %d, cmu: %d, cmu4: %d"%(squ.preState.timeID, cmu.TimeID, cmu4.TimeID))
        break
    i += 1

    # squeeze
    newTurn, indicator, timeID, val, slope, scolor, bcolor, slopeColor = squ.RunOnce()
    colorChange = False
    if not newTurn:
        break
    if scolor == "gray":
        if bcolor == "lime" and squ.preState.scolor == "black":
            # up
            squGoal = 1
        if bcolor == "maroon" and squ.preState.bcolor == "red":
            squGoal = 0.5

        if bcolor == "red" and squ.preState.scolor == "black":
            # down
            squGoal = -1
        if bcolor == "green" and squ.preState.bcolor == "lime":
            squGoal = -0.5
    else:
        if squGoal > 0 and (bcolor == "red" or bcolor == "maroon"):
            squGoal = 0
        if squGoal < 0 and (bcolor == "lime" or bcolor == "green"):
            squGoal = 0
    dic = {"id": timeID, "value": val, "scolor": scolor, "bcolor": bcolor, "slope": slope, "slopeColor": slopeColor}
    squData.append(dic)
    squ.updatePreState(timeID, val, slope, scolor, bcolor, slopeColor)

    # cmmacd
    indicator, closePrice, lastMacd, lastSlowMA, stdMA, err = cmu.RunOnce()
    if err == "nil":
        cp = closePrice

    if indicator == "buy":
        cmu.PrevBP = lastMacd
        cmGoal = 1
        if lastMacd < cmu.GMacdBP:
            cmu.GMacdBP = lastMacd
        if (cmu.GMacdSP-lastMacd)/lastSlowMA > 0.954*stdMA:
            cmGoal = 2
    if indicator == "sell":
        cmu.PrevSP = lastMacd
        cmGoal = -1
        if lastMacd > cmu.GMacdSP:
            cmu.GMacdSP = lastMacd
        if (lastMacd-cmu.GMacdBP)/lastSlowMA > 0.954*stdMA:
            cmGoal = -2

    # cmmacd high level
    if cmu.TimeID + cmu.Offset == cmu4.TimeID + 2*cmu4.Offset:
        indicator, closePriceH, lastMacd, lastSlowMA, stdMA, err = cmu4.RunOnce()
        if indicator == "buy":
            cmGoal4 = 2
            timeBPHigh.append(cmu4.TimeID)
            dataBPHigh.append(closePriceH)
        if indicator == "sell":
            cmGoal4 = -2
            timeSPHigh.append(cmu4.TimeID)
            dataSPHigh.append(closePriceH)
    
    # squ high level
    if cmu.TimeID + cmu.Offset == squ4.preState.timeID + 2*squ4.Offset:
        # squeeze
        newTurn, indicator, timeID, val, slope, scolor, bcolor, slopeColor = squ4.RunOnce()
        colorChange = False
        if not newTurn:
            break
        if scolor == "gray":
            if bcolor == "lime" and squ4.preState.scolor == "black":
                # up
                squGoal4 = 1
            if slopeColor == "maroon" and squ4.preState.slopeColor == "red":
                squGoal4 = 0.5

            if bcolor == "red" and squ4.preState.scolor == "black":
                # down
                squGoal4 = -1
            if slopeColor == "green" and squ4.preState.slopeColor == "lime":
                squGoal4 = -0.5
        else:
            if squGoal4 > 0 and (bcolor == "red" or bcolor == "maroon"):
                squGoal4 = 0
            if squGoal4 < 0 and (bcolor == "lime" or bcolor == "green"):
                squGoal4 = 0
        dic = {"id": timeID, "value": val, "scolor": scolor, "bcolor": bcolor, "slope": slope, "slopeColor": slopeColor}
        squData4.append(dic)
        squ4.updatePreState(timeID, val, slope, scolor, bcolor, slopeColor)


    goalTime.append(cmu.TimeID)
    gGoal =  cmGoal+squGoal
    goals.append(gGoal)
    date = datetime.datetime.fromtimestamp(cmu.TimeID).strftime('%Y-%m-%d %H:%M:%S')
    if gGoal >= 3:
        #buy
        if not cmu.BPLock:
            cmu.BPLock = True
            cmu.SPLock = False
            cmu.GMacdBP = lastMacd
            Amount = Money / closePrice * 0.998
            Money = 0
            timeBP.append(cmu.TimeID)
            dataBP.append(closePrice)
            print("%s, HB-%s-%s, Bought, indicator: %s, ts: %d, close: %f, amount: %f, round: %d/%d" \
                %(date, cmu.symbol, cmu.period, indicator, cmu.TimeID, closePrice, Amount, i+cmu.winLen, BaseCount))
    if gGoal <= -3:
        if not cmu.SPLock:
            cmu.SPLock = True
            cmu.BPLock = False
            cmu.GMacdSP = lastMacd
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


cmu.Plot(ax1,ax2)
ax1.scatter(timeBP,dataBP,marker='o',c='w',edgecolors='g')
ax1.scatter(timeSP,dataSP,marker='o',c='m',edgecolors='m')
squ.Plot(squData, ax3)

cmu4.Plot(ax4,ax5)
ax4.scatter(timeBPHigh,dataBPHigh,marker='o',c='w',edgecolors='g')
ax4.scatter(timeSPHigh,dataSPHigh,marker='o',c='m',edgecolors='m')
squ4.Plot(squData4, ax6)
squ4.PlotDerivate(squData4, ax7)

ax8.plot(goalTime, goals, label="goals")
plt.show()

