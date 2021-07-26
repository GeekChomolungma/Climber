from strategy import baseObj

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@localhost:27017"
bo = baseObj.baseObjSpot(conn_str)
bo.LoadData("marketinfo","btcusdt-1min")
bo.Run("1min")