from logging import critical
from Mistika.Qt import QColor
from Mistika.classes import Cconnector
import Mistika
from baseItemTools import totalNumberOfUPs

class CmetadataAssistant:
    def __init__(self,node,metadata):      
        self.m_node=node       
        self.m_metadata=metadata 
    
    def getMetadataValue(self, name):
        return self.getValueRecursive(name, self.m_metadata)

    def getValueRecursive(self, name, data):   
        if name in data:
            return data[name]
        for e in data:
            if type(data[e]) is dict:             
                found = self.getValueRecursive(name, data[e])
                if found is not None:
                    return found

def init(self):
    self.setClassName("Classify By Aspect Ratio")
    self.addProperty("errorMode",0)
    self.addProperty("outputList", "0.56,1.00,1.33,1.78,1.85,2,2.35")
    self.addProperty("threshold", 0)
    #creating connectors
    self.addConnector("files",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("notFound",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("other",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    outputList = self.outputList.split(",")
    for ext in outputList:
        ext = ext.strip()
        try:
            num = float(ext)
            if num.is_integer():
                ext = f"{int(num)}.0"
            else:
                ext = str(num)
        except ValueError:
            pass
        self.addConnector(ext, Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True,"files")
    #configuring the node
    self.bypassSupported=True
    self.color=QColor(0x677688)
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res = True
    outputList = self.evaluate(self.outputList).strip()
    if outputList == "":
        res = self.critical("classifyByAspectRatio:isReady", "'outputList' can not be empty") and res   
    if int(self.errorMode)<0 or int(self.errorMode)>3:
        res=self.critical("classifyByAspectRatio:isReady","Invalid errorMode {}".format(self.errorMode),"errorMode") and res
    return res

def process(self):
    res=True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    outputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_OUTPUT)
    func=[None,self.info,self.warning,self.critical][int(self.errorMode)]
    threshold = self.threshold
    
    for c in outputs:
      c.clearUniversalPaths()
    
    self.setComplexity(totalNumberOfUPs(self))
    if self.bypassEnabled:
        self.progressUpdated(self.complexity())
        return True
    
    currentProgress=0
    for c in inputs:                                 
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False

            currentProgress=currentProgress+1
            self.progressUpdated(currentProgress)
            metadata=up.getMetadata() #get metadata
            if not metadata:
                up.readMetadataFromFile() #read the metadata if it was empty, and get it again
                metadata=up.getMetadata()                
            
            metadataAssistant=CmetadataAssistant(self,metadata)
            resX=metadataAssistant.getMetadataValue("resolutionX")
            resY=metadataAssistant.getMetadataValue("resolutionY")

            try:
                v = round((float(resX) / float(resY)), 2)
            except (TypeError, ZeroDivisionError):
                v = None

            if v == None:
                if func:
                    func("classifyByAspectRatio:process:ext"," Unable to calculate aspect ratio. Sent to 'notFound'".format(up.getFileName()),"")
                out = self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, "notFound")
                out.addUniversalPath(up)
            else:
                classified = False
                outputList=self.outputList.replace(" ","").split(",")

                if threshold == 0:
                    out=self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT,v)
                    if out:
                        self.info("classifyByMetadata:process:info","sending '{}' to '{}'".format(up.getFileName(),v),"")
                        classified = True
                        out.addUniversalPath(up)
                else:
                    vMin = float(v) - float(v)*float(threshold)/100
                    vMax = float(v) + float(v)*float(threshold)/100
                    #print(vMin, v, vMax)

                    for case in outputList:
                        out = None
                        
                        if float(case) >= vMin and float(case) <= vMax:
                            out=self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT,case)

                        if out:
                            self.info("classifyByMetadata:process:info","sending '{}' to '{}'".format(up.getFileName(),case),"")
                            classified = True
                            out.addUniversalPath(up)

                if not classified:
                    if func:
                        func("classifyByMetadata:process:ext","'{}' has aspect ratio of value '{}', not in output list. Sent to 'other'".format(up.getFileName(), v),"") and res
                    out = self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, "other")             
                    out.addUniversalPath(up)

    self.progressUpdated(self.complexity())
    return res

def  onPropertyUpdated(self,name):
    if name =="outputList":
        self.rebuild()
        