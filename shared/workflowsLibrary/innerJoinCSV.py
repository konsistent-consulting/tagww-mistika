import pandas as pd
import os
from Mistika.classes import Cconnector,CuniversalPath,CnameConvention
from Mistika.Qt import QColor
import csvTools

def init(self):
    self.setClassName("Inner Join CSV")
    self.color=QColor("#94b4f2")
    self.addConnector("csv",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("csv",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addProperty("csvDelimiter", '-1')
    self.addProperty("csvFilePath")
    self.addProperty("dstPath")    
    self.addProperty("inputFirst",False)
    self.setDropToProperty("csvFilePath")
    self.setDropSupportedTypes(2) #Files
    self.setDropSupportedFileMasks(["csv"])
    self.bypassSupported=True
    return True
    
def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    return True
    
def process(self):
    def innerJoinCsv(up1,up2,outputFile,csvDelimiter,inputFirst):
        res=True
        self.info("innerJoinCsv:join:out","generating '{}'".format(outputFile))
        file1=up1.getFilePath()
        file2=up2.getFilePath()
        if not file1.endswith(".csv"):
            return self.critical("innerJoinCsv:join:File1","'{}' has no csv extension".format(file1))
        if not file2.endswith(".csv"):
            return self.critical("innerJoinCsv:join:File2","'{}' has no csv extension".format(file2))
        df1 = pd.read_csv(file1,sep=csvDelimiter)
        df2 = pd.read_csv(file2,sep=csvDelimiter)
        commonColumns = list(set(df1.columns) & set(df2.columns))
        if not commonColumns:
            return self.critical("innerJoinCsv:join:noIntersection","Unable to join: No common columns found")                    
        if inputFirst:
            mergedDf = pd.merge(df1, df2, on=commonColumns, how='inner')
        else:
            mergedDf = pd.merge(df2, df1, on=commonColumns, how='inner')
        # Guardar el resultado en un nuevo archivo CSV
        mergedDf.to_csv(outputFile,sep=csvDelimiter,index=False)
        return res
    res=True
    if self.bypassEnabled:
        return True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    output=self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT,"csv")
    csvFilePath=self.evaluate(self.csvFilePath).strip()
    dstPath=self.evaluate(self.dstPath).strip()
    inputFirst=self.inputFirst
    if not os.path.exists(dstPath):
        os.makedirs(dstPath)
    outputList=[]
    up2=CuniversalPath(CnameConvention("[path][baseName][.ext]"))
    up2.setFilePath(csvFilePath)
    csvDelimiterNumber = int(self.csvDelimiter)
    if csvDelimiterNumber<0:
        csvDelimiter=csvTools.getCSVautoDelimiter(up2.getFilePath())      
    else:
        delimiters={ -1:'Auto',0: '\t', 1: ',', 2:';' }
        csvDelimiter=delimiters[csvDelimiterNumber]
    for c in inputs:                                  
        for up in c.getUniversalPaths():
            newup=CuniversalPath(up)            
            if self.isCancelled():
                return False
            dstUP=self.composeDstFilePath(dstPath,newup,False,0)
            ok=innerJoinCsv(up,up2,dstUP.getFilePath(),csvDelimiter,inputFirst)
            if ok:
                outputList.append(dstUP)
            else:
                self.addFailedUP(up)                
    output.addUniversalPaths(outputList)
    return res