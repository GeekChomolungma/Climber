from re import I
import sys

from numpy.core.numeric import NaN
sys.path.append('..')
import builtIndicators
import pandas as pd
import numpy as np

# ma = sma(source, 20)
# range = useTrueRange ? tr : (high - low)
#  It is max(high - low, abs(high - close[1]), abs(low - close[1]))
# rangema = sma(range, lengthKC)
# upperKC = ma + rangema * multKC
# lowerKC = ma - rangema * multKC
def KC(close, high, low):
    'Keltner Channel'
    closePrevious = pd.Series([NaN])
    closePrevious.append(close[1:])
    multKC = 1.5
    ma = builtIndicators.ma.SMA(close,20)
    normalRange = high - low
    upRange = abs(high - closePrevious)
    lowRange = abs(low - closePrevious)
    data = {'normal':normalRange,
            'up':upRange,
            'low':lowRange}
    df = pd.DataFrame(data)
    rangeMax = df.max(axis=1)
    rangema = builtIndicators.ma.SMA(rangeMax,20)
    upperKC = ma + rangema * multKC
    lowerKC = ma - rangema * multKC
    return upperKC, lowerKC