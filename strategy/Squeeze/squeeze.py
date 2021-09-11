import strategy.baseObj
import pymongo
import indicators.KC
import indicators.BB
import pandas as pd
from scipy.stats import linregress
import numpy as np

class stateMachine():
    def __init__(self):
        print()

class SqueezeUnit(strategy.baseObj.baseObjSpot):
    def __init__(self, DB_URL, symbol, period):
        super(SqueezeUnit, self).__init__(DB_URL)
        self.symbol = symbol
        self.period = period
        self.collectionName = "HB-%s-%s"%(self.symbol, self.period)
        self.collection = self.DB[self.collectionName]

        dbCount = self.collection.find().count()
        self.data = []
        #dbCur = self.collection.find().sort('id', pymongo.ASCENDING).skip(1).limit(1)

    def LoadDB(self, db):
        'choose the db collection'
        self.DB = self.MgoClient[db]
    
    def calcu(self):
        df = pd.DataFrame(self.data)
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # cross
        upperKC, lowerKC = indicators.KC.KC(close, high, low)
        upperBB, lowerBB = indicators.BB.BB(close)

        # val
        # val = linreg(source - avg(avg(highest(high, lengthKC), lowest(low, lengthKC)),sma(close,lengthKC)), lengthKC,0)
        highS = high.rolling(window=20).max()
        lowS = low.rolling(window=20).min()
        hlAvg = (highS + lowS)/2.0
        smaS = close.rolling(window=20).mean()
        diffAvgs = (hlAvg + smaS)/2.0
        slope, intercept, r_value, p_value, std_err = linregress(np.arange(20), close[-20:] - diffAvgs[-20:])
        


    def Run(self):
        c = "HB-%s-%s"%(self.symbol, self.period)
        Collection = self.DB[c]
        Collection.find().sort('id', pymongo.ASCENDING).skip(1).limit(1)

    
    