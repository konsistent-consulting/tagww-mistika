from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CnameConvention,CuniversalPath
from mistikaTools import installModule
import os
import sys

try:
    import re
except:
    installModule("re")


def init(self):
    self.setClassName("EDL To Markers")
    self.addConnector("edl",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("edlMarkers",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addProperty("edlMarkersPath")
    self.setDropToProperty("edlMarkersPath")
    self.setDropSupportedTypes(1)
    self.addProperty("LOC", "Any")
    self.addProperty("ShotNaming",0)
    self.addProperty("Mistika", True)
    self.addProperty("DaVinciResolve", False)
    self.addProperty("MarkersColorMTK",3)
    self.addProperty("MarkersColorDVR", 1)
    # self.addProperty("suffix","_edlMarkers")
    self.setAcceptConnectors(True,"edl")
    self.bypassSupported=True
    self.color=QColor(0,90,90)
    return True

def isReady(self):
    res=True
    if self.bypassSupported and self.bypassEnabled:
        return res
    if not self.edlMarkersPath:
        res=self.critical("edl2Markers:edlMarkersPath:notFound","Destination Path can not be empty") and res
    return res

def process(self):

    def checkRegEx(locs,vfxRegex):
        for loc in locs:
            vfxn = re.fullmatch(vfxRegex, loc)
            if vfxn:
                return vfxn
        self.warning("edl2Markers:getVFXName:RegEx", vfxRegex + '\tDoes Not Match any ShotNaming in markers '+str(locs))
        return

    def getLOCindex(UserLoc,locs):
        for i, loc in enumerate(locs):
            if UserLoc == loc:
                return i
        self.warning("edl2Markers:getLOCindex:locs", UserLoc + '\tCouldn\'t be found in ' + str(locs))
        return

    def getLOCindexMarkers(locs):
        for i, loc in enumerate(locs):
            if loc in MistikaMarkers:
                return i
        self.warning("edl2Markers:getLOCindexMarkers:locs", str(locs) + '\tCouldn\'t be found in ' + str(MistikaMarkers))
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
            i = getLOCindex(UserLoc, locs)
            try:
                vfxn=locs[i+1]
            except:
                vfxn=locs[i]
                self.warning("edl2Markers:getVFXName:locs",str(locs) + '   Has not anything after\t' + str(UserLoc))

        elif UserLoc in StringRules:
            if UserLoc == StringRules[0]:
                i = getLOCindexMarkers(locs)
                try:
                    vfxn=locs[i+1]
                except:
                    vfxn = locs[i]
                    self.warning("edl2Markers:getVFXName:locs", str(locs) + '   Has not anything after\t' + str(UserLoc))
            elif UserLoc == StringRules[1]:
                locs=line.split(':')
                vfxn = locs[1]
            elif UserLoc==StringRules[2]:
                vfxn = locs[1]
        else:
            vfxn = locs[3]
            self.warning("edl2Markers:getVFXName:RegEx", vfxn + '\tNo ShotNaming neither LOC matched, getting default ')

        vfxn=vfxn.strip()
        for i in illegalChars:
            if i in vfxn:
                self.warning("edl2cc:getVFXName:illegalChars", vfxn + '\tContains illegal characters \ /:*?"<>| -> Replacing by \"-"')
                vfxn = vfxn.replace(i, "-")

        VFXName.append(vfxn)
        # print(VFXName)
        return VFXName


    def processEDL (up,dstPath):
        files=up.getFiles()
        if not files:
            self.addFailedUP(up)
            self.critical("edl2Markers:processEDL:notEDL","Unable to interpret input UP {}".format(up.getFilePath()))
            return [False,None,None]
        filename=files[0]
        dstFilesDVR = []
        dstFilesMTK = []

        self.info("edl2Markers:processEDL:edlName","processing {}".format(filename))
        if filename.endswith('.edl'):
            VFXName = []
            VFXNameLine=[]
            edlMarkers = []
            edlMarkersLine = []
            try:
                with open (filename) as f:
                    for line in f:
                        if line.startswith('0'):  ## Weak Condition to find tapename ID (000001  A099C003_220223NE) => should look for int()
                            VFXName = []
                            eventDescription = line.strip(' \n')
                            IDValue = line.split()[1]
                            edlEvent = line.split()[0]
                            srcTCin = line.split()[4]
                            srcTCout = line.split()[5]
                            recTCin = line.split()[6]
                            recTCout = line.split()[7]

                            if UserLoc == "TapeName":
                                getVFXName(line, UserLoc, vfxRegex, VFXName)
                                VFXNameLine.append(edlEvent + ';' + VFXName[0] + ';' + srcTCin + ';' + srcTCout + ';' + recTCin + ';' + recTCout)

                        elif (line.__contains__('FROM CLIP NAME') and UserLoc=="FromClipName"):
                            getVFXName(line, UserLoc, vfxRegex, VFXName)
                            VFXNameLine.append(edlEvent + ';' + VFXName[0] + ';' + srcTCin + ';' + srcTCout + ';' + recTCin + ';' + recTCout)
                            print(VFXNameLine)

                        elif (line.startswith('*LOC:') or line.startswith('* LOC:')) and UserLoc != "TapeName" and UserLoc != "FromClipName":
                            getVFXName(line, UserLoc, vfxRegex, VFXName)
                            VFXNameLine.append(edlEvent + ';' + VFXName[0] + ';' + srcTCin + ';' + srcTCout + ';' + recTCin + ';' + recTCout)

                        else:
                            continue
                    # print(VFXNameLine)
                    if VFXNameLine:
                        for l in VFXNameLine:
                            edlMarkers.append(l)
                f.close()

                [edlMarkersLine.append(x) for x in edlMarkers if x not in edlMarkersLine]  ## REMOVE DUPLICATES IN LIST
                # print(edlMarkersLine)
                dstFileDVR = dstPath + os.path.basename(filename)[:-4] + '_edlMarkersDVR.edl'
                if os.path.isfile(dstFileDVR) and self.DaVinciResolve:
                    os.remove(dstFileDVR)
                dstFileMTK = dstPath + os.path.basename(filename)[:-4] + '_edlMarkersMTK.edl'
                if os.path.isfile(dstFileMTK) and self.Mistika:
                    os.remove(dstFileMTK)

                for i in edlMarkersLine:
                    edlEvent = i.split(';')[0]
                    VFXName = i.split(';')[1]
                    srcTCin = i.split(';')[2]
                    srcTCout = i.split(';')[3]
                    recTCin = i.split(';')[4]
                    recTCout = i.split(';')[5]

                    if self.DaVinciResolve:
                        lineDVR = (edlEvent + '  ' + VFXName + '  V  C  ' + srcTCin + ' ' + srcTCout + ' ' + recTCin + ' ' + recTCout + ' ' + '\n'
                                   + ' ' + DaVinciMarkers[ColorsIndexDVR] + ' |M:' + VFXName + ' |D:1\n')
                        with open(dstFileDVR, 'a') as f:
                            f.writelines('\n' + lineDVR)
                        f.close()
                        print(lineDVR)
                    if self.Mistika:
                        lineMTK = (edlEvent + '  ' + VFXName + '  V  C  ' + srcTCin + ' ' + srcTCout + ' ' + recTCin + ' ' + recTCout + ' ' + '\n'
                                   + '*LOC:  ' + recTCin + ' ' + MistikaMarkers[ColorsIndexMTK] + '  ' + VFXName + '\n')
                        with open(dstFileMTK, 'a') as f:
                            f.writelines('\n' + lineMTK)
                        f.close()
                        print(lineMTK)

                if self.DaVinciResolve:
                    dstFilesDVR.append(dstFileDVR)
                if self.Mistika:
                    dstFilesMTK.append(dstFileMTK)

            except OSError:
                self.addFailedUP(up)
                self.critical("edl2Markers:processEDL:notFound","Unable to Open File {}".format(filename))
                return [False,None,None]

        # print(dstFiles)
        return [True,dstFilesDVR,dstFilesMTK]

    res=True


    if self.bypassEnabled:
        #this node leaves the outputs empty during bypass as the files are not generated
        return True

    # vfxRegex check at https: // regex101.com /
    ShotNaming = int(self.ShotNaming)
    if ShotNaming == 0:
        vfxRegex = ""
    elif ShotNaming == 1:
        vfxRegex = "([a-zA-Z0-9]+[_]){2}[a-zA-Z0-9]+"  # showID_episode_shotID
    elif ShotNaming == 2:
        vfxRegex = "([a-zA-Z0-9]+[_]){2,7}[a-zA-Z0-9]+"  # showID_episode_shotID_[UptoALL]
    elif ShotNaming == 3:
        vfxRegex = "([a-zA-Z0-9]+[_]){3}[a-zA-Z0-9]+"  # showID_episode_seq_shotID
    elif ShotNaming == 4:
        vfxRegex = "([a-zA-Z0-9]+[_]){3,7}[a-zA-Z0-9]+"  # showID_episode_seq_shotID_[UptoALL]
    elif ShotNaming == 5:
        vfxRegex = "([a-zA-Z0-9]+[_]){4}[a-zA-Z0-9]+"  # showID_episode_seq_scene_shotID
    elif ShotNaming == 6:
        vfxRegex = "([a-zA-Z0-9]+[_]){5}[a-zA-Z0-9]+"  # showID_episode_seq_scene_shotID_task
    elif ShotNaming == 7:
        vfxRegex = "([a-zA-Z0-9]+[_]){6}[a-zA-Z0-9]+"  # showID_episode_seq_scene_shotID_task_vendor
    elif ShotNaming == 8:
        vfxRegex = "([a-zA-Z0-9]+[_]){7}[a-zA-Z0-9]+"  # showID_episode_seq_scene_shotID_task_vendorID_version

    ColorsIndexDVR=int(self.MarkersColorDVR)
    DaVinciMarkers = ['|C:ResolveColorBlue', '|C:ResolveColorCyan', '|C:ResolveColorGreen', '|C:ResolveColorYellow', '|C:ResolveColorRed','|C:ResolveColorPink','|C:ResolveColorPurple','|C:ResolveColorFuchsia',
                      '|C:ResolveColorRose','|C:ResolveColorLavender','|C:ResolveColorSky','|C:ResolveColorMint','|C:ResolveColorLemon','|C:ResolveColorSand','|C:ResolveColorCocoa','|C:ResolveColorCream']
    ColorsIndexMTK=int(self.MarkersColorMTK)
    MistikaMarkers=['RED','GREEN','BLUE','CYAN','MAGENTA','YELLOW','BLACK','WHITE','PINK','ORANGE','TURQUOISE','PURPLE']

    if not self.DaVinciResolve and not self.Mistika:
        res = self.critical("edl2Markers:edlMarkersFormat:No format selected", "At least one edl format is required") and res

    UserLoc = self.evaluate(self.LOC)
    outConEDLMarkers=self.getFirstConnectorByName("edlMarkers")
    outConEDLMarkers.clearUniversalPaths()
    input=self.getFirstConnectorByName("edl")
    dstPath=self.evaluate(self.edlMarkersPath).strip()
    list=input.getUniversalPaths()

    nc=CnameConvention(self.getNameConvention())
    if not nc.toString():
        nc=self.getWorkflow().getNameConvention()

    for up in list:
        if self.isCancelled():
            return False

        dstPathEDL=up.getStringOverride(dstPath)
        if not os.path.exists(dstPathEDL):
            os.makedirs(dstPathEDL)

        [r,dstFilesDVR,dstFilesMTK]=processEDL(up,dstPathEDL)
        res=res and r
        if res:
            if dstFilesDVR:
                for c in dstFilesDVR:
                    outUP = CuniversalPath(nc, c)
                    outConEDLMarkers.addUniversalPath(outUP)
            if dstFilesMTK:
                for d in dstFilesMTK:
                    outUP = CuniversalPath(nc, d)
                    outConEDLMarkers.addUniversalPath(outUP)

    return res
