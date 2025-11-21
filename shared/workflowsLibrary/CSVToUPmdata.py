
import Mistika
import csv
import sys
import os
from Mistika.classes import Cconnector
from Mistika.classes import CuniversalPath
from Mistika.classes import CnameConvention
from Mistika.Qt import QColor
# from timecode import Timecode
try:
    import re
except:
    installModule("re")

def init(self):
    self.setClassName("CSV To UPmdata")
    self.addConnector("csv",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_REQUIRED)
    self.addConnector("mdata",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True, "csv")
    self.addProperty("csvDelimiter", '-1')
    self.addProperty("MediaFilesColIndex", 0)
    self.addProperty("SkipLines",0)
    self.addProperty("ChangeBackSlashes",True)
    self.addProperty("SetPrivateData", True)
    self.addProperty("TokenName1")
    self.addProperty("ColumnT1", 0)
    self.addProperty("TokenName2")
    self.addProperty("ColumnT2", 0)
    self.addProperty("TokenName3")
    self.addProperty("ColumnT3", 0)
    self.addProperty("TokenName4")
    self.addProperty("ColumnT4", 0)
    self.addProperty("TokenName5")
    self.addProperty("ColumnT5", 0)
    self.addProperty("TokenNameFrom", 0)
    self.color=QColor(0x94b4f2)
    self.bypassSupported=True    
    onPropertyUpdated(self,"TokenNameFrom")
    return True

def isReady(self):

    res=True
    if self.bypassSupported and self.bypassEnabled:
        return res
    return res

