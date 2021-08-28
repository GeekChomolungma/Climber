import sys
sys.path.append('..')
from indicators import CMMACD
import strategy.baseObj
import utils.ticker
import pymongo
import chomoClient.client
from alert import alert
import datetime

class CmMacd30Min(strategy.baseObj.baseObjSpot):
    def LoadDB(self, db, collection):
        'choose the db collection'
        self.DB = self.MgoClient[db]
        self.Collection = self.DB[collection]

    def Run(self,period,windowLen):
        self.timeID = 0
        while True:
            t = utils.ticker.Ticker(period)
            t.Loop()
            data = []
            DBcursor = self.Collection.find().sort('id', pymongo.DESCENDING).limit(windowLen)
            for doc in DBcursor:
                data.append(doc)
            data.reverse()
            indicator,timeID = CMMACD.CmIndicator(data)
            if indicator == "buy" and self.timeID != timeID:
                timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print("HuoBi BTC-30min: 要涨了!!! 现在买入! ", timeNow)
                self.Buy()
                self.timeID = timeID
                for i in range(3):
                    text = "HuoBi BTC-30min: 要涨了!!! 现在买入! 当前时间: %s, 报警提醒次数(%d/3)" %(timeNow,i+1)
                    alert.Alert(text)
            elif indicator == "sell" and self.timeID != timeID:
                timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print("HuoBi BTC-30min: 要跌了!!! 赶紧卖掉! ", timeNow)
                self.Sell()
                self.timeID = timeID
                for i in range(3):
                    text = "HuoBi BTC-30min: 要跌了!!! 赶紧卖掉! 当前时间: %s, 报警提醒次数(%d/3)" %(timeNow,i+1)
                    alert.Alert(text)

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
        