import sys
sys.path.append('../..')
import cm
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
cm5 = cm.CmMacd(conn_str)
cm5.LoadDB("marketinfo")
symbol = "btcusdt"
symbols = ["btcusdt"]
#cm5.BT5min(300,symbol)
cm5.CMTest(300,symbol)
#cm5.RunV3(symbols, 300)
