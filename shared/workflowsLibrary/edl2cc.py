from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CnameConvention,CuniversalPath
from mistikaTools import installModule
import os
try:
    from xml.dom import minidom
    import re
except:
    installModule("xml.dom")
    installModule("re")



def init(self):
    self.setClassName("EDL To CC")
    self.addConnector("edl",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("cc",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addProperty("ccPath")
    self.setDropToProperty("ccPath")
    self.setDropSupportedTypes(1)
    self.addProperty("LOC", "Any")
    self.addProperty("ShotNaming",0)
    # self.addProperty("suffix","_cdl")
    self.setAcceptConnectors(True,"edl")
    self.bypassSupported=True
    self.color=QColor(0,180,180)
    return True

def isReady(self):
    res=True
    if self.bypassSupported and self.bypassEnabled:
        return res
    if not self.ccPath:
        res=self.critical("edl2cc2csv:ccPath:notFound","Destination Path can not be empty") and res
    return res

def process(self):

    def GenerateCC (outputFileCC,VFXName,eventDescription,SOPValues,SATValue):

        document = minidom.Document()

        CCid = document.createElement('ColorCorrection')
        CCid.setAttribute ('id',VFXName[0])

        Description = document.createElement('Description')
        DescriptionText = document.createTextNode(eventDescription)
        CCid.appendChild (Description)
        Description.appendChild (DescriptionText)

        SOPNode = document.createElement('SOPNode')
        CCid.appendChild (SOPNode)
        Slope = document.createElement('Slope')
        SlopeValue = document.createTextNode(SOPValues[0])
        Offset = document.createElement('Offset')
        OffsetValue = document.createTextNode(SOPValues[1])
        Power = document.createElement('Power')
        PowerValue = document.createTextNode(SOPValues[2])

        SOPNode.appendChild(Slope)
        Slope.appendChild(SlopeValue)
        SOPNode.appendChild(Offset)
        Offset.appendChild(OffsetValue)
        SOPNode.appendChild(Power)
        Power.appendChild(PowerValue)

        SATNode = document.createElement('SATNode')
        CCid.appendChild (SATNode)
        Saturation = document.createElement('Saturation')
        SaturationValue = document.createTextNode(SATValue[0])
        SATNode.appendChild(Saturation)
        Saturation.appendChild(SaturationValue)

        document.appendChild(CCid)
        xmlStr = document.toprettyxml(indent ="\t",encoding='UTF-8')

        with open (outputFileCC, 'wb') as f:
            f.write(xmlStr)

        return outputFileCC



    def checkRegEx(locs,vfxRegex):
        for loc in locs:
            vfxn = re.fullmatch(vfxRegex, loc)
            if vfxn:
                return vfxn
        self.warning("edl2cc:getVFXName:RegEx", vfxRegex + '\tDoes Not Match any ShotNaming in markers '+str(locs))
        return

    def getLOCindex(UserLoc,locs):
        for i, loc in enumerate(locs):
            if UserLoc == loc:
                return i
        self.warning("edl2cc:getLOCindex:locs", UserLoc + '\tCouldn\'t be found in ' + str(locs))
        return
    def getLOCindexMarkers(locs):
        for i, loc in enumerate(locs):
            if loc in MistikaMarkers:
                return i
        self.warning("edl2cc:getLOCindexMarkers:locs", str(locs) + '\tCouldn\'t be found in ' + str(MistikaMarkers))
        return

    def getVFXName(line,UserLoc,vfxRegex,VFXName):
        line=line.strip()
        locs = line.split()
        StringRules=["Any","FromClipName","TapeName"]
        illegalChars='\/:*?"<>|'
        vfxn = ""

        if ((UserLoc in locs or UserLoc in StringRules) and vfxRegex != ""):
            vfxn = checkRegEx(locs, vfxRegex)
            if vfxn:
                vfxn=vfxn[0]

        elif UserLoc in locs:
            i=getLOCindex(UserLoc,locs)
            try:
                vfxn=locs[i+1]
            except:
                vfxn=locs[i]
                self.warning("edl2cc:getVFXName:locs",str(locs) + '   Has not anything after\t' + str(UserLoc))

        elif UserLoc in StringRules:
            if UserLoc == StringRules[0]:
                i = getLOCindexMarkers(locs)
                try:
                    vfxn=locs[i+1]
                except:
                    vfxn = locs[i]
                    self.warning("edl2cc:getVFXName:locs", str(locs) + '   Has not anything after\t' + str(UserLoc))
            elif UserLoc == StringRules[1]:
                locs=line.split(':')
                vfxn = locs[1]
            elif UserLoc==StringRules[2]:
                vfxn = locs[1]
        else:
            vfxn = locs[3]
            self.warning("edl2cc:getVFXName:RegEx", vfxn + '\tNo ShotNaming neither LOC matched, getting default... GoodLuck... ')

        vfxn=vfxn.strip()
        for i in illegalChars:
            if i in vfxn:
                self.warning("edl2cc:getVFXName:illegalChars", vfxn + '\tContains illegal characters \ /:*?"<>| -> Replacing by \"-"')
                vfxn = vfxn.replace(i, "-")

        # print(VFXName)
        VFXName.append(vfxn)
        return VFXName




    def processEDL (up,dstPathCC):
        ccFiles=[]
        files=up.getFiles()
        metadata = up.getMetadata()
        print(metadata)
        if not files:
            self.addFailedUP(up)
            self.critical("edl2cc:processEDL:notEDL","Unable to interpret input UP {}".format(up.getFilePath()))
            return [False,None,None]
        filename=files[0]
        self.info("edl2cc:processEDL:edlName","processing {}".format(filename))
        if filename.endswith('.edl'):
            VFXName = []
            SOPValues = []
            SATValue = []
            try:
                with open (filename) as f:
                    for line in f:
                        if line.startswith('0'):                            
                            if VFXName and not SOPValues:
                                self.info("edl2cc:processEDL:edlName", VFXName[0] +'\tNOT FOUND SOP/SAT Values in edlEvent: '+edlEvent+':'+IDValue)
                            VFXName = []
                            SOPValues = []
                            SATValue = []
                            eventDescription=line.strip(' \n')
                            IDValue = line.split()[1]
                            edlEvent = line.split()[0]
                            # srcTCin= line.split()[4]
                            # srcTCout= line.split()[5]
                            # recTCin= line.split()[6]
                            # recTCout= line.split()[7]
                            if UserLoc == "TapeName":
                                getVFXName(line, UserLoc, vfxRegex, VFXName)

                        elif (line.__contains__('FROM CLIP NAME') and UserLoc=="FromClipName"):
                            getVFXName(line, UserLoc, vfxRegex, VFXName)
                        elif (line.startswith('*LOC:') or line.startswith('* LOC')) and UserLoc != "TapeName" and UserLoc != "FromClipName":
                            getVFXName(line, UserLoc, vfxRegex, VFXName)

                        elif line.startswith('*ASC_SOP') or line.startswith('* ASC_SOP'):
                            params=line.split(')(')
                            Slope=(params[0].split('('))[1]
                            Offset=params[1]
                            Power=(params[2].replace(')','')).strip(' \n')
                            SOPValues.append(Slope)
                            SOPValues.append(Offset)
                            SOPValues.append(Power)

                        elif line.startswith('*ASC_SAT') or line.startswith ('* ASC_SAT'):
                            n=len(line.split())
                            SATValue.append(line.split()[n-1])

                        else:
                            continue

                        if IDValue and VFXName and SOPValues and SATValue:
                            outputFileCC = dstPathCC + VFXName[0] +'_cdl.cc'
                            outputFiles = GenerateCC(outputFileCC,VFXName,eventDescription,SOPValues,SATValue)
                            ccFiles.append(outputFiles)

                    if VFXName and not SOPValues:
                        self.info("edl2cc:processEDL:edlName", VFXName[0] +'\tNOT FOUND SOP/SAT Values in edlEvent: '+edlEvent+':'+IDValue)
                    f.close()

            except OSError:
                self.addFailedUP(up)
                self.critical("edl2cc:processEDL:notFound","Unable to Open File {}".format(filename))
                return [False,None,None]

        # print (ccFiles)
        return [True,ccFiles]

    res=True
    if self.bypassEnabled:
        #this node leaves the outputs empty during bypass as the files are not generated
        return True

    # vfxRegex1=r'[a-zA-Z0-9]+_+[a-zA-Z0-9]+_+[a-zA-Z0-9]+_?+[a-zA-Z0-9]+_?+[a-zA-Z0-9]+'
    # vfxRegex2="([a-zA-Z0-9]+[_]){2,7}[a-zA-Z0-9]+"
    # vfxRegex check at https: // regex101.com /

    ShotNaming=int(self.ShotNaming)
    if ShotNaming == 0:
        vfxRegex=""
    elif ShotNaming == 1:
        vfxRegex = "([a-zA-Z0-9]+[_]){2}[a-zA-Z0-9]+"                           #showID_episode_shotID
    elif ShotNaming == 2:
        vfxRegex = "([a-zA-Z0-9]+[_]){2,7}[a-zA-Z0-9]+"                         #showID_episode_shotID_[UptoALL]
    elif ShotNaming == 3:
        vfxRegex = "([a-zA-Z0-9]+[_]){3}[a-zA-Z0-9]+"                           #showID_episode_seq_shotID
    elif ShotNaming == 4:
        vfxRegex = "([a-zA-Z0-9]+[_]){3,7}[a-zA-Z0-9]+"                         #showID_episode_seq_shotID_[UptoALL]
    elif ShotNaming == 5:
        vfxRegex = "([a-zA-Z0-9]+[_]){4}[a-zA-Z0-9]+"                           #showID_episode_seq_scene_shotID
    elif ShotNaming == 6:
        vfxRegex = "([a-zA-Z0-9]+[_]){5}[a-zA-Z0-9]+"                           #showID_episode_seq_scene_shotID_task
    elif ShotNaming == 7:
        vfxRegex = "([a-zA-Z0-9]+[_]){6}[a-zA-Z0-9]+"                           #showID_episode_seq_scene_shotID_task_vendor
    elif ShotNaming == 8:
        vfxRegex = "([a-zA-Z0-9]+[_]){7}[a-zA-Z0-9]+"                           #showID_episode_seq_scene_shotID_task_vendorID_version

    MistikaMarkers=['RED','GREEN','BLUE','CYAN','MAGENTA','YELLOW','BLACK','WHITE','PINK','ORANGE','TURQUOISE','PURPLE']

    nc=CnameConvention(self.getNameConvention())
    if not nc.toString():
        nc=self.getWorkflow().getNameConvention()

    outConCC=self.getFirstConnectorByName("cc")
    outConCC.clearUniversalPaths()
    UserLoc = self.evaluate(self.LOC)
    input=self.getFirstConnectorByName("edl")
    dstPath=self.evaluate(self.ccPath).strip()
    list=input.getUniversalPaths()

    for up in list:
        if self.isCancelled():
            return False

        dstPathCC=up.getStringOverride(dstPath)
        if not os.path.exists(dstPathCC):
            os.makedirs(dstPathCC)

        [r,CCs]=processEDL(up,dstPathCC)
        res=res and r
        if res:
            if CCs:
                for c in CCs:
                    outUP=CuniversalPath(nc,c)
                    outUP.setMediaFileInfoData(up.getMediaFileInfoData())
                    outConCC.addUniversalPath(outUP)

    return res
