from strategy.FirstBuy import fb
from strategy.CmMacd import cm

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
cm = cm.CmMacd(conn_str)
cm.LoadDB("marketinfo")
symbols = ["btcusdt","ethusdt","bchusdt","ltcusdt"]
#cm.RunV2("1min",300,symbols,"30min")
cm.RunV3(symbols, 300, "30min", "4hour")