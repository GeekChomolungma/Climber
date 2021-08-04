from strategy.FirstBuy import fb

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@localhost:27017"
bo = fb.FirstBuyPoint(conn_str)
bo.LoadDB("marketinfo","HB-btcusdt-1min")
bo.Run("1min")
