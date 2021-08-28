import sys
sys.path.append('..')
import builtIndicators
import pandas as pd

def CmIndicator(data):
    df = pd.DataFrame(data)
    times = df["id"]
    close = df["close"]
    fastMA = builtIndicators.ma.EMA(close,12)
    slowMA = builtIndicators.ma.EMA(close,26)
    MACD = fastMA - slowMA
    signal = builtIndicators.ma.SMA(MACD,9)
    crossIndexSell, crossIndexBuy= builtIndicators.cross.cross(MACD,signal)
    if crossIndexSell[-1] == (len(data)-1):
        # the last index in data
        print("sell point: time:", times[len(times)-1])
        return "sell"
    elif crossIndexBuy[-1] == (len(data)-1):
        print("sell point: time:", times[len(times)-1])
        return "buy"
    
    return "nothing"

