from strategy.FirstBuy import fb
from strategy.CmMacd import cm

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
cm = cm.CmMacd(conn_str)
cm.LoadDB("marketinfo")
symbols = ["btcusdt","ethusdt","bchusdt","ltcusdt"]
cm.Run("1min",300,symbols,"5min")
