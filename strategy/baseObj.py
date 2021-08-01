import pymongo
import chomoClient.client
import utils.ticker

conn_str = "mongodb://market:admin123@localhost:27017"

class baseObjSpot:
    'baseObjSpot is a father object for all strategy.'
    
    def __init__(self, DB_URL):
        'init DB'
        self.MgoClient = pymongo.MongoClient(DB_URL,serverSelectionTimeoutMS=5000)

    def LoadDB(self, db, collection):
        'choose the db collection'
        self.DB = self.MgoClient[db]
        self.Collection = self.DB[collection]

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
        chomoClient.client.PlaceOrder(amount)

    def Sell(self):
        'Sell'
        chomoClient.client.PlaceOrder("sell")