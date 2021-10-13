import builtIndicators
from indicators import CMMACD
import pandas as pd
import strategy.baseObj
import pymongo
import datetime
import matplotlib.pyplot as plt
import bson
import chomoClient.client
from alert import alert

class CmUnit(strategy.baseObj.baseObjSpot):
    def __init__(self, DB_URL, db, symbol, period, winLen):
        super(CmUnit, self).__init__(DB_URL)
        self.collectionName = "HB-%s-%s"%(symbol, period)
        super(CmUnit, self).LoadDB(db, self.collectionName, period)
        self.symbol = symbol
        self.period = period
        self.winLen = winLen

        # init stateMachine
        self.TimeID = 0
        self.BPLock = False
        self.SPLock = True
        self.PrevBP = -999999
        self.PrevSP = 999999
        self.GMacdBP = -999999
        self.GMacdSP = 999999
        self.MustBuy = False
        self.MustSell = False
        self.PrevFastMA = 0
        self.PreSlowMA = 0
        self.PrevMA30 = 0

        # set data
        dbCursor = self.Collection.find().sort('id', pymongo.ASCENDING).limit(self.winLen)
        self.data = list(dbCursor)

        # calcu once
        self.CmCoreOnePageWithoutMust()
    
    def initModel(self):
        f = open('out.log','a+')
        while True:
            indicator, Bought, Sold, closePrice, lastMacd, err = self.RunOnce()
            if err == "no new":
                break
            if err == "conn failed":
                continue
            date = datetime.datetime.fromtimestamp(self.TimeID).strftime('%Y-%m-%d %H:%M:%S')
            if Bought == True:
                print("%s %s Bought, indicator: %s, ts: %d, close: %f"%(date, self.collectionName, indicator, self.TimeID, closePrice), file = f)
            if Sold == True:
                print("%s %s Sold,   indicator: %s, ts: %d, close: %f"%(date, self.collectionName, indicator, self.TimeID, closePrice), file = f)
        print("%s initially done. BPLock: %r, SPLock: %r, mustBuy: %r, mustSell: %r, gMacdBP: %f, gMacdSP: %f, timeID: %d, prevFastMA: %f, preSlowMA: %f, prevMA30: %f" \
            %(self.collectionName, self.BPLock, self.SPLock, self.MustBuy, self.MustSell, self.GMacdBP, self.GMacdSP, self.TimeID, self.PrevFastMA, self.PreSlowMA, self.PrevMA30), file = f)
        f.close()
        
    def CmCoreOnePage(self):
        Bought = False
        Sold = False
        indicator,timeID,closePrice,lastMacd,lastSlowMA,stdMA = CMMACD.CmIndicator(self.data)        
        self.TimeID = timeID
        if indicator == "buy":
            self.PrevBP = lastMacd
            up, down = self.GenMustSignal()
            self.MustSell = down
            if self.MustSell and not self.SPLock:
                # sell 1
                self.GMacdSP = lastMacd # optional
                self.SPLock = True
                self.BPLock = False
                self.MustSell = False
                self.MustBuy = False
                Sold = True
            # elif lastMacd > self.PrevSP and lastMacd > 0 and not self.BPLock:
            #     # buy 1
            #     self.BPLock = True
            #     self.SPLock = False
            #     self.GMacdBP = lastMacd
            #     self.MustBuy = False
            #     Bought = True
            else:
                # buy 2              
                if not self.MustSell and not self.BPLock and (self.MustBuy or (self.GMacdSP-lastMacd)/lastSlowMA > 0.954*stdMA):
                    self.BPLock = True
                    self.SPLock = False
                    self.GMacdBP = lastMacd
                    self.MustBuy = False
                    Bought = True
                elif lastMacd < self.GMacdBP:
                    self.GMacdBP = lastMacd

        if indicator == "sell":
            self.PrevSP = lastMacd
            up, down = self.GenMustSignal()
            self.MustBuy = up
            if self.MustBuy and not self.BPLock:
                # buy 1
                self.GMacdBP = lastMacd # optional
                self.BPLock = True
                self.SPLock = False
                self.MustBuy = False
                self.MustSell = False
                Bought = True
            # elif lastMacd < self.PrevBP and lastMacd < 0 and not self.SPLock:
            #     # sell 1
            #     self.SPLock = True
            #     self.BPLock = False
            #     self.GMacdSP = lastMacd
            #     self.MustSell = False
            #     Sold = True
            else:
                # sell 2
                if not self.MustBuy and not self.SPLock and (self.MustSell or (lastMacd-self.GMacdBP)/lastSlowMA > 0.954*stdMA):
                    self.SPLock = True
                    self.BPLock = False
                    self.GMacdSP = lastMacd
                    self.MustSell = False
                    Sold = True
                elif lastMacd > self.GMacdSP:
                    self.GMacdSP = lastMacd
        return indicator, Bought, Sold, closePrice, lastMacd, lastSlowMA, stdMA

    def CmCoreOnePageWithoutMust(self):
        indicator,timeID,closePrice,lastMacd,lastSlowMA,stdMA = CMMACD.CmIndicator(self.data)
        self.TimeID = timeID
        #self.ExpectedID = self.TimeID + self.Offset
        return indicator, closePrice, lastMacd, lastSlowMA, stdMA

    def GenMustSignal(self):
        df = pd.DataFrame(self.data)
        close = df["close"]
        fastMA = builtIndicators.ma.EMA(close,5)
        slowMA = builtIndicators.ma.EMA(close,10)
        MA30 = builtIndicators.ma.EMA(close,30)
        curFastMA = fastMA[len(fastMA)-1]
        curSlowMA = slowMA[len(slowMA)-1]
        curMA30 = MA30[len(MA30)-1] 
        up, down = self.judgeCross(curFastMA, curSlowMA, curMA30)
        self.PrevFastMA = curFastMA
        self.PreSlowMA = curSlowMA
        self.PrevMA30 = curMA30
        return up, down

    def judgeCross(self, curFastMA, curSlowMA, curMA30):
        up = False
        down = False
        if curFastMA > curSlowMA and self.PrevFastMA < self.PreSlowMA:
            if curSlowMA > curMA30 and self.PreSlowMA < self.PrevMA30:
                up = True
        if curFastMA < curSlowMA and self.PrevFastMA > self.PreSlowMA:
            if curSlowMA < curMA30 and self.PreSlowMA > self.PrevMA30:
                down = True
        return up, down

    def getAccountBalance(self, currency):
        'get currency balance'
        balance = chomoClient.client.GetAccountBalance(currency)
        print("the currency: ", currency, "amount: ", balance)
        return balance
        
    def AlarmAndAction(self, collection, symbol, period, indicator, outlog):
        timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if indicator == "buy":
            alertText = "%s %s: will rise!!! buy now!"%(timeNow, collection)
            print(alertText,file=outlog)
            if symbol == "btcusdt":
                self.Buy()
            for i in range(2):
                text = "HuoBi %s-%s: 要涨了!!! 现在买入! 当前时间: %s, 报警提醒次数(%d/2)" %(symbol,period,timeNow,i+1)
                alert.Alert(text)
        if indicator == "sell":
            alertText = "%s %s: will descend!!! sell quickly!"%(timeNow, collection)
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
    
    def RunOnce(self):
        indicator = ""
        err = "nil"
        closePrice = 0
        lastMacd = 0
        timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # check new candle updated.
        try:
            curID = self.TimeID + self.Offset
            count = self.Collection.count_documents({'id':bson.Int64(curID)})
            if count == 0:
                f = open('out.log','a+')
                outStr = "%s HB-%s check once: timeID: %d, BPLock: %r, SPLock: %r, mustBuy: %r, mustSell: %r, gMacdBP: %f, gMacdSP: %f, prevFastMA: %f, preSlowMA: %f, prevMA30: %f"\
                    %(timeNow, self.symbol, self.TimeID, self.BPLock, self.SPLock, self.MustBuy, self.MustSell, self.GMacdBP, self.GMacdSP, self.PrevFastMA, self.PreSlowMA, self.PrevMA30)
                print(outStr, file=f)
                f.close()
                return indicator, closePrice, lastMacd, 0, 0, "no new"
            dbCursor = self.Collection.find({"id":bson.Int64(curID)})                    
        except:
            f = open('out.log','a+')
            errStr = "%s Error: HB-%s DB Connection failed"%(timeNow, self.symbol)
            print(errStr, file=f)
            f.close()
            return indicator, closePrice, lastMacd, 0, 0, "conn failed"
        else:
            for doc in dbCursor:
                self.data = self.data[1:]
                self.data.append(doc)
                indicator, closePrice, lastMacd, lastSlowMA, stdMA = self.CmCoreOnePageWithoutMust()
            return indicator, closePrice, lastMacd, lastSlowMA, stdMA, err

    def Plot(self, ax1, ax2):
        dataAll = [] 
        DBcursorAll = self.Collection.find().sort('id', pymongo.ASCENDING)
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

        # plot cross dots between Macd and signal
        crossIndexSell, crossIndexBuy= builtIndicators.cross.cross(MACD,signal)
        crossTimesSell = [timeAll[ci] for ci in crossIndexSell]
        crossSell = [signal[ci] for ci in crossIndexSell]
        crossTimesBuy = [timeAll[ci] for ci in crossIndexBuy]
        crossBuy = [    signal[ci] for ci in crossIndexBuy]
        ax2.plot(timeAll, MACD, label="MACD")
        ax2.plot(timeAll, signal, label="signal")
        ax2.scatter(crossTimesSell,crossSell,marker='o',c='r',edgecolors='r')
        ax2.scatter(crossTimesBuy,crossBuy,marker='o',c='g',edgecolors='g')
        ax2.bar(timeAll,hist,width=600,label="hist")
        

    def BackTest(self):
        Money = 10000.0
        Amount = 0.0
        closePrice = 0
        cp = 0
        f = open('cmTest.log','a+')
        BaseCount = self.Collection.find().sort('id', pymongo.ASCENDING).count()
        timeBP = [] 
        timeSP = []
        dataSP = []
        dataBP = []
        timeBPA = []
        timeSPA = []
        dataBPA = []
        dataSPA = []
        i = 0
        while True:
            i += 1 
            indicator, Bought, Sold, cp, lastMacd, err = self.RunOnce()
            if err == "no new" or err == "conn failed":
                break
            closePrice = cp
            date = datetime.datetime.fromtimestamp(self.TimeID).strftime('%Y-%m-%d %H:%M:%S')
            if indicator == "buy":
                timeBPA.append(self.TimeID)
                dataBPA.append(closePrice)
            if indicator == "sell":
                timeSPA.append(self.TimeID)
                dataSPA.append(closePrice)
            if Bought == True:
                Amount = Money / closePrice * 0.998
                Money = 0
                timeBP.append(self.TimeID)
                dataBP.append(closePrice)
                print("%s, HB-%s-%s, Bought, indicator: %s, ts: %d, close: %f, amount: %f, round: %d/%d" \
                    %(date, self.symbol, self.period, indicator, self.TimeID, closePrice, Amount, i+self.winLen, BaseCount), file = f)
            if Sold == True:
                Money = Amount * closePrice * 0.998
                Amount = 0
                timeSP.append(self.TimeID)
                dataSP.append(closePrice)
                print("%s, HB-%s-%s, Sold,   indicator: %s, ts: %d, close: %f, Money:  %f, round: %d/%d"% \
                    (date, self.symbol, self.period, indicator, self.TimeID, closePrice, Money, i+self.winLen, BaseCount), file = f)

        RateOfReturn = 0.0
        if Money == 0:
            RateOfReturn = closePrice * Amount / 10000.0 - 1.0
        elif Amount == 0:
            RateOfReturn = Money / 10000.0 - 1.0
        print("%s back test done. Rate of Return:%f" \
                %(self.collectionName, RateOfReturn), file = f)
        f.close()

        dataAll = []
        DBcursorAll = self.Collection.find().sort('id', pymongo.ASCENDING)
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
