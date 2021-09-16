import sys
sys.path.append('../..')
import cm
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
cm5 = cm.CmUnit(conn_str, "marketinfo", "btcusdt", "30min", 300)
cm5.BackTest()
