from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CnameConvention,CuniversalPath
import Mistika
import json
import os
from baseItemTools import totalNumberOfUPs

_UNITS_FRAMES=0
#_UNITS_SECS=1

def init(self):
    self.setClassName("Trim Media")
    #At the moment, Unit supports FRAMES only
    self.addProperty("units",_UNITS_FRAMES)
    self.addProperty("trimHead",0)
    self.addProperty("trimTail", 0)

    self.addConnector("input",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("output",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True,"input")
    #configuring the node
    self.bypassSupported=True
    self.color=QColor(0x677688)
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res = True
    return res

def process(self):
    '''
    def splitTC(tc):
        elements=tc.split('@')
        if len(elements)!=2:
            self.critical("TrimMedia:invalidTC","Unsupported TC format: {}".format(tc))
            return [None,None]
        frames=elements[0]
        if frames.endswith('D'):
            frames=frames[:-1]
        frames=int(frames)
        fps=float(elements[1])
        print(frames,fps)
        return [frames,fps]
    '''
    def splitTC(tc, fps=None):
        '''
        Supported TC formats:
        - hh:mm:ss:ff
        - hh:mm:ss;ff
        - hh:mm:ss:ff@fps
        - hh:mm:ss:ffD@fps
        - frames@fps
        - framesD@fps
        '''
        if not tc:
            self.critical("TrimMedia:missingTC", "No TimeCode found")
            return [None, None]

        tc = tc.strip()
        dropFrame = False
        detectedFPS = float(fps) if fps else 25.0

        if '@' in tc:
            tc, fpsStr = tc.split('@')
            detectedFPS = float(fpsStr)

        # Timecode format
        if ':' in tc or ';' in tc:
            dropFrame = tc.endswith('D') or ';' in tc
            tc = tc.rstrip('D').replace(';', ':')
            parts = tc.split(':')
            if len(parts) != 4:
                self.critical("TrimMedia:invalidTC", f"Invalid TimeCode: {tc}")
                return [None, None]
            try:
                hh, mm, ss, ff = map(int, parts)
            except ValueError:
                self.critical("TrimMedia:invalidTC2", f"Invalid TimeCode Values: {tc}")
                return [None, None]

            if dropFrame:
                if detectedFPS.is_integer():
                    self.critical("TrimMedia:invalidFPS", f"Drop Frame not supported for {detectedFPS} fps")
                    return [None, None]
                dropFrames = 2 if detectedFPS < 30 else 4
                totalMinutes = hh * 60 + mm
                dropped = dropFrames * (totalMinutes - totalMinutes // 10)
                frames = ((hh * 3600) + (mm * 60) + ss) * round(detectedFPS) + ff - dropped
            else:
                frames = ((hh * 3600) + (mm * 60) + ss) * detectedFPS + ff

            return [int(frames), detectedFPS]

        # Frame count format
        try:
            frames = int(tc.rstrip('D'))
            return [frames, detectedFPS]
        except ValueError:
            self.critical("TrimMedia:invalidFrames", f"Invalid frame count: {tc}")
            return [None, None]
        
    def addTrimInfo(up,units,head,tail):
        mfid=up.getMediaFileInfoData()
        tc=mfid.getToken("TimeCode")
        fps=mfid.getToken("fps")
        [framesTC,fps]=splitTC(tc,fps)
        if not fps:
            return False
        framesLen=int(mfid.getToken("Frames"))
        inPoint=int(up.getParam("in",-1))
        outPoint=int(up.getParam("out",-1))
        print ("tc",tc,"in",inPoint,"out",outPoint)
        if inPoint<0:
            inPoint=framesTC
        if outPoint<0:
            outPoint=inPoint+framesLen
        print ("in",inPoint,"out",outPoint)
        if head>0:
            inPoint=inPoint+head
            up.setParam("in",inPoint)
        if tail>0:
            outPoint=outPoint-tail
            if outPoint<0:
                outPoint=0
            up.setParam("out",outPoint)        
        print("Trim Info: tc={} in={} out={}".format(tc,inPoint,outPoint))
        self.info("TrimMedia:trimInfo","Trim Info: tc={} in={} out={}".format(tc,inPoint,outPoint))
        return True
            
    res=True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    output=self.getFirstConnectorByName("output")
    output.clearUniversalPaths()
    
    if self.bypassEnabled:
        return True
    
    self.setComplexity(totalNumberOfUPs(self)*100)
    current=0
    self.progressUpdated(current)

    units=int(self.units)
    head=int(self.trimHead)
    tail=int(self.trimTail)
    resList=[]
    for c in inputs:                                 
        for iup in c.getUniversalPaths():
            if self.isCancelled():
                return False
            print(iup.getFileName())
            up=CuniversalPath(iup)
            if head>0 or tail>0:
                if addTrimInfo(up,units,head,tail):
                    resList.append(up)
                else:
                    self.addFailedUP(up)
                    res=False
        current+=1
        self.progressUpdated(current*100)
    
    output.addUniversalPaths(resList)
    self.progressUpdated(self.complexity())
    return res
