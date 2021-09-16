import sys
sys.path.append('../..')
import strategy.baseObj
import pymongo
import indicators.KC
import indicators.BB
import pandas as pd
from scipy.stats import linregress
import numpy as np
import matplotlib.pyplot as plt
import time
import bson
import datetime

class stateMachine():
    'for squeeze state'
    def __init__(self, TimeID, Val, scolor, bcolor):
        self.timeID = TimeID
        self.val = Val
        self.scolor = scolor
        self.bcolor = bcolor

class SqueezeUnit(strategy.baseObj.baseObjSpot):
    def __init__(self, DB_URL, db, symbol, period, winLen):
        super(SqueezeUnit, self).__init__(DB_URL)
        self.collectionName = "HB-%s-%s"%(symbol, period)
        super(SqueezeUnit, self).LoadDB(db, self.collectionName, period)
        self.symbol = symbol
        self.period = period
        self.winLen = winLen
        self.preState = stateMachine(0, 0, "blue", "black")
        dbCursor = self.Collection.find().sort('id', pymongo.ASCENDING).limit(self.winLen)
        self.data = list(dbCursor)
        # first calcu
        timeID, val, scolor, bcolor = self.calcu()
        self.updatePreState(timeID, val, scolor, bcolor)
    
    def calcu(self):
        df = pd.DataFrame(self.data)
        time = df["id"]
        close = df["close"]
        high = df["high"]
        low = df["low"]
        # cross
        upperKC, lowerKC = indicators.KC.KC(close, high, low)
        upperBB, lowerBB = indicators.BB.BB(close)
        sqzOn  = ((lowerBB[len(lowerBB)-1] > lowerKC[len(lowerKC)-1]) and (upperBB[len(upperBB)-1] < upperKC[len(upperKC)-1]))
        sqzOff = ((lowerBB[len(lowerBB)-1] < lowerKC[len(lowerKC)-1]) and (upperBB[len(upperBB)-1] > upperKC[len(upperKC)-1]))
        noSqz  = ((sqzOn == False) and (sqzOff == False))
        if noSqz:
            scolor = "blue"
        else:
            if sqzOn:
                scolor = "black"
            else:
                scolor = "gray"
        # val
        # val = linreg(source - avg(avg(highest(high, lengthKC), lowest(low, lengthKC)),sma(close,lengthKC)), lengthKC,0)
        highS = high.rolling(window=20).max()
        lowS = low.rolling(window=20).min()
        hlAvg = (highS + lowS)/2.0
        smaS = close.rolling(window=20).mean()
        diffAvgs = (hlAvg + smaS)/2.0
        slope, intercept, r_value, p_value, std_err = linregress(np.arange(20), close[-20:] - diffAvgs[-20:])
        val = intercept + slope*19
        if val > 0:
            if val > self.preState.val:
                bcolor = "lime"
            else:
                bcolor = "green"
        else:
            if  val < self.preState.val:
                bcolor = "red"
            else:
                bcolor = "maroon"
        return time[len(time)-1], val, scolor, bcolor
    
    def updatePreState(self, timeID, val, scolor, bcolor):
        self.preState.timeID = timeID
        self.preState.val = val
        self.preState.scolor = scolor
        self.preState.bcolor = bcolor
        
    def Run(self):
        indicator = ""
        curID = self.preState.timeID + self.Offset
        count = self.Collection.count_documents({'id':bson.Int64(curID)})
        if count == 0:
            return False, indicator
        dbCursor = self.Collection.find({"id":bson.Int64(curID)})
        for doc in dbCursor:
            self.data = self.data[1:]
            self.data.append(doc)
            timeID, val, scolor, bcolor = self.calcu()
            if bcolor == "green" and self.preState.bcolor == "lime":
                indicator = "sell"
            if bcolor == "maroon" and self.preState.bcolor == "red":
                indicator = "buy"
            self.close = doc["close"]
            self.updatePreState(timeID, val, scolor, bcolor)
            return True, indicator
    
    def BackTest(self):
        Money = 10000.0
        Amount = 0.0
        RR = 0.0
        buyID = []
        buyData = []
        sellID = []
        sellData = []
        DataAll = []

        newTurn = True
        while newTurn:
            newTurn, indicator = self.Run()
            dic ={"id":self.preState.timeID, "value":self.preState.val, "scolor":self.preState.scolor, "bcolor":self.preState.bcolor}
            DataAll.append(dic)
            date = datetime.datetime.fromtimestamp(self.preState.timeID).strftime('%Y-%m-%d %H:%M:%S')
            if indicator == "sell":
                if Amount != 0:
                    Money = 0.998 * Amount * self.close
                    Amount = 0
                    print("%s %s Sell, close: %f, money: %f, amount: %f"%(date, self.collectionName, self.close, Money, Amount))
                    sellID.append(self.preState.timeID)
                    sellData.append(self.close)
            
            if indicator == "buy":
                if Money != 0:
                    Amount = 0.998 * Money / self.close
                    Money = 0
                    print("%s %s Sell, close: %f, money: %f, amount: %f"%(date, self.collectionName, self.close, Money, Amount))
                    buyID.append(self.preState.timeID)
                    buyData.append(self.close)
                    

        if Money != 0:
            RR = (Money - 10000.0) / 10000.0
        else:
            RR = (Amount * self.close - 10000.0) / 10000.0
        print("rate of return is: %f"%(RR))

        #plot
        fig, (ax1, ax2) = plt.subplots(2,1,sharex=True,figsize=(8,12))
        cursor = self.Collection.find().sort('id', pymongo.ASCENDING)
        dfAll = pd.DataFrame(list(cursor))
        
        ax1.plot(dfAll["id"], dfAll["close"], color='gray', label="close")
        ax1.scatter(buyID,buyData,marker='^',c='g',edgecolors='g')
        ax1.scatter(sellID,sellData,marker='v',c='r',edgecolors='r')
        self.Plot(DataAll, ax2)
        plt.show()

    def Plot(self, units, ax):
        # units = []
        # dbCount = self.Collection.estimated_document_count()
        # print("%s has %d items"%(self.collectionName, dbCount))
        # for i in range(dbCount-self.winLen):
        #     dbCursor = self.Collection.find().sort('id', pymongo.ASCENDING).skip(i + self.winLen).limit(1)
        #     self.data = self.data[1:]
        #     self.data.append(list(dbCursor)[0])
        #     timeID, val, scolor, bcolor = self.calcu()
        #     self.updatePreState(timeID, val, scolor, bcolor)
        #     dic ={"id":timeID, "value":val, "scolor":scolor, "bcolor":bcolor}
        #     units.append(dic)
        #     print("%s, round: %d/%d"%(self.collectionName, i+self.winLen, dbCount))
        df = pd.DataFrame(units)
        ax.bar(df["id"], df["value"], width=self.Offset*0.75, label="hist", alpha=0.2, color="gray")

        limeVals = [dic for dic in units if dic["bcolor"] == "lime"]
        if len(limeVals)>0:
            dfLime = pd.DataFrame(limeVals)
            ax.bar(dfLime["id"], dfLime["value"], width=self.Offset*0.75, label="hist", color="lime")

        greenVals = [dic for dic in units if dic["bcolor"] == "green"]
        if len(greenVals)>0:
            dfgreen = pd.DataFrame(greenVals)
            ax.bar(dfgreen["id"], dfgreen["value"], width=self.Offset*0.75, label="hist", color="green")

        redVals = [dic for dic in units if dic["bcolor"] == "red"]
        if len(redVals)>0:
            dfRed = pd.DataFrame(redVals)
            ax.bar(dfRed["id"], dfRed["value"], width=self.Offset*0.75, label="hist", color="red")

        maroonVals = [dic for dic in units if dic["bcolor"] == "maroon"]
        if len(maroonVals)>0:
            dfMaroon = pd.DataFrame(maroonVals)
            ax.bar(dfMaroon["id"], dfMaroon["value"], width=self.Offset*0.75, label="hist", color="maroon")

        blackCross = [dic for dic in units if dic["scolor"] == "black"]
        if len(blackCross)>0:
            dfBlack= pd.DataFrame(blackCross)
            ax.scatter(dfBlack["id"], np.zeros(len(dfBlack["id"]), dtype=object), marker='+', color="black")

        grayCross = [dic for dic in units if dic["scolor"] == "gray"]
        if len(grayCross)>0:
            dfGray = pd.DataFrame(grayCross)
            ax.scatter(dfGray["id"], np.zeros(len(dfGray["id"]), dtype=object), marker='+', color="gray")

        blueCross = [dic for dic in units if dic["scolor"] == "blue"]
        if len(blueCross) > 0:
            dfBlue = pd.DataFrame(blueCross)
            ax.scatter(dfBlue["id"], np.zeros(len(dfBlue["id"]), dtype=object), marker='+', color="blue")
