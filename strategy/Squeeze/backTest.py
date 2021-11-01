import squeeze
conn_str = "mongodb://market:admin123@65.52.174.232:27017"
squ = squeeze.SqueezeUnit(conn_str, "marketinfo", "btcusdt", "30min", 80)
squ.BackTest()
