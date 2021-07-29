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
        iter = self.Collection.find().sort('id', pymongo.DESCENDING).limit(2)
        headerData = [doc for doc in iter]
        print("header[0] id is:",headerData[0]["id"], "and header[1] id is:" , headerData[1]["id"])
        print("latest id in trainData:", self.trainData.loc[len(self.trainData)-1]["id"])
        if headerData[0]["id"] > self.trainData.loc[len(self.trainData)-1]["id"]:
            'db is updated, so update the trainData'
            # first, add header0 into df tail.
            s0 = pd.Series(headerData[0])
            s0.drop(['_id'],inplace = True)
            self.trainData = self.trainData.append(s0,ignore_index=True)
            self.trainData = self.trainData[1:]
            self.trainData.reset_index(drop=True, inplace=True)
            
            # then, update header1 to df tail - 1.
            s1 = pd.Series(headerData[1])
            s1.drop(['_id'],inplace = True)
            print(s1)
            self.trainData.loc[len(self.trainData)-2] = s1
            print("updated train data:")
            print(self.trainData)
        else:
            print("continue...")
    
    def loadHistory(self):
        data = []
        DBcursor = self.Collection.find().sort('id', pymongo.DESCENDING).limit(60)
        for doc in DBcursor:
            data.append(doc)
        data.reverse()
        df = pd.DataFrame(data)
        df.drop(columns=['_id'],inplace = True)
        self.trainData = df
        print(df)
        
        
