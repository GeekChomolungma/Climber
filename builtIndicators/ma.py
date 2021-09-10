def SMA(data,length):
    'data pandas dataframe or series'
    return data.rolling(window=length).mean()

def EMA(data,length):
    'data pandas dataframe or series'
    return data.ewm(span=length,min_periods=length,adjust=False).mean()

def STD(series, length):
    'standard diff of series'
    return series.rolling(window=length).std()
