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
    def __init__(self, TimeID, Val, slope, scolor, bcolor, slopeColor):
        self.timeID = TimeID
        self.val = Val
        self.slope = slope
        self.scolor = scolor
        self.bcolor = bcolor
        self.slopeColor = slopeColor

class SqueezeUnit(strategy.baseObj.baseObjSpot):
    def __init__(self, DB_URL, db, symbol, period, winLen):
        super(SqueezeUnit, self).__init__(DB_URL)
        self.collectionName = "HB-%s-%s"%(symbol, period)
        super(SqueezeUnit, self).LoadDB(db, self.collectionName, period)
        self.symbol = symbol
        self.period = period
        self.winLen = winLen
        self.preState = stateMachine(0, 0, 0, "blue", "lime", "lime")
        dbCursor = self.Collection.find().sort('id', pymongo.ASCENDING).limit(self.winLen)
        self.data = list(dbCursor)
        # first once
        timeID, val, slope, scolor, bcolor, slopeColor = self.calcu()
        self.updatePreState(timeID, val, slope, scolor, bcolor, slopeColor)
    
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

        # check slope color
        if slope > 0:
            if slope > self.preState.slope:
                slopeColor = "lime"
            else:
                slopeColor = "green"
        else:
            if  slope < self.preState.slope:
                slopeColor = "red"
            else:
                slopeColor = "maroon"
        return time[len(time)-1], val, slope, scolor, bcolor, slopeColor
    
    def updatePreState(self, timeID, val, slope, scolor, bcolor, slopeColor):
        self.preState.timeID = timeID
        self.preState.val = val
        self.preState.slope = slope
        self.preState.scolor = scolor
        self.preState.bcolor = bcolor
        self.preState.slopeColor = slopeColor
        
    def RunOnce(self):
        indicator = ""
        curID = self.preState.timeID + self.Offset
        count = self.Collection.count_documents({'id':bson.Int64(curID)})
        if count == 0:
            return False, indicator, 0, 0, 0, 0, 0, 0
        dbCursor = self.Collection.find({"id":bson.Int64(curID)})
        for doc in dbCursor:
            self.data = self.data[1:]
            self.data.append(doc)
            timeID, val, slope, scolor, bcolor, slopeColor = self.calcu()
            if bcolor == "green" and self.preState.bcolor == "lime":
                indicator = "sell"
            if bcolor == "red" and scolor == "gray" and self.preState.scolor == "black":
                indicator = "sell"

            if bcolor == "maroon" and self.preState.bcolor == "red":
                indicator = "buy"
            if bcolor == "lime" and scolor == "gray" and self.preState.scolor == "black":
                indicator = "buy"
            self.close = doc["close"]
            #self.updatePreState(timeID, val, slope, scolor, bcolor, slopeColor)
            return True, indicator, timeID, val, slope, scolor, bcolor, slopeColor
    
    def BackTest(self):
        Money = 10000.0
        Amount = 0.0
        RR = 0.0
        buyID = []
        buyData = []
        sellID = []
        sellData = []
        DataAll = []

        while True:
            newTurn, indicator, timeID, val, slope, scolor, bcolor, slopeColor = self.RunOnce()
            if not newTurn:
                break
            self.updatePreState(timeID, val, slope, scolor, bcolor, slopeColor)
            dic = {"id": self.preState.timeID, "value": self.preState.val, "scolor": self.preState.scolor, "bcolor": self.preState.bcolor, "slope": self.preState.slope, "slopeColor": self.preState.slopeColor}
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
                    print("%s %s buy, close: %f, money: %f, amount: %f"%(date, self.collectionName, self.close, Money, Amount))
                    buyID.append(self.preState.timeID)
                    buyData.append(self.close)

        if Money != 0:
            RR = (Money - 10000.0) / 10000.0
        else:
            RR = (Amount * self.close - 10000.0) / 10000.0
        print("rate of return is: %f"%(RR))

        #plot
        fig, (ax1, ax2, ax3) = plt.subplots(3,1,sharex=True,figsize=(8,12))
        cursor = self.Collection.find().sort('id', pymongo.ASCENDING)
        dfAll = pd.DataFrame(list(cursor))
        
        ax1.plot(dfAll["id"], dfAll["close"], color='gray', label="close")
        ax1.scatter(buyID,buyData,marker='^',c='g',edgecolors='g')
        ax1.scatter(sellID,sellData,marker='v',c='r',edgecolors='r')
        self.Plot(DataAll, ax2, ax3)
        plt.show()

    def Plot(self, units, ax):
        df = pd.DataFrame(units)
        ax.bar(df["id"], df["value"], width=self.Offset*0.75, label="hist", alpha=0.2, color="gray")

        # for vals
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

        # for cross
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
    
    def PlotDerivate(self, units, ax):        
        # for slope
        limeSlopes = [dic for dic in units if dic["slopeColor"] == "lime"]
        if len(limeSlopes)>0:
            dfLime = pd.DataFrame(limeSlopes)
            ax.bar(dfLime["id"], dfLime["slope"], width=self.Offset*0.75, label="hist", color="lime")

        greenSlopes = [dic for dic in units if dic["slopeColor"] == "green"]
        if len(greenSlopes)>0:
            dfgreen = pd.DataFrame(greenSlopes)
            ax.bar(dfgreen["id"], dfgreen["slope"], width=self.Offset*0.75, label="hist", color="green")

        redSlopes = [dic for dic in units if dic["slopeColor"] == "red"]
        if len(redSlopes)>0:
            dfRed = pd.DataFrame(redSlopes)
            ax.bar(dfRed["id"], dfRed["slope"], width=self.Offset*0.75, label="hist", color="red")

        maroonSlopes = [dic for dic in units if dic["slopeColor"] == "maroon"]
        if len(maroonSlopes)>0:
            dfMaroon = pd.DataFrame(maroonSlopes)
            ax.bar(dfMaroon["id"], dfMaroon["slope"], width=self.Offset*0.75, label="hist", color="maroon")
