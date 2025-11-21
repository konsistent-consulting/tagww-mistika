
from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CnameConvention,CuniversalPath
from mistikaTools import installModule
from Cedl import Cedl
from token2mdata import token2mdataMapper
import os
import sys
import json
import csv
from timecode import Timecode
import argparse
try:
    import re
except:
    installModule("re")


def init(self):
    self.setClassName("Leonard Assist")
    self.addConnector("json",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("edl",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("files", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.addProperty("edlOutputPath")
    self.setDropToProperty("edlOutputPath")
    self.setDropSupportedTypes(1)
    self.addProperty("overwrite", True)
    self.addProperty("jsonInputOverride", False)
    self.addProperty("TracksToProcess","1-3,5,8")
    self.addProperty("exportMarkers",True)
    self.addProperty("edlEvents",1)
    self.addProperty("getMarkersName", True)
    self.addProperty("getMarkersNotes", False)
    self.addProperty("MarkersColor1","Blue")
    self.addProperty("MarkersTrackTarget1",1)
    self.addProperty("MarkersSuffix1")
    self.addProperty("MarkersColor2","Blue")
    self.addProperty("MarkersTrackTarget2",2)
    self.addProperty("MarkersSuffix2","_Layer001")
    self.addProperty("MarkersColor3","Blue")
    self.addProperty("MarkersTrackTarget3",3)
    self.addProperty("MarkersSuffix3","_Layer002")
    self.addProperty("MarkersColor4","Red")
    self.addProperty("MarkersTrackTarget4",4)
    self.addProperty("MarkersSuffix4")
    self.addProperty("MarkersColor5","Yellow")
    self.addProperty("MarkersTrackTarget5",5)
    self.addProperty("MarkersSuffix5")
    self.addProperty("edlNC")
    self.addProperty("filesNC")

    self.bypassSupported=True
    return True


def isReady(self):
    res=True
    if self.bypassSupported and self.bypassEnabled:
        return res
    if not self.edlOutputPath:
        res=self.critical("LeonardAssist:edlOutputPath:notFound","edlOutputPath can not be empty") and res
    if self.exportMarkers:
        if not self.getMarkersName and not self.getMarkersNotes:
            res = self.critical("LeonardAssist:MarkersOptions:No getMarkers source selected", "Name or Notes from getMarkers is required") and res
    return res


def process(self):
    def getFiles(jsonData,Tracks):
        filesClean=[]
        files=[]
        for track in Tracks:
            currentTrack = f'VideoTrack {track}'
            if currentTrack in jsonData:
                for event in jsonData[currentTrack]:
                    clipName=event['Clip Name']
                    padding=clipName.split('.')[1]
                    isSeq = re.fullmatch(seqRegex,padding)
                    if isSeq is not None:
                        ext = clipName.split('.')[2]
                        tapeName = clipName.split('.')[0]
                        frameIN=(padding.strip('[]')).split('-')[0]
                        frameOUT=(padding.strip('[]')).split('-')[1]
                        mwfSeqFile=f'{tapeName}.{frameIN}.{ext}'
                        fileUPname=(event['File Path']).replace(clipName,mwfSeqFile)
                        files.append(fileUPname)
                    else:
                        files.append(event['File Path'])
            else:
                self.warning("LeonardAssist:getFiles:currentTrack", str(currentTrack) + ' Does not exist, skipping')
                continue
        [filesClean.append(x) for x in files if x not in filesClean]
        return [True,filesClean]

    def buildEDL(jsonData,Tracks):
        edlFiles=[]
        currentTimeline=jsonData['timeline']
        for track in Tracks:
            outputEDL = f'{dstPathEDL}{currentTimeline}_V{track}.edl'
            edlLines=[]
            title=f'TITLE: {currentTimeline}_V{track}'
            fcm='FCM: NON-DROP FRAME'+'\n'
            edlLines.append(title)
            edlLines.append(fcm)
            currentTrack=f'VideoTrack {track}'
            if currentTrack in jsonData:
                for event in jsonData[currentTrack]:
                    if edlClipOptions==1 and not 'LOC' in event:
                        continue
                    line=event['EventNr']+ '   ' + event['Clip Name'][:-4] + '  V   C  ' + event['srcIn']+ ' ' + event['srcOut']+ ' ' + event ['recIn']+ ' ' + event['recOut']+'\n'
                    if 'LOC' in event:
                        line += '*LOC: ' + event['LOC'].split()[0] + ' ' + event['LOC'].split()[1] + '  ' + event['LOC'].split()[2]+'\n'
                    if 'ASC_SOP' in event:
                        line += '*ASC_SOP ' + event['ASC_SOP']+'\n'
                        line += '*ASC_SAT ' + event['ASC_SAT']+'\n'
                    edlLines.append(line)
                    continue
                if os.path.isfile(outputEDL) and not self.overwrite:
                    self.warning("LeonardAssist:buildEDL:fileExists", "EDL file already exists" + outputEDL)
                    continue
                if len(edlLines) == 2:  ##if only title and fcm are in edlLines
                    continue
                else:
                    with open (outputEDL,'w') as f:
                        for line in edlLines:
                            f.writelines(line+'\n')
                    f.close()
                    edlFiles.append(outputEDL)
            else:
                self.warning("LeonardAssist:buildEDL:currentTrack", str(currentTrack) + ' Does not exist, skipping')
                continue
        return [True,edlFiles]

    def getVideoTracks(VideoTracks):
        Tracks = []
        try:
            numbers = VideoTracks.split(',')
        except:
            self.critical("LeonardAssist:getVideoTracks:split Index out of range",
                          "check the VideoTracks input to process".format(self.TracksToProcess))
            return False
        for number in numbers:
            if '-' in str(number):
                start, end = number.split('-')
                numbers.extend(range(int(start), int(end) + 1))
            else:
                Tracks.append(int(number))
        Tracks.sort()
        return Tracks

    def processJSON (jsonFile):
        # print (jsonFile)
        with open(jsonFile, "r") as js:
            jsonData = json.load(js)
        dvTimeline=jsonData["timeline"]
        fps= jsonData["fps"]
        csvFile=jsonData["csvFilePath"]
        aleFile=jsonData["aleFilePath"]

        CDLValues={}
        with open(aleFile, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            ALEValues={}
            for i,row in enumerate(reader):
                if i ==7:
                    Headers=row
                elif i >= 10:
                    for j, header in enumerate (Headers):
                        ALEValues[header]=row[j]
                    CDLValues[ALEValues['Name']]=[ALEValues['ASC_SOP'],ALEValues['ASC_SAT']]
        with open(csvFile, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=',')
            for i,row in enumerate(reader):
                if i < 1:
                    continue
                else:
                    ClipName=row[11]
                    ReelName=row[1]
                    Track=row[3]
                    srcIn=row[6]
                    srcOut=row[7]
                    recIn=row[9]
                    recOut=row[10]
                    durationTC = row[8]
                    FrameSrcIn=(Timecode(float(fps),srcIn)).frame_number
                    FrameSrcOut=(Timecode(float(fps),srcOut)).frame_number
                    FrameRecIn=(Timecode(float(fps),recIn)).frame_number
                    FrameRecOut=(Timecode(float(fps),recOut)).frame_number
                    FrameDuration=(Timecode(float(fps),durationTC)).frame_number
                    if Track.startswith('V'):
                        for track, clips in jsonData.items():
                            if Track.replace('V','VideoTrack ') in track:
                                for clip in clips:
                                    ClipNameNoExt=(clip['Clip Name']).rsplit('.',1)[0]
                                    if FrameRecIn == clip['FrameRecIn'] and FrameRecOut == clip['FrameRecOut'] and FrameDuration == clip['duration'] and (ClipName == ClipNameNoExt or ReelName == ClipNameNoExt):
                                        clip['FrameSrcIn']=FrameSrcIn
                                        clip['FrameSrcOut']=FrameSrcOut
                                        clip['srcIn'] =srcIn
                                        clip['srcOut'] =srcOut
                                        clip['recIn'] =recIn
                                        clip['recOut'] =recOut
                                        clip['durationTC'] = durationTC
                                    for media,cdlValues in CDLValues.items():
                                        if media == clip['Clip Name']:
                                            clip['ASC_SOP']=cdlValues[0]
                                            clip['ASC_SAT']=cdlValues[1]
                                        else:
                                            continue

        if self.exportMarkers:
            for j,k in markersOptions.items():
                mTrack = f'VideoTrack {j}'
                if j==0:
                    continue
                if mTrack in jsonData:
                    for marker, data in jsonData['markers'].items():
                        for clip in jsonData[mTrack]:
                            if (int(marker)+int(jsonData['RecIn'])) in range (clip['FrameRecIn'],clip['FrameRecOut']) and data['color']==markersOptions[j][0]:
                                if self.getMarkersName:
                                    clip['LOC']=clip['recIn'] + '  ' + data['color'].upper() + '  ' + data['name']+markersOptions[j][1]
                                if self.getMarkersNotes:
                                    clip['LOC'] = clip['recIn'] + '  ' + data['color'].upper() + '  ' + data['note']+markersOptions[j][1]
                else:
                    self.warning("LeonardAssist:processJson:mTrack", 'MarkersTargetTrack '+ str(j) + ' Does not exist, skipping')
        print(json.dumps(jsonData, sort_keys=False, indent=3))
        return jsonData

    def getJsonFile (up):
        jsonFile=up.getFilePath()
        if not jsonFile:
            self.addFailedUP(up)
            self.critical("LeonardAssist:getJsonFile:notJSON","Unable to interpret input UP {}".format(up.getFilePath()))
            return [False,None,None]
        return [True,jsonFile]

    def getJsonOverride():
        jsonFilePath="JSONFILE-FROMDVR-WORKFLOWSLAUNCHER"
        # print(jsonFilePath)
        return [True,jsonFilePath]

    def buildOutputUP(res, jsonFile):
        jsonData = processJSON(jsonFile)
        [r, files] = getFiles(jsonData, Tracks)
        res = res and r
        if res:
            if files:
                for file in files:
                    if self.isCancelled():
                        return False            ## TO DO: ADD PROPER EXCEPTION
                    fileUP = CuniversalPath(filesNC)
                    fileUP.autoFromName(file)
                    fileUP.readMetadataFromFile()
                    fileUP = tokensMapper.nc2mdata(fileUP)
                    outputFiles.addUniversalPath(fileUP)
        [r, edls] = buildEDL(jsonData, Tracks)
        res = res and r
        if res:
            if edls:
                for edl in edls:
                    edlUP = CuniversalPath(edlNC)
                    edlUP.autoFromName(edl)
                    edlUP = tokensMapper.nc2mdata(edlUP)
                    outputEDL.addUniversalPath(edlUP)
        return res

    res=True
    if self.bypassEnabled:
        return True

    input=self.getFirstConnectorByName("json")
    outputFiles=self.getFirstConnectorByName("files")
    outputFiles.clearUniversalPaths()
    outputEDL=self.getFirstConnectorByName("edl")
    outputEDL.clearUniversalPaths()
    dstPath=self.evaluate(self.edlOutputPath).strip()
    tokensMapper = token2mdataMapper(self)
    Tracks = getVideoTracks(self.evaluate(self.TracksToProcess).strip())
    edlClipOptions=int(self.evaluate(self.edlEvents))
    markersOptions={}
    MarkersColor1 = self.evaluate(self.MarkersColor1)
    MarkersTrack1 = int(self.evaluate(self.MarkersTrackTarget1))
    MarkersSuffix1= (self.evaluate(self.MarkersSuffix1)).strip()
    markersOptions[MarkersTrack1]=[MarkersColor1,MarkersSuffix1]
    MarkersColor2 = self.evaluate(self.MarkersColor2)
    MarkersTrack2 = int(self.evaluate(self.MarkersTrackTarget2))
    MarkersSuffix2= (self.evaluate(self.MarkersSuffix2)).strip()
    markersOptions[MarkersTrack2]=[MarkersColor2,MarkersSuffix2]
    MarkersColor3 = self.evaluate(self.MarkersColor3)
    MarkersTrack3 = int(self.evaluate(self.MarkersTrackTarget3))
    MarkersSuffix3= (self.evaluate(self.MarkersSuffix3)).strip()
    markersOptions[MarkersTrack3]=[MarkersColor3,MarkersSuffix3]
    MarkersColor4 = self.evaluate(self.MarkersColor4)
    MarkersTrack4 = int(self.evaluate(self.MarkersTrackTarget4))
    MarkersSuffix4= (self.evaluate(self.MarkersSuffix4)).strip()
    markersOptions[MarkersTrack4]=[MarkersColor4,MarkersSuffix4]
    MarkersColor5 = self.evaluate(self.MarkersColor5)
    MarkersTrack5 = int(self.evaluate(self.MarkersTrackTarget5))
    MarkersSuffix5= (self.evaluate(self.MarkersSuffix5)).strip()
    markersOptions[MarkersTrack5]=[MarkersColor5,MarkersSuffix5]
    seqRegex = "\[\d+-\d+\]"

    edlNC=CnameConvention(self.edlNC)
    if not edlNC.toString():
        edlNC=self.getWorkflow().getNameConvention()
    filesNC=CnameConvention(self.filesNC)
    if not filesNC.toString():
        filesNC=self.getWorkflow().getNameConvention()

    if self.jsonInputOverride:
        if self.isCancelled():
            return False
        [r, jsonFile] = getJsonOverride()
        if jsonFile == "JSONFILE-FROMDVR-WORKFLOWSLAUNCHER":
            self.critical("LeonardAssist:jsonInputOverride:No json input file",
                          "jsonInputOverride Activated: this workflow must be launched from Resolve's Mistika Workflows Launcher")
            return False
        jsonUP=CuniversalPath(self.getWorkflow().getNameConvention())
        jsonUP.autoFromName(jsonFile)
        dstPathEDL=jsonUP.getStringOverride(dstPath)
        if not os.path.exists(dstPathEDL):
            os.makedirs(dstPathEDL)
        res = buildOutputUP(res,jsonFile)
    else:
        list = input.getUniversalPaths()
        for up in list:
            if self.isCancelled():
                return False
            dstPathEDL=up.getStringOverride(dstPath)
            if not os.path.exists(dstPathEDL):
                os.makedirs(dstPathEDL)
            [r,jsonFile]=getJsonFile(up)
            res = buildOutputUP(res,jsonFile)

    return res

