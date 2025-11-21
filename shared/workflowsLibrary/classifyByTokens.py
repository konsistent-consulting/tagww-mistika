from Mistika.Qt import QColor
from Mistika.classes import Cconnector
import os

def init(self):
    self.setClassName("Classify By Tokens")
    self.color=QColor(0x677688)
# creating properties
    self.addProperty("errorMode",0)
    self.addProperty("classifyMode", 0)
    self.addProperty("separator")
    self.addProperty("outputList", "1,2,3,4,5")
#creating connectors
    self.addConnector("files",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_REQUIRED)
    extList=self.outputList.split(",")
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
    if not self.separator:
        res = self.critical("filesSplitter:isReady","separator can not be empty") and res
    if int(self.errorMode)<0 or int(self.errorMode)>3:
        res=self.critical("filesSplitter:isReady","Invalid errorMode {}".format(self.errorMode),"errorMode") and res
    return res

def process(self):
    #And finally, Do the thing here!
    res=True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    outputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_OUTPUT)
    outputList = self.outputList.split(",")
    classifyMode = int(self.classifyMode)

    for c in outputs:
      c.clearUniversalPaths()
    if self.bypassEnabled:
        return True
    for c in inputs:                                 
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
  
            name = os.path.splitext(up.getFileName())[0]
            #print(os.path.splitext(name)[0])
            tokenList=name.split(self.separator)
            numberOfTokens = len(tokenList)
            #print(numberOfTokens)
       
            classified = False
            #print(tokenList)
            #print(outputList)
            for case in outputList:
                case = case.strip()
                #print(case)
                out = None
                if (classifyMode == 0 and str(numberOfTokens) == case) or (classifyMode == 1 and case in tokenList) or ((classifyMode == 2 and str(numberOfTokens) == case)or(classifyMode == 2 and case in tokenList)):
                    #print("MATCH")
                    out=self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, case)
                
                if out:
                    self.info("filesClassifier:process:info","sending {} to {} tokens".format(up.getFileName(),case),"")
                    classified = True
                    out.addUniversalPath(up)

            if not classified:
                func=[None,self.info,self.warning,self.critical][int(self.errorMode)]
                if func:
                    if func == self.critical:
                        self.addFailedUP(up)
                    if classifyMode == 0:
                        res=func("filesClassifier:process:ext","There is no output for {} tokens, sending to 'other'".format(numberOfTokens),"") and res
                    elif classifyMode == 1 or classifyMode ==2:
                        res=func("filesClassifier:process:ext","{} does not have corresponding output, sending to 'other'".format(name),"") and res
                out = self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, "other")
                out.addUniversalPath(up)
    return res

def  onPropertyUpdated(self,name):
    if name=="outputList":
        self.rebuild()
