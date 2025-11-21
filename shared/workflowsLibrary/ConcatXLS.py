import Mistika
from Mistika.Qt import QColor
from Mistika.classes import  CbaseItem
from Mistika.classes import  Cconnector
from mistikaTools import installModule
try:
    import pandas as pd
    import openpyxl
    import xlwt
except: 
    installModule("pandas")
    installModule("openpyxl")
    installModule("xlwt")
    import pandas as pd

def init(self):
    self.setClassName("Concat XLS")
    self.addConnector("xls",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("xls",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addProperty("dstFile")
    self.bypassSupported=True
    self.color=QColor(0x677688)
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res=True
    if not self.dstFile:
        res=self.critical("mergeXLS:dstFile:notFound","Destination Path can not be empty")
    return res

def process(self):

    outputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_OUTPUT)
    out=outputs[0]
    out.clearUniversalPaths()
    if self.bypassEnabled:
        for c in self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT):
            for p in c.getUniversalPaths():
                out.addUniversalPath(p)
        return True
        
    inputFound=False
    dst=self.evaluate(self.dstFile);
    #create destination File
    #add input files to the destonation file
    all=pd.DataFrame()
    for c in self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT):
        for p in c.getUniversalPaths():   
            if self.isCancelled():
                return False   
            for f in p.getAllFiles():
                inputFound=True
                df = pd.read_excel(f)
                all=all.append(df,ignore_index=True)
    if inputFound:
        writer=pd.ExcelWriter(dst)
        all.to_excel(writer,"mergedData")
        writer.save()

        out.setUniversalPathFromString(dst)
    return True