from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CnameConvention,CuniversalPath
from mistikaTools import installModule
import Mistika
import os
import csv
from datetime import datetime
try:
    import re
except:
    installModule("re")



def init(self):
    self.setClassName("Metadata To CSV")
    self.addConnector("files",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_REQUIRED)
    self.addConnector("csv",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addProperty("csvPath")
    self.setDropToProperty("csvPath")
    self.setDropSupportedTypes(1)
    self.addProperty("singleCSVperFile",False)
    self.addProperty("overwrite", True)
    self.addProperty("FullMediaPath", True)
    self.addProperty("MediaNameOnly", False)
    self.addProperty("RemoveExtension", False)
    self.addProperty("Header")
    self.addProperty("Footer")
    self.addProperty("BodyText01")
    self.addProperty("BodyText02")
    self.addProperty("BodyText03")
    # self.setAcceptConnectors(True,"files")
    self.bypassSupported=True
    self.color=QColor(65,180,80)
    return True

def isReady(self):
    res=True
    if self.bypassSupported and self.bypassEnabled:
        return res
    if not self.csvPath:
        res=self.critical("mdata2CSV:csvPath:notFound","Destination Path can not be empty") and res
    if self.FullMediaPath and self.MediaNameOnly:
        res=self.warning("mdata2CSV:isReady:TooMany CSV Rows", 'Select FullMediaPath and MediaNameOnly will fail with CSVtoDFILT node') and res
    return res

def process(self):

    def myStringOverride(up,TokenLine):
        mfidTokens={}
        Tokens = re.findall(TokenRegEx, TokenLine)
        tmfid = up.getMediaFileInfoData()
        # print(tmfid.dataTree())
        for t in Tokens:
            tUP=str(tmfid.getTokenDecorated(t.strip("[]")))
            if t == "[nowDate]":
                tUP=nowDate
            if tUP == 'None':
                tUP = up.getStringOverride(t)
                if tUP == 'Undefined':
                    self.warning("mdata2CSV:getToken:Undefined", t +'  in  ' +SourceFile+ '   Does not refer to any metadata value')
            mfidTokens[t] = tUP
        for i,j in mfidTokens.items():
            TokenLine=TokenLine.replace(i,j)
        # print(TokenLine)
        return TokenLine

    def generateCSV (dstPathCSV,csvContent):
        try:
            for path in dstPathCSV:
                if not os.path.exists(path):
                    try:
                        os.makedirs(path)
                    except OSError:
                        self.critical("mdata2CSV:csvFile:notFound", "Error creating dir csvFile".format(csvFile))
                dstFileCSV = path + mwfName + '_' + nodeName +'.csv'
                if os.path.isfile(dstFileCSV) and self.overwrite:
                    os.remove(dstFileCSV)
                elif os.path.isfile(dstFileCSV):
                    return self.critical("mdata2CSV:GenerateCSV:overwrite", "csvFile already exists")

                for row in csvContent:
                    with open(dstFileCSV, 'a', newline='') as f:
                        wr = csv.writer(f, quoting=csv.QUOTE_ALL)
                        wr.writerow(row)
                    f.close()
        except csv.Error as e:
            return self.critical('mdata2CSV:CSVerror', 'file {}, line {}: {}'.format(f, writer.line_num, e))
        return [True,dstFileCSV]

    def generateSingleCSV (dstPathCSV,csvContent):
        try:
            dstFileCSV = dstPathCSV + '_' + mwfName + '_' + nodeName +'.csv'
            if os.path.isfile(dstFileCSV) and self.overwrite:
                os.remove(dstFileCSV)
            elif os.path.isfile(dstFileCSV):
                return self.critical("mdata2CSV:GenerateCSV:overwrite", "csvFile already exists")

            with open(dstFileCSV, 'a', newline='') as f:
                wr = csv.writer(f, quoting=csv.QUOTE_ALL)
                wr.writerow(csvContent)
            f.close()
        except csv.Error as e:
            return self.critical('mdata2CSV:CSVerror', 'file {}, line {}: {}'.format(f, writer.line_num, e))
        return [True,dstFileCSV]


    if self.bypassEnabled:
        return True
    res=True
    nc=CnameConvention(self.getNameConvention())
    if not nc.toString():
        nc=self.getWorkflow().getNameConvention()
    outConCSV=self.getFirstConnectorByName("csv")
    outConCSV.clearUniversalPaths()
    input = self.getFirstConnectorByName("files")
    list=input.getUniversalPaths()
    csvPath=self.evaluate(self.csvPath).strip()
    Header = self.evaluate(self.Header).strip()
    Footer = self.evaluate(self.Footer).strip()
    BodyText01 = self.evaluate(self.BodyText01).strip()
    BodyText02 = self.evaluate(self.BodyText02).strip()
    BodyText03 = self.evaluate(self.BodyText03).strip()
    TokenRegEx = "\[[^\]]*\]"       # [baseName],[comment2]...
    mwfName=self.getWorkflow().objectName if self.getWorkflow() else None
    nodeName=self.objectName
    csvContent=[]
    dstPathCSV=[]
    now = datetime.now()
    nowDate = now.strftime("%m/%d/%Y_%I:%M:%S %p")

    for up in list:
        if self.isCancelled():
            return False
        csvRow=[]
        mfid = up.getMediaFileInfoData()
        SourceFile=str(mfid.getToken("sourceFile"))
        SourceName=str(mfid.getToken("name"))
        if self.RemoveExtension:
            SourceName=SourceName.rsplit('.')[0]
        csvPathUP= myStringOverride(up,csvPath)
        if not os.path.exists(csvPathUP):
            try:
                os.makedirs(csvPathUP)
            except OSError:
                self.addFailedUP(up)
                self.critical("mdata2CSV:csvPathUP:notFound", "Error creating dir csvFile".format(csvPathUP))
        HeaderUP = myStringOverride(up,Header)
        FooterUP = myStringOverride(up,Footer)
        BodyText01UP = myStringOverride(up,BodyText01)
        BodyText02UP = myStringOverride(up,BodyText02)
        BodyText03UP = myStringOverride(up,BodyText03)

        if self.FullMediaPath:
            csvRow.append(SourceFile)
        if self.MediaNameOnly:
            csvRow.append(SourceName)
        csvRow.extend([HeaderUP,BodyText01UP,BodyText02UP,BodyText03UP,FooterUP])
        csvContent.append(csvRow)
        dstPathCSV.append(csvPathUP)

        if self.singleCSVperFile:
            csvBaseName=up.getBaseName()
            csvPathUPBase=csvPathUP +'/'+ csvBaseName
            [r, CSV] = generateSingleCSV(csvPathUPBase, csvRow)
            res = res and r
            if res:
                outUP = CuniversalPath(nc, CSV)
                outConCSV.addUniversalPath(outUP)

    if not self.singleCSVperFile:
        [r,CSV]=generateCSV(dstPathCSV,csvContent)
        res=res and r
        if res:
            outUP=CuniversalPath(nc,CSV)
            outConCSV.addUniversalPath(outUP)

    return res

