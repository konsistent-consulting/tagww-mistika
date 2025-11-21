from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CnameConvention,CuniversalPath
from mistikaTools import installModule
import os
try:
    import re
except:
    installModule("re")


def init(self):
    self.setClassName("VR Input Bunches")
    self.addConnector("files", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_REQUIRED)
    self.addProperty("InputCameras", 2)
    self.addProperty("MediaNaming",1)
    self.addProperty("useRelativePaths",False)

    nCamsLetterCases = [10, 11, 12, 14, 18]
    nCams=int(self.InputCameras)
    MediaNaming=int(self.MediaNaming)
    for i in range(1, nCams + 1):
        if MediaNaming in nCamsLetterCases:
            nCamsLetter = chr(i + 64)
            outCam = f'Cam{nCamsLetter}'
        else:
            outCam = f'Cam{str(i).zfill(2)}'
        self.addConnector(outCam, Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.bypassSupported=True
    self.color=QColor(0,180,180)
    return True

def isReady(self):
    res=True
    if self.bypassSupported and self.bypassEnabled:
        return res
    return res

def process(self):

    def matchRegEx(allFiles):
        CamsUPs = {}
        CamsNames = []
        for up in list:
            if self.isCancelled():
                return False
            file=up.getFilePath()
            baseName=up.getBaseName()
            if self.useRelativePaths:
                relpath = up.getRelPath()
                baseName=f'{relpath}{up.getBaseName()}'
            matchFile=re.fullmatch(MediaRegEx,file)
            if matchFile:
                CamsNames.append(baseName)
                CamsUPs[baseName] = up
            else:
                self.warning("VRInputbunches:matchRegEx","MediaNaming " + self.evaluate(MediaNaming) + '\tDoes Not Match with ' + file+'. Will be discarded')
            continue
        return CamsUPs, CamsNames

    def createVRBunches(CamsNames):
        sortedCamsNames = sorted(CamsNames)
        # print(CamsNames)
        # print(sortedCamsNames)
        if MediaNaming == 9:
            sortedCamsNames = sorted(CamsNames, key=lambda x: int(x.split('_')[0]))
        elif not self.useRelativePaths and MediaNaming == 17:
            # sortedCamsNames = sorted(CamsNames, key=lambda x: (int(x.split('GX')[0])))
            sortedCamsNames = CamsNames
        elif MediaNaming == 18:
            sortedCamsNames = sorted(CamsNames, key=lambda x:(x.split('_')[0][-5:], x[0]))
        # print(sortedCamsNames)
        n = int(len(sortedCamsNames))
        if n % nCams != 0:
            self.critical ("VRInputbunches:createVRBunches","VRBunch of "+ str(n) +' filtered cams is not multiple of '+self.InputCameras+' input cameras')
            return None
        VRBunches = [[] for _ in range(int(nCams))]
        for i in range(n):
            listIndex = i % nCams
            VRBunches[listIndex].append(sortedCamsNames[i])
        for i, sublist in enumerate(VRBunches):
            print(f"List {i + 1}: {sublist}")
        return VRBunches


    nCams=int(self.InputCameras)
    nCamsLetter=chr(int(nCams) + 64)
    nCamsLetterCases = [10, 11, 12, 14, 18]
    MediaNaming=int(self.MediaNaming)
    # # MediaRegEx check at https: // regex101.com /
    if MediaNaming == 0:
        MediaRegEx=""
    elif MediaNaming == 1:
        MediaRegEx = f'^.+/[A-Za-z0-9]+[0-{nCams}]+\\.[A-Za-z0-9]+$'                        # case01 blabla1.ext , blabla2.ext --->> includes case13 !!
    elif MediaNaming == 2:
        MediaRegEx = f'^.+/[cC][aA][mM]+[0-{nCams}]_[A-Za-z0-9]+\\.[A-Za-z0-9]+$'           # case02 CAM1_balblabla.ext, CAM2_blablabl.ext
    elif MediaNaming == 3:
        MediaRegEx = f'^.+/[cC][aA][mM]+\s+[0-{nCams}]+\\.[A-Za-z0-9]+$'                    #case03 CAM 1.ext, CAM 2.ext
    elif MediaNaming == 4:
        MediaRegEx= f'^.+/[A-Za-z0-9_]+_[cC][aA][mM]+[0-{nCams}]+\\.[A-Za-z0-9]+$'          #case04 blabla_CAM1.ext, blabla_CAM2.ext
    elif MediaNaming == 5:
        MediaRegEx = f'^.+/[A-Za-z0-9]+_[cC][aA][mM]+[0-{nCams}]+_[A-Za-z0-9]+_[A-Za-z0-9]+\\.[A-Za-z0-9]+$'    #case05 blabla_CAM1_blabla_blabla.ext, blabla_CAM2_blabla_blabla.ext
    elif MediaNaming == 6:
        MediaRegEx = f'^.+/[A-Za-z0-9]+_000[0-{nCams}]+_[A-Za-z0-9]+\\.[A-Za-z0-9]+$'       #case06 blabla_0000_blabal.ext, blabla_0001_blabla.ext
    elif MediaNaming == 7:
        MediaRegEx = f'^.+/[cC][aA][mM]+_[0-{nCams}]+\\.[A-Za-z0-9]+$'                      #case07 blablabla_CAM01.ext, blablbal_01.ext
    elif MediaNaming == 8:
        MediaRegEx = f'^.+/[0-9]+_[0-9]+_[0-9]+_[0-{nCams}]+\\.[A-Za-z0-9]+$'               #case08 0006_20171229_142940_01.MOV, 0006_20171229_142940_02.MOV
    elif MediaNaming == 9:
        MediaRegEx = f'^.+/({"|".join(str(i) for i in range(nCams+1))})+_[0-9]+\\.[A-Za-z0-9]+$'   #case09 1_1.ext, 2_1.ext
    elif MediaNaming == 10:
        MediaRegEx = f'^.+/[A-Za-z0-9_\s]+_[A-{nCamsLetter}]+\\.[A-Za-z0-9]+$'              #case10 blbalba_A.ext, blabla_B.ext, blabla_C.ext
    elif MediaNaming == 11:
        MediaRegEx = f'^.+/[A-{nCamsLetter}]+_[A-Za-z0-9_\s]+\\.[A-Za-z0-9]+$'              #case11 A_blalba.ext, B_blablabl.ext, C_blablabla.ext
    elif MediaNaming == 12:
        MediaRegEx = f'^.+/[0-9][a-{nCamsLetter.lower()}]+\\.[A-Za-z0-9]+$'                 #case12 4a.ext, 4b.ext, 4c.ext
    elif MediaNaming == 13:
        MediaRegEx = f'^.+/[A-Z0-9][A-Z0-9][A-Z0-9][0-{nCams}][0-9][0-9][0-9][0-9]\\.[A-Za-z0-9]+$'             #case13 A0019922.ext, A0029922.ext, A0039922.ext
    elif MediaNaming == 14:
        MediaRegEx = f'^.+/[0-9][0-9][0-9][0-9][A-{nCamsLetter}]\\.[A-Za-z0-9]+$'                      #case14 0001A.ext, 0001B.ext, 0001C.ext
    elif MediaNaming == 15:
        MediaRegEx = f'^.+/[A-Za-z0-9][A-Za-z0-9]+_[A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][0-{nCams+1}]\\.[A-Za-z0-9]+$'     # case15 3D_L4842.ext, 3D_L4843.ext, 3D_L4844.ext
    elif MediaNaming == 16:
        MediaRegEx = f'^.+/[A-Za-z_\s]+_[0-{nCams}]\\.[A-Za-z0-9]+$'                   #case16 Sample Video Motor_Origin_0.mp4, Sample Video Motor_Origin_1.mp4
    elif MediaNaming == 17:
        MediaRegEx = f'^.+/[0-{nCams}]GX0[0-9][0-9][0-9][0-9][0-9]\\.[A-Za-z0-9]+$'  # case17 -Trini - '1GX011195.mp4', '2GX010044.mp4', '3GX010001.mp4'
    elif MediaNaming == 18:
        MediaRegEx = f'^.+/[A-{nCamsLetter}]\d{{3}}C\d{{4}}_\d{{14}}_\d{{4}}\\.[A-Za-z0-9]+$'  # case18 -Meta3 - A001C0001_20250224143218_0001.MOV, B001C0001_20250224143218_0001.MOV
    elif MediaNaming == 19:
        MediaRegEx = f'^.+/c[0-{nCams+1}][A-Za-z]*_\d+\\.[A-Za-z0-9]+$'                 # case19 -2Freedom - c1_24238183_1740409219.jpg, c2i_24238180_1740409220.jpg
    elif MediaNaming == 20:
        MediaRegEx = f'^.+/\d{{4}}-\d{{2}}-\d{{2}}_cam+[0-{nCams - 1}]_frame\\.[A-Za-z0-9]+$'  # case20 -FieldGeo -- yyyy-mm-dd_cam0_framexxx.ext, yyyy-mm-dd_cam1_framexxx.ext


    res=True
    if self.bypassEnabled:
        return True

    nc=CnameConvention(self.getNameConvention())
    if not nc.toString():
        nc=self.getWorkflow().getNameConvention()

    input = self.getFirstConnectorByName("files")
    list = input.getUniversalPaths()

    for i in range (1,int(self.InputCameras)+1):
        if MediaNaming in nCamsLetterCases:
            nCamsLetter = chr(i + 64)
            outCam = f'Cam{nCamsLetter}'
        else:
            outCam = f'Cam{str(i).zfill(2)}'
        output = self.getFirstConnectorByName(outCam)
        output.clearUniversalPaths()
    CamsUPs,CamsNames=matchRegEx(list)
    VRBunches = createVRBunches(CamsNames)

    if VRBunches:
        VRUpBunches = [[CamsUPs.get(cam) for cam in bunch] for bunch in VRBunches]
        for i, bunch in enumerate(VRUpBunches):
            if MediaNaming in nCamsLetterCases:
                nCamsLetter = chr(i+1 + 64)
                outCam = f'Cam{nCamsLetter}'
            else:
                outCam = f'Cam{str(i+1).zfill(2)}'
            output = self.getFirstConnectorByName(outCam)
            output.addUniversalPaths(bunch)
        return res
    else:
        return False


def onPropertyUpdated(self, name):
    if name == "InputCameras" or name == "MediaNaming":
        try:
            self.rebuild()
        except Exception:
            pass
