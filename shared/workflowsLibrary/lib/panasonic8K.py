# v 1.0 bug fixed. not detecting remaining size correctly

import os
import json
import shutil
import psutil
from threading import Thread
from queue import Queue
import lxml.etree as ET
from Mistika import sgoPaths

_FIX_NODE_NAME="FixP2Serial"
_QUADRANT_PROPERTIES={0:"exP2_1",1:"exP2_2",2:"exP2_3",3:"exP2_4",4:"mP2"}
    

# Card item class ##############################################
class Cp2Card:
    QUADRANT_UNKNOWN=-1
    QUADRANT_1=0
    QUADRANT_2=1
    QUADRANT_3=2
    QUADRANT_4=3        
    QUADRANT_PROXY=4    
    componentDirectories=["exP2-1","exP2-2","exP2-3","exP2-4","mP2"]
    
    def __init__(self,serial=None,quadrant=QUADRANT_UNKNOWN,rootPath=None):      
        self.m_serial=serial
        self.m_quadrant=quadrant
        self.m_rootPath=rootPath      
        
    def fromJSON(self,jsonStr):
        data=json.loads(jsonStr)
        # m_rootPath is not added to the JSON because we actually do not want to store that info as it may change from one system to another.
        # so it is better calculated every time
        self.m_serial=data["serial"]
        self.m_quadrant=data['quadrant']

    def toJSON(self):
        dict ={  
            "serial": self.m_serial,  
            "quadrant": self.m_quadrant
        }
        jsonStr = json.dumps(dict)  
        return jsonStr 
        
    def serial(self):
        return self.m_serial
    
    def setSerial(self,serial):
        self.m_serial=serial
        
    def quadrant(self):
        return self.m_quadrant
            
    def setQuadrant(self,quadrant):
        self.m_quadrant=quadrant        
    
    def rootPath(self):
        return self.m_rootPath
            
    def setRootPath(self,rootPath):
        self.m_rootPath=rootPath
 
    def getAvailableSpace(self):
        # -------------------------- TEST ------------------------
        #if os.name=="nt":
        #    return 3*1024**3
        if not self.m_rootPath or not len(self.m_rootPath):
            return 0
        partitions = psutil.disk_partitions()
        for p in partitions:
            if os.name=="nt":
                mountpoint=p.mountpoint.replace("\\","/")
                root=self.m_rootPath.replace("\\","/")
            else:            
                mountpoint=p.mountpoint             
                root=self.m_rootPath
            if mountpoint==root:
                try:
                    free=psutil.disk_usage(p.mountpoint).free                    
                    return free
                except:
                    pass
        return 0    
        
    @staticmethod
    def getQuadrantFromPath(filePath):
        for idx,d in enumerate(Cp2Card.componentDirectories):
            if '/{}/'.format(d) in filePath:
                return idx                       
        return -1 # This should not happen. it is not in a P2 structure!          
 
               
