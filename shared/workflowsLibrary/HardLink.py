import os
import platform
from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CnameConvention,CuniversalPath



def init(self):
    self.setClassName("Hard Link")
    self.addConnector("Files",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_REQUIRED)
    self.addConnector("Links",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addProperty("dstPath")
    self.setDropToProperty("dstPath")
    self.setDropSupportedTypes(1)
    self.bypassSupported=True
    self.setAcceptConnectors(False, "input")
    self.color = QColor(0, 180, 180)
    return True


def isReady(self):
    res=True
    OS = platform.system()
    if OS == "Darwin":
        res = self.critical("HardLink:OS:macOS","python os.link is only available for Unix and Windows platforms: https://docs.python.org/3/library/os.html#os.link") and res
    if self.bypassSupported and self.bypassEnabled:
        return res
    if not self.dstPath:
        res=self.critical("makeLinks:dstPath:notFound","Destination Path can not be empty") and res
    return res


def process(self):

    def makeLink(up,dstPathLnk):
        srcBasePath=up.getBasePath()
        srcBaseName=up.getBaseName()
        srcFileName=up.getFileName()
        isSeq = CuniversalPath().isSequenceByExtension(srcFileName)
        LnkPaths=[]
        if isSeq:
            dst = f'{dstPathLnk}{srcBaseName}'
            if not os.path.exists(dst):
                os.makedirs(dst)
            for dirpath, dirs, files in os.walk(srcBasePath):
                LnkPath=f'{dst}/{files[0]}'
                for file in files:
                    src=f'{srcBasePath}{file}'
                    Lnk=f'{dst}/{file}'
                    try:
                        os.link(src, Lnk)
                    except:
                        self.warning("HardLink:isSeq:", Lnk + ' already exists')
                        continue
            LnkPaths.append(LnkPath)
        else:
            src= f'{srcBasePath}{srcFileName}'
            LnkPath = f'{dstPathLnk}{srcFileName}'
            try:
                os.link(src,LnkPath)
            except:
                self.warning("HardLink:isMovie:", LnkPath + ' already exists')
            LnkPaths.append(LnkPath)

        return [True,LnkPaths]


    res=True
    if self.bypassEnabled:
        #this node leaves the outputs empty during bypass as the files are not generated
        return True

    input=self.getFirstConnectorByName("Files")
    dstPath = self.evaluate(self.dstPath).strip()
    list=input.getUniversalPaths()
    output=self.getFirstConnectorByName("Links")
    output.clearUniversalPaths()

    nc=CnameConvention(self.getNameConvention())
    if not nc.toString():
        nc=self.getWorkflow().getNameConvention()


    for up in list:
        if self.isCancelled():
            return False
        dstPathLnk = up.getStringOverride(dstPath)
        if not os.path.exists(dstPathLnk):
            os.makedirs(dstPathLnk)

        [r,UPlnk]=makeLink(up,dstPathLnk)
        res=res and r
        if res:
            if UPlnk:
                for lnk in UPlnk:
                    outUP=CuniversalPath(nc)
                    outUP.autoFromName(lnk)
                    output.addUniversalPath(outUP)

    return res


