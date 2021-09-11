from enum import Flag
from os import close, truncate
from re import L, T
import sys

import numpy as np
from numpy.lib.index_tricks import ix_
from numpy.lib.twodim_base import triu_indices_from

import indicators
sys.path.append('..')
import builtIndicators
from indicators import CMMACD
import strategy.baseObj
import utils.ticker
import pymongo
import chomoClient.client
from alert import alert
import datetime
import pandas as pd
import matplotlib.pyplot as plt

class CmMacd(strategy.baseObj.baseObjSpot):
    def LoadDB(self, db):
        'choose the db collection'
        self.DB = self.MgoClient[db]

    def RunV2Re(self, symbols, baseWindowLen=300, basePeriod="30min"):
        baseUnits = []
        for idx in range(len(symbols)):
            CmUBase = CmUnit(symbols[idx], basePeriod, baseWindowLen, False, True, -999999, 999999, False, False, 0, 0, 0)
            baseUnits.append(CmUBase)
        self.InitModelV2(symbols, baseUnits)
        # loop
        while True:
            t = utils.ticker.Ticker("1min")
            t.Loop()
            for idx in range(len(symbols)):
                f = open('out.log','a+')
                timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                baseUnit = baseUnits[idx]

                # check new candle updated.
                try:                    
                    DBcursor = baseUnit.Collection.find().sort('id', pymongo.DESCENDING).limit(1)
                except:
                    errStr = "%s Error: HB-%s DB Connection failed"%(timeNow, baseUnit.Symbol)
                    print(errStr, file=f)
                    f.close()
                    continue
                else:
                    for doc in DBcursor:
                        if doc["id"] > baseUnit.Data[len(baseUnit.Data)-1]["id"]:
                            # base level updated
                            BaseCollection = "HB-%s-%s"%(baseUnit.Symbol,baseUnit.Period)
                            action = "nill   "
                            baseUnit.Data = baseUnit.Data[1:]
                            baseUnit.Data.append(doc)
                            indicator, Brought, Sold, closePrice = baseUnit.CmCoreOnePage()
                            if Brought == True:
                                action = "Brought"
                                self.AlarmAndAction(BaseCollection, baseUnit.Symbol, baseUnit.Period, "buy", f)
                            if Sold == True:
                                action = "Sold   "
                                self.AlarmAndAction(BaseCollection, baseUnit.Symbol, baseUnit.Period, "sell", f)
                            outStr = "%s %s %s, indicator:%s, ts: %d, BPLock: %r, SPLock: %r, mustBuy: %r, mustSell: %r, gMacdBP: %f, gMacdSP: %f, timeID: %d, prevFastMA: %f, preSlowMA: %f, prevMA30: %f" \
                                %(timeNow, BaseCollection, action, indicator, baseUnit.TimeID, baseUnit.BPLock, baseUnit.SPLock, baseUnit.MustBuy, baseUnit.MustSell, baseUnit.GMacdBP, baseUnit.GMacdSP, baseUnit.TimeID, baseUnit.PrevFastMA, baseUnit.PreSlowMA, baseUnit.PrevMA30)
                            print(outStr, file = f)
                        else:
                            outStr = "%s HB-%s check once: ts: %d, BPLock: %r, SPLock: %r, mustBuy: %r, mustSell: %r, gMacdBP: %f, gMacdSP: %f, timeID: %d, prevFastMA: %f, preSlowMA: %f, prevMA30: %f"\
                                %(timeNow, baseUnit.Symbol, baseUnit.TimeID, baseUnit.BPLock, baseUnit.SPLock, baseUnit.MustBuy, baseUnit.MustSell, baseUnit.GMacdBP, baseUnit.GMacdSP, baseUnit.TimeID, baseUnit.PrevFastMA, baseUnit.PreSlowMA, baseUnit.PrevMA30)
                            print(outStr, file=f)
                    f.close()
        
    def RunV3(self, symbols, baseWindowLen=400, basePeriod="30min", highPeriod="4hour"):
        'V3 is conservative. \
         When higher K candle suffered a down cm cross, V3 will wait and only could do SELL action'        
        baseUnits = []
        highUnits = []
        for idx in range(len(symbols)):
            CmUBase = CmUnit(symbols[idx], basePeriod, baseWindowLen, False, True, -999999, 999999, False, False, 0, 0, 0)
            CmUHigh = CmUnit(symbols[idx], highPeriod, baseWindowLen/8, False, True, -999999, 999999, False, False, 0, 0, 0)
            baseUnits.append(CmUBase)
            highUnits.append(CmUHigh)
        
        self.InitModelV3(symbols, baseUnits, highUnits)
        # loop
        while True:
            t = utils.ticker.Ticker("1min")
            t.Loop()
            for idx in range(len(symbols)):
                f = open('out.log','a+')
                timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                baseUnit = baseUnits[idx]
                highUnit = highUnits[idx]
                outStr = "%s HB-%s check once"%(timeNow, baseUnit.Symbol)
                print(outStr, file=f)

                # check high level update
                DBcursor = highUnit.Collection.find().sort('id', pymongo.DESCENDING).limit(1)
                for doc in DBcursor:
                    if doc["id"] > highUnit.Data[len(highUnit.Data)-1]["id"]:
                        # high level updated
                        HighCollection = "HB-%s-%s"%(highUnit.Symbol,highUnit.Period)
                        highUnit.Data = highUnit.Data[1:]
                        highUnit.Data.append(doc)
                        indicator, Brought, Sold, closePrice = highUnit.CmCoreWithoutMustSignal()
                        if Brought == True:
                            outStr = "%s, %s, Brought, indicator:%s, ts: %d, "%(timeNow, HighCollection, indicator, highUnit.TimeID)
                            print(outStr, file = f)
                            baseUnit.RiseFlag = True
                            baseUnit.ChomoTime = highUnit.TimeID
                        if Sold == True:
                            outStr = "%s, %s, Sold,    indicator:%s, ts: %d, "%(timeNow, HighCollection, indicator, highUnit.TimeID)
                            print(outStr, file = f)
                            baseUnit.RiseFlag = False
                            baseUnit.ChomoTime = highUnit.TimeID
                    
                DBcursor = baseUnit.Collection.find().sort('id', pymongo.DESCENDING).limit(1)
                for doc in DBcursor:
                    if doc["id"] > baseUnit.Data[len(baseUnit.Data)-1]["id"]:
                        # base level updated
                        BaseCollection = "HB-%s-%s"%(baseUnit.Symbol,baseUnit.Period)
                        action = "nill   "
                        baseUnit.Data = baseUnit.Data[1:]
                        baseUnit.Data.append(doc)
                        indicator, Brought, Sold, closePrice = baseUnit.CmCoreOnePage()
                        if Brought == True:
                            action = "Brought"
                            self.AlarmAndAction(BaseCollection, baseUnit.Symbol, baseUnit.Period, "buy", f)
                        if Sold == True:
                            action = "Sold   "
                            self.AlarmAndAction(BaseCollection, baseUnit.Symbol, baseUnit.Period, "sell", f)
                        outStr = "%s, %s, %s, indicator:%s, ts: %d, BPLock: %r, SPLock: %r, mustBuy: %r, mustSell: %r, gMacdBP: %f, gMacdSP: %f, timeID: %d, prevFastMA: %f, preSlowMA: %f, prevMA30: %f" \
                            %(timeNow, BaseCollection, action, indicator, baseUnit.TimeID, baseUnit.BPLock, baseUnit.SPLock, baseUnit.MustBuy, baseUnit.MustSell, baseUnit.GMacdBP, baseUnit.GMacdSP, baseUnit.TimeID, baseUnit.PrevFastMA, baseUnit.PreSlowMA, baseUnit.PrevMA30)
                        print(outStr, file = f)
                f.close()

    def InitModelV2(self, symbols, baseUnits):
        for idx in range(len(symbols)):
            f = open('out.log','a+')
            baseUnit = baseUnits[idx]
            BaseData = []
            collection = "HB-%s-%s"%(baseUnit.Symbol, baseUnit.Period)
            baseUnit.SetCollection(self.DB[collection])
            BaseCount = baseUnit.Collection.find().sort('id', pymongo.ASCENDING).count()
            DBcursorAll = baseUnit.Collection.find().sort('id', pymongo.ASCENDING)
            for doc in DBcursorAll:
                BaseData.append(doc)
            baseUnit.SetData(BaseData[:baseUnit.WindowLen])

            # loop
            for i in range(BaseCount-baseUnit.WindowLen):
                DBcursor = baseUnit.Collection.find().sort('id', pymongo.ASCENDING).skip(i+baseUnit.WindowLen).limit(1)
                for doc in DBcursor:
                    baseUnit.Data = baseUnit.Data[1:]
                    baseUnit.Data.append(doc)
                indicator, Brought, Sold, closePrice = baseUnit.CmCoreOnePage()
                date = datetime.datetime.fromtimestamp(baseUnit.TimeID).strftime('%Y-%m-%d %H:%M:%S')
                if Brought == True:
                    print("%s, HB-%s-%s, Brought, indicator: %s, ts: %d, close: %f, amount: %f, round: %d/%d"%(date, baseUnit.Symbol, baseUnit.Period, indicator, baseUnit.TimeID, closePrice, baseUnit.Amount, i+baseUnit.WindowLen, BaseCount), file = f)
                if Sold == True:
                    print("%s, HB-%s-%s, Sold   , indicator: %s, ts: %d, close: %f, Money:  %f, round: %d/%d"%(date, baseUnit.Symbol, baseUnit.Period, indicator, baseUnit.TimeID, closePrice, baseUnit.Money, i+baseUnit.WindowLen, BaseCount), file = f)
            print("%s initially done. BPLock: %r, SPLock: %r, mustBuy: %r, mustSell: %r, gMacdBP: %f, gMacdSP: %f, timeID: %d, prevFastMA: %f, preSlowMA: %f, prevMA30: %f" \
                    %(collection, baseUnit.BPLock, baseUnit.SPLock, baseUnit.MustBuy, baseUnit.MustSell, baseUnit.GMacdBP, baseUnit.GMacdSP, baseUnit.TimeID, baseUnit.PrevFastMA, baseUnit.PreSlowMA, baseUnit.PrevMA30), file = f)
            f.close()

    def InitModelV3(self, symbols, baseUnits, highUnits):
        for idx in range(len(symbols)):
            timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f = open('out.log','a+')
            baseUnit = baseUnits[idx]
            highUnit = highUnits[idx]
            
            BaseData = []
            collection = "HB-%s-%s"%(baseUnit.Symbol, baseUnit.Period)
            baseUnit.SetCollection(self.DB[collection])
            BaseCount = baseUnit.Collection.find().sort('id', pymongo.ASCENDING).count()
            DBcursorAll = baseUnit.Collection.find().sort('id', pymongo.ASCENDING)
            for doc in DBcursorAll:
                BaseData.append(doc)
            baseUnit.SetData(BaseData[:baseUnit.WindowLen])

            HighData = []
            collection = "HB-%s-%s"%(highUnit.Symbol, highUnit.Period)
            highUnit.SetCollection(self.DB[collection])
            HighCount = highUnit.Collection.find().sort('id', pymongo.ASCENDING).count()
            DBcursorAll = highUnit.Collection.find().sort('id', pymongo.ASCENDING)
            for docAll in DBcursorAll:
                HighData.append(docAll)
            highUnit.SetData(HighData[:highUnit.WindowLen])

            # loop
            j = baseUnit.WindowLen
            for i in range(HighCount - highUnit.WindowLen):
                DBcursor = highUnit.Collection.find().sort('id', pymongo.ASCENDING).skip(i+highUnit.WindowLen).limit(1)
                for doc in DBcursor:
                    highUnit.Data = highUnit.Data[1:]
                    highUnit.Data.append(doc)
                indicator, Brought, Sold, closePrice = highUnit.CmCoreWithoutMustSignal()
                date = datetime.datetime.fromtimestamp(highUnit.TimeID).strftime('%Y-%m-%d %H:%M:%S')
                if Brought == True:
                    print("%s, HB-%s-%s, Brought, indicator:%s, ts: %d, close: %f, amount: %f, round: %d/%d"%(date, highUnit.Symbol, highUnit.Period, indicator, highUnit.TimeID, closePrice, highUnit.Amount, i+1, HighCount-highUnit.WindowLen), file = f)
                    baseUnit.RiseFlag = True
                    baseUnit.ChomoTime = highUnit.TimeID
                if Sold == True:
                    print("%s, HB-%s-%s, Sold   , indicator:%s, ts: %d, close: %f, Money:  %f, round: %d/%d"%(date, highUnit.Symbol, highUnit.Period, indicator, highUnit.TimeID, closePrice, highUnit.Money, i+1, HighCount-highUnit.WindowLen), file = f)
                    baseUnit.RiseFlag = False
                    baseUnit.ChomoTime = highUnit.TimeID
                
                while j < BaseCount:
                    OverID = False
                    DBcursor = baseUnit.Collection.find().sort('id', pymongo.ASCENDING).skip(j).limit(1)
                    for doc in DBcursor:
                        LatestTimeID = doc["id"]
                        if LatestTimeID >= highUnit.TimeID + 4*3600:
                            # over High Time ID.
                            OverID = True
                            break
                        baseUnit.Data = baseUnit.Data[1:]
                        baseUnit.Data.append(doc)
                    if OverID:
                        BaseCollection = "HB-%s-%s"%(baseUnit.Symbol,baseUnit.Period)
                        outStr = "%s, %s, Warning: Found baseUnit ID Over HighUnit! base ID:%s, high ID:%s"%(timeNow, BaseCollection, LatestTimeID, highUnit.TimeID + 4*3600)
                        print(outStr, file=f)
                        break
                    indicator, Brought, Sold, closePrice = baseUnit.CmCoreOnePage()
                    date = datetime.datetime.fromtimestamp(baseUnit.TimeID).strftime('%Y-%m-%d %H:%M:%S')
                    if Brought == True:
                        print("%s, HB-%s-%s, Brought, indicator: %s, ts: %d, close: %f, amount: %f, round: %d/%d"%(date, baseUnit.Symbol, baseUnit.Period, indicator, baseUnit.TimeID, closePrice, baseUnit.Amount, j+1, BaseCount), file = f)
                    if Sold == True:
                        print("%s, HB-%s-%s, Sold   , indicator: %s, ts: %d, close: %f, Money:  %f, round: %d/%d"%(date, baseUnit.Symbol, baseUnit.Period, indicator, baseUnit.TimeID, closePrice, baseUnit.Money, j+1, BaseCount), file = f)
                    j += 1
            print("%s initially done. BPLock: %r, SPLock: %r, mustBuy: %r, mustSell: %r, gMacdBP: %f, gMacdSP: %f, timeID: %d, prevFastMA: %f, preSlowMA: %f, prevMA30: %f" \
                 %(collection, baseUnit.BPLock, baseUnit.SPLock, baseUnit.MustBuy, baseUnit.MustSell, baseUnit.GMacdBP, baseUnit.GMacdSP, baseUnit.TimeID, baseUnit.PrevFastMA, baseUnit.PreSlowMA, baseUnit.PrevMA30), file = f)
            f.close()

    def getAccountBalance(self, currency):
        'get currency balance'
        balance = chomoClient.client.GetAccountBalance(currency)
        print("the currency: ", currency, "amount: ", balance)
        return balance
        
    def AlarmAndAction(self, collection, symbol, period, indicator, outlog):
        timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if indicator == "buy":
            alertText = "%s HuoBi %s: will rise!!! buy now!"%(timeNow, collection)
            print(alertText,file=outlog)
            if symbol == "btcusdt":
                self.Buy()
            for i in range(2):
                text = "HuoBi %s-%s: 要涨了!!! 现在买入! 当前时间: %s, 报警提醒次数(%d/2)" %(symbol,period,timeNow,i+1)
                alert.Alert(text)
        if indicator == "sell":
            alertText = "%s HuoBi %s: will descend!!! sell quickly!"%(timeNow, collection)
            print(alertText,file=outlog)
            if symbol == "btcusdt":
                self.Sell()
            for i in range(2):
                text = "HuoBi %s-%s: 要跌了!!! 赶紧卖掉! 当前时间: %s, 报警提醒次数(%d/2)" %(symbol,period,timeNow,i+1)
                alert.Alert(text)

    def Buy(self):
        amount = self.getAccountBalance("usdt")
        if float(amount) > 15.0:
            'Buy'
            chomoClient.client.PlaceOrder("btcusdt", "buy-market", amount, "100", "spot-api")
        else:
            print("But not enought usdt, do not buy btc.")
    
    def Sell(self):
        amount = self.getAccountBalance("btc")
        if float(amount) > 0.000001:
            chomoClient.client.PlaceOrder("btcusdt", "sell-market", amount, "100", "spot-api")
        else:
            print("But not enought btc, do not sell btc.")
    
    def CMTest(self, symbol, period, winLen):
        baseUnit = CmUnit(symbol, period, winLen, False, True, -999999, 999999, False, False, 0, 0, 0)
        MoneyInitial = baseUnit.Money
        AmountInitial = baseUnit.Amount
        f = open('cmTest.log','a+')
        BaseData = []
        collection = "HB-%s-%s"%(baseUnit.Symbol, baseUnit.Period)
        baseUnit.SetCollection(self.DB[collection])
        BaseCount = baseUnit.Collection.find().sort('id', pymongo.ASCENDING).count()
        DBcursorAll = baseUnit.Collection.find().sort('id', pymongo.ASCENDING)
        for doc in DBcursorAll:
            BaseData.append(doc)
        baseUnit.SetData(BaseData[:baseUnit.WindowLen])

        # loop
        timeBP = [] 
        timeSP = []
        dataSP = []
        dataBP = []
        timeBPA = []
        timeSPA = []
        dataBPA = []
        dataSPA = []
        for i in range(BaseCount-baseUnit.WindowLen):
            DBcursor = baseUnit.Collection.find().sort('id', pymongo.ASCENDING).skip(i+baseUnit.WindowLen).limit(1)
            for doc in DBcursor:
                baseUnit.Data = baseUnit.Data[1:]
                baseUnit.Data.append(doc)
                indicator, Brought, Sold, closePrice = baseUnit.CmCoreOnePage()
                date = datetime.datetime.fromtimestamp(baseUnit.TimeID).strftime('%Y-%m-%d %H:%M:%S')
                if indicator == "buy":
                    timeBPA.append(doc["id"])
                    dataBPA.append(doc["close"])
                if indicator == "sell":
                    timeSPA.append(doc["id"])
                    dataSPA.append(doc["close"])
                if Brought == True:
                    timeBP.append(doc["id"])
                    dataBP.append(doc["close"])
                    print("%s, HB-%s-%s, Brought, indicator: %s, ts: %d, close: %f, amount: %f, round: %d/%d"%(date, baseUnit.Symbol, baseUnit.Period, indicator, baseUnit.TimeID, closePrice, baseUnit.Amount, i+baseUnit.WindowLen, BaseCount), file = f)
                if Sold == True:
                    timeSP.append(doc["id"])
                    dataSP.append(doc["close"])
                    print("%s, HB-%s-%s, Sold,    indicator: %s, ts: %d, close: %f, Money:  %f, round: %d/%d"%(date, baseUnit.Symbol, baseUnit.Period, indicator, baseUnit.TimeID, closePrice, baseUnit.Money, i+baseUnit.WindowLen, BaseCount), file = f)
        RateOfReturn = 0.0
        if baseUnit.Money == 0:
            RateOfReturn = doc["close"] * baseUnit.Amount / MoneyInitial - 1.0
        elif baseUnit.Amount == 0:
            RateOfReturn = baseUnit.Money / MoneyInitial - 1.0
        print("%s back test done. Rate of Return:%f" \
                %(collection, RateOfReturn), file = f)
        f.close()

        dataAll = []
        DBcursorAll = baseUnit.Collection.find().sort('id', pymongo.ASCENDING)
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
        fig, (ax1, ax2, ax3) = plt.subplots(3,1,sharex=True,figsize=(8,12), facecolor="gray")
        fastMAAll = builtIndicators.ma.EMA(closeAll,5)
        slowMAAll = builtIndicators.ma.EMA(closeAll,10)
        #ax1.set_facecolor('dimgrey')
        ax1.plot(timeAll, closeAll, color='gray', label="close")
        ax1.plot(timeAll, fastMAAll, color='y', label="MA30")
        ax1.plot(timeAll, slowMAAll, color='g', label="MA30")
        ax1.plot(timeAll, MA30All, color='m', label="MA30")
        ax1.scatter(timeBPA,dataBPA,marker='^',c='g',edgecolors='g')
        ax1.scatter(timeSPA,dataSPA,marker='v',c='r',edgecolors='r')

        #ax2.set_facecolor('dimgrey')
        ax2.plot(timeAll, closeAll, color='gray', label="close")
        ax2.scatter(timeBP,dataBP,marker='o',c='w',edgecolors='g')
        ax2.scatter(timeSP,dataSP,marker='o',c='m',edgecolors='m')

        # plot cross dots between Macd and signal
        crossIndexSell, crossIndexBuy= builtIndicators.cross.cross(MACD,signal)
        crossTimesSell = [timeAll[ci] for ci in crossIndexSell]
        crossSell = [signal[ci] for ci in crossIndexSell]
        crossTimesBuy = [timeAll[ci] for ci in crossIndexBuy]
        crossBuy = [signal[ci] for ci in crossIndexBuy]
        #ax3.set_facecolor('dimgrey')
        ax3.plot(timeAll, MACD, label="MACD")
        ax3.plot(timeAll, signal, label="signal")
        ax3.scatter(crossTimesSell,crossSell,marker='o',c='r',edgecolors='r')
        ax3.scatter(crossTimesBuy,crossBuy,marker='o',c='g',edgecolors='g')
        ax3.bar(timeAll,hist,width=600,label="hist")
        plt.show()
    
    def CMTest30MinAnd4Hour(self,windowLen,symbol):
        'Standard Back Test of CMMACD'
        timeAll = []
        closeAll = []
        timeBPA = []
        timeSPA = []
        dataBPA = []
        dataSPA = []
        timeBP = []
        timeSP = []
        dataBP = []
        dataSP = []
        CmU30min = CmUnit("btcusdt", "30min", 400, False, True, -999999, 999999, False, False, 0, 0, 0)
        timeBP4h = []
        timeSP4h = []
        dataBP4h = []
        dataSP4h = []
        CmU4h = CmUnit("btcusdt", "4hour", 50, False, True, -999999, 999999, False, False, 0, 0, 0)
        

        dataAll = []
        collection = "HB-%s-30min"%(symbol)
        CmU30min.SetCollection(self.DB[collection])
        tCount = CmU30min.Collection.find().sort('id', pymongo.ASCENDING).count()
        DBcursorAll = CmU30min.Collection.find().sort('id', pymongo.ASCENDING)
        for docAll in DBcursorAll:
            dataAll.append(docAll)
        df = pd.DataFrame(dataAll)
        timeAll = df["id"]
        closeAll = df["close"]
        data = dataAll[:windowLen]
        CmU30min.SetData(data)
        fastMAAll = builtIndicators.ma.EMA(closeAll,5)
        slowMAAll = builtIndicators.ma.EMA(closeAll,10)
        MA30All = builtIndicators.ma.EMA(closeAll,30)

        dataAll4h = []
        windowLen4h = int(windowLen/8)
        collection4h = "HB-%s-4hour"%(symbol)
        CmU4h.SetCollection(self.DB[collection4h])
        tCount4h = CmU4h.Collection.find().sort('id', pymongo.ASCENDING).count()
        DBcursorAll4h = CmU4h.Collection.find().sort('id', pymongo.ASCENDING)
        for docAll in DBcursorAll4h:
            dataAll4h.append(docAll)
        data4h = dataAll4h[:windowLen4h]
        CmU4h.SetData(data4h)

        # loop
        j = windowLen
        for i in range(tCount4h - windowLen4h):
            DBcursor = CmU4h.Collection.find().sort('id', pymongo.ASCENDING).skip(i+windowLen4h).limit(1)
            for doc in DBcursor:
                CmU4h.Data = CmU4h.Data[1:]
                CmU4h.Data.append(doc)
            indicator, Brought, Sold, closePrice = CmU4h.CmCoreWithoutMustSignal()
            date = datetime.datetime.fromtimestamp(CmU4h.TimeID).strftime('%Y-%m-%d %H:%M:%S')
            if Brought == True:
                print("%s, 4hour buy point found,  ts: %d, close: %f, amount: %f,    round: %d/%d"%(date, CmU4h.TimeID, closePrice, CmU4h.Amount, i+1, tCount4h-windowLen4h))
                CmU30min.RiseFlag = True
                CmU30min.ChomoTime = CmU4h.TimeID
                dataBP4h.append(closePrice)
                timeBP4h.append(CmU4h.TimeID)
            if Sold == True:
                print("%s, 4hour sell point found, ts: %d, close: %f, Money:  %f, round: %d/%d"%(date, CmU4h.TimeID, closePrice, CmU4h.Money, i+1, tCount4h-windowLen4h))
                CmU30min.RiseFlag = False
                CmU30min.ChomoTime = CmU4h.TimeID
                dataSP4h.append(closePrice)
                timeSP4h.append(CmU4h.TimeID)
            
            while j < tCount:
                date = datetime.datetime.fromtimestamp(CmU30min.TimeID).strftime('%Y-%m-%d %H:%M:%S')
                OverID = False
                DBcursor = CmU30min.Collection.find().sort('id', pymongo.ASCENDING).skip(j).limit(1)
                for doc in DBcursor:
                    LatestTimeID = doc["id"]
                    if LatestTimeID >= CmU4h.TimeID + 4*3600:
                        # over High Time ID.
                        OverID = True
                        break
                    CmU30min.Data = CmU30min.Data[1:]
                    CmU30min.Data.append(doc)
                if OverID:
                    BaseCollection = "HB-%s-%s"%(symbol,"30min")
                    outStr = "%s, %s, Warning: Found baseUnit ID Over HighUnit! base ID:%s, high ID:%s "%(date, BaseCollection, LatestTimeID, CmU4h.TimeID + 4*3600)
                    print(outStr)
                    break
                
                indicator, Brought, Sold, closePrice = CmU30min.CmCoreOnePage()
                if indicator == "buy":
                    dataBPA.append(closePrice)
                    timeBPA.append(CmU30min.TimeID)
                if indicator == "sell":
                    dataSPA.append(closePrice)
                    timeSPA.append(CmU30min.TimeID)
                if Brought == True:
                    print("%s, buy, indicator: %s, ts: %d, close: %f, amount: %f,    round: %d/%d"%(date, indicator, CmU30min.TimeID, closePrice, CmU30min.Amount, j+1, tCount))
                    dataBP.append(closePrice)
                    timeBP.append(CmU30min.TimeID)
                if Sold == True:
                    print("%s, sell, indicator: %s, ts: %d, close: %f, Money:  %f, round: %d/%d"%(date, indicator, CmU30min.TimeID, closePrice, CmU30min.Money, j+1, tCount))
                    dataSP.append(closePrice)
                    timeSP.append(CmU30min.TimeID)
                j += 1
                    
        RateOfReturn = 0.0
        if CmU30min.Money == 0:
            RateOfReturn = closePrice * CmU30min.Amount / 10000.0 - 1.0
        elif CmU30min.Amount == 0:
            RateOfReturn = CmU30min.Money / 10000.0 - 1.0
        print("Rate of Return in %s is %f, Money:%f, amount:%f, closePrice:%f"%(symbol, RateOfReturn, CmU30min.Money, CmU30min.Amount, closePrice))
        fastMA = builtIndicators.ma.EMA(closeAll,12)
        slowMA = builtIndicators.ma.EMA(closeAll,26)
        MACD = fastMA - slowMA
        signal = builtIndicators.ma.SMA(MACD,9)
        hist = MACD - signal
        crossIndexSell, crossIndexBuy= builtIndicators.cross.cross(MACD,signal)
        crossTimesSell = [timeAll[ci] for ci in crossIndexSell]
        crossSell = [signal[ci] for ci in crossIndexSell]
        crossTimesBuy = [timeAll[ci] for ci in crossIndexBuy]
        crossBuy = [signal[ci] for ci in crossIndexBuy]

        f, (ax1, ax2, ax3) = plt.subplots(3,1,sharex=True,figsize=(8,12))
        ax1.plot(timeAll, closeAll, color='gray', label="close")
        ax1.plot(timeAll, fastMAAll, color='y', label="MA30")
        ax1.plot(timeAll, slowMAAll, color='g', label="MA30")
        ax1.plot(timeAll, MA30All, color='m', label="MA30")
        ax1.scatter(timeBPA,dataBPA,marker='^',c='g',edgecolors='g')
        ax1.scatter(timeSPA,dataSPA,marker='v',c='r',edgecolors='r')

        ax2.plot(timeAll, closeAll, color='gray', label="close")
        ax2.scatter(timeBP,dataBP,marker='o',c='w',edgecolors='g')
        ax2.scatter(timeSP,dataSP,marker='o',c='m',edgecolors='m')
        ax2.scatter(timeBP4h,dataBP4h,marker='^',c='g',edgecolors='g')
        ax2.scatter(timeSP4h,dataSP4h,marker='v',c='r',edgecolors='r')

        ax3.plot(timeAll, MACD, label="MACD")
        ax3.plot(timeAll, signal, label="signal")
        ax3.scatter(crossTimesSell,crossSell,marker='o',c='r',edgecolors='r')
        ax3.scatter(crossTimesBuy,crossBuy,marker='o',c='g',edgecolors='g')
        ax3.bar(timeAll,hist,width=600,label="hist")
        plt.show()

