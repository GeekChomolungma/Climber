import squeeze
conn_str = "mongodb://market:admin123@139.196.155.97:27017"
squ = squeeze.SqueezeUnit(conn_str, "marketinfo", "btcusdt", "4hour", 100)
squ.BackTest()
