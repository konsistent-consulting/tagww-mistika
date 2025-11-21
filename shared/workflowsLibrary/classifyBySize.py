from Mistika.Qt import QColor
from Mistika.classes import Cconnector
import os

def init(self):
    self.setClassName("Classify By Size")
    self.color=QColor(0x677688)
# creating properties
    self.addProperty("errorMode",0)
    self.addProperty("classifyMode", 0)
    self.addProperty("value", "5")
    self.addProperty("valueRanges", "1-2,2-7,7-50")
    self.setPropertyVisible("value", int(self.classifyMode) == 0)
    self.setPropertyVisible("valueRanges", int(self.classifyMode) == 1)
    self.addProperty("units", "1")
#creating connectors
    self.addConnector("files",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_REQUIRED)
    if int(self.classifyMode) == 0:
        self.addConnector("< "+ str(self.value),Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
        self.addConnector("= " + str(self.value),Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
        self.addConnector("> "+ str(self.value),Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    elif int(self.classifyMode) == 1:
        extList=self.valueRanges.split(",")
        for ext in extList:
            self.addConnector(ext.strip(),Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
        self.addConnector("other",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True,"files")
#configuring the node
    self.bypassSupported=True
    self.color=QColor(0,180,180)
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res=True
    if int(self.classifyMode) == 1:
        for case in self.valueRanges.split(","):
            limits = case.split("-")
            try:
                minim, maxim = int(limits[0]), int(limits[1])
            except (ValueError, IndexError):
                res = self.critical("classifyBySize:badRanges", "valueRanges does not have a correct structure. Ex: 'min0-max0, min1-max1, ..., minX-maxX'") and res
    if not self.value:
        res = self.critical("filesSplitter:isReady","value can not be empty") and res
    if int(self.errorMode)<0 or int(self.errorMode)>3:
        res=self.critical("filesSplitter:isReady","Invalid errorMode {}".format(self.errorMode),"errorMode") and res
    return res

def process(self):
    #And finally, Do the thing here!
    res=True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    outputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_OUTPUT)
    valueRanges = self.valueRanges.split(",")
    units = int(self.units)

    for c in outputs:
      c.clearUniversalPaths()
    if self.bypassEnabled:
        return True
    for c in inputs:                                 
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False

            size = up.getTotalSize()

            classified = False
            if int(self.classifyMode) == 0:
                if size < int(self.value)*units:
                    out=self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, "< "+ str(self.value))
                elif size == int(self.value)*units:
                    out=self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, "= "+ str(self.value))
                else:
                    out=self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, "> "+ str(self.value))

                out.addUniversalPath(up)

            if int(self.classifyMode) == 1:
                for case in valueRanges:
                    out = None
                    limits = case.split("-")
                    minim, maxim = int(limits[0]), int(limits[1])

                    if size >= minim*units and size < maxim*units:
                        out=self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, case)
                    
                    if out:
                        self.info("classifyBySize:process:info","sending {} to {} tokens".format(up.getFileName(),case),"")
                        classified = True
                        out.addUniversalPath(up)

                if not classified:
                    func=[None,self.info,self.warning,self.critical][int(self.errorMode)]
                    if func:
                        if func == self.critical:
                            self.addFailedUP(up)
                        res=func("classifyBySize:process:ext","There is no output for {} bytes, sending to 'other'".format(size),"") and res
                    out = self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, "other")
                    out.addUniversalPath(up)
    return res

def  onPropertyUpdated(self,name):
    if name== "classifyMode":
        self.setPropertyVisible("value", int(self.classifyMode) == 0)
        self.setPropertyVisible("valueRanges", int(self.classifyMode) == 1)
        self.rebuild()
    if name=="value":
        self.rebuild()
    if name=="valueRanges":
        self.rebuild()
