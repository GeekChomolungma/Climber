import sys
sys.path.append('../..')
import cm
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
cm5 = cm.CmMacd(conn_str)
cm5.LoadDB("marketinfo")
symbol = "btcusdt"
symbols = ["btcusdt"]
cm5.CMTest(symbol,"30min", 300)
