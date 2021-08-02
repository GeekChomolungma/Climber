from numpy.core.numeric import NaN
import pymongo
import strategy.baseObj
import utils.ticker
import numpy as np
import pandas as pd
import chomoClient.client


class FirstBuyPoint(strategy.baseObj.baseObjSpot):
        
    def Run(self,period):
        print("Initially load history data...")
        self.loadHistory()
        print("history data loaded...")
        iter = self.Collection.find().sort('id', pymongo.DESCENDING).limit(1)
        for item in iter:
            print("timestap is :",item["id"])

        #print("!!!Train Data length is",self.trainData["high"][:])

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
            # firstly, add header0 into df tail.
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

            # try to calculate metrics
            # and make order
            res, exist = self.calculateBuyPoint()
            if exist == True:
                amount = self.getAccountBalance("usdt")
                if float(amount) > 15.0:
                    self.Buy(amount)
            
            res, exist = self.calculateSellPoint()
            if exist == True:
                amount = self.getAccountBalance("btc")
                self.Sell(amount)


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
        
    def getAccountBalance(self, currency):
        'get currency balance'
        balance = chomoClient.client.GetAccountBalance(currency)
        print("the currency: ", currency, "amount: ", balance)
        return balance

    def calculateBuyPoint(self):
        'calculate metrics'
        # firstly, find max high spot globally
        gIndex = self.trainData["high"][:-1].idxmax()
        gSpot = self.trainData.iloc[gIndex,:]
        if gIndex < len(self.trainData)/3:
            # left window is too short, it's late
            return NaN, False
        print("BuyPoint Train Data length is",len(self.trainData["high"][:-1]),"Max high price is: ", gSpot["high"], "timestamp: ", gSpot["id"])

        # secondly, check left window
        leftWindow = self.trainData[:gIndex]
        leftLowIndex, leftHigIndex = leftWindow["low"].idxmin(), leftWindow["high"].idxmin()
        leftMinSpot, leftMaxSpot = leftWindow[leftLowIndex,:],leftWindow[leftHigIndex,:]

        # thirdly, check right window
        rightWindow = self.trainData[gIndex+1:-1]
        rightLowIndex, rightHigIndex = rightWindow["low"].idxmin(), rightWindow["high"].idxmin()
        rightMinSpot, rightMaxSpot = rightWindow[rightLowIndex,:],rightWindow[rightHigIndex,:]
        if (rightLowIndex - gIndex) < (len(self.trainData) - gIndex) * 3/4:
            # rightMinSpot is too close to gSpot, it's late
            return NaN, False
        elif rightMinSpot["low"] < leftMinSpot["low"]:
            # tilt and decline right side
            return NaN, False
        
        return 1,True

    def calculateSellPoint(self):
        'calculate metrics'
        # firstly, find max high spot globally
        gIndex = self.trainData["low"][:-1].idxmin()
        gSpot = self.trainData.iloc[gIndex,:]
        if gIndex < len(self.trainData)/3:
            # left window is too short, it's late
            return NaN, False
        print("SellPoint Train Data length is",len(self.trainData["low"][:-1]),"Min low price is: ", gSpot["low"], "timestamp: ", gSpot["id"])

        # secondly, check left window
        leftWindow = self.trainData[:gIndex]
        leftLowIndex, leftHigIndex = leftWindow["low"].idxmax(), leftWindow["high"].idxmax()
        leftMinSpot, leftMaxSpot = leftWindow[leftLowIndex,:],leftWindow[leftHigIndex,:]

        # thirdly, check right window
        rightWindow = self.trainData[gIndex+1:-1]
        rightLowIndex, rightHigIndex = rightWindow["low"].idxmax(), rightWindow["high"].idxmax()
        rightMinSpot, rightMaxSpot = rightWindow[rightLowIndex,:],rightWindow[rightHigIndex,:]
        if (rightMaxSpot - gIndex) < (len(self.trainData) - gIndex) * 3/4:
            # rightMaxSpot is too close to gSpot, it's late
            return NaN, False
        elif rightMaxSpot["high"] > leftMaxSpot["high"]:
            # tilt and decline left side
            return NaN, False
        
        return 1,True

