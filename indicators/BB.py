import sys
sys.path.append('..')
import builtIndicators
import pandas as pd
import numpy as np

def BB(close):
    'bollinger band'
    mult = 1.5
    basis = builtIndicators.ma.SMA(close,20)
    dev = mult * builtIndicators.ma.STD(close,20)
    upperBB = basis + dev
    lowerBB = basis - dev
    return upperBB, lowerBB