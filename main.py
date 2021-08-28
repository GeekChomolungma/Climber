from strategy.FirstBuy import fb
from strategy.CmMacd import cm

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
cm30 = cm.CmMacd30Min(conn_str)
cm30.LoadDB("marketinfo","HB-btcusdt-30min")
cm30.Run("1min",300)
