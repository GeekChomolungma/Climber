from strategy.FirstBuy import fb

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
bo = fb.FirstBuyPoint(conn_str)
bo.LoadDB("marketinfo","HB-btcusdt-5min")
bo.Run("1min")
