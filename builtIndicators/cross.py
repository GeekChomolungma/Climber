def  cross(seriesA, seriesB):
    'A, B are series, return their crossing dots series'
    diff =  seriesA - seriesB
    color = ["red","green"]
    return [i for i in range(diff.size) if i > 0 and diff[i] * diff[i-1] < 0 and diff[i-1] > 0],[i for i in range(diff.size) if i > 0 and diff[i] * diff[i-1] < 0 and diff[i-1] < 0]

