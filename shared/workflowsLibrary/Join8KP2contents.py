# v 0.5 bug fixed. QColor import missing
# v 0.4 bug fixed. not detecting remaining size correctly
# v 0.3 P8 classes extracted to lib/panasonic8K
# v 0.2 
# tesst only mode added
# repeated names check added
#v 0.1 initial draft

import os
import shutil
import sys
from Mistika.classes import Cconnector
from Mistika.classes import CuniversalPath
from Mistika.Qt import QColor

import panasonic8K
from panasonic8K import Cp2CardCopier
    
def init(self):
    self.setClassName("Join 8KP2 Contents")   
    self.color=QColor(0x677688)
    self.addProperty("dstPath")
    self.addProperty("cardName","p2Card")
    self.addProperty("cardSize",32)
    self.addProperty("mode",Cp2CardCopier.MODE_COPY) #0=move, 1=copy
    self.addConnector("p8",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("out",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True,"p8")
    self.bypassSupported=True    
    self.setDropToProperty("dstPath")
    #1=Directories, 2=Files, 3=both
    self.setDropSupportedTypes(1) 
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res=True
    dst=self.evaluate(self.dstPath)
    if dst=="":
        res=self.critical("joinP8contents:isReady:dst","'dstPath' can not be empty") and res
    if not os.path.isdir(dst):
        res=self.critical("joinP8contents:isReady:notDIr","'dstPath' {} is not a directory".format(dst)) and res
    return res

def process(self):
    out=self.getFirstConnectorByName("out")
    out.clearUniversalPaths()
    if self.bypassEnabled:
        for c in self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT):
            for p in c.getUniversalPaths():      
                out.addUniversalPath(p)
        return True
    res=True
    dstFolder=self.evaluate(self.dstPath)
    cardName=self.evaluate(self.cardName)
    mode=int(self.mode)
    size=int(self.cardSize)
    copier=Cp2CardCopier(self,None)
    self.progressUpdated(0) 
    inputList=copier.getInputList()
    sz=len(inputList)

    while res and sz>0:
        root,cards=copier.getNextCardFolderAvailable(dstFolder,cardName,size,mode!=Cp2CardCopier.MODE_TRACE_ONLY)
        self.info("joinP8contents:process:root","creating p2 tree "+root)
        res,inputList,processedList=copier.transfer(inputList,cards) 
        for x in processedList:
            if self.isCancelled():
                return False
            fp=x.getFilePath() 
            pos=fp.rfind("/exP2-")
            if pos<0:
                pos=fp.rfind("/mP2/")           
            if pos>=0:
                fp=root+fp[pos:]
            newUP=CuniversalPath(x)
            newUP.setFilePath(fp)
            out.addUniversalPath(newUP)
        newsz=len(inputList)
        if newsz==sz:
            res=self.critical("joinP8contents:process:end","Unable to copy more files") and res
        else:
            sz=newsz
    return res