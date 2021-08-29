import sys
sys.path.append('..')
import builtIndicators
import pandas as pd

def CmIndicator(data):
    df = pd.DataFrame(data)
    dataLen = len(data)
    times = df["id"]
    close = df["close"]
    fastMA = builtIndicators.ma.EMA(close,12)
    slowMA = builtIndicators.ma.EMA(close,26)
    MACD = fastMA - slowMA
    signal = builtIndicators.ma.SMA(MACD,9)
    crossIndexSell, crossIndexBuy= builtIndicators.cross.cross(MACD,signal)
    if crossIndexSell[-1] == (dataLen-1):
        return "sell",times[dataLen-1],close[dataLen-1]
    elif crossIndexBuy[-1] == (dataLen-1):
        return "buy",times[dataLen-1],close[dataLen-1]
    return "nothing",times[dataLen-1],close[dataLen-1]


