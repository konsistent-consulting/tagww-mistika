import Mistika
import csv
import sys
from Mistika.classes import Cconnector,CnameConvention,CuniversalPath
from Mistika.Qt import QColor

def init(self):
    self.setClassName("CSV To DFILT") 
    self.color=QColor(0x94b4f2)
    self.addProperty("delimiter",",")
    self.addProperty("headerDefault","MISTIKA WATERMARK")
    self.addProperty("bodyDefault","body Text body Text")
    self.addProperty("footerDefault","footer line")
    self.addConnector("csv",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("files",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.bypassSupported=True
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res=True
    if self.delimiter=="":
        res=self.critical("CSVtoDFILT:delimiter","'Delimiter can not be empty")
    return res

def process(self):   
       
    def processOneCSV(up,output):
        filename=up.getFilePath()
        self.info('CSVtoDFILT:processOneCSV','Processing CSV {}'.format(filename))
        with open(filename, encoding='utf-8') as f:
            delim=self.delimiter.encode('utf-8','ignore') if sys.version_info[0]<3 else self.delimiter
            reader=csv.reader(f, delimiter=delim)
            try:
                for line in reader:
                    nc=self.getNameConvention()
                    if nc.toString()=="":
                        nc=self.getWorkflow().getNameConvention()
                    dst=CuniversalPath(nc)
                    dst.autoFromName(line[0])
                    data={}
                    data["header.text"]= line[1] if line[1]!="" else self.headerDefault
                    data["body1.text"]= line[2] if line[2]!="" else self.bodyDefault
                    data["body2.text"] = line[3] if line[3] != "" else self.bodyDefault
                    data["body3.text"] = line[4] if line[4] != "" else self.bodyDefault
                    data["footer.text"]= line[5] if line[5]!="" else self.footerDefault
                    dst.setPrivateData("CurvesData",data)
                    print(data)
                    output.addUniversalPath(dst)      
            except csv.Error as e:
                return self.critical('CSVtoDFILT:CSVerror','file {}, line {}: {}'.format(filename, reader.line_num, e))
        return True
        
    res=True  
    input=self.getFirstConnectorByName("csv")
    output=self.getFirstConnectorByName("files")
    output.clearUniversalPaths ()
    if self.bypassEnabled:
        return True
    list=input.getUniversalPaths()
    for up in list:
            if self.isCancelled():
                return False
            res=res and processOneCSV(up,output) 
    return res