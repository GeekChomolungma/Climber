from strategy import baseObj
conn_str = "mongodb://market:admin123@localhost:27017"

testut = baseObj.baseObjSpot(conn_str)
testut.Buy("100")