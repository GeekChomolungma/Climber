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

    def Run(self,tickTime,windowLen,symbols,period="5min"):
        # 1st query balance of usdt
        # if >15$, then we are buyer.
        amount = self.getAccountBalance("usdt")
        if float(amount) > 15.0:
            self.Wallet = [True]*len(symbols)
            self.Amounts = [False]*len(symbols)
        else:
            self.Wallet = [False]*len(symbols)
            self.Amounts = [True]*len(symbols)

        # 2nd lets go trade
        self.tradePriceList = [0]*len(symbols)
        self.timeIDList = [0]*len(symbols)
        while True:
            t = utils.ticker.Ticker(tickTime)
            t.Loop()
            for idx in range(len(symbols)):
                collection = "HB-%s-%s"%(symbols[idx],period)
                self.Collection = self.DB[collection]
                data = []
                DBcursor = self.Collection.find().sort('id', pymongo.DESCENDING).limit(windowLen)
                for doc in DBcursor:
                    data.append(doc)
                data.reverse()
                indicator,timeID,clPrice = CMMACD.CmIndicator(data)
                timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                outStr = "symbol: %s, indicator: %s, has balance: %r, has amount: %r, timeID: %d, timeNow: %s" %(symbols[idx],indicator,self.Wallet[idx], self.Amounts[idx], timeID, timeNow)
                f = open('out.log','a+')
                print(outStr,file = f)
                if indicator == "buy" and self.timeIDList[idx] != timeID and self.Wallet[idx]:
                    # need: 1. if self.tradePriceList[idx] > clPrice 
                    #       2. if macd cross down ZERO, means selling power released?
                    #       3. if macd cross down alot but not cross ZERO, means buying power is huge?
                    # record the tradePriceList
                    self.tradePriceList[idx] = clPrice
                    timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    alertText = "HuoBi %s: will rise!!! buy now! time: %s"%(collection,timeNow)
                    print(alertText,file=f)
                    if symbols[idx] == "btcusdt":
                        self.Buy()
                    self.Wallet[idx] = False
                    self.Amounts[idx] = True
                    self.timeIDList[idx] = timeID
                    for i in range(2):
                        text = "HuoBi %s-%s: 要涨了!!! 现在买入! 当前时间: %s, 报警提醒次数(%d/2)" %(symbols[idx],period,timeNow,i+1)
                        alert.Alert(text)
                elif indicator == "sell" and self.timeIDList[idx] != timeID and self.Amounts[idx] and self.tradePriceList[idx] < clPrice:
                    # need: 1. if macd cross up ZERO, means buying power released?
                    #       2. if macd cross up alot but not cross ZERO, means selling power is huge?
                    self.tradePriceList[idx] = clPrice
                    # 4 conditions: sell, not same id, have amount, and not descending
                    timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    alertText = "HuoBi %s: will descend!!! sell quickly! time: %s"%(collection,timeNow)
                    print(alertText,file=f)
                    if symbols[idx] == "btcusdt":
                        self.Sell()
                    self.Wallet[idx] = True
                    self.Amounts[idx] = False
                    self.timeIDList[idx] = timeID
                    for i in range(2):
                        text = "HuoBi %s-%s: 要跌了!!! 赶紧卖掉! 当前时间: %s, 报警提醒次数(%d/2)" %(symbols[idx],period,timeNow,i+1)
                        alert.Alert(text)
                f.close()

    def RunV2(self,tickTime,windowLen,symbols,period="5min"):
        # get balance of usdt
        amount = self.getAccountBalance("usdt")
        if float(amount) > 15.0:
            BPLockList = [False]*len(symbols)
            SPLockList = [True]*len(symbols)
        else:
            BPLockList = [True]*len(symbols)
            SPLockList = [False]*len(symbols)
        
        gMacdBPList = [-99999999]*len(symbols)
        gMacdSPList = [99999999]*len(symbols)
        timeIDList = [0]*len(symbols)
        mustBuys = [False]*len(symbols)
        mustSells = [False]*len(symbols)
        curFastMAList = [0]*len(symbols)
        curSlowMAList = [0]*len(symbols)
        curMA30List = [0]*len(symbols)
        prevFastMAList = [0]*len(symbols)
        preSlowMAList = [0]*len(symbols)
        prevMA30List = [0]*len(symbols)
        
        # init the strategy
        for idx in range(len(symbols)):
            initVals = self.InitModel(symbols[idx], period, windowLen, BPLockList[idx], SPLockList[idx], False, False, -99999999, 99999999, 0, 0, 0)
            BPLockList[idx] = initVals.BPLock 
            SPLockList[idx] = initVals.SPLock
            mustBuys[idx] = initVals.MustBuy
            mustSells[idx] = initVals.MustSell
            gMacdBPList[idx] = initVals.GMacdBP
            gMacdSPList[idx] = initVals.GMacdSP
            timeIDList[idx] = initVals.TimeID
            prevFastMAList[idx] = initVals.PrevFastMA
            preSlowMAList[idx] = initVals.PreSlowMA
            prevMA30List[idx] = initVals.PrevMA30
            collection = "HB-%s-%s"%(symbols[idx],period)
            f = open('out.log','a+')
            overStr = "%s initially done. BPLock: %r, SPLock: %r, mustBuy: %r, mustSell: %r, gMacdBP: %f, gMacdSP: %f, timeID: %d, prevFastMA: %f, preSlowMA: %f, prevMA30: %f" \
                 %(collection, BPLockList[idx], SPLockList[idx], mustBuys[idx], mustSells[idx], gMacdBPList[idx], gMacdSPList[idx], timeIDList[idx], prevFastMAList[idx], preSlowMAList[idx], prevMA30List[idx])
            print(overStr,file = f)
            f.close()

        # loop
        while True:
            t = utils.ticker.Ticker(tickTime)
            t.Loop()
            for idx in range(len(symbols)):
                collection = "HB-%s-%s"%(symbols[idx],period)
                self.Collection = self.DB[collection]
                data = []
                DBcursor = self.Collection.find().sort('id', pymongo.DESCENDING).limit(windowLen)
                for doc in DBcursor:
                    data.append(doc)
                data.reverse()
                indicator,timeID,clPrice,lastMacd,lastSlowMA,stdMA = CMMACD.CmIndicator(data)
                timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                outStr = "%s symbol: %s, indicator: %s, has balance: %r, has amount: %r, timeID: %d, lastMacd: %f, lastSlowMA: %f, gMacdBPList[idx]: %f, gMacdSPList[idx]:%f, stdMA: %f" %(timeNow, symbols[idx], indicator, not BPLockList[idx], not SPLockList[idx], timeID, lastMacd, lastSlowMA, gMacdBPList[idx], gMacdSPList[idx], stdMA)
                f = open('out.log','a+')
                print(outStr,file = f)
                if indicator == "nothing":
                    if not BPLockList[idx] and mustBuys[idx]:
                        buyStr = "nothing, but buy: lastMacd: %f, lastSlowMA: %f, gMacdSPList[idx]:%f, stdMA: %f" %(lastMacd, lastSlowMA, gMacdSPList[idx], stdMA)
                        print(buyStr,file = f)
                        gMacdBPList[idx] = lastMacd # optional
                        BPLockList[idx] = True
                        SPLockList[idx] = False
                        mustBuys[idx] = False
                        mustSells[idx] = False
                        self.AlarmAndAction(collection, symbols[idx], period, "buy", f)
                    elif not SPLockList[idx] and mustSells[idx]:
                        sellStr = "nothing, but sell: lastMacd: %f, lastSlowMA: %f, gMacdBPList[idx]:%f, stdMA: %f" %(lastMacd, lastSlowMA, gMacdBPList[idx], stdMA)
                        print(sellStr,file = f)
                        gMacdSPList[idx] = lastMacd # optional
                        SPLockList[idx] = True
                        BPLockList[idx] = False
                        mustSells[idx] = False
                        mustBuys[idx] = False
                        self.AlarmAndAction(collection, symbols[idx], period, "sell", f)

                if indicator == "buy" and timeIDList[idx] != timeID:
                    timeIDList[idx] = timeID
                    df = pd.DataFrame(data)
                    close = df["close"]
                    fastMA = builtIndicators.ma.EMA(close,5)
                    slowMA = builtIndicators.ma.EMA(close,10)
                    MA30 = builtIndicators.ma.EMA(close,30)
                    curFastMAList[idx] = fastMA[len(fastMA)-1]
                    curSlowMAList[idx] = slowMA[len(slowMA)-1]
                    curMA30List[idx] = MA30[len(MA30)-1] 
                    dangerous, mustSells[idx] = self.judgeBuy(curFastMAList[idx], curSlowMAList[idx], curMA30List[idx], prevFastMAList[idx], preSlowMAList[idx], prevMA30List[idx])
                    prevFastMAList[idx] = curFastMAList[idx]
                    preSlowMAList[idx] = curSlowMAList[idx]
                    prevMA30List[idx] = curMA30List[idx]
                    if not mustSells[idx] and not BPLockList[idx] and ((mustBuys[idx] or (gMacdSPList[idx]-lastMacd)/lastSlowMA > stdMA)):
                        buyStr = "buy: lastMacd: %f, lastSlowMA: %f, gMacdSPList[idx]:%f, stdMA: %f" %(lastMacd, lastSlowMA, gMacdSPList[idx], stdMA)
                        print(buyStr,file = f)
                        BPLockList[idx] = True
                        SPLockList[idx] = False
                        gMacdBPList[idx] = lastMacd
                        mustBuys[idx] = False
                        self.AlarmAndAction(collection, symbols[idx], period, indicator, f)
                    elif lastMacd < gMacdBPList[idx]:
                        gMacdBPList[idx] = lastMacd

                if indicator == "sell" and timeIDList[idx] != timeID:
                    timeIDList[idx] = timeID
                    df = pd.DataFrame(data)
                    close = df["close"]
                    fastMA = builtIndicators.ma.EMA(close,5)
                    slowMA = builtIndicators.ma.EMA(close,10)
                    MA30 = builtIndicators.ma.EMA(close,30)
                    curFastMAList[idx] = fastMA[len(fastMA)-1]
                    curSlowMAList[idx] = slowMA[len(slowMA)-1]
                    curMA30List[idx] = MA30[len(MA30)-1] 
                    dangerous, mustBuys[idx] = self.judgeSell(curFastMAList[idx], curSlowMAList[idx], curMA30List[idx], prevFastMAList[idx], preSlowMAList[idx], prevMA30List[idx])
                    prevFastMAList[idx] = curFastMAList[idx]
                    preSlowMAList[idx] = curSlowMAList[idx]
                    prevMA30List[idx] = curMA30List[idx]
                    if not mustBuys[idx] and not SPLockList[idx] and (mustSells[idx] or (lastMacd-gMacdBPList[idx])/lastSlowMA > stdMA): 
                        sellStr = "sell: lastMacd: %f, lastSlowMA: %f, gMacdBPList[idx]:%f, stdMA: %f" %(lastMacd, lastSlowMA, gMacdBPList[idx], stdMA)
                        print(sellStr,file = f)
                        SPLockList[idx] = True
                        BPLockList[idx] = False
                        gMacdSPList[idx] = lastMacd
                        mustSells[idx] = False
                        self.AlarmAndAction(collection, symbols[idx], period, indicator, f)
                    elif lastMacd > gMacdSPList[idx]:
                        gMacdSPList[idx] = lastMacd
                f.close()

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

    def InitModel(self, symbol, period, windowLen, BPLock, SPLock, mustBuy, mustSell, gMacdBP, gMacdSP, prevFastMA, preSlowMA, prevMA30):
        collection = "HB-%s-%s"%(symbol,period)
        self.Collection = self.DB[collection]
        data = []
        tCount = self.Collection.find().sort('id', pymongo.ASCENDING).count()
        DBcursor = self.Collection.find().sort('id', pymongo.ASCENDING).limit(windowLen)
        for doc in DBcursor:
            data.append(doc)
        f = open('out.log','a+')
        for i in range(tCount-windowLen):
            DBcursor = self.Collection.find().sort('id', pymongo.ASCENDING).skip(i+windowLen).limit(1)
            for doc in DBcursor:
                data = data[1:]
                data.append(doc)
            indicator,timeID,clPrice,lastMacd,lastSlowMA,stdMA = CMMACD.CmIndicator(data)
            date = datetime.datetime.fromtimestamp(timeID).strftime('%Y-%m-%d %H:%M:%S')
            if indicator == "nothing": 
                if not BPLock and mustBuy:
                    buyStr = "%s, %s, timeid: %d, nothing but buy: lastMacd: %f, lastSlowMA: %f, gMacdSP:%f, stdMA: %f" %(date, collection, timeID, lastMacd, lastSlowMA, gMacdSP, stdMA)
                    print(buyStr,file = f)
                    gMacdBP = lastMacd # optional
                    BPLock = True
                    SPLock = False
                    mustBuy = False
                    mustSell = False
                elif not SPLock and mustSell:
                    sellStr = "%s, %s, timeid: %d, nothing but sell: lastMacd: %f, lastSlowMA: %f, gMacdBP:%f, stdMA: %f" %(date, collection, timeID, lastMacd, lastSlowMA, gMacdBP, stdMA)
                    print(sellStr,file = f)
                    gMacdSP = lastMacd # optional
                    SPLock = True
                    BPLock = False
                    mustSell = False
                    mustBuy = False

            if indicator == "buy":
                df = pd.DataFrame(data)
                close = df["close"]
                fastMA = builtIndicators.ma.EMA(close,5)
                slowMA = builtIndicators.ma.EMA(close,10)
                MA30 = builtIndicators.ma.EMA(close,30)
                curFastMA = fastMA[len(fastMA)-1]
                curSlowMA = slowMA[len(slowMA)-1]
                curMA30 = MA30[len(MA30)-1] 
                dangerous, mustSell = self.judgeBuy(curFastMA, curSlowMA, curMA30, prevFastMA, preSlowMA, prevMA30)
                prevFastMA = curFastMA
                preSlowMA = curSlowMA
                prevMA30 = curMA30
                if not mustSell and not BPLock and ((mustBuy or (gMacdSP-lastMacd)/lastSlowMA > stdMA)):
                    buyStr = "%s, %s, timeid: %d: buy: lastMacd: %f, lastSlowMA: %f, gMacdSPList[idx]:%f, stdMA: %f" %(date, collection, timeID, lastMacd, lastSlowMA, gMacdSP, stdMA)
                    print(buyStr,file = f)
                    BPLock = True
                    SPLock = False
                    gMacdBP = lastMacd
                    mustBuy = False
                elif lastMacd < gMacdBP:
                    gMacdBP = lastMacd

            if indicator == "sell":
                df = pd.DataFrame(data)
                close = df["close"]
                fastMA = builtIndicators.ma.EMA(close,5)
                slowMA = builtIndicators.ma.EMA(close,10)
                MA30 = builtIndicators.ma.EMA(close,30)
                curFastMA = fastMA[len(fastMA)-1]
                curSlowMA = slowMA[len(slowMA)-1]
                curMA30 = MA30[len(MA30)-1] 
                dangerous, mustBuy = self.judgeSell(curFastMA, curSlowMA, curMA30, prevFastMA, preSlowMA, prevMA30)
                prevFastMA = curFastMA
                preSlowMA = curSlowMA
                prevMA30 = curMA30
                if not mustBuy and not SPLock and (mustSell or (lastMacd-gMacdBP)/lastSlowMA > stdMA): 
                    sellStr = "%s, %s, timeid: %d: sell: lastMacd: %f, lastSlowMA: %f, gMacdBPList[idx]:%f, stdMA: %f" %(date, collection, timeID, lastMacd, lastSlowMA, gMacdBP, stdMA)
                    print(sellStr,file = f)
                    SPLock = True
                    BPLock = False
                    gMacdSP = lastMacd
                    mustSell = False
                elif lastMacd > gMacdSP:
                    gMacdSP = lastMacd
        f.close()
        return InitVals(BPLock, SPLock, mustBuy, mustSell, gMacdBP, gMacdSP, timeID, prevFastMA, preSlowMA, prevMA30)
        
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
    
    def BT5min(self,windowLen,symbol):
        'Back Test for huge stock, like btc'
        Money = 10000.0
        amount = 0.0
        RateOfReturn = 0.0
        TradePrice = 0.0
        collection = "HB-%s-30min"%(symbol)
        self.Collection = self.DB[collection]
        tCount = self.Collection.find().sort('id', pymongo.ASCENDING).count()
        data = []
        DBcursor = self.Collection.find().sort('id', pymongo.ASCENDING).limit(windowLen)
        for doc in DBcursor:
            data.append(doc)
            
        # query all data for plot
        dataAll = []
        timeAll = []
        closeAll = []
        dataBPA = []
        dataSPA = []
        timeBPA = []
        timeSPA = []
        dataBP = []
        dataSP = []
        timeBP = []
        timeSP = []
        std30Buy = []
        std30Sell = []
        gMacdBP = -999999
        gMacdSP =  999999
        prevFastMA = 0
        preSlowMA = 0
        prevMA30 = 0
        mustBuy = False
        mustSell = False
        prevMacd = 0
        BPMAUsed = False
        SPMAUsed = False
        DBcursorAll = self.Collection.find().sort('id', pymongo.ASCENDING)
        for docAll in DBcursorAll:
            dataAll.append(docAll)
        df = pd.DataFrame(dataAll)
        timeAll = df["id"]
        closeAll = df["close"]
        fastMAAll = builtIndicators.ma.EMA(closeAll,5)
        slowMAAll = builtIndicators.ma.EMA(closeAll,10)
        MA30All = builtIndicators.ma.EMA(closeAll,30)

        # regardless of the initial window
        # loop
        # mid = True
        f = open('bt5min.log','a+')
        for i in range(tCount-windowLen):
            DBcursor = self.Collection.find().sort('id', pymongo.ASCENDING).skip(i+windowLen).limit(1)
            for doc in DBcursor:
                data = data[1:]
                data.append(doc)
            indicator,timeID,closePrice,lastMacd,lastSlowMA,stdMA= CMMACD.CmIndicator(data)
            df = pd.DataFrame(data)
            close = df["close"]
            fastMA = builtIndicators.ma.EMA(close,5)
            slowMA = builtIndicators.ma.EMA(close,10)
            MA30 = builtIndicators.ma.EMA(close,30)
            std30 = np.std(close-MA30)
            date = datetime.datetime.fromtimestamp(timeID).strftime('%Y-%m-%d %H:%M:%S')
            if indicator == "nothing" : #and mid
                if mustBuy and Money > 0:
                    gMacdBP = lastMacd # optional
                    BPMAUsed = True
                    SPMAUsed = False
                    mustBuy = False
                    mustSell = False
                    amount = Money / closePrice * 0.998
                    Money = 0
                    TradePrice = closePrice
                    dataBP.append(closePrice)
                    timeBP.append(timeID)
                    print("%s buy normal point found,  ts: %d, close: %f, amount: %f,    round: %d/%d"%(date, timeID, closePrice,amount, i+1, tCount-windowLen), file=f)
                    #mid = False
                elif mustSell and amount>0:
                    gMacdSP = lastMacd # optional
                    SPMAUsed = True
                    BPMAUsed = False
                    mustSell = False
                    mustBuy = False
                    Money = amount * closePrice * 0.998
                    amount = 0
                    TradePrice = closePrice
                    dataSP.append(closePrice)
                    timeSP.append(timeID)
                    print("%s sell normal point found, ts: %d, close: %f, Money:  %f, round: %d/%d"%(date, timeID, closePrice,Money,i+1, tCount-windowLen), file=f)
                    #mid = False

            if indicator == "buy":
                std30Buy.append(std30)
                dataBPA.append(closePrice)
                timeBPA.append(timeID)
                dangerous = False
                curFastMA = fastMA[len(fastMA)-1]
                curSlowMA = slowMA[len(slowMA)-1]
                curMA30 = MA30[len(MA30)-1] 
                dangerous, mustSell = self.judgeBuy(curFastMA, curSlowMA, curMA30, prevFastMA, preSlowMA, prevMA30)
                # if mustSell:
                #     mid = True
                prevFastMA = curFastMA
                preSlowMA = curSlowMA
                prevMA30 = curMA30
                print("%s indicator: buy, ts: %d, close:%f, Money:%f, Amount:%f, mustBuy:%r, mustSell:%r, BPMAUsed:%r, SPMAUsed:%r, gMacdBP:%f, gMacdSP:%f, lastMacd:%f, lastSlowMA:%f, stdMA:%f, round: %d/%d" \
                    %(date, timeID, closePrice, Money, amount, mustBuy, mustSell, BPMAUsed, SPMAUsed, gMacdBP, gMacdSP, lastMacd, lastSlowMA, stdMA, i+1, tCount-windowLen), file=f)
                if not mustSell and not BPMAUsed and (mustBuy or ((gMacdSP-lastMacd)/lastSlowMA > stdMA)): # or (dangerous and Money>0)
                    BPMAUsed = True
                    SPMAUsed = False
                    mustBuy = False
                    gMacdBP = lastMacd
                    amount = Money / closePrice * 0.998
                    Money = 0
                    TradePrice = closePrice
                    dataBP.append(closePrice)
                    timeBP.append(timeID)
                    print("%s brought, ts: %d, close: %f, Money:  %f, round: %d/%d"%(date, timeID, closePrice,Money,i+1, tCount-windowLen), file=f)
                elif lastMacd < gMacdBP:
                    gMacdBP = lastMacd
                dangerous = False
                #prevMacd = lastMacd

            if indicator == "sell":
                std30Sell.append(std30)
                dataSPA.append(closePrice)
                timeSPA.append(timeID)
                dangerous = False 
                curFastMA = fastMA[len(fastMA)-1]
                curSlowMA = slowMA[len(slowMA)-1]
                curMA30 = MA30[len(MA30)-1]        
                dangerous, mustBuy = self.judgeSell(curFastMA, curSlowMA, curMA30, prevFastMA, preSlowMA, prevMA30)
                prevFastMA = curFastMA
                preSlowMA = curSlowMA
                prevMA30 = curMA30
                # if mustBuy:
                #     mid = True
                print("%s indicator: sell, ts: %d, close:%f, Money:%f, Amount:%f, mustBuy:%r, mustSell:%r, BPMAUsed:%r, SPMAUsed:%r, gMacdBP:%f, gMacdSP:%f, lastMacd:%f, lastSlowMA:%f, stdMA:%f, round: %d/%d"\
                    %(date, timeID, closePrice, Money, amount, mustBuy, mustSell, BPMAUsed, SPMAUsed, gMacdBP, gMacdSP, lastMacd, lastSlowMA, stdMA, i+1, tCount-windowLen), file=f)
                if not mustBuy and not SPMAUsed and (mustSell or ((lastMacd-gMacdBP)/lastSlowMA > stdMA)): # or (dangerous and amount>0)
                    SPMAUsed = True
                    BPMAUsed = False
                    mustSell = False
                    gMacdSP = lastMacd
                    if TradePrice == 0:
                        print("first point is sell, do nothing", file=f)
                    else:
                        Money = amount * closePrice * 0.998
                        amount = 0
                        TradePrice = closePrice
                        dataSP.append(closePrice)
                        timeSP.append(timeID)
                        print("%s sold, ts: %d, close: %f, Money:  %f, round: %d/%d"%(date, timeID, closePrice,Money,i+1, tCount-windowLen), file=f)
                elif lastMacd > gMacdSP:
                    gMacdSP = lastMacd
                dangerous = False
                #prevMacd = lastMacd
        
        if Money == 0:
            RateOfReturn = TradePrice * amount / 10000.0 - 1.0
        elif amount == 0:
            RateOfReturn = Money / 10000.0 - 1.0
        print("Rate of Return in %s is %f"%(symbol, RateOfReturn), file=f)
        f.close()

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

        f, (ax1, ax2, ax3, ax4) = plt.subplots(4,1,sharex=True,figsize=(8,12))
        #plt.subplot(211)
        ax1.plot(timeAll, closeAll, color='gray', label="close")
        ax1.plot(timeAll, fastMAAll, color='y', label="MA30")
        ax1.plot(timeAll, slowMAAll, color='g', label="MA30")
        ax1.plot(timeAll, MA30All, color='m', label="MA30")
        ax1.scatter(timeBPA,dataBPA,marker='^',c='g',edgecolors='g')
        ax1.scatter(timeSPA,dataSPA,marker='v',c='r',edgecolors='r')

        ax2.plot(timeAll, closeAll, color='gray', label="close")
        ax2.scatter(timeBP,dataBP,marker='o',c='w',edgecolors='g')
        ax2.scatter(timeSP,dataSP,marker='o',c='m',edgecolors='m')

        ax4.plot(timeAll, abs(closeAll-MA30All), color='royalblue', label="diff of close and ma30")
        ax4.scatter(timeBPA,std30Buy,marker='^',c='g',edgecolors='g')
        ax4.scatter(timeSPA,std30Sell,marker='v',c='r',edgecolors='r')
        ax4.plot(timeAll, [0]*len(closeAll),color='k', label="0")
        #plt.subplot(212)
        ax3.plot(timeAll, MACD, label="MACD")
        ax3.plot(timeAll, signal, label="signal")
        ax3.scatter(crossTimesSell,crossSell,marker='o',c='r',edgecolors='r')
        ax3.scatter(crossTimesBuy,crossBuy,marker='o',c='g',edgecolors='g')
        ax3.bar(timeAll,hist,width=600,label="hist")
        plt.show()

    def judgeBuy(self, curFastMA, curSlowMA, curMA30, prevFastMA, preSlowMA, prevMA30):
        dangerous = False
        mustSell = False
        if curFastMA > curSlowMA and prevFastMA < preSlowMA:
            if curSlowMA > curMA30 and preSlowMA < prevMA30:
                dangerous = True
        if curFastMA < curSlowMA and prevFastMA > preSlowMA:
            if curSlowMA < curMA30 and preSlowMA > prevMA30:
                mustSell = True
        return dangerous, mustSell
    
    def judgeSell(self, curFastMA, curSlowMA, curMA30, prevFastMA, preSlowMA, prevMA30):
        dangerous = False
        mustBuy = False
        if curFastMA < curSlowMA and prevFastMA > preSlowMA:
            if curSlowMA < curMA30 and preSlowMA > prevMA30:
                dangerous = True
        if curFastMA > curSlowMA and prevFastMA < preSlowMA:
            if curSlowMA > curMA30 and preSlowMA < prevMA30:
                mustBuy = True
        return dangerous, mustBuy
    
    def CMTest(self,windowLen,symbol):
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

class InitVals:
    def __init__(self, BPLock, SPLock, mustBuy, mustSell, gMacdBP, gMacdSP, timeID, prevFastMA, preSlowMA, prevMA30):
        self.BPLock = BPLock
        self.SPLock = SPLock
        self.MustBuy = mustBuy
        self.MustSell = mustSell
        self.GMacdBP = gMacdBP
        self.GMacdSP = gMacdSP
        self.TimeID = timeID
        self.PrevFastMA = prevFastMA
        self.PreSlowMA = preSlowMA
        self.PrevMA30 = prevMA30

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