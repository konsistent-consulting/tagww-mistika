#v 0.9 msgIfRemaining property and final report added 
#v 0.8 P8 classes extracted to lib/panasonic8K
#v 0.7 bug fixed changing the cardset
#v 0.6 multiple bugs fixed
#v 0.5 non auto mode removed. now it works in auto only
#v 0.4 auto mode revamped
#v 0.3 auto added to automatically detect p2 devices. their size and initial space
#v 0.2 tesst only mode added
#      repeated names check added
#v 0.1 initial draft


from Mistika.Qt import QColor
from Mistika.classes import Cconnector
from Mistika.classes import CuniversalPath

import panasonic8K
from panasonic8K import Cp2Card,Cp2CardsCache,Cp2CardCopier
    
def init(self):
    self.setClassName("Copy To 8KP2 Cards")    
    self.color=QColor(0x677688)
    self.addProperty("mode",Cp2CardCopier.MODE_COPY) #0=move, 1=copy
    self.addProperty("bufferSize",16) #in Mb
    self.addProperty("errorIfRemaining",0) #0=None, 1=Info, 2=Warning, 3=Critical
    for index in panasonic8K._QUADRANT_PROPERTIES:
        self.addProperty(panasonic8K._QUADRANT_PROPERTIES[index])  
    self.addConnector("p8",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True,"p8")
    self.bypassSupported=True
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res=True
    #fixer=self.getRegisteredItem(panasonic8K._FIX_NODE_NAME)
    #if not fixer:
    #    res=self.critical("copyP2Card:isReady:p2Serial",u"{} not registered, This node works in OSX only".format(panasonic8K._FIX_NODE_NAME)) and res       
    if self.isProcessing():
        return True
    cache=panasonic8K.packP2LoadCache(self)    
    copier=Cp2CardCopier(self,cache)
    res=copier.checkCardsSpace() and res
    return res

def process(self):
    if self.bypassEnabled:
        return True
    res=True    
    mode=int(self.mode)
    bs=int(self.bufferSize)
    if bs<=0:
        bs=16
    errorIfRemaining=int(self.errorIfRemaining)
    cache=panasonic8K.packP2LoadCache(self)    
    copier=Cp2CardCopier(self,cache)
    self.progressUpdated(0) 
    inputList=copier.getInputList()
    if inputList:
        if mode!=copier.MODE_MOVE:
            res=copier.checkCardsSpace(inputList) and res
        if res:
            r,remaining,processed=copier.transfer(inputList,bufferSize=bs*1024*1024)
            res=r and res
            if len(processed)==0:
                res=self.info("copyP2Card:process:noProcessed","No file copied. Please check available space") and res
            else:
                for p in processed:            
                    res=self.info("copyP2Card:process:processed","{} successfully copied".format(p.getFileName())) and res
            if errorIfRemaining>0 and len(remaining)>0:
                if errorIfRemaining==1:
                    res=self.info("copyP2Card:process:remaining","Error: Not enough space for all the contents") and res
                elif errorIfRemaining==2:
                    res=self.warning("copyP2Card:process:remaining","Error: Not enough space for all the contents") and res
                elif errorIfRemaining==3:
                    res=self.critical("copyP2Card:process:remaining","Error: Not enough space for all the contents") and res  
    return res
