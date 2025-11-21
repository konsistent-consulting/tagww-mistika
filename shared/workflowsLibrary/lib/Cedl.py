class CedlEvent:
    def __init__(self):
        self.m_labels=[]
        self.m_keys={}
    
    def getKey(self,key):
        return self.m_keys[key] if key in self.m_keys else None
    
    def setKey(self,key,value):
        self.m_keys[key]=value
        
    def getLabel(self,label):
        for l in self.m_labels:
            if l.startswith(label):
                return l[len(label):].strip()
        return None      
        
    def addLabel(self,label):
        self.m_labels.append(label)
        
    def getTapeName(self):
        return self.getKey('tapeName')
        
    def getClipName(self):
        return self.getLabel('FROM CLIP NAME:')
                
    def getKeys(self):
        return self.m_keys
        
    def getLabels(self):
        return self.m_labels
        
class Cedl:
    def __init__(self,node):
        self.m_node=node
        self.m_lastError=None
        self.clear()
        
    def clear(self):
        self.m_headers={}
        self.m_events=[]

    def load(self,filePath):
        self.clear()
        try:
            f=open(filePath,'r')
            lines=f.readlines()
        except e:
            self.m_lastError="Unable to Open edl {}:{}".format(filePath,e)
            self.m_node.error("Cedl:load:open",self.m_lastError)        
            return [None,None]
        loadingHeader=True
        newEventBuffer=None
        for l in lines:
            l=l.strip()
            if len(l)==0:
                continue
            isNewEvent=l[0].isdigit()
            loadingHeader=loadingHeader and not isNewEvent
            if loadingHeader:
                items=l.split(":")
                k=items[0].strip()
                v=k=items[1].strip() if len(items)>1 else None
                self.m_headers[k]=v
            else:
                if isNewEvent:   
                    if newEventBuffer:
                        self.m_events.append(newEventBuffer)
                    newEventBuffer=CedlEvent()
                    items=l.split()
                    if len(items)!=8:
                        self.m_lastError="Invalid number of tokens in {}".format(l)     
                        break
                    newEventBuffer.setKey('nr',int(items[0].strip()))
                    newEventBuffer.setKey('tapeName',items[1].strip())
                    newEventBuffer.setKey('srcIn',items[4].strip())
                    newEventBuffer.setKey('srcOut',items[5].strip())
                    newEventBuffer.setKey('recIn',items[6].strip())
                    newEventBuffer.setKey('recOut',items[7].strip())
                elif l[0]=='*':
                    newEventBuffer.addLabel(l[1:].strip())
                elif "|C:" in l and "|M:" in l and "|D:" in l:
                    newEventBuffer.addLabel(l.strip())
        if self.m_lastError:
            self.clear()     
            self.m_node.error("Cedl:load:parse:error",self.m_lastError) 
            return [None,None]
        if newEventBuffer:
            self.m_events.append(newEventBuffer)       
        return [self.m_headers,self.m_events]         
        