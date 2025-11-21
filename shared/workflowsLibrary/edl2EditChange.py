from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CnameConvention,CuniversalPath
from mistikaTools import installModule
import os
import sys
from timecode import Timecode



def init(self):
    self.setClassName("EDL Edit Changes")
    self.addConnector("edlBefore",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_REQUIRED)
    self.addConnector("edlAfter", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_REQUIRED)
    self.addConnector("edlMarkers",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addProperty("edlMarkersPath")
    self.setDropToProperty("edlMarkersPath")
    self.setDropSupportedTypes(1)
    self.addProperty("Mistika", True)
    self.addProperty("DaVinciResolve", False)
    self.addProperty("FrameRate", "25")
    self.addProperty("EditChangesMTK",5)
    self.addProperty("NewVFXMTK", 0)
    self.addProperty("EditChangesDVR", 3)
    self.addProperty("NewVFXDVR", 4)


    self.setAcceptConnectors(False,"edlBefore")
    self.setAcceptConnectors(False, "edlAfter")
    self.bypassSupported=True
    self.color=QColor(0,45,45)
    return True

def isReady(self):
    res=True
    if self.bypassSupported and self.bypassEnabled:
        return res
    if not self.edlMarkersPath:
        res=self.critical("edl2EditChange:edlMarkersPath:notFound","Destination Path can not be empty") and res
    return res

def process(self):

    def getEvents(up):
        edlEvents=[]
        files=up.getFiles()
        if not files:
            self.addFailedUP(up)
            self.critical("edl2EditChange:getEvents:notEDL", "Unable to interpret input UP {}".format(up.getFilePath()))
            return False
        filename=files[0]
        if filename.endswith('.edl'):
            try:
                with open(filename) as f:
                    for line in f:
                        try:
                            eventNumber = int(line.split()[0])
                            isEvent = isinstance(eventNumber, int)
                        except:
                            continue
                        if isEvent:
                            line = line.strip()
                            edlEvents.append(line)
                    f.close()
            except:
                self.addFailedUP(up)
                self.critical("edl2EditChange:getEvents:'.edl' file", ".edl file not found".format(up.getFilePath()))
                return False

        return edlEvents

    def rmEqualEvents(eventsBefore,eventsAfter):
        eventsIndex=[]
        eventsClean=eventsAfter
        for i, EventAfter in enumerate (eventsAfter):
            for j, EventBefore in enumerate (eventsBefore):
                if EventAfter == EventBefore:
                    eventsIndex.append(i)
                else:
                    continue
        for k in reversed(eventsIndex):
            eventsClean.pop(k)
        return eventsClean

    def tryDeltaZero(FrameRate,TCin,TCout):
        try:
            delta=Timecode(FrameRate,TCin).frames-Timecode(FrameRate,TCout).frames
        except:
            return 0
        else:
            return delta

    def tryDeltaZeroTC(FrameRate,TCin,TCout):
        try:
            TC=Timecode(FrameRate,TCin)-Timecode(FrameRate,TCout)
        except:
            return 0
        else:
            return TC

    def processEDL (up1,up2,dstPathEDL):
        eventsBefore=[]
        eventsAfter=[]
        files = up2.getFiles()
        filename = files[0]
        dstFileDVR = dstPathEDL + os.path.basename(filename)[:-4] + '_EditChangesDVR.edl'
        if os.path.isfile(dstFileDVR) and self.DaVinciResolve:
            os.remove(dstFileDVR)
        dstFileMTK = dstPathEDL + os.path.basename(filename)[:-4] + '_EditChangesMTK.edl'
        if os.path.isfile(dstFileMTK) and self.Mistika:
            os.remove(dstFileMTK)
        dstFilesDVR = []
        dstFilesMTK = []
        eventsBefore=getEvents(up1)
        eventsAfter=getEvents(up2)
        eventsAfter=rmEqualEvents(eventsBefore,eventsAfter)
        eventsProcessed = []
        eventsIndex=[]
        try:
            for i, EventAfter in enumerate (eventsAfter):
                for j, EventBefore in enumerate (eventsBefore):
                    if EventAfter.split()[1] == EventBefore.split()[1]:
                        deltas=[]
                        deltasTC=[]
                        edlEvent=EventAfter.split()[0]
                        VFXName=EventAfter.split()[1]
                        srcTCinBefore=EventBefore.split()[4]
                        srcTCinAfter=EventAfter.split()[4]
                        srcTCoutBefore=EventBefore.split()[5]
                        srcTCoutAfter=EventAfter.split()[5]
                        recTCinBefore=EventBefore.split()[6]
                        recTCinAfter=EventAfter.split()[6]
                        recTCoutBefore=EventBefore.split()[7]
                        recTCoutAfter=EventAfter.split()[7]

                        deltaSrcTCin = tryDeltaZero(FrameRate,srcTCinAfter,srcTCinBefore)
                        deltaSrcTCout = tryDeltaZero(FrameRate,srcTCoutAfter,srcTCoutBefore)
                        deltaRecTCin = tryDeltaZero(FrameRate,recTCinAfter,recTCinBefore)
                        deltaRecTCout = tryDeltaZero(FrameRate,recTCoutAfter,recTCoutBefore)
                        deltas.extend([deltaSrcTCin,deltaSrcTCout,deltaRecTCin,deltaRecTCout])

                        deltaTCRecTCin=tryDeltaZeroTC(FrameRate,recTCinAfter,recTCinBefore)
                        deltaTCRecTCOut=tryDeltaZeroTC(FrameRate,recTCoutAfter,recTCoutBefore)
                        deltasTC.extend([deltaTCRecTCin,deltaTCRecTCOut])

                        eventsIndex.append(i)


                        if self.DaVinciResolve:
                            lineDVR = (edlEvent + '  ' + VFXName + '  V  C  ' + srcTCinAfter + ' ' + srcTCoutAfter + ' ' + recTCinAfter + ' ' + recTCoutAfter + ' ' + '\n'
                                    + 'Head Trim:' + str(deltas[0]) + ' frames' +' --- '
                                    + 'Tail Trim:' + str(deltas[1]) + ' frames' + '\n'
                                    + 'Rec TC In:' + str(deltas[2]) + ' frames (' + str(deltaTCRecTCin) +')\n'
                                    + 'Rec TC Out:' + str(deltas[3]) + ' frames (' + str(deltaTCRecTCOut) +')\n'
                                    + ' ' + DaVinciMarkers[EditColorsIndexDVR] + ' |M:' + VFXName + ' |D:1\n')
                            with open(dstFileDVR, 'a') as f:
                                f.writelines('\n' + lineDVR)
                            f.close()
                            print(lineDVR)

                        if self.Mistika:
                            lineMTK = (edlEvent + '  ' + VFXName + '  V  C  ' + srcTCinAfter + ' ' + srcTCoutAfter + ' ' + recTCinAfter + ' ' + recTCoutAfter + ' ' + '\n'
                                    + '*LOC: ' + recTCinAfter + '  ' + MistikaMarkers[EditColorsIndexMTK] + '  ' + VFXName
                                    + ' HeadTrim:' + str(deltas[0]) + ' frames'
                                    + ' TailTrim:' + str(deltas[1]) + ' frames'
                                    + ' RecTCIn:' + str(deltas[2]) + ' frames (' + str(deltaTCRecTCin) + ')'
                                    + ' RecTCOut:' + str(deltas[3]) + ' frames (' + str(deltaTCRecTCOut) + ')'
                                    + ' \n')

                            with open(dstFileMTK, 'a') as f:
                                f.writelines('\n' + lineMTK)
                            f.close()
                            print(lineMTK)

            eventsRemain=eventsAfter
            [eventsProcessed.append(x) for x in eventsIndex if x not in eventsProcessed]

            for k in reversed(eventsProcessed):
                eventsRemain.pop(k)

            for event in eventsRemain:
                edlEvent = EventAfter.split()[0]
                VFXName = EventAfter.split()[1]
                srcTCinAfter = EventAfter.split()[4]
                srcTCoutAfter = EventAfter.split()[5]
                recTCinAfter = EventAfter.split()[6]
                recTCoutAfter = EventAfter.split()[7]

                if self.DaVinciResolve:
                    lineDVR = (edlEvent + '  ' + VFXName + '  V  C  ' + srcTCinAfter + ' ' + srcTCoutAfter + ' ' + recTCinAfter + ' ' + recTCoutAfter + ' ' + '\n'
                                + 'NEW VFX  ' + '\n'
                                + ' ' + DaVinciMarkers[NewVFXColorsIndexDVR] + ' |M:' + VFXName + ' |D:1\n')
                    with open(dstFileDVR, 'a') as f:
                        f.writelines('\n' + lineDVR)
                    f.close()
                    print(lineDVR)

                if self.Mistika:
                    lineMTK = (edlEvent + '  ' + VFXName + '  V  C  ' + srcTCinAfter + ' ' + srcTCoutAfter + ' ' + recTCinAfter + ' ' + recTCoutAfter + ' ' + '\n'
                                + '*LOC: ' + recTCinAfter + '  ' + MistikaMarkers[NewVFXColorsIndexMTK] + '  ' + VFXName
                                + '  NEW VFX  ' + ' \n')

                    with open(dstFileMTK, 'a') as f:
                        f.writelines('\n' + lineMTK)
                    f.close()
                    print(lineMTK)

            if self.DaVinciResolve:
                dstFilesDVR.append(dstFileDVR)
            if self.Mistika:
                dstFilesMTK.append(dstFileMTK)

        except OSError:
            self.addFailedUP(up2)
            self.critical("edl2EditChange:processEDL:notFound","Unable to process File {}".format(filename))
            return [False,None,None]

        return [True,dstFilesDVR,dstFilesMTK]

    res=True


    if self.bypassEnabled:
        #this node leaves the outputs empty during bypass as the files are not generated
        return True

    EditColorsIndexDVR=int(self.EditChangesDVR)
    NewVFXColorsIndexDVR=int(self.NewVFXDVR)
    DaVinciMarkers = ['|C:ResolveColorBlue', '|C:ResolveColorCyan', '|C:ResolveColorGreen', '|C:ResolveColorYellow', '|C:ResolveColorRed','|C:ResolveColorPink','|C:ResolveColorPurple','|C:ResolveColorFuchsia',
                      '|C:ResolveColorRose','|C:ResolveColorLavender','|C:ResolveColorSky','|C:ResolveColorMint','|C:ResolveColorLemon','|C:ResolveColorSand','|C:ResolveColorCocoa','|C:ResolveColorCream']
    EditColorsIndexMTK=int(self.EditChangesMTK)
    NewVFXColorsIndexMTK=int(self.NewVFXMTK)
    MistikaMarkers=['RED','GREEN','BLUE','CYAN','MAGENTA','YELLOW','BLACK','WHITE','PINK','ORANGE','TURQUOISE','PURPLE']

    outConEDLMarkers=self.getFirstConnectorByName("edlMarkers")
    outConEDLMarkers.clearUniversalPaths()
    input1=self.getFirstConnectorByName("edlBefore")
    input2=self.getFirstConnectorByName("edlAfter")
    FrameRate=float(self.FrameRate)

    if not self.DaVinciResolve and not self.Mistika:
        res = self.critical("edl2EditChange:edlMarkersFormat:No format selected", "At least one edl format is required") and res

    dstPath=self.evaluate(self.edlMarkersPath).strip()
    list1=input1.getUniversalPaths()
    if len(list1) > 1:
        res = self.critical("edl2EditChange:edlBeforeCut:TooManyFiles", "Only one edl file can be compared") and res
    list2=input2.getUniversalPaths()
    if len(list2) > 1:
        res = self.critical("edl2EditChange:edlAfterCut:TooManyFiles", "Only one edl file can be compared") and res

    nc=CnameConvention(self.getNameConvention())
    if not nc.toString():
        nc=self.getWorkflow().getNameConvention()

    for up1 in list1:
        if self.isCancelled():
            return False
        dstPathEDL=up1.getStringOverride(dstPath)
        if not os.path.exists(dstPathEDL):
            os.makedirs(dstPathEDL)

        for up2 in list2:
            [r,dstFilesDVR,dstFilesMTK]=processEDL(up1,up2,dstPathEDL)
            res=res and r
            if res:
                if dstFilesDVR:
                    for c in dstFilesDVR:
                        outUP=CuniversalPath(nc,c)
                        outConEDLMarkers.addUniversalPath(outUP)
                if dstFilesMTK:
                    for d in dstFilesMTK:
                        outUP=CuniversalPath(nc,d)
                        outConEDLMarkers.addUniversalPath(outUP)

    return res
