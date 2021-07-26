from mongoengine import *

connect("marketinfo",host="mongodb://market:admin123@localhost:27017/marketinfo?authSource=admin")

class CandleTicker(Document):
    id = IntField(primary_key=True)  
    amount = FloatField()  
    count = IntField() 
    open = FloatField()
    close = FloatField()
    low = FloatField() 
    high = FloatField() 
    vol = FloatField()
    meta = {'collection': 'btcusdt-1min'}

ticker = CandleTicker.objects(id=1626716400).first()
print(ticker.amount)