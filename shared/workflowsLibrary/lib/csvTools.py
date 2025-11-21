import csv

def getCSVautoDelimiter(csvFile,skipLines=0):
    delimiters={ -1:'Auto',0: '\t', 1: ',', 2:';' }
    with open(csvFile,encoding='utf-8') as f:
        for i in range (skipLines+1):
            line= f.readline()
    f.close()
    cnt=0;
    delimiter=2 #default to ;
    for idx in range(3):
        n=line.count(delimiters[idx])
        if n>cnt:
            delimiter=idx;
            cnt=n
    return delimiters[delimiter]
        