# Cards cache class ##############################################
class Cp2CardsCache:
    def __init__(self,node): 
        self.m_cache={}
        self.m_node=node
        self.loadDefault()
        
    def fromJSON(self,jsonStr):
        self.m_cache={}        
        data = json.loads(jsonStr)['cards']
        for item in data:
            card=Cp2Card() 
            card.fromJSON(item)
            self.m_cache[card.serial()]=card  
    
    def toJSON(self):
        data = {"cards":[]}           
        for key in self.m_cache:
            j=self.m_cache[key].toJSON()
            data['cards'].append(j)
        return json.dumps(data)
        
    
    def defaultCacheFile(self):
        return '{}/packP2CardCache.json'.format(sgoPaths.workflowsLibrary())
        
    def loadCacheFile(self,filePath):    
        self.m_cache={}
        try:
            with open(filePath) as json_file:
                str = json_file.read()
                self.fromJSON(str)
        except:
            pass

    def loadDefault(self):
        self.loadCacheFile(self.defaultCacheFile())

    def saveCacheFile(self,filePath):
        jsonStr=self.toJSON()
        try:
            with open(filePath, 'w') as outfile:
                outfile.write(jsonStr)
        except:
            pass

    def saveDefault(self):
        self.saveCacheFile(self.defaultCacheFile())

    def add(self,card):        
        self.m_cache[card.serial()]=card
        self.saveDefault()
        
    def get(self,serial):        
        if serial in self.m_cache:
            return self.m_cache[serial]
        return None       
        
    def cache(self):
        return self.m_cache
        
    def dump(self):
        print("Dump -----")
        for key in self.m_cache:
            c=self.m_cache[key]
            print("card: serial={} quadrant={} root={}".format(c.serial(),c.quadrant(),c.rootPath())) 
        print("End  -----") 
        
    # list is a dictionary serial->rootPath
    def updateRootPaths(self,list):
        for serial in self.m_cache:
            card=self.m_cache[serial]
            if serial in list:
                card.setRootPath(list[serial])
                if card.quadrant()>=0:
                    del list[serial]
            else:
                card.setRootPath(None)        
            self.m_cache[serial]=card
        if len(list)>0:
            self.m_node.info("updateRootPaths","new Cards found: {}".format(list))
            self.registerNewCards(list)
          
    def readQuadrant(self,xmlFile):
        root=ET.parse(xmlFile).getroot()
        
        rx='\{{.*\}}{}$'.format('\/P2Main\/ClipContent\/GlobalClipID')
        r = re.compile(rx)
        for s in root.iter():
            if r.match(s.tag):
                id=s.text
                if len(id)>32:
                    v=int(id.at(31))
                    return v
        return -1
                    
    def findQuadrantFromFiles(self,rootPath):
        for idx,name in enumerate(Cp2Card.componentDirectories):
            if os.path.exists('{}/{}'.format(rootPath,name)):
                return idx
                
        for root, subFolders, files in os.walk(rootPath):
            for f in files:
                if f.endswith(".XML"):
                    q=self.readQuadrant(f)
                    if q>=0:
                        return q #found!
            for d in subFolders:
                return self.findQuadrantFromFiles('{}/{}'.format(root,d))
        return -1    
    
    def registerNewCards(self,list):    
        # first try to auto detect quadrant
        unregistered={}
        for serial in list:
            rootPath=list[serial]
            quadrant=self.findQuadrantFromFiles(rootPath)
            if quadrant>=0:
                card=Cp2Card(serial,quadrant,rootPath)
                self.add(card)
            else:
                unregistered[serial]=rootPath
                #del list[serial]
        #now ask if anyone still pending (To Be Implemented)
        #if len(list)>0:
        #    Cp2CardCopier.m_gui.updateCardsListSignal(list)
        #    #form.show()
        #    #method=getattr(form,'exec')
        #    #ok=method()
        #    quadrants=form.getQuadrants()
        #    print list
        #    print quadrants            
        #    for serial in list:      
        #        rootPath=list[serial]      
        #        quadrant=quadrants[serial]                
        #        card=Cp2Card(serial,quadrant,rootPath)
        if len(unregistered)>0:
            for s in unregistered:
                self.m_node.warning("copyP2Card:registerNewCards:unregistered","Unable to register {} (serial={}). Please create its reference directory (exP2-? or mP2)".format(unregistered[s],s))
        self.saveDefault()      

    def getSerialFromRootPath(self,rootPath):
        for serial in self.m_cache:
            card=self.m_cache[serial]
            if card.rootPath()==rootPath:
                return card.serial()
        return None
    

