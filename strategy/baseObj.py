import pymongo
import chomoClient.client
import utils.ticker

conn_str = "mongodb://market:admin123@localhost:27017"

class baseObjSpot:
    'baseObjSpot is a father object for all strategy.'
    
    def __init__(self, DB_URL):
        'init DB'
        self.MgoClient = pymongo.MongoClient(DB_URL,serverSelectionTimeoutMS=5000)

    def LoadDB(self, db, collection, period):
        'choose the db collection'
        self.DB = self.MgoClient[db]
        self.Collection = self.DB[collection]
        # get offset of period: 1min, 5min, 15min, 30min, 60min, 4hour
        if period == "1min":
            self.Offset = 60
        elif period == "5min":
            self.Offset = 5 * 60
        elif period == "15min":
            self.Offset = 15 * 60
        elif period == "30min":
            self.Offset = 30 * 60
        elif period == "60min":
            self.Offset = 60 * 60
        elif period == "4hour":
            self.Offset = 240 * 60
        else:
            self.Offset = 60

    def Run(self,period):
        'use data to run strategy'
        i = 0
        while i < 10:
            t = utils.ticker.Ticker(period)
            t.Loop()
            print("baseObj Running...")
            i += 1
    def Buy(self,amount):
        'Buy'
        chomoClient.client.PlaceOrder("btcusdt", "buy-market", amount, "100", "spot-api")

    def Sell(self,amount):
        'Sell'
        chomoClient.client.PlaceOrder("btcusdt", "sell-market", amount, "100", "spot-api")