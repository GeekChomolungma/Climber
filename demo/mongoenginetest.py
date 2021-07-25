from mongoengine import *

connect("marketinfo",host="mongodb://market:admin123@localhost:27017/marketinfo?authSource=admin")

class CandleTicker(Document):
    id = IntField()  
    amount = FloatField()  
    count = IntField() 
    open = FloatField()
    close = FloatField()
    low = FloatField() 
    high = FloatField() 
    vol = FloatField()
    meta = {'collection': 'btcusdt-1min'}

ticker = CandleTicker.objects().get(id=1626716400)
print(ticker.amount)