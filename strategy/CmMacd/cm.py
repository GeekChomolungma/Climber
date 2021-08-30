from os import close
import sys
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
            # self.haveMoney = True
            # self.haveAmount = False
            self.Wallet = [True]*len(symbols)
            self.Amounts = [False]*len(symbols)
        else:
            # self.haveMoney = False
            # self.haveAmount = True
            self.Wallet = [True]*len(symbols)
            self.Amounts = [False]*len(symbols)

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

    def getAccountBalance(self, currency):
        'get currency balance'
        balance = chomoClient.client.GetAccountBalance(currency)
        print("the currency: ", currency, "amount: ", balance)
        return balance

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
        'Back Test'
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
        DBcursorAll = self.Collection.find().sort('id', pymongo.ASCENDING)
        for docAll in DBcursorAll:
            dataAll.append(docAll)
            df = pd.DataFrame(dataAll)
            timeAll = df["id"]
            closeAll = df["close"]

        # init step
        indicator,timeID,closePrice = CMMACD.CmIndicator(data)
        if indicator == "buy":
            dataBPA.append(closePrice)
            timeBPA.append(timeID)
            if Money > 0:
                amount = Money / closePrice
                Money = 0
                TradePrice = closePrice
                dataBP.append(closePrice)
                timeBP.append(timeID)
                print("buy point found,  ts: %d, close: %f, amount: %f,    round: %d/%d"%(timeID, closePrice,amount, i+1, tCount-windowLen))
        elif indicator == "sell":
            dataSPA.append(closePrice)
            timeSPA.append(timeID)
            if amount > 0 and (closePrice - TradePrice) / TradePrice > 0.01:
                if TradePrice == 0:
                    print("first point is sell, do nothing")
                else:
                    Money = amount * closePrice
                    amount = 0
                    TradePrice = closePrice
                    dataSP.append(closePrice)
                    timeSP.append(timeID)
                    print("sell point found, ts: %d, close: %f, Money:  %f, round: %d/%d"%(timeID, closePrice,Money,i+1, tCount-windowLen))

        # loop
        for i in range(tCount-windowLen):
            DBcursor = self.Collection.find().sort('id', pymongo.ASCENDING).skip(i+windowLen).limit(1)
            for doc in DBcursor:
                data = data[1:]
                data.append(doc)
                
            indicator,timeID,closePrice = CMMACD.CmIndicator(data)
            if indicator == "buy":
                dataBPA.append(closePrice)
                timeBPA.append(timeID)
                if Money > 0:
                    amount = Money / closePrice
                    Money = 0
                    TradePrice = closePrice
                    dataBP.append(closePrice)
                    timeBP.append(timeID)
                    print("buy point found,  ts: %d, close: %f, amount: %f,    round: %d/%d"%(timeID, closePrice,amount, i+1, tCount-windowLen))
            elif indicator == "sell":
                dataSPA.append(closePrice)
                timeSPA.append(timeID)
                if amount > 0 and (closePrice - TradePrice) / TradePrice > 0.01:
                    if TradePrice == 0:
                        print("first point is sell, do nothing")
                    else:
                        Money = amount * closePrice
                        amount = 0
                        TradePrice = closePrice
                        dataSP.append(closePrice)
                        timeSP.append(timeID)
                        print("sell point found, ts: %d, close: %f, Money:  %f, round: %d/%d"%(timeID, closePrice,Money,i+1, tCount-windowLen))
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

        f, (ax1, ax2, ax3) = plt.subplots(3,1,sharex=True,figsize=(8,12))
        #plt.subplot(211)
        ax1.plot(timeAll, closeAll, color='gray', label="close")
        ax1.scatter(timeBPA,dataBPA,marker='v',c='g',edgecolors='g')
        ax1.scatter(timeSPA,dataSPA,marker='^',c='r',edgecolors='r')

        ax2.plot(timeAll, closeAll, color='gray', label="close")
        ax2.scatter(timeBP,dataBP,marker='o',c='w',edgecolors='g')
        ax2.scatter(timeSP,dataSP,marker='o',c='m',edgecolors='m')

        #plt.subplot(212)
        ax3.plot(timeAll, MACD, label="MACD")
        ax3.plot(timeAll, signal, label="signal")
        ax3.scatter(crossTimesSell,crossSell,marker='o',c='r',edgecolors='r')
        ax3.scatter(crossTimesBuy,crossBuy,marker='o',c='g',edgecolors='g')
        ax3.bar(timeAll,hist,width=600,label="hist")

        #plt.legend()
        plt.show()
