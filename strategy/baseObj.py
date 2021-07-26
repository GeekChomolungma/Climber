import pymongo
import chomoClient
import utils

conn_str = "mongodb://market:admin123@localhost:27017"

class baseObjSpot:
    'baseObj is a father object for all strategy.'
    
    def __init__(self, DB_URL):
        'init DB'
        self.MgoClient = pymongo.MongoClient(DB_URL,serverSelectionTimeoutMS=5000)

    def LoadData(self, db, collection):
        'choose the db collection'
        self.DB = self.MgoClient[db]
        self.Collection = self.DB[collection]

    def Run(self,period):
        'use data to run strategy'
        i = 0
        while i < 10:
            t = utils.ticker.Ticker(period)
            t.Loop()
            c = self.Collection
            item = c.find_one({"id":1626710400})
            print(item)
            i += 1
        
    def Buy(self):
        'Buy'
        chomoClient.client.PlaceOrder("buy")

    def Sell(self):
        'Sell'
        chomoClient.client.PlaceOrder("sell")