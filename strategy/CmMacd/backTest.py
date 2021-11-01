import sys
sys.path.append('../..')
import cm
conn_str = "mongodb://market:admin123@65.52.174.232:27017"
cm5 = cm.CmUnit(conn_str, "marketinfo", "btcusdt", "30min", 300)
cm5.BackTest()
