import pymongo
import strategy.baseObj
import utils.ticker
import numpy as np
import pandas as pd


class FirstBuyPoint(strategy.baseObj.baseObjSpot):
    
    def Run(self,period):
        print("Initially load history data...")
        self.loadHistory()
        print("history data loaded...")
        iter = self.Collection.find().sort('id', pymongo.DESCENDING).limit(1)
        for item in iter:
            print("timestap is :",item["id"])
        while True:
            t = utils.ticker.Ticker(period)
            t.Loop()
            self.catchPoint()
            
    def catchPoint(self):
        iter = self.Collection.find().sort('id', pymongo.DESCENDING).limit(1)
        for item in iter:
            print("timestap is :",item["id"])
        
    def loadHistory(self):
        data = []
        DBcursor = self.Collection.find().sort('id', pymongo.DESCENDING).limit(60)
        for doc in DBcursor:
            data.append(doc)
        s = pd.Series(data[0])
        s.drop(['_id'],inplace = True)
        print(s)
        data.reverse()
        df = pd.DataFrame(data)
        df.drop(columns=['_id'],inplace = True)
        print(df)
        #df.set_index('id',inplace=True)
        df = df.append(s,ignore_index=True)
        print(df)
