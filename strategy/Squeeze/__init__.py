# sqzOn  = (lowerBB > lowerKC) and (upperBB < upperKC)
# sqzOff = (lowerBB < lowerKC) and (upperBB > upperKC)
# noSqz  = (sqzOn == false) and (sqzOff == false)

# val = linreg(source  -  avg(avg(highest(high, lengthKC), lowest(low, lengthKC)),sma(close,lengthKC)), 
#             lengthKC,0)

# bcolor = iff( val > 0, 
#             iff( val > nz(val[1]), lime, green),
#             iff( val < nz(val[1]), red, maroon))
# scolor = noSqz ? blue : sqzOn ? black : gray 
# plot(val, color=bcolor, style=histogram, linewidth=4)
# plot(0, color=scolor, style=cross, linewidth=2)