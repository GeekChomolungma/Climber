import sys
sys.path.append('..')
from indicators import CMMACD
import strategy.baseObj
import utils.ticker
import numpy as np
import pandas as pd
import pymongo
import chomoClient.client



class CmMacd30Min(strategy.baseObj.baseObjSpot):
    def LoadDB(self, db, collection):
        'choose the db collection'
        self.DB = self.MgoClient[db]
        self.Collection = self.DB[collection]

    def Run(self,period,windowLen):
        while True:
            t = utils.ticker.Ticker(period)
            t.Loop()
            print("history data loaded...")
            data = []
            DBcursor = self.Collection.find().sort('id', pymongo.DESCENDING).limit(windowLen)
            for doc in DBcursor:
                data.append(doc)
            data.reverse()
            indicator = CMMACD.CmIndicator(data)
            print("indicator: ", indicator)
            if indicator == "buy":
                self.Buy()
            elif indicator == "sell":
                self.Sell()

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
        