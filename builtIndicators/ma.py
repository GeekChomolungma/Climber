import pandas as pd
import matplotlib.pyplot as plt

def SMA(data,length):
    'data pandas dataframe or series'
    return data.rolling(window=length).mean()

def EMA(data,length):
    'data pandas dataframe or series'
    return data.ewm(span=length,min_periods=length,adjust=False).mean()