# Cards functionalities #########################################
class Cp2CardCopier:
    MODE_COPY=1
    MODE_MOVE=0 
    MODE_TRACE_ONLY=-1 
    m_gui=None
        
    def __init__(self,node,cache):
        self.m_threads=[[0,0],[0,0],[0,0],[0,0],[0,0]]
        self.m_node=node
        self.m_cache=cache
        m_clipNames=[] #list to track potential repeated names
        
    # returns a dictionary quadrant->(rootPath,availableSpace)
    def getMountedCardsToUse(self):
        cardsMounted={}  
        cache=self.m_cache.cache()
        for s in cache:
            card=cache[s]
            path=card.rootPath()
            quadrant=card.quadrant()
            sz=card.getAvailableSpace()
            if sz>=0:
                if path:
                    if path in cardsMounted:
                        if sz>=cardsMounted[path][1]:
                            cardsMounted[card.quadrant()]=[card.rootPath(),sz]
                    else:                    
                        cardsMounted[card.quadrant()]=[card.rootPath(),sz]
        return cardsMounted

    def updateCardsAvailableSpace(self,cards):
        updated={}
        for id in cards:
            rootPath=cards[id][0]
            card=Cp2Card(None,-1,rootPath)
            sz=card.getAvailableSpace()
            updated[id]=[rootPath,sz]
        return updated   

    def updateDirectoriesSpaceleft(self,cards,used):
        updated={}
        for id in cards:
            rootPath=cards[id][0]
            sz=cards[id][1]-used[id]
            updated[id]=[rootPath,sz]
        return updated  

    #returns a list of 5 elements with the subdirectory sizes (exP2-1,2,3,4 and mP2)
    def sizeof(self,up):    
        total_sizes=[0,0,0,0,0]            
        blockSize=0x40000 # 256K
        files=up.getAllFiles()
        for f in files:
            if os.path.isfile(f):
                idx=Cp2Card.getQuadrantFromPath(f)   
                if idx>=0:
                    total_sizes[idx] += os.path.getsize(f) + blockSize 
        return total_sizes        
        
    #returns the list of all the P2 UPs paired with a list of their 5 sizes (mP2, exP2-1, 2, 3 and 4)
    def findAllP2Contents(self,up):
        list=[]
        if up.getParam("megaPack","")=="Panasonic8k":                  
            list.append([up,self.sizeof(up)])
        return list        

    def getRepeatedName(self,files):
        list=[value for value in files if os.path.basename(value).lower() in self.m_clipNames]
        return list
    
    def addToClipNames(self,files):
        self.m_clipNames.extend([os.path.basename(value).lower() for value in files if value.lower().endswith(".xml")]) #tracking the xml filenames only should be enough            
        
    def cleanClipNames(self):
        self.m_clipNames=[]
        
    def fit(self,fileSizes,cardSizes):    
        print("comparing: ",fileSizes,cardSizes)
        for idx,sz in enumerate(fileSizes):
            if sz>cardSizes[idx]:
                return False
        return True
    
    def getSubPath(self,filePath,quadrant):
        d=Cp2Card.componentDirectories[quadrant]
        pos=filePath.rfind(d)+len(d)+1 #+1 for the slash
        return filePath[pos:]
        
    def allCardsAvailable(self,cardsToUse):
        #print cardsToUse
        if len(cardsToUse)!=5:
            return False
        indexesNeeeded=[0,1,2,3,4]
        for idx in indexesNeeeded:
            if not idx in cardsToUse or len(cardsToUse[idx][0])==0:            
                return False
        return True
    
    def copy(self,q,progressQueue,move,bufferSize):
        res=True
        try:
            O_BINARY = os.O_BINARY
        except:
            O_BINARY = 0
        READ_FLAGS = os.O_RDONLY | O_BINARY
        WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | O_BINARY      
        while True:
            [src,dst]=q.get()
            if not src:
                break
            if move:
                print('Thread moving {} -> {}'.format(src,dst))
                try:
                    shutil.move(src,dst) 
                except OSError as err:            
                    print("Copy Error:",src,"Error {}".format(err))
                    res=self.m_node.critical("copyP2Card:move:copyError","Error {}".format(err)) and res
                    progressQueue.put(-1) #error
                except IOError as err:   
                    print("Copy Error:",src,"IO Error {}".format(err))
                    res=self.m_node.critical("copyP2Card:move:copyError2","IO Error {}".format(err)) and res  
                    progressQueue.put(-1) #error
                finally:
                    if os.path.isdir(src):
                        if len(os.listdir(src))==0:
                            os.rmdir(src)
            else:
                print('Thread copying {} -> {}'.format(src,dst))
                try:
                    fin = os.open(src, READ_FLAGS)
                    stat = os.fstat(fin)
                    fout = os.open(dst, WRITE_FLAGS, stat.st_mode)
                    for x in iter(lambda: os.read(fin, bufferSize), None):
                        if not x:
                            break
                        bytes=os.write(fout, x)
                        progressQueue.put(bytes)
                except OSError as err:           
                    print("Copy Error:",src,"Error {}".format(err)) 
                    res=self.m_node.critical("copyP2Card:copy:copyError","Error {}".format(err)) and res
                    progressQueue.put(-1) #error
                except IOError as err:                
                    print("Copy IO Error:",src,"Error {}".format(err))
                    self.m_node.critical("copyP2Card:copy:copyError2","IO Error {}".format(err)) and res  
                    res=progressQueue.put(-1) #error
                finally:
                    try: 
                        os.close(fin)
                        os.close(fout)
                    except: pass
        return res

    def removeEmptyFolders(self,path):
        print("removeEmptyFolders",path)
        empty=True
        for f in os.listdir(path):
            child=os.path.join(path,f)
            if os.path.isdir(child):
                self.removeEmptyFolders(child)
            elif os.path.isfile(child):
                empty=False
        if empty:
            try:            
                if len(os.listdir(path))==0:
                    os.rmdir(path)
            except: pass
            
    def threadedCopy(self,quadrant,src,dst,progressQueue,move,bufferSize):
        [thread,q]=self.m_threads[quadrant]        
        if not thread:
            q=Queue()
            q.put([src,dst])
            thread=Thread(target=self.copy, args=(q,progressQueue,move,bufferSize))
            self.m_threads[quadrant]=[thread,q]
            thread.start()
        else:        
            q.put([src,dst])
            
    def updateProgress(self,current,totalSize,progressQueue):
        while not progressQueue.empty():
            sz=progressQueue.get()
            if sz<0:
                self.m_error=1
            else:
                current+=sz
                self.m_node.progressUpdated(current/(1024**2))
        return current
        
    def finishThreads(self,current,totalSize,progressQueue):
        for i in range(5):
            print('finishing thread {}'.format(i))
            [thread,q]=self.m_threads[i]  
            if not thread:
                continue
            q.put([None,None])
            while thread.is_alive():
                thread.join(timeout=1)
                current=self.updateProgress(current,totalSize,progressQueue)
            print('Thread {} finished'.format(i))    
        print('all threads finished')                    
        self.m_threads=[[0,0],[0,0],[0,0],[0,0],[0,0]]
        current=self.updateProgress(current,totalSize,progressQueue)
        return current
                        
    def getNextCardFolderAvailable(self,dstFolder,cardName,sz,createDirs=True):
        max=0
        if dstFolder.endswith("/"):
            dstFolder=dstFolder[:-1]
        for file in os.listdir(dstFolder):
            start='{}-'.format(cardName)
            if file.startswith(start):
                str=file.replace(start,'')
                try:
                    n=int(str)
                    if n>max:
                        max=n
                except:
                    pass
        root='{}/{}-{}'.format(dstFolder,cardName,max+1)
        result={}
        for i in range(5):
            path=root+"/"+Cp2Card.componentDirectories[i]
            if createDirs and not os.path.exists(path):
                os.makedirs(path)
            cardSz=sz*1024**3 if i<4 else sz*(1024**3)/8 # required mP2 card size is 8 times smaller exP-*
            cardSz=cardSz*0.9 #remove format margin
            result[i]=[path,cardSz]
        return root,result
            
    #copy or move the contents to the dst P2 card
    def transfer(self,inputList,cards=None,bufferSize=16*1024*1024):
        self.m_error=0
        remaining=[]
        processedList=[]
        totalSize=sum(sum(x[1]) for x in inputList)
        mode=int(self.m_node.mode)
        self.m_node.setComplexity(totalSize/(1024**2))    
        copied=0
        self.cleanClipNames()
        print(cards)
        if cards:
            cardsToUse=cards 
        else:
            cardsToUse=self.getMountedCardsToUse()
        if not self.allCardsAvailable(cardsToUse):
            return [self.m_node.critical("copyP2Card:pack:incomplete","Missing cards. found={}".format(cardsToUse))and res,remaining,processedList]
        progressQueue=Queue()
        for up,sz in inputList:
            if not cards:
                cardsToUse=self.updateCardsAvailableSpace(cardsToUse)
            if self.m_node.isCancelled():
                return [self.m_node.critical('pack:Processing:cancel','Cancelled by user')and res,remaining,processedList]
            szcardsToUse=[cardsToUse[x][1] for x in range(0,5)]  
            print('cards space available : {} MB'.format([x/1024**2 for x in szcardsToUse]))
            self.m_node.info('pack:Processing','Processing {} / Space Needed: {} MB'.format(up.toString(),[x/1024**2 for x in sz]))            
            print('Processing {}/{}'.format(up.toString(),[x/1024**2 for x in sz]))
            files=up.getAllFiles()
            if self.fit(sz,szcardsToUse):
                print("fits")
                repeatedNames=self.getRepeatedName(files)
                if not len(repeatedNames): # process only if the contents doesnt have repeated names 
                    processedList.append(up)
                    #copy UP to dst                
                    sourcePath=up.getPath()                    
                    try:
                        for f in files:  
                            if self.m_node.isCancelled():
                                return [self.m_node.critical('pack:Processing:cancel2','Cancelled by user')and res,remaining,processedList]
                            quadrant=Cp2Card.getQuadrantFromPath(f)
                            if quadrant<0:
                                self.m_node.warning("copyP2Card:pack:quadrant","ignoring {}. No quadrant detected".format(f))
                                continue
                            dstDir=cardsToUse[quadrant][0]
                            availableSpace=cardsToUse[quadrant][1]                     
                            if f.endswith("/"):
                                f=f[0:len(f)-1]
                            sourceSubPath=self.getSubPath(f,quadrant)
                            dstFilePath='{}/{}'.format(dstDir,sourceSubPath)
                            if  os.path.isdir(f):
                                if not os.path.exists(dstFilePath):
                                    #self.m_node.info("copyP2Card:pack:mkdir",u"Making dir {}".format(f,dstFilePath)) 
                                    print("Making dir {}".format(f,dstFilePath))
                                    if mode>=0:
                                        os.makedirs(dstFilePath)
                            else:
                                if os.path.basename(f)!="LASTCLIP.TXT": # do not copy this file as it seems to be protected
                                    #self.m_node.info("copyP2Card:pack:trace",u"Copying {} to {}".format(f,dstFilePath)) 
                                    print("Copying {} to {}".format(f,dstFilePath))
                                    if not os.path.exists(os.path.dirname(dstFilePath)) and mode>=0:
                                        os.makedirs(os.path.dirname(dstFilePath))
                                    if mode>=0:
                                        self.threadedCopy(quadrant,f,dstFilePath,progressQueue,mode==self.MODE_MOVE,bufferSize)   
                            
                    except OSError as err:            
                        return [self.m_node.critical("copyP2Card:pack:copyError","Error {}".format(err)) and res, remaining,processedList]
                    except IOError as err:                     
                        return [self.m_node.critical("copyP2Card:pack:copyError2","IO Error {}".format(err)) and res,remaining,processedList]
                    #except:            
                        #return self.m_node.critical("copyP2Card:pack:unexpected",u"Unexpected Error") and res          
                    #if cards:
                    #    cardsToUse=self.updateDirectoriesSpaceleft(cardsToUse,sz) 
                    #else:
                    #    cardsToUse=self.updateCardsAvailableSpace(cardsToUse)
                    self.addToClipNames(files)                    
                else:
                    self.m_node.info("copyP2Card:pack:repeated","Repeated name {} detected.".format(repeatedNames))
                    remaining.append([up,sz])
                if cards:
                    for idx,s in enumerate(sz):
                        cardsToUse[idx][1]=cardsToUse[idx][1]-s
            else:  
                self.m_node.info("copyP2Card:pack:nofit","Pack Not Copied. It does not fit: {}".format(up.getFilePath()))
                remaining.append([up,sz])
                print("does not fit")
            copied=self.finishThreads(copied,totalSize,progressQueue)
            self.m_node.info("copyP2Card:pack:endLoop",'{} finished'.format(up.getFilePath()))
            if mode==self.MODE_MOVE:
                self.removeEmptyFolders(up.getPath())
            print('{} finished'.format(up.getFilePath()))       
        print("final space available: {} MB".format([x/1024**2 for x in szcardsToUse]))
        self.m_node.progressUpdated(totalSize/(1024**2))
        return [self.m_error==0,remaining,processedList]
            
    def getInputList(self):
        inputList=[]
        for c in self.m_node.getConnectorsByName("p8"):
            for p in c.getUniversalPaths():
                fp=p.getFilePath()
                l=self.findAllP2Contents(p)
                if len(l)>0:
                    inputList.extend(l)
                else:
                    self.m_node.warning('Cp2CardCopier:getInputList:noP8','{} ignored. Not a P8 Megapack'.format(fp))
        return inputList
        
    def checkCardsSpace(self,inputList=None):
        res=True
        cardsToUse=self.getMountedCardsToUse()
        quadrants=_QUADRANT_PROPERTIES.keys()
        available=0
        rootPath=None
        totalSizeNeeded=[0,0,0,0,0]
        if inputList:
            for up,sz in inputList:
                map(sum, zip(totalSizeNeeded,sz))
        for idx in quadrants:
            spaceNeeded=totalSizeNeeded[idx]
            if idx in cardsToUse:
                sz=cardsToUse[idx][1]
                rootPath=cardsToUse[idx][0]
                card=Cp2Card(None,idx,rootPath)
                available=card.getAvailableSpace()
            else:
                card=None
            v='Serial={}. Available Space={} GB ({})'.format(self.m_cache.getSerialFromRootPath(rootPath),available/(1023**3),available)
            setattr(self.m_node,_QUADRANT_PROPERTIES[idx],v)
            if not card:
                res=self.m_node.critical("copyP2Card:isReady:notCard","{} card not found".format(_QUADRANT_PROPERTIES[idx])) and res
            elif inputList and available<totalSizeNeeded[idx]:
                res=self.m_node.critical("copyP2Card:isReady:notSpace","{} Not Enough Space Available".format(_QUADRANT_PROPERTIES[idx])) and res
        return res
    