def process(self):

    def checkWinShares(FileName):
        pattern = r'^[A-Z]:\\'
        isWinShare=bool(re.match(pattern, FileName, re.IGNORECASE))
        if isWinShare:
            FileName=FileName.replace('\\','/')
        return FileName

    def isEmptyRow(row):
        for item in row:
            if item!="":
                return False;
        return True;
        
    def addToken(token,rowContent,mfid,mfpd,curvesData):
        if self.ChangeBackSlashes:
            rowContent=checkWinShares(rowContent)
            mfid.setToken(token, rowContent)
            if token.__contains__('.'):
                mfpd[token]=rowContent
                curvesData[token]=rowContent
                
    def processItem(j,token,lenRow,lenHeader,rowValue,mfid,mfpd,curvesData):
        res=True
        if j<lenRow:
            if token != "" :
                addToken(token,rowValue,mfid,mfpd,curvesData)
        else:
            res=self.critical("CSVToUPmdata:processItem:lenError","CSV File has {} but {} excepted".format(lenRow,lenHeader)) and res
        return res
        
    def getAutoDelimiter(csvFile):
        with open(csvFile,encoding='utf-8') as f:
            for i in range (SkipLines+1):
                line= f.readline()
        f.close()
        cnt=0;
        delimiter=2 #default to ;
        for idx in range(3):
            n=line.count(delimiters[idx])
            if n>cnt:
                delimiter=idx;
                cnt=n
        return delimiter
        
    def addMetadata(upLine,row,HeaderTokens):
        res=True
        mfid = upLine.getMediaFileInfoData()
        mfpd = upLine.getPrivateData("propertiesOverride")
        if mfpd == None:
            mfpd = {}
        curvesData = upLine.getPrivateData("CurvesData")
        if curvesData == None:
            curvesData = {}     
        tokensFrom=int(self.TokenNameFrom)
        lenHeader = len(HeaderTokens)
        if tokensFrom==0: # process GetTokenFromHeader tokens
            for j, token in enumerate(HeaderTokens):
                    res=processItem(j,token,len(row),lenHeader,row[j],mfid,mfpd,curvesData) and res
                    
        elif tokensFrom==1: # process useCustomTokens tokens
            for j,k in mfidTokens.items():                                
                    res=processItem(k,j,len(row),lenHeader,row[k],mfid,mfpd,curvesData) and res
        if self.SetPrivateData:
            upLine.setPrivateData("propertiesOverride", mfpd)
            upLine.setPrivateData("CurvesData", curvesData)
            upLine.setMediaFileInfoData(mfid)
        return res            
    
    def injectMdata(up):
        res=True
        csvFile=up.getFilePath()
        ShotsUP=[]
        HeaderTokens=[]
        self.info('CSVtoUPmdata:injectMdata','Processing CSV {}'.format(csvFile))        
        csvDelimiterNumber = int(self.csvDelimiter)
        if csvDelimiterNumber<0:
            csvDelimiterNumber=getAutoDelimiter(csvFile)
        csvDelimiter=delimiters[csvDelimiterNumber]
        with open(csvFile,encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=csvDelimiter)
            numRows=sum(1 for row in enumerate(reader))
            self.setComplexity(numRows*10)
            f.seek(0)
            for i,row in enumerate(reader):
                self.progressUpdated(i*10+1)
                if (self.isCancelled()):
                    return [False,[]]                    
                if i < SkipLines:
                    continue
                if i==SkipLines:
                    HeaderTokens=row
                    #print('HeaderTokens: ',HeaderTokens)
                    numHeaders=len(HeaderTokens)
                    if numHeaders<=1:
                        self.warning("CSVToUPmdata:injectMdata:columnsWarning","CSV file has {} column(s) only. Please check the csv delimiter currently using {} delimiter".format(numHeaders,csvDelimiter))
                else:
                    if isEmptyRow(row):
                        continue
                    FileName =row[FilesRowIndex]
                    hasBrackets='[' in FileName
                    if self.ChangeBackSlashes:
                        FileName=checkWinShares(FileName)
                    #print (FileName)
                    upLine = CuniversalPath(nc)
                    if not hasBrackets:
                        upLine.autoFromName(FileName)
                        upLine.readMetadataFromFile()
                    res=addMetadata(upLine,row,HeaderTokens) and res
                    #resolve tokens in name
                    if hasBrackets: # reprocess with all the metadata loaded to find the file if it exists
                        FileName=upLine.getStringOverride(FileName)                    
                        upLine.autoFromName(FileName)
                        upLine.readMetadataFromFile()
                        res=addMetadata(upLine,row,HeaderTokens) and res
                    ShotsUP.append(upLine)

            f.close()
        return [res,ShotsUP]

    res=True
    if self.bypassEnabled:
        #this node leaves the outputs empty during bypass as the files are not generated
        return True

    input=self.getFirstConnectorByName("csv")
    list = input.getUniversalPaths()
    output=self.getFirstConnectorByName("mdata")
    output.clearUniversalPaths()
    delimiters={ -1:'Auto',0: '\t', 1: ',', 2:';' }
    FilesRowIndex = int(self.evaluate(self.MediaFilesColIndex))
    SkipLines= int(self.evaluate(self.SkipLines))
    mfidTokens = {}
    TokenName1 = self.evaluate(self.TokenName1).strip()
    RowIndexT1 =int(self.evaluate(self.ColumnT1))
    mfidTokens[TokenName1] = RowIndexT1
    TokenName2 = self.evaluate(self.TokenName2).strip()
    RowIndexT2 = int(self.evaluate(self.ColumnT2))
    mfidTokens[TokenName2] = RowIndexT2
    TokenName3 = self.evaluate(self.TokenName3).strip()
    RowIndexT3 = int(self.evaluate(self.ColumnT3))
    mfidTokens[TokenName3] = RowIndexT3
    TokenName4 = self.evaluate(self.TokenName4).strip()
    RowIndexT4 = int(self.evaluate(self.ColumnT4))
    mfidTokens[TokenName4] = RowIndexT4
    TokenName5 = self.evaluate(self.TokenName5).strip()
    RowIndexT5 = int(self.evaluate(self.ColumnT5))
    mfidTokens[TokenName5] = RowIndexT5
    # FrameRate = float(self.mediaFilesFPS)
    # StartFloat = Timecode(FrameRate, StartTC).frame_number
    # EndFloat = Timecode(FrameRate, EndTC).frame_number

    nc=CnameConvention(self.getNameConvention())
    if not nc.toString():
        nc=self.getWorkflow().getNameConvention()

    for upToProcess in list:
        if self.isCancelled():
            return False
        [r, ShotsUP] = injectMdata(upToProcess)
        res = res and r
        if res:
            if ShotsUP:            
                output.addUniversalPaths(ShotsUP)
            self.progressUpdated(self.complexity())
    return res
        
def onPropertyUpdated(self,name):
    try:
        if name=="TokenNameFrom":
            visible=int(self.TokenNameFrom)==1
            for i in range(6):
                self.setPropertyVisible("TokenName{}".format(i),visible)
                self.setPropertyVisible("ColumnT{}".format(i),visible)
                   
    except AttributeError:
        pass            