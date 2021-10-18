from pymongo import database
from strategy.CmMacd import cm
from strategy.Squeeze import squeeze
import datetime
import time

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
symbols = ["btcusdt"]
CmUnits = []
Cm4Units = []
SquUnits = []
cmGoals = [0]*len(symbols)
squGoals = [0]*len(symbols)
for symbol in symbols:
    cmu = cm.CmUnit(conn_str, "marketinfo", symbol, "30min", 300)
    cmu.RunOnce()
    CmUnits.append(cmu)

    cmu4 = cm.CmUnit(conn_str, "marketinfo", "btcusdt", "4hour", 75)
    cmu4.RunOnce()
    Cm4Units.append(cmu4)

    squ = squeeze.SqueezeUnit(conn_str, "marketinfo", "btcusdt", "30min", 80)
    while squ.preState.timeID < cmu.TimeID:
        newTurn, indicator, timeID, val, slope, scolor, bcolor, slopeColor = squ.RunOnce()
        squ.updatePreState(timeID, val, slope, scolor, bcolor, slopeColor)
    print("%s timeid cm: %d, squ: %d"%(cmu.collectionName, cmu.TimeID, squ.preState.timeID))
    SquUnits.append(squ)

utcStart = time.time()
print(utcStart)
while True:
    if cmu.TimeID > (utcStart - 3600):
        time.sleep(30.0)
    for idx in range(len(symbols)):
        gGoal = 0
        cmu = CmUnits[idx]
        cmu4 = Cm4Units[idx]
        squ = SquUnits[idx]
        
        # cmmacd
        indicator, closePrice, lastMacd, lastSlowMA, stdMA, err = cmu.RunOnce()
        if err == "no new":
            continue
        if err == "nil":
            cp = closePrice
        if indicator == "buy":
            cmu.PrevBP = lastMacd
            cmGoals[idx] = 1
            if lastMacd < cmu.GMacdBP:
                cmu.GMacdBP = lastMacd
            if (cmu.GMacdSP-lastMacd)/lastSlowMA > 0.954*stdMA:
                cmGoals[idx] = 2
        if indicator == "sell":
            cmu.PrevSP = lastMacd
            cmGoals[idx] = -1
            if lastMacd > cmu.GMacdSP:
                cmu.GMacdSP = lastMacd
            if (lastMacd-cmu.GMacdBP)/lastSlowMA > 0.954*stdMA:
                cmGoals[idx] = -2

        # cmmacd high level
        if cmu.TimeID + cmu.Offset == cmu4.TimeID + 2*cmu4.Offset:
            indicatorH, closePriceH, lastMacd, lastSlowMA, stdMA, err = cmu4.RunOnce()
            if err == "no new":
                timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f = open('out.log','a+')
                outStr = "%s HB-%s hight level cmacd no new data found"%(timeNow, cmu4.symbol)
                print(outStr, file=f)
                f.close()
            if err == "conn failed":
                timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f = open('out.log','a+')
                outStr = "%s HB-%s hight level cmacd conn failed!"%(timeNow, cmu4.symbol)
                print(outStr, file=f)
                f.close()    
        
        # squeeze
        newTurn, indicatorS, timeID, val, slope, scolor, bcolor, slopeColor = squ.RunOnce()
        colorChange = False
        if not newTurn:
            continue
        if scolor == "gray":
            if bcolor == "lime" and squ.preState.scolor == "black":
                # up
                squGoals[idx] = 1
            if bcolor == "maroon" and squ.preState.bcolor == "red":
                squGoals[idx] = 0.5

            if bcolor == "red" and squ.preState.scolor == "black":
                # down
                squGoals[idx] = -1
            if bcolor == "green" and squ.preState.bcolor == "lime":
                squGoals[idx] = -0.5
        else:
            if squGoals[idx] > 0 and (bcolor == "red" or bcolor == "maroon"):
                squGoals[idx] = 0
            if squGoals[idx] < 0 and (bcolor == "lime" or bcolor == "green"):
                squGoals[idx] = 0
        squ.updatePreState(timeID, val, slope, scolor, bcolor, slopeColor)

        if squ.preState.timeID != cmu.TimeID:
            f = open('out.log','a+')
            print("%s wrong time id! squ: %d, cmu: %d"%(cmu.collectionName, squ.preState.timeID, cmu.TimeID), file = f)
            f.close()
            continue
        
        # calcu gGoal
        date = datetime.datetime.fromtimestamp(cmu.TimeID).strftime('%Y-%m-%d %H:%M:%S')
        gGoal =  cmGoals[idx] + squGoals[idx]
        f = open('out.log','a+')
        print("%s %s timeID: %d, BPLock: %r, SPLock: %r, gGoal: %d, cmGoal: %f, squGoal: %f"%(date, cmu.collectionName, cmu.TimeID, cmu.BPLock, cmu.SPLock, gGoal, cmGoals[idx], squGoals[idx]), file = f)
        f.close()
        if gGoal >= 3:
            #buy
            if not cmu.BPLock:
                cmu.BPLock = True
                cmu.SPLock = False
                cmu.GMacdBP = lastMacd
                f = open('out.log','a+')
                if cmu.TimeID > utcStart:
                    cmu.AlarmAndAction(cmu.collectionName, cmu.symbol, cmu.period, "buy", f)
                print("%s %s Bought, indicator: %s, ts: %d, close: %f"%(date, cmu.collectionName, indicator, cmu.TimeID, closePrice), file = f)
                f.close()
        if gGoal <= -3:
            if not cmu.SPLock:
                cmu.SPLock = True
                cmu.BPLock = False
                cmu.GMacdSP = lastMacd
                f = open('out.log','a+')
                if cmu.TimeID > utcStart:
                    cmu.AlarmAndAction(cmu.collectionName, cmu.symbol, cmu.period, "sell", f)
                print("%s %s Sold,   indicator: %s, ts: %d, close: %f"%(date, cmu.collectionName, indicator, cmu.TimeID, closePrice), file = f)
                f.close()
