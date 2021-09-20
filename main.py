from strategy.CmMacd import cm
import time

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
symbols = ["btcusdt","ethusdt","bchusdt","ltcusdt"]

CmUnits = []
for symbol in symbols:
    cmu = cm.CmUnit(conn_str, "marketinfo", symbol, "30min", 300)
    cmu.initModel()
    CmUnits.append(cmu)

while True:
    time.sleep(30.0)
    for idx in range(len(symbols)):
        indicator, Brought, Sold, closePrice = CmUnits[idx].RunOnce()
        f = open('out.log','a+')
        if Brought == True:
            CmUnits[idx].AlarmAndAction(CmUnits[idx].collectionName, CmUnits[idx].symbol, CmUnits[idx].period, "buy", f)
        if Sold == True:
            CmUnits[idx].AlarmAndAction(CmUnits[idx].collectionName, CmUnits[idx].symbol, CmUnits[idx].period, "sell", f)
        f.close()