class CmUnit:
    def __init__(self, symbol, period, winLen, BPLock, SPLock, GMacdBP, GMacdSP, MustBuy, MustSell, PrevFastMA, PreSlowMA, PrevMA30):
        self.Symbol = symbol
        self.Period = period
        self.WindowLen = int(winLen)
        self.BPLock = BPLock
        self.SPLock = SPLock
        self.RiseFlag = True
        self.DownFlag = True
        self.GMacdBP = GMacdBP
        self.GMacdSP = GMacdSP
        self.TimeID = 0
        self.ChomoTime = 0
        self.MustBuy = MustBuy
        self.MustSell = MustSell
        self.PrevFastMA = PrevFastMA
        self.PreSlowMA = PreSlowMA
        self.PrevMA30 = PrevMA30

        self.TradePrice = 0
        self.CurFastMA = 0
        self.CurSlowMA = 0
        self.CurMA30 = 0
        self.Money = 10000.0
        self.Amount = 0.0

    def SetCollection(self, c):
        self.Collection = c
    
    def SetData(self, data):
        self.Data = data

    def CmCoreOnePage(self):
        CanBuy = False
        Brought = False
        Sold = False
        indicator,timeID,closePrice,lastMacd,lastSlowMA,stdMA= CMMACD.CmIndicator(self.Data)

        if self.RiseFlag == True:
            if timeID >= self.ChomoTime:
                CanBuy = True
        
        if self.RiseFlag == False:
            if timeID <= self.ChomoTime:
                CanBuy = True
        
        self.TimeID = timeID
        if indicator == "nothing" :
            if CanBuy and self.MustBuy and not self.BPLock:
                self.GMacdBP = lastMacd # optional
                self.BPLock = True
                self.SPLock = False
                self.MustBuy = False
                self.MustSell = False
                self.Amount = self.Money / closePrice * 0.998
                self.Money = 0
                Brought = True
            elif self.MustSell and not self.SPLock:
                self.GMacdSP = lastMacd # optional
                self.SPLock = True
                self.BPLock = False
                self.MustSell = False
                self.MustBuy = False
                self.Money = self.Amount * closePrice * 0.998
                self.Amount = 0
                Sold = True

        if indicator == "buy":
            up, down, self.PrevFastMA, self.PreSlowMA, self.PrevMA30 = self.GenMustSignal(self.Data, self.PrevFastMA, self.PreSlowMA, self.PrevMA30)
            self.MustSell = down
            if CanBuy and not self.MustSell and not self.BPLock and ((self.MustBuy or (self.GMacdSP-lastMacd)/lastSlowMA > stdMA)):
                self.BPLock = True
                self.SPLock = False
                self.GMacdBP = lastMacd
                self.Amount = self.Money / closePrice * 0.998
                self.Money = 0
                self.MustBuy = False
                Brought = True
            elif lastMacd < self.GMacdBP:
                self.GMacdBP = lastMacd

        if indicator == "sell":
            up, down, self.PrevFastMA, self.PreSlowMA, self.PrevMA30 = self.GenMustSignal(self.Data, self.PrevFastMA, self.PreSlowMA, self.PrevMA30)
            self.MustBuy = up
            if not self.MustBuy and not self.SPLock and (self.MustSell or (lastMacd-self.GMacdBP)/lastSlowMA > stdMA):
                self.SPLock = True
                self.BPLock = False
                self.GMacdSP = lastMacd
                self.Money = self.Amount * closePrice * 0.998
                self.Amount = 0
                self.MustSell = False
                Sold = True
            elif lastMacd > self.GMacdSP:
                self.GMacdSP = lastMacd
        return indicator, Brought, Sold, closePrice

    def CmCoreWithoutMustSignal(self):
        CanBuy = False
        Brought = False
        Sold = False
        indicator,timeID,closePrice,lastMacd,lastSlowMA,stdMA= CMMACD.CmIndicator(self.Data)        
        if self.RiseFlag == True:
            if timeID >= self.ChomoTime:
                CanBuy = True
        
        if self.RiseFlag == False:
            if timeID <= self.ChomoTime:
                CanBuy = True
        
        self.TimeID = timeID
        if indicator == "buy":
            if CanBuy and not self.BPLock and (self.GMacdSP-lastMacd)/lastSlowMA > stdMA:
                self.BPLock = True
                self.SPLock = False
                self.GMacdBP = lastMacd
                self.Amount = self.Money / closePrice * 0.998
                self.Money = 0
                Brought = True
            elif lastMacd < self.GMacdBP:
                self.GMacdBP = lastMacd

        if indicator == "sell":
            if  not self.SPLock and (lastMacd-self.GMacdBP)/lastSlowMA > stdMA:
                self.SPLock = True
                self.BPLock = False
                self.GMacdSP = lastMacd
                self.Money = self.Amount * closePrice * 0.998
                self.Amount = 0
                Sold = True
            elif lastMacd > self.GMacdSP:
                self.GMacdSP = lastMacd
        return indicator, Brought, Sold, closePrice

    def GenMustSignal(self, data, prevFastMA, preSlowMA, prevMA30):
        df = pd.DataFrame(data)
        close = df["close"]
        fastMA = builtIndicators.ma.EMA(close,5)
        slowMA = builtIndicators.ma.EMA(close,10)
        MA30 = builtIndicators.ma.EMA(close,30)
        curFastMA = fastMA[len(fastMA)-1]
        curSlowMA = slowMA[len(slowMA)-1]
        curMA30 = MA30[len(MA30)-1] 
        up, down = self.judgeCross(curFastMA, curSlowMA, curMA30, prevFastMA, preSlowMA, prevMA30)
        prevFastMA = curFastMA
        preSlowMA = curSlowMA
        prevMA30 = curMA30
        return up, down, prevFastMA, preSlowMA, prevMA30

    def judgeCross(self, curFastMA, curSlowMA, curMA30, prevFastMA, preSlowMA, prevMA30):
        up = False
        down = False
        if curFastMA > curSlowMA and prevFastMA < preSlowMA:
            if curSlowMA > curMA30 and preSlowMA < prevMA30:
                up = True
        if curFastMA < curSlowMA and prevFastMA > preSlowMA:
            if curSlowMA < curMA30 and preSlowMA > prevMA30:
                down = True
        return up, down