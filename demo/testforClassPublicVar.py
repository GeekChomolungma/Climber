class test:
    count = 0
    
    def __init__(self):
        test.count += 1

t1 = test()
print("t1=",t1.count)
t2 = test()
print("t1=",t1.count,"t2=",t2.count)
t3 = test()
print("t1=",t1.count,"t2=",t2.count,"t3=",t3.count)

class t1(test):
    def __init__(self):
        test.__init__(self)
        self.Omit = "111"

class t2(test):
    def __init__(self):
        test.__init__(self)
        self.Omit = "222"

class t3(test):
    def __init__(self):
        test.__init__(self)
        self.Omit = "333"

tt1 = t1()
tt2 = t2()
tt3 = t3()
print("t1Omit=",tt1.Omit,"t2Omit=",tt2.Omit,"t3Omit=",tt3.Omit)
