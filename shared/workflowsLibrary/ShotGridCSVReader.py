
import Mistika
import csv
import sys
import os
from datetime import date,datetime,timedelta
from Mistika.classes import Cconnector
from Mistika.classes import CuniversalPath
from Mistika.classes import CnameConvention
from Mistika.Qt import QColor
from token2mdata import token2mdataMapper
try:
    import re
except:
    installModule("re")

def init(self):
    self.setClassName("ShotGrid CSV Reader")
    self.addConnector("SGcsv",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("MaxVersion",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True, "SGcsv")
    self.addProperty("SearchPath")
    self.setDropToProperty("SearchPath")
    self.setDropSupportedTypes(1)
    self.addProperty("ShotNaming",2)
    self.addProperty("CSVShotTokens")
    self.addProperty("Status", "apr")
    self.addProperty("SinceDays",0)
    # self.addProperty("delimiter",",")
    self.color=QColor(0x94b4f2)
    self.bypassSupported=True
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res=True
    # if self.delimiter=="":
    #     res=self.critical("ShotGridCSVReader:delimiter","'Delimiter can not be empty")
    return res

def process(self):

    def maxVersion(SearchPath):
        dirs=[]
        for dirpath, dirnames, files in os.walk(SearchPath):
            dirs.append(dirpath)
        maxVersionFolder = max(dirs)
        maxVersionFiles=os.listdir(maxVersionFolder)
        maxVFF = f'{maxVersionFolder}/{(maxVersionFiles[0])}'
        # print (maxVFF)
        return maxVFF


    def checkRegEx(vfxRegex,ShotCode):
        vfxn = re.fullmatch(vfxRegex,ShotCode)
        if vfxn:
            return True
        else:
            self.warning("ShotGridCSVReader:checkRegEx:RegEx", ShotCode + '\tDoes Not Match Regex '+vfxRegex)
            return False

    def isNamed(ShotCode):
        if ShotNaming == 0:
            isNamed=True
        else:
            isNamed=checkRegEx(vfxRegex,ShotCode)
        return isNamed

    def isStatus(ShotStatus):
        if ShotStatus==Status:
            isStatus = True
        else:
            isStatus = False
        return isStatus

    def isDated(ShotDate):
        dtShotDate = datetime.strptime(ShotDate,'%Y/%m/%d')
        if Days ==0.0 or (dtShotDate + DeltaDays >= dtToday):
            isDated=True
        else:
            isDated=False
        return isDated

    def readCSV(up,sourcePath):
        filename=up.getFilePath()
        MatchShots=[]
        ShotsUP=[]
        # separator = self.evaluate(self.delimiter).strip()
        self.info('ShotGridCSVReader:readCSV','Processing CSV {}'.format(filename))

        with open(filename) as f:
            reader = csv.reader(f, delimiter=',')
            for i,row in enumerate(reader):
                if i==0 or i==1:
                    continue
                ShotCode=row[1]
                ShotStatus=row[3]
                ShotDate=(row[12].split())[0]
                hasName=isNamed(ShotCode)
                hasStatus=isStatus(ShotStatus)
                hasDate=isDated(ShotDate)
                if hasName and hasStatus and hasDate:
                    MatchShots.append(ShotCode)

        for shot in MatchShots:
            shotUP = CuniversalPath(nc)
            shotUP.setSequence(False)
            shotUP.autoFromName(shot)
            tokensMapper = token2mdataMapper(self)
            shotUP = tokensMapper.nc2mdata(shotUP)
            SearchPath = shotUP.getStringOverride(sourcePath)
            if not os.path.exists(SearchPath):
                self.critical("ShotGridCSVReader:SearchPath:notFound","Search Path does not exist".format(SearchPath))
            maxVFF=maxVersion(SearchPath)
            shotUP2 = CuniversalPath(nc2)
            shotUP2.autoFromName(maxVFF)
            shotUP2.readMetadataFromFile()
            shotUP2 = tokensMapper.nc2mdata(shotUP2)

            ShotsUP.append(shotUP2)
        return [True,ShotsUP]

    res=True

    if self.bypassEnabled:
        #this node leaves the outputs empty during bypass as the files are not generated
        return True

    # vfxRegex1=r'[a-zA-Z0-9]+_+[a-zA-Z0-9]+_+[a-zA-Z0-9]+_?+[a-zA-Z0-9]+_?+[a-zA-Z0-9]+'
    # vfxRegex2="([a-zA-Z0-9]+[_]){2,7}[a-zA-Z0-9]+"
    # vfxRegex check at https: // regex101.com /
    ShotNaming = int(self.ShotNaming)
    # print(ShotNaming)
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

    dtToday = datetime.now()
    dateToday = dtToday.strftime("%Y%m%d")
    # print(dateToday)

    input=self.getFirstConnectorByName("SGcsv")
    list = input.getUniversalPaths()
    outConnMV=self.getFirstConnectorByName("MaxVersion")
    outConnMV.clearUniversalPaths()
    sourcePath = self.evaluate(self.SearchPath).strip()
    Status=self.Status
    Days=float(self.SinceDays)
    DeltaDays=timedelta(days=Days)

    tokensMapper = token2mdataMapper(self)
    # nc=self.CSVShotTokens
    nc=CnameConvention(self.CSVShotTokens)
    if not nc.toString():
        nc=self.getWorkflow().getNameConvention()

    nc2=CnameConvention(self.getNameConvention())
    if not nc2.toString():
        nc2=self.getWorkflow().getNameConvention()

    for up in list:
        if self.isCancelled():
            return False
        [r, ShotsUP] = readCSV(up,sourcePath)
        res = res and r
        if res:
            if ShotsUP:
                for sh in ShotsUP:
                    outConnMV.addUniversalPath(sh)
    return res