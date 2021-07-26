import time
class Ticker():
    'Ticker is a time util for loop query.'
    def __init__(self, period):
        'period: 1min, 5min, 15min, 30min, 60min, 4hour'
        if period == "1min":
            self.Period = 1 * 60 / 2 
        elif period == "5min":
            self.Period = 5 * 60 / 2 
        elif period == "15min":
            self.Period = 15 * 60 / 2 
        elif period == "30min":
            self.Period = 30 * 60 / 2 
        elif period == "60min":
            self.Period = 60 * 60 / 2 
        elif period == "4hour":
            self.Period = 240 * 60 / 2 
    
    def Setup(self, timeStart):
        self.Start = timeStart
    
    def Reset(self, timeReset):
        self.Start = timeReset

    def Loop(self):
        time.sleep(self.Period)
        return True
