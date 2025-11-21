from Mistika.Qt import QColor
from Mistika.classes import Cconnector

def init(self):
    self.setClassName("Classify By Extension")
    self.color=QColor(0x677688)
# creating properties
    self.addProperty("errorMode",0)
    self.addProperty("filterMode", 0)
    self.addProperty("caseSensitive", False)
    self.addProperty("extensions","mov,mxf,mp4,j2k,r3d,rnd")
#creating connectors
    self.addConnector("files",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_REQUIRED)
    extList=self.extensions.split(",")
    if not self.caseSensitive:
        extList=self.extensions.lower().split(",")
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
    if int(self.errorMode)<0 or int(self.errorMode)>3:
        res=self.critical("filesSplitter:isReady","Invalid errorMode {}".format(self.errorMode),"errorMode") and res
    return res

def process(self):
    #And finally, Do the thing here!
    res=True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    outputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_OUTPUT)
    caseSensitive = self.caseSensitive 
    extensions = self.extensions
    filterMode = int(self.filterMode)

    for c in outputs:
      c.clearUniversalPaths()
    if self.bypassEnabled:
        return True
    for c in inputs:                                 
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
  
            ext=up.getExtension()

            if not caseSensitive:
                ext = ext.lower()
            
            classified = False
            if caseSensitive:
                extList=self.extensions.replace(" ","").split(",")
            else:
                extList=list(set(self.extensions.lower().replace(" ","").split(",")))

            for case in extList:
                out = None
 
                if (filterMode == 0 and ext == case) or (filterMode == 1 and ext.startswith(case)) or (filterMode == 2 and case in ext) or (filterMode== 3 and ext.endswith(case)):
                    out=self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, case)
                
                if out:
                    self.info("filesClassifier:process:info","sending {} to {}".format(up.getFileName(),case),"")
                    classified = True
                    out.addUniversalPath(up)

            if not classified:
                func=[None,self.info,self.warning,self.critical][int(self.errorMode)]
                if func:
                    if func == self.critical:
                        self.addFailedUP(up)
                    res=func("filesClassifier:process:ext","The extension {} could not be classified".format(ext),"") and res
                out = self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, "other")
                out.addUniversalPath(up)

    return res

def  onPropertyUpdated(self,name):
    if name=="extensions":
        self.rebuild()
    if name=="caseSensitive":
        self.rebuild()
