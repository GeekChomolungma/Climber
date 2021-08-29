from os import close
import sys
sys.path.append('..')
from indicators import CMMACD
import strategy.baseObj
import utils.ticker
import pymongo
import chomoClient.client
from alert import alert
import datetime
import pandas as pd

class CmMacd(strategy.baseObj.baseObjSpot):
    def LoadDB(self, db):
        'choose the db collection'
        self.DB = self.MgoClient[db]

    def Run(self,tickTime,windowLen,symbols,period="5min"):
        # 1st query balance of usdt
        # if >15$, then we are buyer.
        amount = self.getAccountBalance("usdt")
        if float(amount) > 15.0:
            self.haveMoney = True
            self.haveAmount = False
        else:
            self.haveMoney = False
            self.haveAmount = True
        self.tradePrice = 0

        # 2nd lets go trade
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
                outStr = "symbol: %s, indicator: %s, time: %s" %(symbols[idx],indicator,timeNow)
                f = open('out.log','a+')
                print(outStr,file = f)
                if indicator == "buy" and self.timeIDList[idx] != timeID and self.haveMoney:
                    # record the tradePrice
                    self.tradePrice = clPrice
                    timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    alertText = "HuoBi %s: 要涨了!!! 现在买入! 时间: %s"%(collection,timeNow)
                    print(alertText,file=f)
                    if symbols[idx] == "btcusdt":
                        self.Buy()
                    self.haveMoney = False
                    self.haveAmount = True
                    self.timeIDList[idx] = timeID
                    for i in range(2):
                        text = "HuoBi %s-%s: 要涨了!!! 现在买入! 当前时间: %s, 报警提醒次数(%d/2)" %(symbols[idx],period,timeNow,i+1)
                        alert.Alert(text)
                elif indicator == "sell" and self.timeIDList[idx] != timeID and self.haveAmount and self.tradePrice < clPrice:
                    self.tradePrice = clPrice
                    # 4 conditions: sell, not same id, have amount, and not descending
                    timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    alertText = "HuoBi %s: 要跌了!!! 赶紧卖掉! 时间: %s"%(collection,timeNow)
                    print(alertText,file=f)
                    if symbols[idx] == "btcusdt":
                        self.Sell()
                    self.haveMoney = True
                    self.haveAmount = False
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
        collection = "HB-%s-5min"%(symbol)
        self.Collection = self.DB[collection]
        tCount = self.Collection.find().sort('id', pymongo.ASCENDING).count()
        data = []
        DBcursor = self.Collection.find().sort('id', pymongo.ASCENDING).limit(windowLen)
        for doc in DBcursor:
            data.append(doc)

        for i in range(tCount-windowLen):
            DBcursor = self.Collection.find().sort('id', pymongo.ASCENDING).skip(i+windowLen).limit(1)
            for doc in DBcursor:
                data = data[1:]
                data.append(doc)
                
            indicator,timeID,closePrice = CMMACD.CmIndicator(data)
            if indicator == "buy" and Money > 0:
                amount = Money / closePrice
                Money = 0
                TradePrice = closePrice
                print("buy point found,  ts: %d, close: %f, amount: %f,    round: %d/%d"%(timeID, closePrice,amount, i+1, tCount-windowLen))
            elif indicator == "sell" and amount > 0:
                # #M1
                if TradePrice >= closePrice:
                    # DESCENDING         
                    continue
                else:
                    if TradePrice == 0:
                        print("first point is sell, do nothing")
                    else:
                        Money = amount * closePrice
                        amount = 0
                        TradePrice = closePrice
                        print("sell point found, ts: %d, close: %f, Money:  %f, round: %d/%d"%(timeID, closePrice,Money,i+1, tCount-windowLen))
                # #M2
                # if abs((TradePrice - closePrice) / TradePrice) < 0.01:
                #     continue
                # else:
                #     if TradePrice == 0:
                #         print("first point is sell, do nothing")
                #     else:
                #         Money = amount * closePrice
                #         amount = 0
                #         TradePrice = closePrice
                #         print("sell point found, ts: %d, close: %f, Money:  %f, round: %d/%d"%(timeID, closePrice,Money,i+1, tCount-windowLen))
            # #M3
            # else:
            #     if TradePrice > 0 and (closePrice - TradePrice) / TradePrice > 0.03 and amount > 0:
            #         #or (TradePrice - closePrice) / TradePrice > 0.02
            #         Money = amount * closePrice
            #         amount = 0
            #         TradePrice = closePrice
            #         print("sell over 0.04 return, ts: %d, close: %f, Money:  %f, round: %d/%d"%(timeID, closePrice,Money,i+1, tCount-windowLen))
        if Money == 0:
            RateOfReturn = TradePrice * amount / 10000.0 - 1.0
        elif amount == 0:
            RateOfReturn = Money / 10000.0 - 1.0
        print("Rate of Return in %s is %f"%(symbol, RateOfReturn))