def packP2LoadCache(self):
    cache=Cp2CardsCache(self)
    fixer=self.getRegisteredItem(_FIX_NODE_NAME);
    # get mounted paths list
    mountedList={}
    if fixer:
        serials=fixer.getSerials()
        for s in serials:
            mountedList[s]=fixer.getDevice(s)
    #---------------------------- TEST -------------------------
    if os.name=="nt" and not mountedList:
        c=Cp2Card("serial-ex-1")
        c.setRootPath("M:/MATERIAL/tmp/p2/ex-1")
        cache.add(c)
        c=Cp2Card("serial-ex-2")
        c.setRootPath("M:/MATERIAL/tmp/p2/ex-2")
        cache.add(c)
        c=Cp2Card("serial-ex-3")
        c.setRootPath("M:/MATERIAL/tmp/p2/ex-3")
        cache.add(c)
        c=Cp2Card("serial-ex-4")
        c.setRootPath("M:/MATERIAL/tmp/p2/ex-4")
        cache.add(c)
        c=Cp2Card("serial-proxy")
        c.setRootPath("M:/MATERIAL/tmp/p2/mP2")
        cache.add(c)    
        mountedList={"serial-ex-1":"M:/MATERIAL/tmp/p2/ex-1",
                     "serial-ex-2":"M:/MATERIAL/tmp/p2/ex-2",
                     "serial-ex-3":"M:/MATERIAL/tmp/p2/ex-3",
                     "serial-ex-4":"M:/MATERIAL/tmp/p2/ex-4",
                     "serial-proxy":"M:/MATERIAL/tmp/p2/mP2"}
    cache.updateRootPaths(mountedList)
    #cache.dump()
    return cache
