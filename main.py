from strategy.CmMacd import cm

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
CmU = cm.CmMacd(conn_str)
CmU.LoadDB("marketinfo")
symbols = ["btcusdt","ethusdt","bchusdt","ltcusdt"]
CmU.RunV2Re(symbols, 300, "30min")