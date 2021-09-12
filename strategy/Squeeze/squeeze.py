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

class stateMachine():
    def __init__(self):
        print()

class SqueezeUnit(strategy.baseObj.baseObjSpot):
    def __init__(self, DB_URL, db, symbol, period, winLen):
        super(SqueezeUnit, self).__init__(DB_URL)
        self.collectionName = "HB-%s-%s"%(symbol, period)
        super(SqueezeUnit, self).LoadDB(db, self.collectionName)
        self.symbol = symbol
        self.period = period
        self.winLen = winLen
        dbCursor = self.Collection.find().sort('id', pymongo.ASCENDING).limit(self.winLen)
        self.data = list(dbCursor)
        print(self.data)
        print("data lenght is %d"%(len(self.data)))
    
    def calcu(self):
        df = pd.DataFrame(self.data)
        time = df["id"]
        close = df["close"]
        high = df["high"]
        low = df["low"]
        # cross
        upperKC, lowerKC = indicators.KC.KC(close, high, low)
        upperBB, lowerBB = indicators.BB.BB(close)
        sqzOn  = ((lowerBB[-1:].values > lowerKC[-1:].values) and (upperBB[-1:].values < upperKC[-1:].values))
        sqzOff = ((lowerBB[-1:].values < lowerKC[-1:].values) and (upperBB[-1:].values > upperKC[-1:].values))
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
            if val > self.preVal:
                bcolor = "lime"
            else:
                bcolor = "green"
        else:
            if  val < self.preVal:
                bcolor = "red"
            else:
                bcolor = "maroon"
        self.preVal = val
        return time[-1:].values, val, scolor, bcolor

    def RunPlot(self):
        units = []
        dbCount = self.Collection.estimated_document_count()
        print("%s has %d items"%(self.collectionName, dbCount))
        self.preVal = 0
        for i in range(dbCount-self.winLen):
            dbCursor = self.Collection.find().sort('id', pymongo.ASCENDING).skip(i + self.winLen).limit(1)
            self.data = self.data[1:]
            self.data.append(list(dbCursor)[0])
            timeID, val, scolor, bcolor = self.calcu()
            dic ={"id":timeID, "value":val, "scolor":scolor, "bcolor":bcolor}
            units.append(dic)
            print("%s, round: %d/%d"%(self.collectionName, i+self.winLen, dbCount))
        df = pd.DataFrame(units)
        plt.bar(df["id"], df["value"], width=600, label="hist", alpha=0.2, color="gray")

        limeVals = [dic for dic in units if dic["bcolor"] == "lime"]
        if len(limeVals)>0:
            dfLime = pd.DataFrame(limeVals)
            plt.bar(dfLime["id"], dfLime["value"], width=600, label="hist", color="lime")

        greenVals = [dic for dic in units if dic["bcolor"] == "green"]
        if len(greenVals)>0:
            dfgreen = pd.DataFrame(greenVals)
            plt.bar(dfgreen["id"], dfgreen["value"], width=600, label="hist", color="green")

        redVals = [dic for dic in units if dic["bcolor"] == "red"]
        if len(redVals)>0:
            dfRed = pd.DataFrame(redVals)
            plt.bar(dfRed["id"], dfRed["value"], width=600, label="hist", color="red")

        maroonVals = [dic for dic in units if dic["bcolor"] == "maroon"]
        if len(maroonVals)>0:
            dfMaroon = pd.DataFrame(maroonVals)
            plt.bar(dfMaroon["id"], dfMaroon["value"], width=600, label="hist", color="maroon")

        blackCross = [dic for dic in units if dic["scolor"] == "black"]
        if len(blackCross)>0:
            dfBlack= pd.DataFrame(blackCross)
            plt.scatter(dfBlack["id"], np.zeros(len(dfBlack["id"]), dtype=object), marker='+', color="black")

        grayCross = [dic for dic in units if dic["scolor"] == "gray"]
        if len(grayCross)>0:
            dfGray = pd.DataFrame(grayCross)
            plt.scatter(dfGray["id"], np.zeros(len(dfGray["id"]), dtype=object), marker='+', color="gray")

        blueCross = [dic for dic in units if dic["scolor"] == "blue"]
        if len(blueCross) > 0:
            dfBlue = pd.DataFrame(blueCross)
            plt.scatter(dfBlue["id"], np.zeros(len(dfBlue["id"]), dtype=object), marker='+', color="blue")
        plt.show()

conn_str = "mongodb://market:admin123@139.196.155.97:27017"
squ = SqueezeUnit(conn_str, "marketinfo", "btcusdt", "30min", 300)
squ.RunPlot()
