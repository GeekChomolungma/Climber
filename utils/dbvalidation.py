from threading import current_thread
from warnings import catch_warnings
import pymongo

conn_str = "mongodb://market:admin123@localhost:27017"
MgoClient = pymongo.MongoClient(conn_str,serverSelectionTimeoutMS=5000)
db = MgoClient["marketinfo"]
c = db["HB-btcusdt-1min"]

previousItemID = 1627805820 - 60
iter = c.find().sort('id', pymongo.ASCENDING)
count = 0
iterCopy = iter.clone()
iterCopy.next()

for item in iter:
    count += 1
    curTime = item["id"]
    try:
        nextTime = iterCopy.next()["id"]
        #print("from", curTime,"to:",nextTime)
        if curTime + 60 != nextTime:
            print("this interval is not 60")
            print("from", curTime,"to:",nextTime)
    except StopIteration:
        nextTime = curTime
        print("at end of slice")

print(count)