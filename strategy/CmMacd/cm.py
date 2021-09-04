from os import close
from re import L, T
import sys

import numpy as np
from numpy.lib.index_tricks import ix_
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
        amount = self.getAccountBalance("usdt")
        if float(amount) > 15.0:
            BPLockList = [False]*len(symbols)
            SPLockList = [True]*len(symbols)
        else:
            BPLockList = [True]*len(symbols)
            SPLockList = [False]*len(symbols)
        gMacdBPList = [-99999999]*len(symbols)
        gMacdSPList = [99999999]*len(symbols)
        self.tradePriceList = [0]*len(symbols)
        self.timeIDList = [0]*len(symbols)

        mids = [True]*len(symbols)
        mustBuys = [False]*len(symbols)
        mustSells = [False]*len(symbols)
        curFastMAList = [0]*len(symbols)
        curSlowMAList = [0]*len(symbols)
        curMA30List = [0]*len(symbols)
        prevFastMAList = [0]*len(symbols)
        preSlowMAList = [0]*len(symbols)
        prevMA30List = [0]*len(symbols)
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
                if indicator == "nothing" and mids[idx]:
                    if not BPLockList[idx] and mustBuys[idx]:
                        buyStr = "nothing, but buy: lastMacd: %f, lastSlowMA: %f, gMacdSPList[idx]:%f, stdMA: %f" %(lastMacd, lastSlowMA, gMacdSPList[idx], stdMA)
                        print(buyStr,file = f)
                        gMacdBPList[idx] = lastMacd # optional
                        BPLockList[idx] = True
                        SPLockList[idx] = False
                        mustBuys[idx] = False
                        self.tradePriceList[idx] = clPrice
                        self.AlarmAndAction(collection, symbols[idx], period, "buy", f)
                        mids[idx] = False
                    elif not SPLockList[idx] and mustSells[idx]:
                        sellStr = "nothing, but sell: lastMacd: %f, lastSlowMA: %f, gMacdBPList[idx]:%f, stdMA: %f" %(lastMacd, lastSlowMA, gMacdBPList[idx], stdMA)
                        print(sellStr,file = f)
                        gMacdSPList[idx] = lastMacd # optional
                        SPLockList[idx] = True
                        BPLockList[idx] = False
                        mustSells[idx] = False
                        self.tradePriceList[idx] = clPrice
                        self.AlarmAndAction(collection, symbols[idx], period, "sell", f)
                        mids[idx] = False

                if indicator == "buy" and self.timeIDList[idx] != timeID:
                    self.timeIDList[idx] = timeID
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
                    if mustSells[idx]:
                        mids[idx] = True
                    if not mustSells[idx] and not BPLockList[idx] and ((mustBuys[idx] or (gMacdSPList[idx]-lastMacd)/lastSlowMA > stdMA)):
                        buyStr = "buy: lastMacd: %f, lastSlowMA: %f, gMacdSPList[idx]:%f, stdMA: %f" %(lastMacd, lastSlowMA, gMacdSPList[idx], stdMA)
                        print(buyStr,file = f)
                        BPLockList[idx] = True
                        SPLockList[idx] = False
                        gMacdBPList[idx] = lastMacd
                        self.tradePriceList[idx] = clPrice
                        mustBuys[idx] = False
                        self.AlarmAndAction(collection, symbols[idx], period, indicator, f)
                    elif lastMacd < gMacdBPList[idx]:
                        gMacdBPList[idx] = lastMacd

                if indicator == "sell" and self.timeIDList[idx] != timeID:
                    self.timeIDList[idx] = timeID
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
                    if mustBuys[idx]:
                        mids[idx] = True
                    if not mustBuys[idx] and not SPLockList[idx] and (mustSells[idx] or (lastMacd-gMacdBPList[idx])/lastSlowMA > stdMA): 
                        sellStr = "sell: lastMacd: %f, lastSlowMA: %f, gMacdBPList[idx]:%f, stdMA: %f" %(lastMacd, lastSlowMA, gMacdBPList[idx], stdMA)
                        print(sellStr,file = f)
                        SPLockList[idx] = True
                        BPLockList[idx] = False
                        gMacdSPList[idx] = lastMacd
                        self.tradePriceList[idx] = clPrice
                        mustSells[idx] = False
                        self.AlarmAndAction(collection, symbols[idx], period, indicator, f)
                    elif lastMacd > gMacdSPList[idx]:
                        gMacdSPList[idx] = lastMacd
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
        gMacdBP = 0
        gMacdSP = 0
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
        mid = True
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
            if indicator == "nothing" and mid:
                if mustBuy and Money > 0:
                    gMacdBP = lastMacd # optional
                    BPMAUsed = True
                    SPMAUsed = False
                    mustBuy = False
                    amount = Money / closePrice * 0.998
                    Money = 0
                    TradePrice = closePrice
                    dataBP.append(closePrice)
                    timeBP.append(timeID)
                    print("buy normal point found,  ts: %d, close: %f, amount: %f,    round: %d/%d"%(timeID, closePrice,amount, i+1, tCount-windowLen))
                    mid = False
                elif mustSell and amount>0:
                    gMacdSP = lastMacd # optional
                    SPMAUsed = True
                    BPMAUsed = False
                    mustSell = False
                    Money = amount * closePrice * 0.998
                    amount = 0
                    TradePrice = closePrice
                    dataSP.append(closePrice)
                    timeSP.append(timeID)
                    print("sell normal point found, ts: %d, close: %f, Money:  %f, round: %d/%d"%(timeID, closePrice,Money,i+1, tCount-windowLen))
                    mid = False

            if indicator == "buy":
                std30Buy.append(std30)
                dataBPA.append(closePrice)
                timeBPA.append(timeID)
                dangerous = False
                curFastMA = fastMA[len(fastMA)-1]
                curSlowMA = slowMA[len(slowMA)-1]
                curMA30 = MA30[len(MA30)-1] 
                dangerous, mustSell = self.judgeBuy(curFastMA, curSlowMA, curMA30, prevFastMA, preSlowMA, prevMA30)
                if mustSell:
                    mid = True
                prevFastMA = curFastMA
                preSlowMA = curSlowMA
                prevMA30 = curMA30
                if not mustSell and ((mustBuy and Money>0) or (not BPMAUsed and ((gMacdSP-lastMacd)/lastSlowMA > stdMA))): # or (dangerous and Money>0)
                    BPMAUsed = True
                    SPMAUsed = False
                    mustBuy = False
                    gMacdBP = lastMacd
                    amount = Money / closePrice * 0.998
                    Money = 0
                    TradePrice = closePrice
                    dataBP.append(closePrice)
                    timeBP.append(timeID)
                    print("buy point found,  ts: %d, close: %f, amount: %f,    round: %d/%d"%(timeID, closePrice,amount, i+1, tCount-windowLen))
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
                if mustBuy:
                    mid = True
                if not mustBuy and ((mustSell and amount>0) or (not SPMAUsed and ((lastMacd-gMacdBP)/lastSlowMA > stdMA))): # or (dangerous and amount>0)
                    SPMAUsed = True
                    BPMAUsed = False
                    mustSell = False
                    gMacdSP = lastMacd
                    if TradePrice == 0:
                        print("first point is sell, do nothing")
                    else:
                        Money = amount * closePrice * 0.998
                        amount = 0
                        TradePrice = closePrice
                        dataSP.append(closePrice)
                        timeSP.append(timeID)
                        print("sell point found, ts: %d, close: %f, Money:  %f, round: %d/%d"%(timeID, closePrice,Money,i+1, tCount-windowLen))
                elif lastMacd > gMacdSP:
                    gMacdSP = lastMacd
                dangerous = False
                #prevMacd = lastMacd
        if Money == 0:
            RateOfReturn = TradePrice * amount / 10000.0 - 1.0
        elif amount == 0:
            RateOfReturn = Money / 10000.0 - 1.0
        print("Rate of Return in %s is %f"%(symbol, RateOfReturn))

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

        #plt.legend()
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
        Money = 10000.0
        amount = 0.0
        RateOfReturn = 0.0
        TradePrice = 0.0
        collection = "HB-%s-5min"%(symbol)
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
        gMacdSP = 999999
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
            if indicator == "buy":
                std30Buy.append(std30)
                dataBPA.append(closePrice)
                timeBPA.append(timeID)
                if not BPMAUsed and (gMacdSP-lastMacd)/lastSlowMA > stdMA:
                    BPMAUsed = True
                    SPMAUsed = False
                    gMacdBP = lastMacd
                    amount = Money / closePrice * 0.998
                    Money = 0
                    TradePrice = closePrice
                    dataBP.append(closePrice)
                    timeBP.append(timeID)
                    print("buy point found,  ts: %d, close: %f, amount: %f,    round: %d/%d"%(timeID, closePrice,amount, i+1, tCount-windowLen))
                elif lastMacd < gMacdBP:
                    gMacdBP = lastMacd

            if indicator == "sell":
                std30Sell.append(std30)
                dataSPA.append(closePrice)
                timeSPA.append(timeID)
                if not SPMAUsed and (lastMacd-gMacdBP)/lastSlowMA > stdMA:
                    SPMAUsed = True
                    BPMAUsed = False
                    gMacdSP = lastMacd
                    if TradePrice == 0:
                        print("first point is sell, do nothing")
                    else:
                        Money = amount * closePrice * 0.998
                        amount = 0
                        TradePrice = closePrice
                        dataSP.append(closePrice)
                        timeSP.append(timeID)
                        print("sell point found, ts: %d, close: %f, Money:  %f, round: %d/%d"%(timeID, closePrice,Money,i+1, tCount-windowLen))
                elif lastMacd > gMacdSP:
                    gMacdSP = lastMacd
        if Money == 0:
            RateOfReturn = TradePrice * amount / 10000.0 - 1.0
        elif amount == 0:
            RateOfReturn = Money / 10000.0 - 1.0
        print("Rate of Return in %s is %f"%(symbol, RateOfReturn))
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
        ax1.plot(timeAll, closeAll, color='gray', label="close")
        ax1.plot(timeAll, fastMAAll, color='y', label="MA30")
        ax1.plot(timeAll, slowMAAll, color='g', label="MA30")
        ax1.plot(timeAll, MA30All, color='m', label="MA30")
        ax1.scatter(timeBPA,dataBPA,marker='^',c='g',edgecolors='g')
        ax1.scatter(timeSPA,dataSPA,marker='v',c='r',edgecolors='r')

        ax2.plot(timeAll, closeAll, color='gray', label="close")
        ax2.scatter(timeBP,dataBP,marker='o',c='w',edgecolors='g')
        ax2.scatter(timeSP,dataSP,marker='o',c='m',edgecolors='m')

        ax3.plot(timeAll, MACD, label="MACD")
        ax3.plot(timeAll, signal, label="signal")
        ax3.scatter(crossTimesSell,crossSell,marker='o',c='r',edgecolors='r')
        ax3.scatter(crossTimesBuy,crossBuy,marker='o',c='g',edgecolors='g')
        ax3.bar(timeAll,hist,width=600,label="hist")
        
        ax4.plot(timeAll, abs(closeAll-MA30All), color='royalblue', label="diff of close and ma30")
        ax4.scatter(timeBPA,std30Buy,marker='^',c='g',edgecolors='g')
        ax4.scatter(timeSPA,std30Sell,marker='v',c='r',edgecolors='r')
        ax4.plot(timeAll, [0]*len(closeAll),color='k', label="0")
        plt.show()

    def OnlineTest(self,windowLen,symbols,period="5min"):
        #amount = self.getAccountBalance("usdt")
        # if float(amount) > 15.0:
        #     BPLockList = [False]*len(symbols)
        #     SPLockList = [True]*len(symbols)
        # else:
        BPLockList = [True]*len(symbols)
        SPLockList = [False]*len(symbols)
        gMacdBPList = [-99999999]*len(symbols)
        gMacdSPList = [99999999]*len(symbols)
        self.tradePriceList = [0]*len(symbols)
        self.timeIDList = [0]*len(symbols)
        for idx in range(len(symbols)):
            collection = "HB-%s-%s"%(symbols[idx],period)
            self.Collection = self.DB[collection]
            data = []
            DBcursor = self.Collection.find().sort('id', pymongo.ASCENDING).limit(windowLen)
            for doc in DBcursor:
                data.append(doc)
            tCount = self.Collection.find().sort('id', pymongo.ASCENDING).count()
            for i in range(tCount-windowLen):
                print("%d/%d"%(i,tCount-windowLen))
                DBcursor = self.Collection.find().sort('id', pymongo.ASCENDING).skip(i+windowLen).limit(1)
                for doc in DBcursor:
                    data = data[1:]
                    data.append(doc)
                indicator,timeID,clPrice,lastMacd,lastSlowMA,stdMA = CMMACD.CmIndicator(data)
                timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                outStr = "%s symbol: %s, indicator: %s, has balance: %r, has amount: %r, timeID: %d, lastMacd: %f, lastSlowMA: %f, gMacdBPList[idx]: %f, gMacdSPList[idx]:%f, stdMA: %f" %(timeNow, symbols[idx], indicator, not BPLockList[idx], not SPLockList[idx], timeID, lastMacd, lastSlowMA, gMacdBPList[idx], gMacdSPList[idx], stdMA)
                f = open('out.log','a+')
                print(outStr,file = f)
                if indicator == "buy" and self.timeIDList[idx] != timeID:
                    self.timeIDList[idx] = timeID
                    buyStr = "lastMacd: %f, lastSlowMA: %f, gMacdSPList[idx]:%f, stdMA: %f" %(lastMacd, lastSlowMA, gMacdSPList[idx], stdMA)
                    print(buyStr,file = f)
                    if not BPLockList[idx] and (gMacdSPList[idx]-lastMacd)/lastSlowMA > stdMA:
                        BPLockList[idx] = True
                        SPLockList[idx] = False
                        gMacdBPList[idx] = lastMacd
                        self.tradePriceList[idx] = clPrice
                        timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        alertText = "%s HuoBi %s: will rise!!! buy now!"%(timeNow,collection)
                        print(alertText,file=f)
                    elif lastMacd < gMacdBPList[idx]:
                        gMacdBPList[idx] = lastMacd
                elif indicator == "sell" and self.timeIDList[idx] != timeID:
                    self.timeIDList[idx] = timeID
                    sellStr = "lastMacd: %f, lastSlowMA: %f, gMacdBPList[idx]:%f, stdMA: %f" %(lastMacd, lastSlowMA, gMacdBPList[idx], stdMA)
                    print(sellStr,file = f)
                    if not SPLockList[idx] and (lastMacd-gMacdBPList[idx])/lastSlowMA > stdMA:
                        SPLockList[idx] = True
                        BPLockList[idx] = False
                        gMacdSPList[idx] = lastMacd
                        self.tradePriceList[idx] = clPrice
                        timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        alertText = "%s HuoBi %s: will descend!!! sell quickly!"%(timeNow, collection)
                        print(alertText,file=f)
                    elif lastMacd > gMacdSPList[idx]:
                        gMacdSPList[idx] = lastMacd
                f.close()

    def MAAverage(self,symbol):
        collection = "HB-%s-30min"%(symbol)
        self.Collection = self.DB[collection]
        dataAll = []
        timeAll = []
        DBcursorAll = self.Collection.find().sort('id', pymongo.ASCENDING)
        for docAll in DBcursorAll:
            dataAll.append(docAll)
        df = pd.DataFrame(dataAll)
        timeAll = df["id"]
        closeAll = df["close"]
        fastMA = builtIndicators.ma.EMA(closeAll,12)
        slowMA = builtIndicators.ma.EMA(closeAll,26)
        MACD = fastMA - slowMA
        f, (ax1, ax2,ax3) = plt.subplots(3,1,sharex=True,figsize=(8,12))
        ax1.plot(timeAll, fastMA, color='gray', label="fastMA")
        ax1.plot(timeAll, slowMA, color='orange', label="slowMA")
        ax2.plot(timeAll, [0]*len(timeAll), color='black', label="ZERO")
        ax2.plot(timeAll, MACD, color='blue', label="MACD")
        print(np.std(abs(MACD/slowMA)))
        #ax3.plot(timeAll, np.var(MACD/slowMA), color='blue', label="var for macd/slowMA")
        ax3.scatter(timeAll, MACD/slowMA, marker='o',c='w',edgecolors='g')
        plt.show()
